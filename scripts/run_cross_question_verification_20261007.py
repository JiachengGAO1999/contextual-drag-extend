"""Frozen cross-question source contrast; bounded collection and reviewed replay."""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_information_followup_20261005 import freeze
from run_semantic_rejection_20261005 import measure
from selective_context.diagnostic_data import expression_measurement, paired_effect, read_jsonl

# Ordered source preference is fixed before any new continuations/interventions.
SOURCES = (
    "outputs/game24-batch04-dual-anchor-screen-20260925/Qwen3_8B_Thinking/draft_candidates.jsonl",
    "outputs/game24-baseline-screen-vllm-20260918-batch02/draft_candidates.jsonl",
    "outputs/game24-baseline-screen-vllm-20260917-retry1/draft_candidates.jsonl",
    "outputs/game24-heldout-screen-20260917/draft_candidates.jsonl",
    "outputs/game24-qwen3-8b-r0-r4-smoke-boundary-20260906/draft_candidates.jsonl",
    "outputs/game24-qwen3-8b-thinking-drafts-20260908/draft_candidates.jsonl",
    "outputs/game24-qwen3-8b-thinking-r0-r4-20260906/draft_candidates.jsonl",
    "outputs/game24-qwen3-reendorsement-drafts-20260914/draft_candidates.jsonl",
    "outputs/game24-stage-b-drafts-20260911/draft_candidates.jsonl",
    "outputs/game24-stage-b-supplement-20260911/draft_candidates.jsonl",
)


def prepare(output, tokenizer):
    out = output / "cross_question"
    out.mkdir(exist_ok=True)
    path = out / "manifest.json"
    if path.exists():
        return json.loads(path.read_text())
    old = json.loads((output / "manifest.json").read_text())
    frozen = json.loads((output / "semantic_candidate.json").read_text())
    used_ids = {q["id"] for q in old["questions"]}
    used_numbers = {tuple(sorted(q["answer"])) for q in old["questions"]}
    from selective_context.prompting import encode_prompt, make_request, render_chat_prompt
    from selective_context.schema import AccessMode
    from selective_context.tasks import independent_prompt
    from selective_context.phase0.thinking_pilot import extract_final_draft
    choices, counts = {}, {}
    for source in SOURCES:
        count = 0
        for line, row in enumerate(read_jsonl(ROOT / source), 1):
            g = row["init_response_generations"][0]
            numbers = tuple(sorted(row["answer"]))
            expression = g.get("extracted_answer") or ""
            audit = expression_measurement(expression, row["answer"])
            if (str(row["id"]) in used_ids or numbers in used_numbers
                    or g.get("finish_reason") != "eos" or g.get("correctness") is not False
                    or audit["evaluation_status"] != "ok" or audit["exact_game24"]
                    or expression.strip() == "24"):
                continue
            count += 1
            if numbers in choices:
                continue
            draft = row.get("final_response")
            if not draft:
                draft, status = extract_final_draft(g["generated_response"], row["init_response_prompt"], tokenizer.eos_token)
                if status not in ("thinking_parsed", "no_thinking", "ok", "parseable"):
                    # Check the text itself below; historical status strings vary.
                    if not draft or "</think>" in draft or "<think>" in draft:
                        continue
            if not draft or expression not in draft:
                continue
            prompt = render_chat_prompt(tokenizer, independent_prompt(row["problem"], draft), True)
            encoded = encode_prompt(tokenizer, prompt)
            if len(encoded.input_ids) + 2048 > 32768:
                continue
            request = make_request(encoded, "R2", AccessMode.FULL, 20261007)
            choices[numbers] = dict(id=str(row["id"]), problem=row["problem"], answer=row["answer"],
                prompt=prompt, request=request.to_dict(), source=source, source_line=line,
                source_draft_key=row.get("draft_key"), old_expression=expression,
                draft=draft, suffixes={"wrong": {"source": source, "line": line}},
                audit="Completed non-scalar final expression is parseable and fails exact Game24 arithmetic/inventory.")
        counts[source] = count
    items = sorted(choices.values(), key=lambda q: int(q["id"]))
    random.Random(20261007).shuffle(items)
    if len(items) < 24:
        raise ValueError(f"Only {len(items)} usable distinct failed histories; no automatic new-draft screening.")
    selected = items[:24]
    config = dict(model=old["model"], dtype="bfloat16", sampling=old["sampling"],
        heads=frozen["heads"], strength=frozen["strength"], questions=selected,
        seed=20261007, replay_limit=2048, prefix_limit=2048, gpu_hours=24,
        source_counts=counts, available_unique_histories=len(items),
        selection="Fixed source priority, first eligible row per number multiset, numeric-ID sort then seeded shuffle, first 24. No intervention effect filtering.",
        excluded_ids=sorted(used_ids, key=int),
        annotation_rule="First unambiguous natural rejection OR endorsement of the invalid original construction within 2048 tokens. Include both baseline directions. Exclude quotations, sound partial calculations and assertions with ambiguous referents. Missing events are retained without replacement.",
        primary="Question-level CANDIDATE minus NON_DRAFT_MATCHED rejection-minus-endorsement sequence log-prob margin.",
        auxiliary="CANDIDATE minus FULL; length-normalized score, per-question direction and leave-largest-positive-effect-out sensitivity.",
        analysis="One frozen primary comparison. 5000 question bootstrap draws for mean CI; two-sided exact sign test as auxiliary. No significance-driven sample extension or generation bridge.",
        limitations=["Histories predate candidate selection but historical outcomes may have been seen; this is component-disjoint question validation, not a pristine external benchmark.",
            "Only questions with parseable completed explicit failed expressions enter the pool.",
            "New FULL prefixes are capped at 2048 tokens; replay stops at the first reviewed event and candidate completion; missing events limit coverage.",
            "Norm is matched per head before o_proj, not after projection."])
    freeze(path, config)
    return config


def collect(backend, config, out, budget):
    from selective_context.diagnostics import Intervention
    from selective_context.schema import SelectiveContextRequest
    path = out / "prefixes.jsonl"
    done = {r["id"] for r in read_jsonl(path)}
    save(out / "summary.json", dict(status="collecting_fixed_full_prefixes", planned_questions=24))
    for q in config["questions"]:
        if q["id"] in done:
            continue
        started = time.monotonic()
        pre = backend.prefill(q["request"]["input_ids"])
        result = backend.generate_diagnostic(pre, SelectiveContextRequest.from_dict(q["request"]),
            Intervention(), max_new_tokens=config["prefix_limit"], **config["sampling"])
        append(path, dict(id=q["id"], seed=config["seed"], condition="FULL", text=result.text,
            tokens=result.generated_token_ids, finish_reason=result.finish_reason,
            source=q["source"], source_line=q["source_line"], model=config["model"],
            sampling=config["sampling"], gpu_seconds=time.monotonic()-started))
        done.add(q["id"])
        budget.check(force=True)
        print(f"prefix {len(done)}/24 id={q['id']} tokens={len(result.generated_token_ids)} finish={result.finish_reason}", flush=True)
        del pre


def reviewed_probes(config, out, tokenizer):
    reviews = json.loads((out / "reviews.json").read_text())
    prefixes = {r["id"]: r for r in read_jsonl(out / "prefixes.jsonl")}
    probes, missing = {}, {}
    for q in config["questions"]:
        qid = q["id"]
        review = reviews["questions"][qid]
        if review.get("missing"):
            missing[qid] = review["missing"]
            continue
        text = tokenizer.decode(prefixes[qid]["tokens"])
        anchor = review["anchor"]
        start = text.index(anchor) + review.get("offset", 0)
        boundaries = {len(tokenizer.decode(prefixes[qid]["tokens"][:i])): i
                      for i in range(len(prefixes[qid]["tokens"])+1)}
        boundary = max(pos for pos in boundaries if pos <= start)
        leading = text[boundary:start]
        if leading.strip():
            raise ValueError(f"{qid}: probe splits a semantic token")
        index = boundaries[boundary]
        prefix = prefixes[qid]["tokens"][:index]
        candidates = {}
        for key in ("preferred", "alternative"):
            joint = tokenizer.encode(text[:boundary]+leading+review[key], add_special_tokens=False)
            if joint[:index] != prefix or len(joint) > config["replay_limit"]:
                raise ValueError(f"{qid}: candidate changes prefix or exceeds replay limit")
            candidates[key] = joint[index:]
            if not candidates[key]:
                raise ValueError("Empty candidate")
        probes[qid] = dict(index=index, prefix_tokens=prefix, candidates=candidates,
                           semantic=True, **review)
    result = dict(metric="sum_log_probability(reject)-sum_log_probability(endorse)",
                  probes=probes, missing=missing, replay_limit=config["replay_limit"])
    freeze(out / "probes.json", result)
    return result


def analyse(rows, probes, out):
    primary = paired_effect(rows, "CONTROL", "CANDIDATE")
    auxiliary = paired_effect(rows, "FULL", "CANDIDATE")
    values = list(primary["by_question"].values())
    positive = sum(v > 0 for v in values)
    negative = sum(v < 0 for v in values)
    n = positive+negative
    sign_p = min(1., 2*sum(math.comb(n, k) for k in range(min(positive, negative)+1))/2**n) if n else None
    dropped = max(primary["by_question"], key=primary["by_question"].get) if values else None
    remaining = [v for q, v in primary["by_question"].items() if q != dropped]
    result = dict(status="completed_cross_question_verification", available_questions=len(probes["probes"]),
        planned_questions=24, missing=probes["missing"], primary=primary, auxiliary=auxiliary,
        length_normalized_primary=paired_effect(rows, "CONTROL", "CANDIDATE", field="mean_margin"),
        directions=dict(positive=positive, negative=negative, zero=len(values)-n),
        auxiliary_sign_test=dict(two_sided_p=sign_p, trials=n),
        sensitivity=dict(removed_largest_positive_question=dropped,
                         remaining_mean=statistics.mean(remaining) if remaining else None),
        next="No automatic component/window search, sample extension or natural generation. Assess coverage and uncertainty before deciding.")
    save(out / "summary.json", result)
    (out / "report.md").write_text("# Frozen cross-question source contrast\n\n"
        "Questions exclude the original 23 IDs and number multisets. Historical outcomes may have been seen. "
        "Prefixes and semantic annotations are fixed before intervention measurement. Missing questions remain in coverage counts. "
        "Sequence preferences are not solution accuracy; tokens/seeds/heads are not independent samples.\n\n```json\n"+
        json.dumps(result, indent=2)+"\n```\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    out = args.output / "cross_question"
    if args.status:
        manifest_path = out / "manifest.json"
        settings = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        print(json.dumps(dict(prefixes=len(read_jsonl(out / "prefixes.jsonl")),
            prefix_limit=settings.get("prefix_limit"), replay_limit=settings.get("replay_limit"),
            diagnostic_requests=dict(Counter(r["condition"] for r in read_jsonl(out / "diagnostics.jsonl"))),
            summary=json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else None,
            budget=json.loads((args.output / "budget.json").read_text())), indent=2))
        return
    from transformers import AutoTokenizer
    old = json.loads((args.output / "manifest.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(old["model"], local_files_only=True)
    config = prepare(args.output, tokenizer)
    if any(len(q["request"]["input_ids"])+config["prefix_limit"] > 32768 for q in config["questions"]):
        raise ValueError("Frozen question exceeds context budget; do not replace or truncate its draft")
    probes = reviewed_probes(config, out, tokenizer) if (out / "reviews.json").exists() else None
    if args.prepare:
        print(json.dumps(dict(questions=[q["id"] for q in config["questions"]],
            available_histories=config["available_unique_histories"], reviewed_probes=len(probes["probes"]) if probes else None,
            prefix_limit=config["prefix_limit"], replay_limit=config["replay_limit"],
            phase="verification" if probes else "one_bounded_full_prefix_per_question"), indent=2))
        return
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.diagnostics import DiagnosticBackend, Intervention
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    budget = Budget(args.output / "budget.json", config["gpu_hours"])
    try:
        if probes is not None and not probes["probes"]:
            save(out / "summary.json", dict(status="stopped_no_reviewed_events", missing=probes["missing"]))
            return
        model = AutoModelForCausalLM.from_pretrained(config["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0")
        backend = DiagnosticBackend(model, tokenizer, budget.check)
        if probes is None:
            collect(backend, config, out, budget)
            save(out / "summary.json", dict(status="awaiting_cpu_semantic_review", planned_questions=24,
                completed_prefixes=len(read_jsonl(out / "prefixes.jsonl")),
                next="Review first unambiguous reject/endorse event without seeing intervention effects; no replacement generation."))
        else:
            save(out / "summary.json", dict(status="running_frozen_source_verification", available_questions=len(probes["probes"]), missing=probes["missing"]))
            heads = tuple(tuple(h) for h in config["heads"])
            for line, prefix in enumerate(read_jsonl(out / "prefixes.jsonl"), 1):
                for q in config["questions"]:
                    if q["id"] == prefix["id"]:
                        q["suffixes"]["wrong"] = dict(source=str((out / "prefixes.jsonl").relative_to(ROOT)), line=line)
            rows = measure(backend, config, probes, out, budget,
                [("FULL", Intervention()), ("CANDIDATE", Intervention("VALUE_ZERO", heads, strength=config["strength"])),
                 ("CONTROL", Intervention("NON_DRAFT_MATCHED", heads, strength=config["strength"]))],
                "cross_question_source", result_file="diagnostics.jsonl")
            analyse(rows, probes, out)
    except BudgetExceeded:
        save(out / "summary.json", dict(status="budget_exhausted"))
    except Exception as exc:
        save(out / "summary.json", dict(status="failed", error=repr(exc)))
        raise
    finally:
        budget.close()


if __name__ == "__main__":
    main()
