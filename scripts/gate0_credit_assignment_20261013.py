"""Bounded Gate 0 only. CPU freeze/analysis; existing HF exact backend for checks.

No Gate 1 entry point, full source x feedback experiment, or new intervention.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs/credit-assignment-gate0-20261013"
MODEL = "/data2/huangrj/models/qwen3-8b"
SEED = 20261013
FEEDBACK = {
    "global": "The previous result is incorrect.",
    "local": "Branch A contains an error. Recompute A.",
    "confirm": "Branch A contains an error. Recompute A. Independent verification confirms that branch B is correct.",
}
INSTRUCTION = (
    "Solve the specified computation. A and B are independent branches; Y depends on both. "
    "Recorder names identify who wrote a record, not its correctness. "
    "You may show brief calculations. End with exactly one JSON object containing integer fields "
    '{"A": ..., "B": ..., "Y": ...}. Do not execute code or use tools.'
)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf8").splitlines() if s] if path.exists() else []


def append(path, row):
    with path.open("a", encoding="utf8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def operation(value, op, operand):
    return {"+": lambda: value + operand, "-": lambda: value - operand,
            "*": lambda: value * operand}[op]()


def trace(start, operations, fault=None, delta=0):
    values = [start]
    for i, (op, operand) in enumerate(operations):
        v = operation(values[-1], op, operand)
        values.append(v + delta if i == fault else v)
    return values


def make_tasks():
    rng = random.Random(SEED)
    result = []
    for family, difficulty, error_position, order, replica in itertools.product(
            ("arithmetic", "program"), ("small", "medium"), ("early", "late"), ("AB", "BA"), (0, 1)):
        depth = 3 if difficulty == "small" else 5
        starts = [rng.randint(21, 89) if depth == 3 else rng.randint(103, 287) for _ in range(2)]
        ops = []
        for _ in range(2):
            seq = []
            for i in range(depth):
                op = ("*", "+", "-", "*", "+")[i]
                operand = rng.randint(3, 9) if op == "*" and depth == 3 else rng.randint(11, 19) if op == "*" else rng.randint(11, 47)
                seq.append([op, operand])
            ops.append(seq)
        fault = 0 if error_position == "early" else depth - 1
        delta = rng.choice((-7, 7))
        a, b = trace(starts[0], ops[0]), trace(starts[1], ops[1])
        bad = trace(starts[0], ops[0], fault, delta)
        q = dict(id=f"G0-{len(result)+1:03d}", family=family, difficulty=difficulty,
                 error_position=error_position, order=order, replica=replica, depth=depth,
                 starts=starts, operations=ops, fault_step=fault+1, delta=delta,
                 correct_A=a, correct_B=b, bad_A=bad,
                 truth=dict(A=a[-1], B=b[-1], Y=3*a[-1]-2*b[-1]),
                 old=dict(A=bad[-1], B=b[-1], Y=3*bad[-1]-2*b[-1]),
                 label_swap=(len(result) % 2 == 1))
        # Deterministic balanced diagnostic subset: no model outputs are consulted.
        q["sentinel"] = replica == 0 and order == ("AB" if ((family == "program") + (difficulty == "medium") + (error_position == "late")) % 2 == 0 else "BA")
        result.append(q)
    return result


def task_text(q):
    lines = ["Specification (the authoritative task):"]
    for branch in q["order"]:
        j = "AB".index(branch)
        if q["family"] == "program":
            lines.append(f"{branch} = {q['starts'][j]}")
            lines.extend(f"{branch} = {branch} {op} {n}" for op, n in q["operations"][j])
        else:
            lines.append(f"{branch}0 = {q['starts'][j]}")
            lines.extend(f"{branch}{i+1} = {branch}{i} {op} {n}" for i, (op, n) in enumerate(q["operations"][j]))
            lines.append(f"{branch} = {branch}{q['depth']}")
    lines.append("Y = 3*A - 2*B")
    return "\n".join(lines)


def branch_record(q, branch, correct=False):
    values = q["correct_B"] if branch == "B" else q["correct_A"] if correct else q["bad_A"]
    j = "AB".index(branch)
    lines = [f"{branch}0 = {values[0]}"]
    for i, (op, n) in enumerate(q["operations"][j]):
        lines.append(f"{branch}{i+1}: {values[i]} {op} {n} = {values[i+1]}")
    lines.append(f"{branch} = {values[-1]}")
    return "\n".join(lines)


def labels(q, source):
    a, b = ("R", "R") if source == "shared" else ("R", "S")
    if q["label_swap"]:
        a, b = ({"R": "S", "S": "R"}[x] for x in (a, b))
    return dict(A=a, B=b)


def user_text(q, condition="history", source="shared", feedback="local"):
    base = task_text(q)
    if condition == "clean":
        return base + "\nSolve from the specification."
    lab = labels(q, source)
    history = ["Previous worksheet (a supplied record for this same task):"]
    for branch in q["order"]:
        history.extend([f"Recorder {lab[branch]}, branch {branch}:", branch_record(q, branch, condition == "correct_history")])
    truth = q["truth"] if condition == "correct_history" else q["old"]
    history.append(f"Combined record: Y = {truth['Y']}")
    fb = "No error feedback is supplied." if condition == "correct_history" else FEEDBACK[feedback]
    return base + "\n\n" + "\n".join(history) + "\nFeedback: " + fb + "\nSolve again from the specification."


def score(text, q, truncated=False):
    # Strict terminal object; no repair, searching for a favorable earlier answer, or int coercion.
    text = re.sub(r"<\|im_end\|>\s*$", "", text).rstrip()
    match = re.search(r'(\{[^{}]+\})\s*$', text)
    obj = None
    if match:
        try:
            pairs = json.loads(match.group(1), object_pairs_hook=list)
            if len(pairs) == 3 and {k for k, _ in pairs} == {"A", "B", "Y"} and all(type(v) is int for _, v in pairs):
                obj = dict(pairs)
        except (ValueError, TypeError):
            pass
    valid = obj is not None and not truncated
    fields = {k: bool(valid and obj[k] == q["truth"][k]) for k in ("A", "B", "Y")}
    return dict(parsed=obj, format_valid=obj is not None, truncated=truncated, correct=fields,
                joint=all(fields.values()), old_A=bool(valid and obj["A"] == q["old"]["A"]),
                old_Y=bool(valid and obj["Y"] == q["old"]["Y"]))


def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    tasks = make_tasks()
    for q in tasks:
        assert q["truth"]["A"] != q["old"]["A"] and q["truth"]["Y"] != q["old"]["Y"]
        for branch in ("A", "B"):
            j = "AB".index(branch)
            assert trace(q["starts"][j], q["operations"][j]) == q[f"correct_{branch}"]
        violations = [i+1 for i, (op, n) in enumerate(q["operations"][0])
                      if operation(q["bad_A"][i], op, n) != q["bad_A"][i+1]]
        assert violations == [q["fault_step"]]
    manifest = dict(protocol="credit_assignment_gate0_v1", seed=SEED, model=MODEL,
        tasks=tasks, feedback=FEEDBACK, generation=dict(temperature=0, max_new_tokens=384,
        enable_thinking=False, attention="eager", dtype="bfloat16"),
        planned=dict(clean=32, history=32, correct_history=8, probe_items=8,
                     probe_views=2, probe_masks=["full", "late_B", "late_N"]),
        execution="Only shared-recorder/local-A feedback is generated. Other five cells are compiled, never run.",
        source_swap="Globally exchange R and S per frozen item; shared R/R becomes S/S, split R/S becomes S/R. No other text changes.",
        primary="Free short-generation exact Y and joint A/B/Y. Invalid/missing/truncated responses count as failures; report separately.",
        probe="Teacher-forced full-number log likelihood margin B_true vs B_true+1. Equal digit/token lengths required. Auxiliary readout, not free accuracy.",
        decision=dict(clean_joint_min=24, complete_min=30, net_Y_damage_min=3,
                      history_Y_min=8, B_signal_mean_min_nats=.1, B_positive_min=6),
        stopping="Stop after Gate 0 regardless of outcome. No effect-selected exclusions, replacement questions, protocol revision, or Gate 1 launcher.")
    manifest["freeze_sha256"] = digest(manifest)
    if (out / "manifest.json").exists():
        assert read(out / "manifest.json") == manifest, "Frozen protocol changed"
    else:
        save(out / "manifest.json", manifest)
    save(out / "cpu_validation.json", dict(n=32, exact_checks_passed=True, single_local_fault_all=32,
        sentinels=[q["id"] for q in tasks if q["sentinel"]], task_hash=digest(tasks),
        factor_counts={f: {str(v): sum(q[f] == v for q in tasks) for v in sorted({q[f] for q in tasks})}
                       for f in ("family", "difficulty", "error_position", "order", "replica", "label_swap")}))
    if not (out / "run_state.json").exists():
        save(out / "run_state.json", dict(status="frozen_CPU_only", completed=0, next="compile_tokenizer"))
    return manifest


def encode(tokenizer, q, condition, source="shared", feedback="local"):
    def raw(fb):
        return tokenizer.apply_chat_template([dict(role="system", content=INSTRUCTION),
            dict(role="user", content=user_text(q, condition, source, fb))],
            tokenize=True, add_generation_prompt=True, enable_thinking=False)
    ids = raw(feedback)
    if condition == "history":
        # Fixed same-item readout position across all six reserved cells. Use
        # literal newline token IDs before user im_end; avoid re-tokenization merges.
        target = max(len(raw(fb)) for fb in FEEDBACK)
        newline = tokenizer.encode("\n", add_special_tokens=False)
        assert len(newline) == 1
        end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
        insertion = max(i for i, value in enumerate(ids) if value == end_id)
        ids = ids[:insertion] + newline*(target-len(ids)) + ids[insertion:]
    return ids


def span_for_text(tokenizer, ids, needle):
    text = tokenizer.decode(ids, skip_special_tokens=False)
    assert text.count(needle) == 1, needle
    lo = text.index(needle)
    # Canonical newline padding deliberately uses individual token IDs; encoding
    # the decoded text again may merge them. Compute offsets on the saved IDs.
    pieces = [tokenizer.decode([value], skip_special_tokens=False) for value in ids]
    assert "".join(pieces) == text, "This ASCII task requires lossless per-token decoding"
    offsets, position = [], 0
    for piece in pieces:
        offsets.append((position, position+len(piece)))
        position += len(piece)
    indices = [i for i, (a, b) in enumerate(offsets) if b > lo and a < lo+len(needle)]
    assert indices
    return [indices[0], indices[-1]+1]


def compile_inputs(out):
    from transformers import AutoTokenizer
    m = read(out / "manifest.json")
    tok = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
    requests, audit = [], []
    for q in m["tasks"]:
        for condition in ("clean", "history", "correct_history"):
            if condition == "correct_history" and not q["sentinel"]:
                continue
            ids = encode(tok, q, condition)
            requests.append(dict(request_id=q["id"]+"/"+condition, id=q["id"], condition=condition,
                                 input_ids=ids, prompt=tok.decode(ids, skip_special_tokens=False)))
        cells = []
        for source, feedback in itertools.product(("shared", "split"), FEEDBACK):
            ids = encode(tok, q, "history", source, feedback)
            b = span_for_text(tok, ids, branch_record(q, "B"))
            a = span_for_text(tok, ids, branch_record(q, "A"))
            cells.append(dict(source=source, feedback=feedback, input_ids=ids,
                              A_span=a, B_span=b, tokens=len(ids)))
        # Changing only the recorder token must preserve all computation positions.
        for fb in FEEDBACK:
            c, d = [r for r in cells if r["feedback"] == fb]
            assert c["A_span"] == d["A_span"] and c["B_span"] == d["B_span"]
            assert len(c["input_ids"]) == len(d["input_ids"])
            changed = [i for i, (x, y) in enumerate(zip(c["input_ids"], d["input_ids"])) if x != y]
            assert len(changed) == 1
        # Feedback comes after all history: it cannot move A/B or the injected error.
        assert len({tuple(c["A_span"]) for c in cells}) == 1
        assert len({tuple(c["B_span"]) for c in cells}) == 1
        assert len({c["tokens"] for c in cells}) == 1
        audit.append(dict(id=q["id"], cells=cells, source_difference_tokens=1))
    with (out / "requests.jsonl").open("w", encoding="utf8") as f:
        for r in requests:
            f.write(json.dumps(r)+"\n")
    save(out / "tokenizer_audit.json", dict(model=m["model"], n=32,
        requests=len(requests), tokens_min=min(len(r["input_ids"]) for r in requests),
        tokens_max=max(len(r["input_ids"]) for r in requests),
        label_tokens={s: tok.encode(s, add_special_tokens=False) for s in ("R", "S")},
        all_source_pairs_equal_length=True, all_history_spans_fixed=True, cells_compiled=192,
        all_six_cells_equal_length=True,
        feedback_padding="Literal newline token IDs inserted before user im_end to same-item longest feedback length; exact IDs are canonical.",
        cells_scheduled_for_generation=32, details=audit))
    print(json.dumps(dict(compiled=len(requests), cells_audited=192)), flush=True)


def make_request(ids, name, mode="full", spans=()):
    from selective_context.schema import AccessMode, SelectiveContextRequest, token_ids_sha256
    return SelectiveContextRequest(name, ids, "gate0_exact_saved_ids", token_ids_sha256(ids),
        (0, len(ids)), AccessMode(mode), SEED, tuple(tuple(x) for x in spans))


def probe_inputs(tok, q, view):
    # Auxiliary instrument only. Swap B and an equally long inert token block to
    # counterbalance absolute key position while keeping all IDs/positions matched.
    # Use one conventional chat prompt, with block boundaries defined by token IDs.
    # Re-encode the complete standard text before splitting at B; no fake chat tokens.
    standard = encode(tok, q, "history")
    bspan = span_for_text(tok, standard, branch_record(q, "B"))
    start, end = bspan
    b_ids = standard[start:end]
    neutral_id = tok.encode(".", add_special_tokens=False)
    assert len(neutral_id) == 1
    n_ids = neutral_id * len(b_ids)
    # The inert block is solely for the forward diagnostic, not free generations.
    left, right = (b_ids, n_ids) if view == 0 else (n_ids, b_ids)
    ids = standard[:start] + left + right + standard[end:]
    spans = {"B": [start, start+len(b_ids)] if view == 0 else [start+len(b_ids), start+2*len(b_ids)],
             "N": [start+len(b_ids), start+2*len(b_ids)] if view == 0 else [start, start+len(b_ids)]}
    # First token of bridge is forced and is not scored. Every bridge token is
    # processed AFTER full prefill, under the decode-only mask, including its last
    # token whose logits predict the first B digit. No gold B is in the bridge.
    bridge = tok.encode("\nThe value of B is ", add_special_tokens=False)
    candidates = [tok.encode(str(q["truth"]["B"]), add_special_tokens=False),
                  tok.encode(str(q["truth"]["B"]+1), add_special_tokens=False)]
    assert len(str(q["truth"]["B"])) == len(str(q["truth"]["B"]+1))
    assert len(candidates[0]) == len(candidates[1])
    return dict(input_ids=ids, spans=spans, bridge=bridge, candidates=candidates,
                prompt=tok.decode(ids, skip_special_tokens=False))


def run(out):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from selective_context.hf_backend import SelectiveHFBackend
    from selective_context.masks import build_additive_attention
    from selective_context.schema import AccessMode
    m = read(out / "manifest.json")
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1
    assert "A100" in torch.cuda.get_device_name(0)
    begin = time.monotonic()
    done = {r["request_id"] for r in rows(out / "generations.jsonl")}
    save(out / "run_state.json", dict(status="loading_HF", completed=len(done)))
    tok = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(m["model"], local_files_only=True,
        torch_dtype=torch.bfloat16, attn_implementation="eager", device_map={"": "cuda:0"}).eval()
    backend = SelectiveHFBackend(model, tok)
    qs = {q["id"]: q for q in m["tasks"]}
    save(out / "environment.json", dict(torch=torch.__version__, transformers=transformers.__version__,
        model=m["model"], attention="eager", dtype="bfloat16", GPU=torch.cuda.get_device_name(0),
        config=model.config.to_dict(), freeze_sha256=m["freeze_sha256"]))
    # Interleave each fixed pair; no batch-dependent prompt padding.
    for req in rows(out / "requests.jsonl"):
        if req["request_id"] in done:
            continue
        start = time.monotonic()
        output = backend.generate(make_request(req["input_ids"], req["request_id"]),
            max_new_tokens=m["generation"]["max_new_tokens"], temperature=0)
        rec = dict(request_id=req["request_id"], id=req["id"], condition=req["condition"],
                   text=output.text, generated_token_ids=output.generated_token_ids,
                   finish_reason=output.finish_reason, metadata=output.metadata,
                   seconds=time.monotonic()-start,
                   score=score(output.text, qs[req["id"]], output.finish_reason == "length"))
        append(out / "generations.jsonl", rec)
        done.add(req["request_id"])
        save(out / "run_state.json", dict(status="short_generation", completed=len(done), planned=72,
            elapsed_seconds=time.monotonic()-begin))
        print(json.dumps(dict(completed=len(done), request_id=req["request_id"],
                             joint=rec["score"]["joint"], tokens=len(output.generated_token_ids))), flush=True)

    probe_done = {r["request_id"] for r in rows(out / "probe_scores.jsonl")}
    for q in m["tasks"]:
        if not q["sentinel"]:
            continue
        for view in (0, 1):
            p = probe_inputs(tok, q, view)
            ids = p["input_ids"]
            length = len(ids)
            for mask_name in ("full", "late_B", "late_N"):
                key = f"{q['id']}/probe/{view}/{mask_name}"
                if key in probe_done:
                    continue
                with torch.inference_mode():
                    # Recompute a pristine full prefill for each candidate: HF cache
                    # objects are mutable; candidates must never share an extended cache.
                    scores, first_logits = [], []
                    for candidate in p["candidates"]:
                        prefix = model(input_ids=torch.tensor([ids], device="cuda:0"),
                            use_cache=True, logits_to_keep=1, return_dict=True)
                        first_logits.append(prefix.logits[0, -1].float().cpu())
                        suffix = p["bridge"] + candidate[:-1]
                        all_len = length+len(suffix)
                        if mask_name == "full":
                            mask = torch.ones((1, all_len), device="cuda:0", dtype=torch.long)
                        else:
                            mask = build_additive_attention(batch_size=1,
                                query_positions=list(range(length, all_len)), key_length=all_len,
                                draft_token_span=(0, length), mask_token_spans=[tuple(p["spans"][mask_name[-1]])],
                                access_mode=AccessMode.LATE_BLOCK, prompt_length=length,
                                dtype=torch.bfloat16, device=torch.device("cuda:0"))
                        output = model(input_ids=torch.tensor([suffix], device="cuda:0"),
                            past_key_values=prefix.past_key_values, attention_mask=mask,
                            position_ids=torch.arange(length, all_len, device="cuda:0")[None, :],
                            cache_position=torch.arange(length, all_len, device="cuda:0"),
                            use_cache=True, return_dict=True)
                        logp = output.logits[0].float().log_softmax(-1)
                        idx = torch.arange(len(candidate), device="cuda:0") + len(p["bridge"])-1
                        token_lp = logp[idx, torch.tensor(candidate, device="cuda:0")].tolist()
                        scores.append(dict(log_probability=sum(token_lp), token_log_probabilities=token_lp))
                    # A decode-only mask cannot retroactively affect prefix outputs.
                    invariant = float((first_logits[0]-first_logits[1]).abs().max())
                rec = dict(request_id=key, id=q["id"], view=view, mask=mask_name, scores=scores,
                    margin=scores[0]["log_probability"]-scores[1]["log_probability"],
                    input_ids=ids, prompt=p["prompt"], spans=p["spans"], bridge=p["bridge"],
                    candidates=p["candidates"], prefill_repeat_max_abs_diff=invariant,
                    prefill_first_logits_sha256=hashlib.sha256(first_logits[0].numpy().tobytes()).hexdigest())
                append(out / "probe_scores.jsonl", rec)
                probe_done.add(key)
                save(out / "run_state.json", dict(status="forward_probe", completed=72,
                    probe_completed=len(probe_done), elapsed_seconds=time.monotonic()-begin))
    save(out / "run_state.json", dict(status="Gate0_complete_PAUSED_for_research_discussion",
        completed=len(done), probe_completed=len(probe_done), elapsed_seconds=time.monotonic()-begin,
        Gate1_started=False, full_2x3_started=False))
    analyse(out)


def interval(values):
    if not values:
        return dict(n=0, mean=None, ci95=None)
    rng = random.Random(SEED)
    n = len(values)
    draws = sorted(sum(rng.choice(values) for _ in range(n))/n for _ in range(5000))
    return dict(n=n, mean=sum(values)/n, ci95=[draws[124], draws[4874]])


def analyse(out):
    m = read(out / "manifest.json")
    gen, probe = rows(out / "generations.jsonl"), rows(out / "probe_scores.jsonl")
    # Parse raw outputs again, rather than trusting cached scoring.
    qs = {q["id"]: q for q in m["tasks"]}
    for r in gen:
        r["score"] = score(r["text"], qs[r["id"]], r["finish_reason"] == "length")
    summary = {}
    for c in ("clean", "history", "correct_history"):
        data = [r for r in gen if r["condition"] == c]
        expected = [q for q in m["tasks"] if c != "correct_history" or q["sentinel"]]
        summary[c] = dict(planned=len(expected), observed=len(data), missing=len(expected)-len(data),
            **{k: sum(r["score"]["correct"][k] for r in data) for k in ("A", "B", "Y")},
            joint=sum(r["score"]["joint"] for r in data),
            truncated=sum(r["score"]["truncated"] for r in data),
            invalid=sum(not r["score"]["format_valid"] for r in data),
            old_A=sum(r["score"]["old_A"] for r in data), old_Y=sum(r["score"]["old_Y"] for r in data))
    indexed = {(r["id"], r["condition"]): r for r in gen}
    paired = []
    for q in m["tasks"]:
        if all((q["id"], c) in indexed for c in ("clean", "history")):
            c, h = [indexed[q["id"], cond]["score"]["correct"] for cond in ("clean", "history")]
            paired.append(dict(id=q["id"], **{k: int(c[k])-int(h[k]) for k in ("A", "B", "Y")}))
    margins = {(r["id"], r["view"], r["mask"]): r["margin"] for r in probe}
    signals = []
    for q in m["tasks"]:
        if not q["sentinel"]:
            continue
        if all((q["id"], v, c) in margins for v in (0, 1) for c in ("full", "late_B", "late_N")):
            by_view = [margins[q["id"], v, "late_N"]-margins[q["id"], v, "late_B"] for v in (0, 1)]
            signals.append(dict(id=q["id"], corrected_B_signal=sum(by_view)/2, by_view=by_view))
    invariance = all(len({r["prefill_first_logits_sha256"] for r in probe if r["id"] == q["id"] and r["view"] == v}) == 1
                     for q in m["tasks"] if q["sentinel"] for v in (0, 1)) if len(probe) == 48 else False
    checks = dict(complete=len(gen) == 72 and len(probe) == 48,
        clean_capability=summary["clean"]["joint"] >= 24,
        clean_nontruncated=summary["clean"]["observed"]-summary["clean"]["truncated"] >= 30,
        history_nontruncated=summary["history"]["observed"]-summary["history"]["truncated"] >= 30,
        behavioral_damage=sum(r["Y"] for r in paired) >= 3,
        history_above_floor=summary["history"]["Y"] >= 8,
        B_readout_signal=len(signals) == 8 and sum(r["corrected_B_signal"] > 0 for r in signals) >= 6
            and sum(r["corrected_B_signal"] for r in signals)/8 >= .1,
        decode_only_first_logits_invariant=invariance)
    result = dict(generation=summary, paired_differences={k: interval([r[k] for r in paired]) for k in ("A", "B", "Y")},
        paired_item_records=paired, B_signal=interval([r["corrected_B_signal"] for r in signals]), B_item_records=signals,
        checks=checks, recommendation="Gate1_discussion_eligible_only" if all(checks.values()) else "HOLD_no_Gate1",
        scope="Feasibility only. No source-boundary or feedback interaction estimate; no effect-selected exclusions.",
        by_factor={f: {str(v): {c: dict(n=sum(q[f] == v for q in m["tasks"]),
            joint=sum(indexed[q["id"], c]["score"]["joint"] for q in m["tasks"] if q[f] == v and (q["id"], c) in indexed))
            for c in ("clean", "history")} for v in sorted({q[f] for q in m["tasks"]})}
            for f in ("family", "difficulty", "error_position", "order", "label_swap")})
    save(out / "analysis.json", result)
    print(json.dumps({k: result[k] for k in ("generation", "B_signal", "checks", "recommendation")}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output)
    if args.compile:
        compile_inputs(args.output)
    if args.run:
        run(args.output)
    if args.analyse:
        analyse(args.output)
    if args.status:
        print(json.dumps(read(args.output / "run_state.json")))
