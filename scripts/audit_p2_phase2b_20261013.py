"""CPU audit of persisted P2 reproducibility, intervention scope and confounds.

No model loads, new generation, intervention development or experiment requests.
Read-only inputs; writes only outputs/p2-audit-phase2b-20261013.
"""
import hashlib
import itertools
import json
import random
import re
import statistics
import sys
import ast
import difflib
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from selective_context.vllm_mask import key_block_onsets, NEVER
from selective_context.schema import token_ids_sha256
from selective_context.tasks import extract_math_box
from run_identity_mvp_20261011 import audit_expression

OUT = ROOT / "outputs/p2-audit-phase2b-20261013"
BASE = "outputs/generation-diagnostics-20261005/"
SOURCES = {
    "main23": ["outputs/game24-dual-anchor-validation-20260918/results.jsonl",
               "runs/game24_batch02_validation_20260921_raw/results.jsonl",
               "runs/game24_batch03_validation_20260925_raw/results.jsonl"],
    "uft20": ["outputs/game24-uft-external-20q-20260919/results.jsonl"],
    "hf_stage_a3": ["outputs/game24-independent-control-20260910/results.jsonl"],
    "hf_stage_b7": [],
    "early_hf_0906": ["outputs/game24-qwen3-8b-thinking-r0-r4-20260906/results.jsonl"],
    "early_hf_0908": ["outputs/game24-qwen3-8b-thinking-fixed-r0-r4-20260908/results.jsonl"],
}


def digest(x):
    return hashlib.sha256(x).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf8")


def source_lines(path):
    for n, line in enumerate((ROOT / path).read_text(encoding="utf8").splitlines(), 1):
        if line.strip():
            yield n, json.loads(line), digest(line.encode("utf8"))


def percentile(xs, p):
    xs = sorted(xs)
    pos = (len(xs)-1)*p
    lo = int(pos)
    return xs[lo] + (xs[min(lo+1, len(xs)-1)]-xs[lo])*(pos-lo)


def mean_ci(vals, seed=20261013):
    rng = random.Random(seed)
    bs = [statistics.mean(rng.choices(vals, k=len(vals))) for _ in range(5000)]
    return dict(estimate=statistics.mean(vals), ci95=[percentile(bs, .025), percentile(bs, .975)],
                method="5000 question-cluster resamples; descriptive; excludes selection and execution uncertainty")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets, records, raws = [], [], {}

    def register(path, role):
        p = ROOT / path
        if not any(x["path"] == path for x in assets):
            assets.append(dict(path=path, role=role, exists=p.exists(),
                bytes=p.stat().st_size if p.exists() else None,
                sha256=digest(p.read_bytes()) if p.exists() else None))

    def add(r, raw):
        assert r["uid"] not in raws
        records.append(r)
        raws[r["uid"]] = raw

    SOURCES["hf_stage_a3"] += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "outputs/game24-independent-stage-a-20260910").glob("seed-*/results.jsonl"))]
    SOURCES["hf_stage_b7"] = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "outputs/game24-stage-b-paired-20260911").glob("seed-*/results.jsonl"))]
    for pool, paths in SOURCES.items():
        for path in paths:
            register(path, "raw_generations")
            config = str(Path(path).parent / "config.json").replace("\\", "/")
            if (ROOT / config).exists():
                register(config, "historical_configuration")
                cfg = json.loads((ROOT / config).read_text(encoding="utf8"))
                assert (cfg["temperature"], cfg["top_p"], cfg["top_k"]) == (.6, .95, 20)
                if "model" in cfg:
                    assert cfg["model"] == "/data2/huangrj/models/qwen3-8b"
            for n, raw, lh in source_lines(path):
                g, = raw["init_response_generations"]
                meta = g["selective_context_metadata"]
                req = meta.get("request") or raw["init_response_generations_metadata"]["intervention"]
                prompt = raw["init_response_prompt"]
                assert digest(prompt.encode("utf8")) == req["prompt_sha256"]
                assert token_ids_sha256(req["input_ids"]) == req["input_ids_sha256"]
                draft = prompt.split("-- beginning of the draft --", 1)[-1].split("-- end of the draft --", 1)[0] if "-- beginning of the draft --" in prompt else ""
                old = extract_math_box(draft) or (draft.strip().splitlines()[-1].split("=")[0].strip() if draft.strip() else None)
                add(dict(pool=pool, id=str(raw["id"]), seed=req["sample_seed"], condition=req["condition_id"],
                    uid=f"{path}:{n}", source=path, line=n, raw_line_sha256=lh,
                    model="/data2/huangrj/models/qwen3-8b", backend=meta["backend"], dtype="bfloat16",
                    sampling=dict(temperature=.6, top_p=.95, top_k=20),
                    max_tokens=raw.get("max_new_tokens", 32768-len(req["input_ids"])),
                    prompt_hash=req["prompt_sha256"], input_hash=req["input_ids_sha256"],
                    mode=req["access_mode"], draft_span=req["draft_token_span"],
                    selected_spans=req.get("mask_token_spans", []), units=req.get("path_block_units", []),
                    prompt_tokens=len(req["input_ids"]), draft_tokens=req["draft_token_span"][1]-req["draft_token_span"][0],
                    suffix_tokens=len(req["input_ids"])-req["draft_token_span"][1],
                    draft_chars=len(draft), old=old, numbers=raw["answer"],
                    correct=g.get("correctness") is True, score_status=g.get("correctness"),
                    final=g.get("extracted_answer"), finish=g.get("finish_reason"),
                    tokens=raw.get("generated_token_ids", []), batch_size=meta.get("batch_size", 1),
                    decode_layout=meta.get("decode_layout", "HF_single_request")), raw)

    for pool in ("identity_mvp", "identity_alias"):
        mp, gp, bp = BASE+pool+"/manifest.json", BASE+pool+"/generations.jsonl", BASE+pool+"/behaviour.jsonl"
        for path, role in [(mp, "historical_configuration"), (gp, "raw_generations"), (bp, "saved_scores"), (BASE+pool+"/runner.log", "historical_execution_log")]:
            register(path, role)
        m = json.loads((ROOT / mp).read_text(encoding="utf8"))
        qs = {q["id"]: q for q in m["questions"]}
        bs = {(r["id"], r["condition"]): r for _, r, _ in source_lines(bp)}
        for n, raw, lh in source_lines(gp):
            q, b = qs[raw["id"]], bs[raw["id"], raw["condition"]]
            context = q["contexts"][raw["condition"]]
            add(dict(pool=pool, id=raw["id"], seed=raw["seed"], condition=raw["condition"],
                uid=f"{gp}:{n}", source=gp, line=n, raw_line_sha256=lh,
                model=raw["model"], backend=raw["backend"], dtype=raw["dtype"], sampling=raw["sampling"],
                max_tokens=raw["max_new_tokens"], prompt_hash=digest(context["text"].encode("utf8")),
                input_hash=token_ids_sha256(context["input_ids"]), mode="full", draft_span=[0, 0], selected_spans=[], units=[],
                prompt_tokens=len(context["input_ids"]), draft_tokens=None, suffix_tokens=None, draft_chars=None,
                old=q.get("old_expression"), numbers=q["answer"], correct=b["correct"], score_status=b.get("correct"),
                final=b.get("extracted_answer"), finish=raw["finish_reason"], tokens=raw["token_ids"],
                batch_size=m["max_num_seqs"], decode_layout="native_dynamic_continuous"), raw)

    groups = defaultdict(list)
    for r in records:
        key = (r["model"], r["backend"], r["dtype"], json.dumps(r["sampling"], sort_keys=True), r["seed"],
               r["prompt_hash"], r["input_hash"], r["mode"], tuple(r["draft_span"]) if r["mode"] != "full" else (),
               tuple(map(tuple, r["selected_spans"])), tuple(map(tuple, r["units"])), r["max_tokens"])
        groups[key].append(r)
    repeats = []
    for rs in groups.values():
        for a, b in itertools.combinations(rs, 2):
            if a["source"] == b["source"]:
                continue
            common = 0
            for x, y in zip(a["tokens"], b["tokens"]):
                if x != y:
                    break
                common += 1
            repeats.append(dict(id=a["id"], left=a["uid"], right=b["uid"], pools=[a["pool"], b["pool"]],
                backend=a["backend"], seed=a["seed"], common_prefix_tokens=common,
                same_output=a["tokens"] == b["tokens"], left_correct=a["correct"], right_correct=b["correct"],
                left_finish=a["finish"], right_finish=b["finish"], left_tokens=len(a["tokens"]), right_tokens=len(b["tokens"]),
                exclusion="Model/backend/recorded settings match; identical historical code, hardware and RNG state are not established."))
    save("same_input_cross_run.json", repeats)

    effects, fluctuations, qrows, mask_contracts, confounds = [], [], [], [], {}
    for pool in ("main23", "uft20", "hf_stage_a3", "hf_stage_b7"):
        rs = [r for r in records if r["pool"] == pool]
        idx = {(r["id"], r["seed"], r["condition"]): r for r in rs}
        qids = sorted({r["id"] for r in rs})
        byq = {}
        paired = []
        for q in qids:
            seeds = sorted({r["seed"] for r in rs if r["id"] == q})
            xs = []
            for seed in seeds:
                a, b = idx[q, seed, "R4"], idx[q, seed, "R3"]
                assert (a["prompt_hash"], a["input_hash"], a["draft_span"], a["max_tokens"]) == (b["prompt_hash"], b["input_hash"], b["draft_span"], b["max_tokens"])
                delta = int(a["correct"])-int(b["correct"])
                p = dict(id=q, seed=seed, R3=b["uid"], R4=a["uid"], delta=delta,
                    R3_correct=b["correct"], R4_correct=a["correct"], R3_finish=b["finish"], R4_finish=a["finish"],
                    R3_tokens=len(b["tokens"]), R4_tokens=len(a["tokens"]),
                    first_sampled_token_same=(a["tokens"][:1] == b["tokens"][:1]),
                    both_eos=(a["finish"] == b["finish"] == "eos"))
                xs.append(p)
                paired.append(p)
                # Exercise the actual metadata-only onset function, never a model.
                n, (lo, hi) = a["prompt_tokens"], a["draft_span"]
                tables = {mode: key_block_onsets(dict(prompt_length=n, draft_span=[lo, hi], spans=a["selected_spans"], units=a["units"], mode=mode)) for mode in ("late_block", "path_block")}
                assert not a["selected_spans"] and not a["units"]
                assert all(tables["late_block"][k] == n and tables["path_block"][k] == hi for k in range(lo, hi))
                assert all(tables["late_block"][k] == tables["path_block"][k] == NEVER for k in range(n) if not lo <= k < hi)
                mask_contracts.append(dict(pool=pool, id=q, seed=seed, prompt_tokens=n, draft_span=[lo, hi],
                    suffix_tokens=n-hi, additionally_blocked_prefill_edges=(hi-lo)*(n-hi),
                    first_prediction_can_differ=(hi<n), same_decode_edge_rule=True,
                    caveat="Static current-code contract, not verification of saved model activations or of the exact historical worker binary."))
            byq[q] = statistics.mean(x["delta"] for x in xs)
            qrows.append(dict(pool=pool, id=q, seed_deltas=[x["delta"] for x in xs],
                both_eos_deltas=[x["delta"] for x in xs if x["both_eos"]], pairs=xs,
                positive=sum(x["delta"] == 1 for x in xs), negative=sum(x["delta"] == -1 for x in xs),
                mean_delta=byq[q]))
        eos_pairs = [x for x in paired if x["both_eos"]]
        effects.append(dict(pool=pool, questions=len(qids), n=len(paired),
            R3_correct=sum(p["R3_correct"] for p in paired), R4_correct=sum(p["R4_correct"] for p in paired),
            gains=sum(p["delta"] == 1 for p in paired), harms=sum(p["delta"] == -1 for p in paired),
            estimate=mean_ci(list(byq.values())),
            both_eos_sensitivity=dict(n=len(eos_pairs), gains=sum(p["delta"] == 1 for p in eos_pairs), harms=sum(p["delta"] == -1 for p in eos_pairs),
                warning="Post-treatment completion-conditioned description, not a replacement causal estimand."), pairs=paired))
        for c in ("R0", "R2", "R3", "R4"):
            flips = []
            for q in qids:
                cs = sorted([r for r in rs if r["id"] == q and r["condition"] == c], key=lambda r: r["seed"])
                allpairs = list(itertools.combinations(cs, 2))
                flips.append(dict(id=q, n_seeds=len(cs), correct=sum(r["correct"] for r in cs),
                    all_seed_pairs=len(allpairs), correctness_disagreements=sum(a["correct"] != b["correct"] for a, b in allpairs),
                    same_prompt_across_seeds=len({r["input_hash"] for r in cs}) == 1,
                    records=[dict(uid=r["uid"], seed=r["seed"], correct=r["correct"], finish=r["finish"]) for r in cs]))
            fluctuations.append(dict(pool=pool, condition=c, questions=len(flips),
                seed_pairs=sum(x["all_seed_pairs"] for x in flips),
                disagreements=sum(x["correctness_disagreements"] for x in flips),
                mean_question_disagreement=statistics.mean(x["correctness_disagreements"]/x["all_seed_pairs"] for x in flips),
                warning="Different seeds: expected sampling variation. All pairwise seed comparisons within a question are dependent.", by_question=flips))
        if pool in ("main23", "uft20"):
            selected = [next(r for r in rs if r["id"] == q and r["condition"] == "R2") for q in qids]
            profiles = []
            for r in selected:
                old = (r["old"] or "").split("=", 1)[0]
                audit = audit_expression(old, r["numbers"])
                typ = "scalar_final_24" if old == "24" else "unparsed" if not audit["parsed"] else ("inventory_only" if audit["target_correct"] and not audit["inventory_correct"] else "target_only" if not audit["target_correct"] and audit["inventory_correct"] else "target_and_inventory" if not audit["target_correct"] and not audit["inventory_correct"] else "legal")
                profiles.append(dict(id=r["id"], uid=r["uid"], old=old, audit=audit, error_type=typ,
                    draft_chars=r["draft_chars"], draft_tokens=r["draft_tokens"], suffix_tokens=r["suffix_tokens"],
                    R0_correct=sum(x["correct"] for x in rs if x["id"] == r["id"] and x["condition"] == "R0"),
                    effect=byq[r["id"]]))
            confounds[pool] = dict(questions=len(qids), error_types=dict(Counter(x["error_type"] for x in profiles)),
                draft_chars=dict(median=statistics.median(x["draft_chars"] for x in profiles), min=min(x["draft_chars"] for x in profiles), max=max(x["draft_chars"] for x in profiles)),
                draft_tokens=dict(median=statistics.median(x["draft_tokens"] for x in profiles), min=min(x["draft_tokens"] for x in profiles), max=max(x["draft_tokens"] for x in profiles)),
                R0_question_correct_counts=dict(Counter(x["R0_correct"] for x in profiles)),
                conditions={c: dict(n=sum(r["condition"] == c for r in rs), correct=sum(r["condition"] == c and r["correct"] for r in rs),
                    finish=dict(Counter(r["finish"] for r in rs if r["condition"] == c))) for c in ("R0", "R2", "R3", "R4")}, profiles=profiles)

    save("paired_effects.json", effects)
    save("within_condition_seed_variation.json", fluctuations)
    save("per_question.json", qrows)
    save("mask_contract.json", mask_contracts)
    save("pool_confounds.json", confounds)

    # Rescore the 32 outputs in strict cross-run matches under one CPU policy.
    # Saved task correctness and letter-format compliance remain separate.
    rescored = []
    for uid in sorted({p[k] for p in repeats for k in ("left", "right")}):
        r = next(r for r in records if r["uid"] == uid)
        m = json.loads((ROOT / (BASE+r["pool"]+"/manifest.json")).read_text(encoding="utf8"))
        q = next(q for q in m["questions"] if q["id"] == r["id"])
        text = raws[uid]["text"]
        expression = extract_math_box(text.rsplit("</think>", 1)[1]) if "</think>" in text else None
        audit = audit_expression(expression, q["answer"], q["bindings"], q.get("binding_counts"), allow_literals=True)
        task = bool(audit.get("target_correct") and audit.get("inventory_correct"))
        rescored.append(dict(uid=uid, final=expression, audit=audit, task_correct=task,
            protocol_correct=bool(audit["correct"]), saved_correct=r["correct"],
            agrees=task == r["correct"], finish=r["finish"],
            raw_stop_reason=raws[uid].get("stop_reason"), last_token=r["tokens"][-1] if r["tokens"] else None))
    assert all(r["agrees"] for r in rescored)
    save("repeat_uniform_rescore.json", rescored)

    strata = {}
    for pool, profile in confounds.items():
        strata[pool] = {}
        pairs = next(e["pairs"] for e in effects if e["pool"] == pool)
        for field in ("error_type", "R0_correct"):
            strata[pool][field] = {}
            for value in sorted({p[field] for p in profile["profiles"]}, key=str):
                ids = {p["id"] for p in profile["profiles"] if p[field] == value}
                ps = [p for p in pairs if p["id"] in ids]
                strata[pool][field][str(value)] = dict(questions=len(ids), n=len(ps),
                    effect=statistics.mean(p["delta"] for p in ps),
                    gains=sum(p["delta"] == 1 for p in ps), harms=sum(p["delta"] == -1 for p in ps),
                    changed=[p for p in ps if p["delta"]])
    save("descriptive_strata.json", dict(strata=strata,
        warning="Post-hoc observed R0 outcomes are not independent ability estimates; no identified causal interaction."))
    rng = random.Random(20261013)
    qm = [q["mean_delta"] for q in qrows if q["pool"] == "main23"]
    qu = [q["mean_delta"] for q in qrows if q["pool"] == "uft20"]
    bs = [statistics.mean(rng.choices(qu, k=len(qu)))-statistics.mean(rng.choices(qm, k=len(qm))) for _ in range(10000)]
    save("cross_pool_description.json", dict(UFT_minus_main_interaction=statistics.mean(qu)-statistics.mean(qm),
        ci95=[percentile(bs, .025), percentile(bs, .975)], draws=10000, seed=20261013,
        note="Descriptive independent-question-pool bootstrap; not causal attribution to length, source or error type. No execution repeats included."))
    draft_sources = {}
    for path in ("outputs/game24-dual-anchor-validation-20260918-prepared/pairs.jsonl",
                 "outputs/game24-batch02-validation-20260920-source/pairs.jsonl",
                 "runs/batch03_next_experiment_20260924/pairs.jsonl"):
        for _, q, _ in source_lines(path):
            if str(q["id"]) in {r["id"] for r in records if r["pool"] == "main23"}:
                draft_sources[str(q["id"])] = q["source_model"]
    assert len(draft_sources) == 23
    save("main_draft_sources.json", draft_sources)

    archive = "outputs/generation-diagnostics-20261005/overnight_20261011/identity_handoff.zip"
    register(archive, "historical_handoff_not_execution_hash")
    member = "scripts/run_identity_mvp_20261011.py"
    with zipfile.ZipFile(ROOT / archive) as z:
        before_bytes = z.read(member)
    before = re.sub(r"\r+\n", "\n", before_bytes.decode("utf-8-sig"))
    after = (ROOT / member).read_text(encoding="utf-8-sig")
    def functions(s):
        return {n.name: n for n in ast.parse(s).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bf, af = functions(before), functions(after)
    changed = [k for k in bf if k in af and ast.dump(bf[k]) != ast.dump(af[k])]
    def run_source(s, fs):
        return s.splitlines()[fs["run"].lineno-1:fs["run"].end_lineno]
    run_diff = "\n".join(difflib.unified_diff(run_source(before, bf), run_source(after, af), fromfile="archived/run", tofile="current/run"))
    save("archive_code_comparison.json", dict(archive=archive, member=member,
        archived_member_sha256=digest(before_bytes), current_member_sha256=digest((ROOT/member).read_bytes()),
        run_function_ast_same="run" not in changed, changed_functions=changed, run_diff=run_diff,
        scope="Run differences are EOS/stop_reason bookkeeping and dtype metadata, not sampling or scheduling. Scoring functions changed; uniform rescore separately verified. Handoff is not an executed-source hash."))
    save("record_index.json", [{k: v for k, v in r.items() if k != "tokens"} for r in records])
    log_evidence = {}
    for pool in ("identity_mvp", "identity_alias"):
        path = BASE+pool+"/runner.log"
        content = (ROOT / path).read_text(encoding="utf8").splitlines()
        exit_line = next((i for i, s in enumerate(content, 1) if "diagnostic_process_exited" in s), None)
        restore_line = next((i for i, s in enumerate(content, 1) if "restoring_owned_resident" in s), None)
        evidence = [dict(line=i, text=s, scope="experiment" if not restore_line or i<restore_line else "restored_resident") for i, s in enumerate(content, 1)
                    if any(x in s for x in ("non-default args", "Initializing a V1", "Using Flash Attention", "FlashInfer is not available", "Running: 7", "Running: 1", "diagnostic_process_exited", "restoring_owned_resident"))]
        log_evidence[pool] = dict(source=path, experiment_exit_line=exit_line, restored_resident_line=restore_line, evidence=evidence,
            missing=["checkpoint/tokenizer content hashes", "run-specific script/worker hash", "full package lockfile, driver and GPU UUID", "per-step request schedule and prefix-cache contents", "per-request RNG states and logits at first divergence"])
    save("execution_log_evidence.json", log_evidence)
    for path in ["selective_context/vllm_mask.py", "selective_context/masks.py", "selective_context/safe_flex_mask.py", "selective_context/vllm_worker.py", "selective_context/vllm_backend.py", "selective_context/hf_backend.py", "scripts/run_identity_mvp_20261011.py",
                 "outputs/game24-uft-external-20q-20260919-prepared/protocol.json", "outputs/game24-dual-anchor-validation-20260918-prepared/pairs.jsonl", "outputs/game24-batch02-validation-20260920-source/pairs.jsonl", "runs/batch03_next_experiment_20260924/pairs.jsonl",
                 "runs/game24_batch03_validation_20260925_raw/launch_record.json", "docs/quick_validation/batch03_interrupted_audit_20260924.md",
                 "docs/quick_validation/dual_anchor_validation_20260918.md", "docs/quick_validation/uft_external_plan_20260919.md",
                 "docs/quick_validation/public_uft_audit_20260919.md"]:
        register(path, "current_code_or_historical_provenance")
    save("asset_manifest.json", dict(raw_records=len(records), sources=SOURCES, assets=assets,
        note="Code hashes describe current checkout only; not proof of exact historical execution. New model requests and GPU generation are zero."))
    summary = dict(raw_records=len(records), repeat_pairs=len(repeats), repeat_flips=sum(x["left_correct"] != x["right_correct"] for x in repeats),
        repeat_pools=dict(Counter("|".join(x["pools"]) for x in repeats)),
        effects=[{k: v for k, v in e.items() if k != "pairs"} for e in effects],
        fluctuations=[{k: v for k, v in x.items() if k != "by_question"} for x in fluctuations],
        pool_confounds={k: {a: b for a, b in v.items() if a != "profiles"} for k, v in confounds.items()})
    save("summary.json", summary)
    print(json.dumps(dict(raw_records=len(records), repeat_pairs=len(repeats),
        matched_R3_R4_pairs=sum(e["n"] for e in effects), uniform_rescore_agreements=len(rescored)), ensure_ascii=False))


if __name__ == "__main__":
    main()
