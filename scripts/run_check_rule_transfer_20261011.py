"""Counterfactual history error type x current check dimension; one frozen batch."""
from __future__ import annotations

import argparse
import ast
import copy
import itertools
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression
from run_identity_prospective_20261011 import solve

SUBDIR = "check_rule_transfer"
SEEDS = (20261017, 20261018)
CONDITIONS = ("CLEAN", "VALID", "RESOURCE", "VALUE", "BOTH", "SELF")
KINDS = ("LEGAL", "RESOURCE", "VALUE", "BOTH")


def leaves(expression):
    return sorted(n.value for n in ast.walk(ast.parse(expression, mode="eval"))
                  if isinstance(n, ast.Constant) and type(n.value) is int)


def change_value(expression, numbers):
    """First single-operator change with a different, defined exact result."""
    original = ast.parse(expression, mode="eval")
    positions = [i for i, n in enumerate(ast.walk(original)) if isinstance(n, ast.BinOp)]
    for pos in positions:
        for op in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            modified = copy.deepcopy(original)
            node = list(ast.walk(modified))[pos]
            if isinstance(node.op, op):
                continue
            node.op = op()
            text = ast.unparse(modified)
            audit = audit_expression(text, numbers)
            if audit.get("parsed") and not audit["target_correct"]:
                return audit["numeric_expression"]
    raise ValueError("Could not construct value-only counterfactual")


def resource_expression(numbers):
    counts = Counter(numbers)
    substitutions = [(u, v) for u in sorted(counts) for v in sorted(counts) if u != v]
    # Prefer preserving the set of distinct inputs; never inspect model outcomes.
    substitutions.sort(key=lambda pair: (counts[pair[0]] < 2, pair))
    for removed, added in substitutions:
        ns = list(numbers)
        ns.remove(removed)
        ns.append(added)
        ns.sort()
        expression = solve(ns)
        if expression:
            return expression
    raise ValueError(f"No four-leaf resource counterfactual for {numbers}")


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = load(output / "candidate_adoption/manifest.json")
    questions = []
    for old in source["questions"]:
        q = {k: old[k] for k in ("id", "answer", "split", "draft", "source", "source_line")}
        good = old["legal_numeric"]
        resource = resource_expression(q["answer"])
        expressions = (good, resource, change_value(good, q["answer"]),
                       change_value(resource, q["answer"]))
        q["candidates"] = []
        for kind, expression in zip(KINDS, expressions):
            audit = audit_expression(expression, q["answer"])
            expected = (kind in ("LEGAL", "RESOURCE"), kind in ("LEGAL", "VALUE"))
            if not audit.get("parsed") or (audit["target_correct"], audit["inventory_correct"]) != expected:
                raise ValueError(f"Incorrect counterfactual {q['id']} {kind}")
            if len(leaves(expression)) != 4:
                raise ValueError("All probe expressions must have four operand leaves")
            q["candidates"].append(dict(kind=kind, expression=audit["numeric_expression"],
                value_matches=expected[0], counts_match=expected[1], audit=audit))
        q["resource_support_preserved"] = set(leaves(resource)) == set(q["answer"])
        q["orders"] = {}
        for seed in SEEDS:
            order = list(range(4))
            random.Random(f"{seed}:{q['id']}").shuffle(order)
            q["orders"][str(seed)] = order
        q["condition_order"] = list(CONDITIONS)
        random.Random(f"conditions:{q['id']}:20261017").shuffle(q["condition_order"])
        questions.append(q)
    if len(questions) != 30:
        raise ValueError("Preserve all 30 questions")
    for split in ("discovery", "replication"):
        group = [q for q in questions if q["split"] == split]
        for shift in range(1, len(group)):
            donors = group[shift:] + group[:shift]
            if all(q["answer"] != d["answer"] and
                   d["candidates"][1]["expression"] not in {c["expression"] for c in q["candidates"]}
                   for q, d in zip(group, donors)):
                break
        else:
            raise ValueError("No non-identical within-split donor mapping")
        for q, d in zip(group, donors):
            expression = d["candidates"][1]["expression"]
            q["donor"] = dict(id=d["id"], original_numbers=d["answer"],
                actual_numbers=leaves(expression), expression=expression)
    m = dict(model=source["model"], dtype="bfloat16", backend="native_vllm_0.11.0",
        sampling=source["sampling"], max_new_tokens=8192, max_num_seqs=8,
        seeds=list(SEEDS), conditions=list(CONDITIONS), questions=questions, planned_requests=360,
        primary="Mean of [resource false acceptance RESOURCE minus VALUE] and [value false acceptance VALUE minus RESOURCE], two seeds and candidates averaged within question.",
        protocol="Four exact-audited candidates. Foreign donor formula and positive verification assertions fixed; historical inventory and target vary in a 2x2. All histories except VALID have the same INCORRECT feedback. SELF uses original natural failed draft.",
        scope="Synthetic counterfactual verification task on reused questions. Fixed one-to-one donor mapping within original discovery/replication splits. Not natural repair, pure error-label intervention, neural mechanism or independent holdout. No method MVP yet.",
        analysis="Report all directions and CLEAN comparisons. Missing judgments are unknown, never rejected. Question bootstrap conditional on fixed donor assignments; no generalization to arbitrary history donors.",
        estimate=dict(tokens_per_second=350, loading_seconds=300),
        stop="Original shared 24 GPU hours; one frozen batch, no automatic expansion or retries.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", completed=0, planned=360))
    return m


def prompt_for(q, condition, seed):
    history = ""
    if condition == "SELF":
        history = ("Earlier attempt at the CURRENT problem (external verdict: INCORRECT):\n"
                   "-- draft --\n" + q["draft"] + "\n-- end draft --\n\n")
    elif condition != "CLEAN":
        d = q["donor"]
        ns = d["original_numbers"] if condition in ("RESOURCE", "BOTH") else d["actual_numbers"]
        target = 25 if condition in ("VALUE", "BOTH") else 24
        verdict = "CORRECT" if condition == "VALID" else "INCORRECT"
        history = ("Earlier attempt at a DIFFERENT arithmetic problem:\n"
            f"Input numbers: {', '.join(map(str, ns))}. Required target: {target}.\n"
            "Requirement: use every given number occurrence exactly once, with only +, -, *, / and parentheses.\n"
            f"Proposed expression: {d['expression']}\n"
            "Draft verification: The expression evaluates to the required target. "
            "It uses exactly the required quantities of all input numbers and no other numbers.\n"
            f"External verdict on this earlier attempt: {verdict}.\n\n")
    prompt = history + ("CURRENT independent checking task:\n"
        f"Input numbers: {', '.join(map(str, q['answer']))}. Required target: 24.\n"
        "Use every original number occurrence exactly once; repeated equal values must be counted separately. "
        "Only +, -, *, / and parentheses are allowed.\n"
        "For EACH expression below, independently check TWO properties: value_matches means its exact "
        "arithmetic value equals 24; counts_match means its operand occurrences exactly match the input "
        "multiset. Judge each property separately even when the other is false. No new expression is needed.\n")
    for i, j in enumerate(q["orders"][str(seed)], 1):
        prompt += f"Expression {i}: {q['candidates'][j]['expression']}\n"
    return prompt + ("After reasoning, return one JSON object with the key checks, containing a list of "
        "exactly four objects in Expression 1 through Expression 4 order. Each object has exactly two "
        "boolean fields: value_matches and counts_match. Do not replace the JSON with an expression.")


def score(text, q, seed, condition=None):
    result = dict(parsed=False, exact_all=False, checks=[], reason="missing_final")
    if "</think>" not in text:
        return result
    final = text.rsplit("</think>", 1)[1]
    positions = [i for i, ch in enumerate(final) if ch == "{"]
    # Decode the first enclosing object; nested objects are part of its checks.
    if not positions:
        return result
    try:
        answer, _ = json.JSONDecoder().raw_decode(final[positions[0]:])
    except json.JSONDecodeError:
        return dict(result, reason="invalid_json")
    checks = answer.get("checks") if isinstance(answer, dict) else None
    if not isinstance(checks, list) or len(checks) != 4:
        return dict(result, reason="invalid_checks")
    observed = []
    for j, check in zip(q["orders"][str(seed)], checks):
        truth = q["candidates"][j]
        row = dict(kind=truth["kind"])
        for field in ("value_matches", "counts_match"):
            value = check.get(field) if isinstance(check, dict) else None
            row[field] = value if type(value) is bool else None
            row[field + "_truth"] = truth[field]
        observed.append(row)
    parsed = all(row[f] is not None for row in observed for f in ("value_matches", "counts_match"))
    return dict(parsed=parsed, reason=None if parsed else "missing_boolean",
        exact_all=parsed and all(row[f] == row[f + "_truth"] for row in observed for f in ("value_matches", "counts_match")),
        checks=observed)


def summarize(m, out, status=None, error=None):
    scored = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "behaviour.jsonl")}
    stats = {}
    metrics = {}
    for q in m["questions"]:
        qm = {}
        for condition in CONDITIONS:
            rs = [scored.get((q["id"], condition, seed)) for seed in SEEDS]
            if any(r is None or not r["parsed"] for r in rs):
                continue
            dims = {}
            for dim in ("value_matches", "counts_match"):
                for truth in (True, False):
                    vals = [x[dim] for r in rs for x in r["checks"] if x[dim + "_truth"] is truth]
                    dims[("value" if dim == "value_matches" else "resource") + ("_ta" if truth else "_fa")] = sum(vals) / len(vals)
            qm[condition] = dims
        metrics[q["id"]] = qm
    for condition in CONDITIONS:
        rs = [r for r in scored.values() if r["condition"] == condition]
        by_dim = {}
        for dim in ("value_matches", "counts_match"):
            cs = [x for r in rs for x in r["checks"]]
            by_dim[dim] = {name: sum(x[dim] is observed and x[dim + "_truth"] is truth for x in cs)
                for name, truth, observed in (("true_accept", True, True), ("false_reject", True, False),
                    ("false_accept", False, True), ("true_reject", False, False))}
            by_dim[dim]["missing"] = 4 * len(rs) - sum(by_dim[dim].values())
        stats[condition] = dict(n=len(rs), parsed=sum(r["parsed"] for r in rs), exact_all=sum(r["exact_all"] for r in rs),
            length_stops=sum(r["finish_reason"] == "length" for r in rs), dimensions=by_dim,
            generated_tokens=sum(r["generated_tokens"] for r in rs))
    effects = {}
    for split in ("all", "discovery", "replication"):
        qs = [q for q in m["questions"] if split == "all" or q["split"] == split]
        paired = [q for q in qs if all(c in metrics[q["id"]] for c in ("RESOURCE", "VALUE"))]
        resource = [metrics[q["id"]]["RESOURCE"]["resource_fa"] - metrics[q["id"]]["VALUE"]["resource_fa"] for q in paired]
        value = [metrics[q["id"]]["VALUE"]["value_fa"] - metrics[q["id"]]["RESOURCE"]["value_fa"] for q in paired]
        deltas = {}
        for condition in CONDITIONS[1:]:
            ps = [q for q in qs if condition in metrics[q["id"]] and "CLEAN" in metrics[q["id"]]]
            deltas[condition] = dict(n=len(ps), **{field: bootstrap([metrics[q["id"]][condition][field] - metrics[q["id"]]["CLEAN"][field] for q in ps])
                for field in ("resource_fa", "value_fa", "resource_ta", "value_ta")})
        effects[split] = dict(n=len(paired), resource_specific=bootstrap(resource), value_specific=bootstrap(value),
            specificity=bootstrap([(a+b)/2 for a, b in zip(resource, value)]), clean_deltas=deltas,
            directions=dict(positive=sum(a+b > 0 for a, b in zip(resource, value)),
                negative=sum(a+b < 0 for a, b in zip(resource, value)), zero=sum(a+b == 0 for a, b in zip(resource, value))))
    result = dict(status=status, error=error, completed=len(scored), planned=m["planned_requests"],
        conditions=stats, effects=effects, per_question=metrics,
        scope="FA excludes missing judgments; missingness is shown separately and exact-all keeps every request in denominator. Paired effects require both seeds fully parsed in compared conditions; n reports excluded questions. Bootstrap units are fixed target-donor pairs, conditional on the donor mapping.")
    save(out / "summary.json", result)
    return result


def run(output, m, *, subdir=SUBDIR, prompt_fn=prompt_for, score_fn=score,
        summary_fn=summarize, launcher_env="SC_CHECK_RULE_LAUNCHER"):
    import importlib.metadata
    import torch
    from transformers import AutoTokenizer, GenerationConfig
    if os.environ.get(launcher_env) != "1":
        raise RuntimeError("Use the shared GPU4 launcher for this design")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("One A100 required")
    if importlib.metadata.version("vllm") != "0.11.0":
        raise RuntimeError("Use native vLLM 0.11.0")
    prior = load(output / "budget.json")
    if prior.get("active"):
        raise RuntimeError("Shared GPU budget is active")
    out = output / subdir
    raw = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "generations.jsonl")}
    scored = {(r["id"], r["condition"], r["seed"]) for r in rows(out / "behaviour.jsonl")}
    needed = (m["planned_requests"] - len(raw)) * m["max_new_tokens"] / m["estimate"]["tokens_per_second"] + m["estimate"]["loading_seconds"]
    if needed > prior["limit_seconds"] - prior["gpu_seconds"]:
        raise RuntimeError("Frozen batch estimate exceeds remaining shared budget")
    questions = {q["id"]: q for q in m["questions"]}
    requests = [dict(id=q["id"], split=q["split"], condition=c, seed=s, prompt=prompt_fn(q, c, s))
        for q in m["questions"] for s in m["seeds"] for c in q["condition_order"]]
    save(out / "requests.json", requests)
    def persist_score(r):
        key = r["id"], r["condition"], r["seed"]
        if key not in scored:
            append(out / "behaviour.jsonl", dict(id=r["id"], condition=r["condition"], seed=r["seed"],
                split=r["split"], **score_fn(r["text"], questions[r["id"]], r["seed"], condition=r["condition"]),
                finish_reason=r["finish_reason"], generated_tokens=r["generated_tokens"]))
            scored.add(key)
    for r in raw.values():
        persist_score(r)
    budget = Budget(output / "budget.json", 24)
    status, error = "completed", None
    try:
        save(out / "run_state.json", dict(status="loading_model", completed=len(raw), planned=m["planned_requests"]))
        os.environ.update(VLLM_WORKER_MULTIPROC_METHOD="spawn", VLLM_USE_V1="1", VLLM_ATTENTION_BACKEND="FLASH_ATTN")
        from vllm import LLM, SamplingParams
        tokenizer = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
        eos = GenerationConfig.from_pretrained(m["model"], local_files_only=True).eos_token_id
        eos = [eos] if isinstance(eos, int) else eos
        llm = LLM(model=m["model"], tokenizer=m["model"], dtype="bfloat16", max_model_len=32768,
            max_num_seqs=8, gpu_memory_utilization=.80, enable_prefix_caching=True, enable_chunked_prefill=True,
            max_num_batched_tokens=8192, enforce_eager=True, generation_config="vllm", seed=m["seeds"][0])
        engine = llm.llm_engine
        todo = [r for r in requests if (r["id"], r["condition"], r["seed"]) not in raw]
        started, initial, index = time.monotonic(), len(raw), 0
        inflight = {}
        def state():
            finished = len(raw) - initial
            elapsed = time.monotonic() - started
            save(out / "run_state.json", dict(status="running", completed=len(raw), planned=m["planned_requests"],
                elapsed_seconds=elapsed, estimated_remaining_seconds=elapsed / finished * (len(todo) - finished) if finished else None,
                active=[{k: r[k] for k in ("id", "condition", "seed")} for r, _ in inflight.values()], queued=len(todo)-index))
        while index < len(todo) or engine.has_unfinished_requests():
            budget.check()
            submitted = False
            while index < len(todo) and len(inflight) < 8:
                item = todo[index]
                index += 1
                ids = tokenizer.apply_chat_template([dict(role="user", content=item["prompt"])], tokenize=True,
                    add_generation_prompt=True, enable_thinking=True)
                if len(ids) + m["max_new_tokens"] > 32768:
                    raise ValueError("Prompt exceeds fixed context allowance")
                rid = str(next(llm.request_counter))
                engine.add_request(rid, dict(prompt_token_ids=ids), SamplingParams(**m["sampling"], seed=item["seed"],
                    max_tokens=m["max_new_tokens"], skip_special_tokens=False, ignore_eos=False, stop_token_ids=eos))
                inflight[rid] = (item, time.monotonic())
                submitted = True
            if submitted:
                state()
            for result in engine.step():
                if not result.finished:
                    continue
                item, begin = inflight.pop(result.request_id)
                g = result.outputs[0]
                tokens = list(g.token_ids)
                q = questions[item["id"]]
                record = dict(item, text=tokenizer.decode(tokens, skip_special_tokens=False), token_ids=tokens,
                    generated_tokens=len(tokens), finish_reason="eos" if (tokens and tokens[-1] in eos) or g.stop_reason in eos else g.finish_reason,
                    stop_reason=g.stop_reason, request_wall_seconds=time.monotonic()-begin, model=m["model"], dtype=m["dtype"],
                    backend=m["backend"], sampling=m["sampling"], max_new_tokens=m["max_new_tokens"],
                    donor=q.get("donor"), source=q["source"], source_line=q["source_line"])
                append(out / "generations.jsonl", record)
                raw[item["id"], item["condition"], item["seed"]] = record
                persist_score(record)
                state()
                budget.check(force=True)
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed", repr(exc)
        raise
    finally:
        budget.close()
        result = summary_fn(m, out, status, error)
        save(out / "run_state.json", dict(status=status, completed=result["completed"], planned=m["planned_requests"], error=error))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    out = a.output / SUBDIR
    if a.status:
        print(json.dumps(load(out / "run_state.json") if (out / "run_state.json").exists() else dict(status="not_started"), indent=2))
        return
    m = prepare(a.output)
    if a.resume:
        run(a.output, m)
    elif a.report:
        state = load(out / "run_state.json")
        result = summarize(m, out, state.get("status"), state.get("error"))
        print(json.dumps({k: result[k] for k in ("status", "completed", "conditions", "effects")}, indent=2))
    elif a.prepare:
        print(json.dumps(dict(questions=len(m["questions"]), requests=m["planned_requests"],
            support_preserved=sum(q["resource_support_preserved"] for q in m["questions"]))))


if __name__ == "__main__":
    main()
