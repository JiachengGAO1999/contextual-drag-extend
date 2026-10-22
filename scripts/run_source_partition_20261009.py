"""Frozen source-partition replay; reuse old scores and sample no new text."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_information_followup_20261005 import freeze
from selective_context.diagnostic_data import paired_effect, read_jsonl


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(output):
    out = output / "source_partition"
    out.mkdir(exist_ok=True)
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = output / "cross_question"
    original = load(source / "manifest.json")
    probes = load(source / "probes.json")
    if load(source / "summary.json")["status"] != "completed_cross_question_verification":
        raise ValueError("Original frozen source comparison is incomplete")
    if load(output / "cross_question_behavior/summary.json")["status"] != "completed_natural_source_verification":
        raise ValueError("Complete the authorized behavior batch first")
    ids = [q["id"] for q in original["questions"] if q["id"] in probes["probes"]]
    reference = []
    names = dict(FULL="FULL", CANDIDATE="DRAFT", CONTROL="NON_DRAFT")
    for row in read_jsonl(source / "diagnostics.jsonl"):
        if row["id"] in ids and row["condition"] in names:
            reference.append(dict(row, condition=names[row["condition"]],
                reference_source=str((source / "diagnostics.jsonl").relative_to(ROOT))))
    if len(ids) != 23 or len({(r["id"], r["condition"]) for r in reference}) != 69:
        raise ValueError("Expected all 23 frozen probes and 69 reference scores")
    budget = load(output / "budget.json")
    if budget.get("active"):
        raise RuntimeError("Shared budget is already active")
    config = dict(model=original["model"], dtype="bfloat16", heads=original["heads"],
        strength=original["strength"], gpu_hours=original["gpu_hours"],
        source_manifest=str((source / "manifest.json").relative_to(ROOT)),
        source_probes=str((source / "probes.json").relative_to(ROOT)),
        question_ids=ids, missing=probes["missing"], replay_limit=2048,
        new_conditions=dict(PRE_DRAFT="PRE_DRAFT_MATCHED", GENERATED="GENERATED_MATCHED"),
        condition_orders={qid: (["PRE_DRAFT", "GENERATED"] if i % 2 == 0 else ["GENERATED", "PRE_DRAFT"])
            for i, qid in enumerate(ids)},
        geometry_queries={qid: list(range(max(0, probes["probes"][qid]["index"]-3), probes["probes"][qid]["index"])) for qid in ids},
        primary="GENERATED minus PRE_DRAFT rejection-minus-endorsement sequence log-prob margin, question paired.",
        auxiliary=["DRAFT minus PRE_DRAFT", "Original DRAFT minus NON_DRAFT", "GENERATED minus NON_DRAFT", "Each condition minus FULL", "Length-normalized primary", "Original endorse/reject descriptive strata"],
        partitions=dict(P="[0,draft_start)", D="[draft_start,draft_end)",
            F="[draft_end,original_prompt_length)", G="[original_prompt_length,current_KV_length), including current query"),
        matching="Per-head pre-o_proj norm matched to draft contribution on each branch's current state; fixed 1e-8 denominator floor. Record zero/near-zero source, unmatched counts and maximum scale. No replacement or automatic retries.",
        targets="Last three generated queries before the original first judgment, selected by fixed token index; geometry and next-token entropy only here. No full-sequence attention or vector dumps.",
        references_reused=69, planned_new_scores=46, planned_geometry=23,
        budget_before_seconds=budget["gpu_seconds"], estimated_gpu_hours=[1, 2],
        analysis="5000 paired question bootstrap draws; all original questions retained, unmatched-source coverage reported. Per-head and per-token observations are not independent samples. Unmatched sources invalidate an equal-norm interpretation, without triggering a new source/head selection.",
        cpu_audit="The original 23 probe annotations are complete and unchanged. Review of the later 72 natural trajectories remains exploratory and separate; its completion is not used to select probes or gate replay.",
        limitations=["Already observed question pool: mechanism discrimination, not independent confirmation.",
            "Pre-draft values cannot read later draft tokens, but their weights still depend on draft-influenced queries.",
            "Generated values may encode useful reasoning or the present judgment, not necessarily old erroneous content.",
            "Direction similarity, entropy and source effects do not prove semantic information transfer.",
            "Pre-o_proj matching does not guarantee matched projected perturbations; their geometry is measured.",
            "No automatic full generation, content-probe search, head/window search, new model or task."])
    freeze(out / "manifest.json", config)
    freeze(out / "reference_scores.json", reference)
    return config


def progress(config, out, status, **extra):
    rows = read_jsonl(out / "scores.jsonl")
    geometry = read_jsonl(out / "geometry.jsonl")
    save(out / "summary.json", dict(status=status, completed_new_scores=len(rows),
        planned_new_scores=config["planned_new_scores"], geometry_requests=len(geometry),
        planned_geometry=config["planned_geometry"], counts=dict(Counter(r["condition"] for r in rows)), **extra))


def analyse(config, probes, out, status, error=None):
    fresh = read_jsonl(out / "scores.jsonl")
    rows = load(out / "reference_scores.json")+fresh
    geometry = read_jsonl(out / "geometry.jsonl")
    primary = paired_effect(rows, "PRE_DRAFT", "GENERATED")
    groups = {}
    for direction in ("endorse", "reject"):
        ids = {q for q, p in probes["probes"].items() if p["baseline_direction"] == direction}
        group = [r for r in rows if r["id"] in ids]
        groups[direction] = dict(primary=paired_effect(group, "PRE_DRAFT", "GENERATED"),
            effects_vs_full={c: paired_effect(group, "FULL", c) for c in ("DRAFT", "NON_DRAFT", "PRE_DRAFT", "GENERATED")})
    matching = {c: dict(head_queries=sum(r["source_match_stats"][k]["head_queries"] for r in fresh if r["condition"] == c for k in r["source_match_stats"]),
        unmatched=sum(r["source_match_stats"][k]["unmatched"] for r in fresh if r["condition"] == c for k in r["source_match_stats"]),
        zero_source=sum(r["source_match_stats"][k]["zero_source"] for r in fresh if r["condition"] == c for k in r["source_match_stats"]),
        max_scale=max((r["source_match_stats"][k]["max_scale"] for r in fresh if r["condition"] == c for k in r["source_match_stats"]), default=None)) for c in config["new_conditions"]}
    result = dict(status=status, completed_new_scores=len(fresh), planned_new_scores=46,
        geometry_requests=len(geometry), planned_geometry=23, primary=primary,
        length_normalized_primary=paired_effect(rows, "PRE_DRAFT", "GENERATED", field="mean_margin"),
        auxiliary={"DRAFT_minus_PRE_DRAFT": paired_effect(rows, "PRE_DRAFT", "DRAFT"),
            "DRAFT_minus_NON_DRAFT": paired_effect(rows, "NON_DRAFT", "DRAFT"),
            "GENERATED_minus_NON_DRAFT": paired_effect(rows, "NON_DRAFT", "GENERATED")},
        effects_vs_full={c: paired_effect(rows, "FULL", c) for c in ("DRAFT", "NON_DRAFT", "PRE_DRAFT", "GENERATED")},
        descriptive_groups=groups, matching_coverage=matching,
        full_reuse_max_absolute_sum_logp_difference=max((abs(r["full_preferred_sum_logp_difference"]) for r in geometry), default=None),
        pending_scores=[dict(id=q, condition=c) for q in config["question_ids"] for c in config["new_conditions"] if (q, c) not in {(r["id"], r["condition"]) for r in fresh}],
        pending_geometry=[q for q in config["question_ids"] if q not in {r["id"] for r in geometry}],
        error=error, next="Interpret source geometry and coverage; no automatic content experiment or generation.")
    save(out / "summary.json", result)
    (out / "report.md").write_text("# Frozen source-partition replay\n\n"
        "Original FULL/DRAFT/NON_DRAFT scores reused; no new natural sampling. "
        "P weights may still reflect the draft; G is not guaranteed to contain erroneous content. "
        "Zero-source matches, projected perturbations, observed questions and posthoc strata limit causal interpretation.\n\n```json\n"+
        json.dumps(result, indent=2)+"\n```\n", encoding="utf-8")


def run(backend, config, original, probes, out, budget):
    from selective_context.diagnostics import Intervention
    scores = read_jsonl(out / "scores.jsonl")
    scored = {(r["id"], r["condition"]) for r in scores}
    measured = {r["id"] for r in read_jsonl(out / "geometry.jsonl")}
    questions = {q["id"]: q for q in original["questions"]}
    reference = {(r["id"], r["condition"]): r for r in load(out / "reference_scores.json")}
    heads = tuple(tuple(h) for h in config["heads"])
    for qid in config["question_ids"]:
        todo = [c for c in config["condition_orders"][qid] if (qid, c) not in scored]
        if not todo and qid in measured:
            continue
        q, p = questions[qid], probes["probes"][qid]
        span = q["request"]["draft_token_span"]
        pre = backend.prefill(q["request"]["input_ids"])
        try:
            if qid not in measured:
                save(out / "current_request.json", dict(id=qid, condition="FULL_GEOMETRY", status="running"))
                started = time.monotonic()
                result = backend.teacher_force(pre, p["prefix_tokens"]+p["candidates"]["preferred"], span,
                    Intervention("FULL", heads), geometry_tokens=config["geometry_queries"][qid])
                row = dict(id=qid, condition="FULL_GEOMETRY", index=p["index"],
                    source_geometry=result["source_geometry"], target_entropy=result["target_entropy"],
                    full_preferred_sum_logp_difference=sum(result["log_probs"][p["index"]:])-reference[qid, "FULL"]["scores"]["preferred"]["sum_logp"],
                    source=config["source_probes"], model=config["model"], gpu_seconds=time.monotonic()-started)
                append(out / "geometry.jsonl", row)
                measured.add(qid)
                progress(config, out, "running_source_partition")
                budget.check(force=True)
                print(f"geometry {len(measured)}/23 id={qid}", flush=True)
            for name in todo:
                save(out / "current_request.json", dict(id=qid, condition=name, status="running"))
                spec = Intervention(config["new_conditions"][name], heads, strength=config["strength"])
                started = time.monotonic()
                candidate_scores, match = {}, {}
                for key, candidate in p["candidates"].items():
                    result = backend.teacher_force(pre, p["prefix_tokens"]+candidate, span, spec)
                    values = result["log_probs"][p["index"]:]
                    candidate_scores[key] = dict(sum_logp=sum(values), mean_logp=statistics.mean(values), tokens=len(values))
                    match[key] = result["source_match_stats"]
                row = dict(phase="source_partition", id=qid, condition=name, mode=spec.mode,
                    heads=spec.heads, strength=spec.strength, query_window=None, index=p["index"], scores=candidate_scores,
                    margin=candidate_scores["preferred"]["sum_logp"]-candidate_scores["alternative"]["sum_logp"],
                    mean_margin=candidate_scores["preferred"]["mean_logp"]-candidate_scores["alternative"]["mean_logp"],
                    source_match_stats=match, source=config["source_probes"],
                    draft_token_span=span, original_prompt_length=len(q["request"]["input_ids"]),
                    model=config["model"], gpu_seconds=time.monotonic()-started)
                append(out / "scores.jsonl", row)
                scored.add((qid, name))
                save(out / "current_request.json", dict(id=qid, condition=name, status="saved"))
                progress(config, out, "running_source_partition")
                budget.check(force=True)
                print(f"source_score {len(scored)}/46 id={qid} condition={name} margin={row['margin']:.5f}", flush=True)
        finally:
            del pre


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    out = args.output / "source_partition"
    if args.status:
        summary = load(out / "summary.json") if (out / "summary.json").exists() else {}
        compact = {k: v for k, v in summary.items() if k not in ("descriptive_groups", "effects_vs_full", "auxiliary", "pending_scores", "pending_geometry")}
        for name in ("primary", "length_normalized_primary"):
            if name in compact:
                compact[name] = {k: v for k, v in compact[name].items() if k != "by_question"}
        print(json.dumps(dict(summary=compact, budget=load(args.output / "budget.json"),
            current_request=load(out / "current_request.json") if (out / "current_request.json").exists() else None), indent=2))
        return
    config = prepare(args.output)
    original, probes = load(ROOT / config["source_manifest"]), load(ROOT / config["source_probes"])
    for q in original["questions"]:
        if q["id"] in config["question_ids"]:
            p = probes["probes"][q["id"]]
            if max(len(p["prefix_tokens"])+len(t) for t in p["candidates"].values()) > config["replay_limit"]:
                raise ValueError("Frozen probe exceeds original replay limit")
            lo, hi = q["request"]["draft_token_span"]
            if not 0 < lo < hi < len(q["request"]["input_ids"]):
                raise ValueError("Expected nonempty P/D/F sources")
    if args.prepare:
        from selective_context.diagnostics import Intervention
        for mode in config["new_conditions"].values():
            Intervention(mode, tuple(tuple(h) for h in config["heads"])).validate(36, 32)
        progress(config, out, "prepared_waiting_for_gpu4")
        print(json.dumps(dict(questions=config["question_ids"], new_scores=46, geometry=23,
            reused_scores=69, estimated_gpu_hours=config["estimated_gpu_hours"], primary=config["primary"]), indent=2))
        return
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from selective_context.diagnostics import DiagnosticBackend
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    budget = Budget(args.output / "budget.json", config["gpu_hours"])
    status, error = "completed_source_partition", None
    try:
        if not (out / "engine_acceptance.json").exists():
            subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/selective_context/test_diagnostics.py"], cwd=ROOT, check=True)
            save(out / "engine_acceptance.json", dict(passed=True,
                scope="Original regressions, P/D/F/G reconstruction, new source matching, causal query boundary and observational geometry"))
            budget.check(force=True)
        progress(config, out, "loading_model")
        tokenizer = AutoTokenizer.from_pretrained(config["model"], local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(config["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0")
        run(DiagnosticBackend(model, tokenizer, budget.check), config, original, probes, out, budget)
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed", repr(exc)
        raise
    finally:
        budget.close()
        analyse(config, probes, out, status, error)


if __name__ == "__main__":
    main()
