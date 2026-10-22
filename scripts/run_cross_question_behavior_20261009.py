"""Frozen natural-generation source comparison on the existing 24 questions."""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_information_followup_20261005 import freeze, same_tree, tree
from selective_context.diagnostic_data import expression_measurement, paired_effect, read_jsonl

CONDITIONS = ("FULL", "CANDIDATE", "CONTROL")


def prepare(output):
    out = output / "cross_question_behavior"
    out.mkdir(exist_ok=True)
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    source = output / "cross_question"
    diagnostic = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    if diagnostic["status"] != "completed_cross_question_verification":
        raise ValueError("Complete frozen source verification before this behavior bridge")
    config = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    reviews = json.loads((source / "reviews.json").read_text(encoding="utf-8"))["questions"]
    prior = json.loads((output / "budget.json").read_text(encoding="utf-8"))
    if prior.get("active"):
        raise RuntimeError("Shared GPU budget is active; another experiment may be running")
    remaining = prior["limit_seconds"] - prior["gpu_seconds"]
    orders = list(itertools.permutations(CONDITIONS))
    questions = []
    for i, q in enumerate(config["questions"]):
        # Keep the original 24, including the question without a semantic probe.
        questions.append(dict(q, seeds=[20261009],
            max_new_tokens=min(16384, 32768-len(q["request"]["input_ids"])),
            condition_order=list(orders[i % len(orders)]),
            prior_baseline_direction=reviews[q["id"]].get("baseline_direction", "unclassified")))
    estimate = sum(q["max_new_tokens"]*len(CONDITIONS) for q in questions)/25 + 300
    if len(questions) != 24 or estimate > remaining:
        raise ValueError("Frozen 72-generation design does not fit remaining budget at 25 tokens/s; do not silently shrink it")
    manifest = dict(model=config["model"], dtype="bfloat16", sampling=config["sampling"],
        heads=config["heads"], strength=config["strength"], questions=questions,
        conditions=list(CONDITIONS), seed=20261009, context=32768,
        gpu_hours=config["gpu_hours"], planned_requests=72,
        question_selection="All 24 questions, unchanged order from cross_question/manifest.json; includes missing semantic event 1148. No effect-based selection.",
        source_manifest=str((source / "manifest.json").relative_to(ROOT)),
        seed_rule="One fresh paired seed per question; all three conditions rerun from the original full prompt, without teacher forcing.",
        output_limit_rule="16384 new tokens per request, bounded by the original 32768-token context. Chosen before generation; common across conditions; historical full-context caps were approximately 31k-32k.",
        execution_order="Six condition permutations cycle across the 24 fixed questions; shared SDPA prefill and independent KV branches.",
        primary="Question-level official final-answer accuracy difference CANDIDATE minus CONTROL.",
        secondary=["CANDIDATE minus FULL accuracy", "Final-expression structural reuse, not mere quotation during reasoning", "Recovery and damage relative to both baselines", "EOS, truncation, unresolved scoring and output length"],
        analysis="5000 paired question bootstrap draws. One seed per question: no estimate of within-question seed robustness. Use only complete condition triplets for effects and report all pending requests. Truncated and unresolved outputs remain in condition denominators; success requires a final-answer segment and official score True. An unclosed thinking segment is not a final answer even if it contains a box. Report EOS-and-correct separately.",
        continuation_rule="No automatic head/window search, seed extension, additional questions, models or mechanism phase. Assess CANDIDATE versus CONTROL accuracy and wrong-expression reuse together after completing the fixed batch.",
        cost=dict(budget_before_seconds=prior["gpu_seconds"], remaining_seconds=remaining,
            observed_median_tokens_per_second=dict(FULL=29.43, CANDIDATE=28.75, CONTROL=27.74),
            reference="Existing causal_behaviour and random_behaviour request timers; original random-head control differs from this source control.",
            historical_max_generated_tokens=14094, planning_tokens_per_second=25,
            full_cap_estimate_seconds=estimate, estimated_typical_hours=[4, 6],
            estimate_is_not_guarantee=True),
        limitations=["Same question pool as the completed diagnostic comparison; this tests transfer to free generation, not a new independent dataset.",
            "Most existing failed drafts violate number inventory; one seed cannot establish universal robustness.",
            "Previous FULL classifications are descriptive strata from a different seed, not ground truth about the fresh run.",
            "Source-control norm is matched per head before o_proj on each condition's own evolving state. Trajectories need not remain identical.",
            "Final-expression AST equality does not measure all structurally similar errors or all reuse during reasoning.",
            "A 16384-token output cap may truncate some runs; no automatic continuation or retry."])
    freeze(manifest_path, manifest)
    return manifest


def request_key(row):
    return row["id"], row["seed"], row["condition"]


def score_generation(raw, q, raw_line, out):
    from selective_context.hf_backend import GenerationResult
    from selective_context.official_compat import make_official_record
    from selective_context.phase0.thinking_pilot import extract_final_draft
    from selective_context.schema import SelectiveContextRequest
    from selective_context.tasks import score_record

    request = dataclasses.replace(SelectiveContextRequest.from_dict(q["request"]), sample_seed=raw["seed"])
    final, thinking_status = extract_final_draft(raw["text"], q["prompt"], raw["eos_token"])
    generation = GenerationResult(raw["generated_token_ids"], final, raw["finish_reason"], {})
    official = score_record(make_official_record(problem_id=q["id"], problem=q["problem"],
        answer=q["answer"], prompt=q["prompt"], request=request,
        generations=[generation], model_config_alias="Qwen3_8B_Thinking"))
    scored = official["init_response_generations"][0]
    final_answer_available = thinking_status in ("parsable_thinking", "no_thinking")
    expression = scored.get("extracted_answer") if final_answer_available else None
    audit = expression_measurement(expression or "", q["answer"])
    status = scored.get("correctness") if final_answer_available else None
    return dict(id=raw["id"], seed=raw["seed"], condition=raw["condition"],
        correct=status is True, score_status=status, extracted_answer=expression,
        finish_reason=raw["finish_reason"], thinking_status=thinking_status,
        final_answer_available=final_answer_available,
        official_extracted_answer=scored.get("extracted_answer"),
        official_score_status=scored.get("correctness"),
        old_expression=q["old_expression"], structural_reuse=same_tree(q["old_expression"], expression),
        route_available=tree(q["old_expression"]) is not None,
        answer_route_parseable=tree(expression) is not None,
        exact_audit=audit,
        scorer_disagreement=(bool(status) != audit["exact_game24"]
            if status is not None and audit["evaluation_status"] == "ok" else None),
        generated_tokens=len(raw["generated_token_ids"]),
        prior_baseline_direction=q["prior_baseline_direction"],
        source=q["source"], source_line=q["source_line"],
        raw_source=str((out / "generations.jsonl").relative_to(ROOT)), raw_line=raw_line,
        model=raw["model"], sampling=raw["sampling"], mode=raw["mode"],
        heads=raw["heads"], strength=raw["strength"], query_window=raw["query_window"],
        max_new_tokens=raw["max_new_tokens"], gpu_seconds=raw["gpu_seconds"])


def rescore_saved(config, out):
    """A completed generation is never repeated because its scoring was interrupted."""
    path = out / "behaviour.jsonl"
    done = {request_key(r) for r in read_jsonl(path)}
    questions = {q["id"]: q for q in config["questions"]}
    for line, raw in enumerate(read_jsonl(out / "generations.jsonl"), 1):
        if request_key(raw) not in done:
            append(path, score_generation(raw, questions[raw["id"]], line, out))
            done.add(request_key(raw))


def summarize(config, rows, status, out, interrupted=None, error=None):
    planned = [(q["id"], seed, c) for q in config["questions"] for seed in q["seeds"] for c in q["condition_order"]]
    done = {request_key(r): r for r in rows}
    if len(done) != len(rows) or set(done)-set(planned):
        raise ValueError("Duplicate or unplanned behavior result")
    pending = [dict(id=q, seed=s, condition=c) for q, s, c in planned if (q, s, c) not in done]
    stats = {}
    for name in CONDITIONS:
        rs = [r for r in rows if r["condition"] == name]
        stats[name] = dict(n=len(rs), planned=len(config["questions"]),
            correct=sum(r["correct"] for r in rs),
            accuracy=statistics.mean(r["correct"] for r in rs) if rs else None,
            structural_reuse=sum(r["structural_reuse"] for r in rs),
            route_available=sum(r["route_available"] for r in rs),
            answer_route_parseable=sum(r["answer_route_parseable"] for r in rs),
            eos=sum(r["finish_reason"] == "eos" for r in rs),
            length=sum(r["finish_reason"] == "length" for r in rs),
            unresolved=sum(r["score_status"] is None for r in rs),
            eos_and_correct=sum(r["correct"] and r["finish_reason"] == "eos" for r in rs),
            scorer_disagreement=sum(r["scorer_disagreement"] is True for r in rs),
            mean_tokens=statistics.mean(r["generated_tokens"] for r in rs) if rs else None)
    complete_ids = [q["id"] for q in config["questions"]
        if all((q["id"], s, c) in done for s in q["seeds"] for c in CONDITIONS)]
    question_rows = []
    for qid in complete_ids:
        for c in CONDITIONS:
            rs = [r for r in rows if r["id"] == qid and r["condition"] == c]
            question_rows.append(dict(id=qid, condition=c,
                accuracy=statistics.mean(r["correct"] for r in rs),
                reuse=statistics.mean(r["structural_reuse"] for r in rs)))
    comparisons = {}
    for before in ("CONTROL", "FULL"):
        pairs = [(done[qid, s, before], done[qid, s, "CANDIDATE"])
            for q in config["questions"] if q["id"] in complete_ids
            for qid in [q["id"]] for s in q["seeds"]]
        comparisons["CANDIDATE_minus_"+before] = dict(
            accuracy=paired_effect(question_rows, before, "CANDIDATE", field="accuracy"),
            reuse=paired_effect(question_rows, before, "CANDIDATE", field="reuse"),
            paired_requests=len(pairs), recovered=sum(not a["correct"] and b["correct"] for a, b in pairs),
            harmed=sum(a["correct"] and not b["correct"] for a, b in pairs))
    result = dict(status=status, planned_requests=len(planned), completed_requests=len(rows),
        complete_questions=len(complete_ids), conditions=stats, comparisons=comparisons,
        by_question=[dict(id=q["id"], prior_baseline_direction=q["prior_baseline_direction"],
            results={c: {k: done[q["id"], q["seeds"][0], c][k]
                for k in ("correct", "structural_reuse", "finish_reason", "generated_tokens", "extracted_answer")}
                for c in CONDITIONS if (q["id"], q["seeds"][0], c) in done}) for q in config["questions"]],
        pending=pending, interrupted_request=interrupted, error=error,
        next="Assess behavior transfer and uncertainty; no automatic new experiment or sample extension.")
    save(out / "summary.json", result)
    return result


def write_report(config, summary, out):
    lines = ["# Frozen natural-generation source comparison", "",
        "All 24 original questions, including the missing semantic-probe question. "
        "One new paired seed, three conditions, independent natural continuations. "
        "The 16384-token cap is common; truncated/unresolved outputs remain in denominators. "
        "AST reuse measures the final expression only. Question-level effects use complete triplets; "
        "unfinished requests are listed explicitly.", "",
        "| Condition | Scored | Correct | Old-expression reuse | EOS | Truncated | Unresolved |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for c, s in summary["conditions"].items():
        lines.append(f"| {c} | {s['n']} | {s['correct']} | {s['structural_reuse']} | {s['eos']} | {s['length']} | {s['unresolved']} |")
    lines.extend(["", "```json", json.dumps(summary, indent=2), "```", "",
        "Limitations: "+" ".join(config["limitations"])])
    (out / "report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def run(backend, config, out, budget):
    from selective_context.diagnostics import Intervention
    from selective_context.schema import SelectiveContextRequest

    heads = tuple(tuple(h) for h in config["heads"])
    specs = dict(FULL=Intervention(),
        CANDIDATE=Intervention("VALUE_ZERO", heads, strength=config["strength"]),
        CONTROL=Intervention("NON_DRAFT_MATCHED", heads, strength=config["strength"]))
    raw_path, path = out / "generations.jsonl", out / "behaviour.jsonl"
    raw_count = len(read_jsonl(raw_path))
    rows = read_jsonl(path)
    done = {request_key(r) for r in rows}
    for q in config["questions"]:
        pre = None
        try:
            for seed in q["seeds"]:
                request = dataclasses.replace(SelectiveContextRequest.from_dict(q["request"]), sample_seed=seed)
                for name in q["condition_order"]:
                    if (q["id"], seed, name) in done:
                        continue
                    active = dict(id=q["id"], seed=seed, condition=name)
                    save(out / "current_request.json", dict(status="generating", **active))
                    started = time.monotonic()
                    if pre is None:
                        pre = backend.prefill(request.input_ids)
                    result = backend.generate_diagnostic(pre, request, specs[name],
                        max_new_tokens=q["max_new_tokens"], **config["sampling"])
                    # Persist raw output before any potentially fallible scoring.
                    raw = dict(**active, text=result.text, generated_token_ids=result.generated_token_ids,
                        finish_reason=result.finish_reason, eos_token=backend.tokenizer.eos_token,
                        source=q["source"], source_line=q["source_line"], model=config["model"],
                        sampling=config["sampling"], max_new_tokens=q["max_new_tokens"],
                        mode=specs[name].mode, heads=specs[name].heads, strength=specs[name].strength,
                        query_window=specs[name].query_window, draft_token_span=request.draft_token_span,
                        gpu_seconds=time.monotonic()-started)
                    append(raw_path, raw)
                    raw_count += 1
                    row = score_generation(raw, q, raw_count, out)
                    append(path, row)
                    rows.append(row)
                    done.add(request_key(row))
                    save(out / "current_request.json", dict(status="saved", **active))
                    # Intermediate effects are not computed or used for decisions.
                    save(out / "summary.json", dict(status="running_natural_generation", planned_requests=72,
                        completed_requests=len(rows), completed_by_condition=dict(Counter(r["condition"] for r in rows))))
                    print(f"behavior {len(rows)}/72 id={q['id']} seed={seed} condition={name} "
                        f"correct={row['correct']} reuse={row['structural_reuse']} "
                        f"tokens={row['generated_tokens']} finish={row['finish_reason']}", flush=True)
                    budget.check(force=True)
        finally:
            del pre


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    out = args.output / "cross_question_behavior"
    if args.status:
        result = dict(raw_generations=len(read_jsonl(out / "generations.jsonl")),
            completed_by_condition=dict(Counter(r["condition"] for r in read_jsonl(out / "behaviour.jsonl"))))
        for name, path in (("summary", out / "summary.json"),
                           ("current_request", out / "current_request.json"),
                           ("budget", args.output / "budget.json")):
            if path.exists():
                value = json.loads(path.read_text(encoding="utf-8"))
                if name == "summary":
                    full = value
                    value = {k: v for k, v in value.items() if k not in ("by_question", "pending", "comparisons")}
                    value["pending_requests"] = len(full.get("pending", []))
                    if full.get("comparisons"):
                        value["comparisons"] = {label: {k: ({m: n for m, n in v.items() if m != "by_question"}
                            if isinstance(v, dict) else v) for k, v in comparison.items()}
                            for label, comparison in full["comparisons"].items()}
                result[name] = value
        print(json.dumps(result, indent=2))
        return
    config = prepare(args.output)
    rescore_saved(config, out)
    if args.prepare:
        from transformers import AutoTokenizer
        from selective_context.schema import SelectiveContextRequest
        from selective_context.tasks import score_record
        from selective_context.official_compat import make_official_record
        from selective_context.phase0.thinking_pilot import extract_final_draft
        tokenizer = AutoTokenizer.from_pretrained(config["model"], local_files_only=True)
        for q in config["questions"]:
            request = SelectiveContextRequest.from_dict(q["request"])
            if tokenizer.encode(q["prompt"], add_special_tokens=False) != request.input_ids:
                raise ValueError("Frozen prompt does not match its input IDs")
            if len(request.input_ids)+q["max_new_tokens"] > config["context"]:
                raise ValueError("Frozen context exceeds model budget")
            if not 0 <= request.draft_token_span[0] < request.draft_token_span[1] <= len(request.input_ids):
                raise ValueError("Invalid draft span")
        summary = summarize(config, read_jsonl(out / "behaviour.jsonl"), "prepared_waiting_for_gpu4", out)
        print(json.dumps(dict(questions=[q["id"] for q in config["questions"]], seeds=[config["seed"]],
            conditions=config["conditions"], max_new_tokens=16384, planned_requests=72,
            cost=config["cost"], completed_requests=summary["completed_requests"]), indent=2))
        return
    rows = read_jsonl(out / "behaviour.jsonl")
    if len(rows) == config["planned_requests"]:
        summary = summarize(config, rows, "completed_natural_source_verification", out)
        write_report(config, summary, out)
        return
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from selective_context.diagnostics import DiagnosticBackend
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    budget = Budget(args.output / "budget.json", config["gpu_hours"])
    status, error = "completed_natural_source_verification", None
    try:
        save(out / "summary.json", dict(status="loading_model", planned_requests=72, completed_requests=len(rows)))
        tokenizer = AutoTokenizer.from_pretrained(config["model"], local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(config["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0")
        backend = DiagnosticBackend(model, tokenizer, budget.check)
        run(backend, config, out, budget)
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed", repr(exc)
        raise
    finally:
        budget.close()
        current = out / "current_request.json"
        interrupted = json.loads(current.read_text(encoding="utf-8")) if current.exists() else None
        if interrupted and interrupted.get("status") == "saved":
            interrupted = None
        summary = summarize(config, read_jsonl(out / "behaviour.jsonl"), status, out, interrupted, error)
        write_report(config, summary, out)


if __name__ == "__main__":
    main()
