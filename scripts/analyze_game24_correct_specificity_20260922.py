"""Frozen paired analysis for the Game24 correct-history specificity control."""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from analyze_continued_access_math_20260921 import (
    exact_mcnemar_p,
    load_rows as load_failed_rows,
    percentile,
    sha256,
)


CONDITIONS = ("C_FULL", "C_LATE")


def load_control(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        generations = raw.get("init_response_generations") or []
        if len(generations) != 1:
            raise ValueError(f"line {line_number}: expected one generation")
        generation = generations[0]
        metadata = generation.get("selective_context_metadata") or {}
        request = metadata.get("request") or {}
        correctness = generation.get("correctness")
        condition = request.get("condition_id")
        if condition not in CONDITIONS or correctness not in (True, False, None):
            raise ValueError(f"line {line_number}: invalid condition/correctness")
        tokens = raw.get("generated_token_ids") or []
        rows.append({
            "id": str(raw["id"]),
            "seed": int(request["sample_seed"]),
            "condition": condition,
            "correct": int(correctness is True),
            "score_status": "correct" if correctness is True else "incorrect" if correctness is False else "unresolved",
            "finish_reason": str(generation.get("finish_reason")),
            "thinking_status": str(raw.get("thinking_status")),
            "generated_tokens": len(tokens),
            "first_generated_token": tokens[0] if tokens else None,
            "prompt_sha256": request.get("prompt_sha256"),
            "input_ids_sha256": request.get("input_ids_sha256"),
            "draft_token_span": request.get("draft_token_span"),
            "access_mode": metadata.get("access_mode"),
            "extracted_answer": generation.get("extracted_answer"),
        })
    return rows


def audit(rows: list[dict[str, Any]], source_pairs: Path, manifest: Path, completion: Path) -> dict[str, Any]:
    keys = [(r["id"], r["seed"], r["condition"]) for r in rows]
    counts = Counter(keys)
    ids = sorted({r["id"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    expected = {(qid, seed, condition) for qid in ids for seed in seeds for condition in CONDITIONS}
    indexed = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    paired = [(qid, seed) for qid in ids for seed in seeds]
    sources = [json.loads(line) for line in source_pairs.read_text(encoding="utf-8").splitlines() if line.strip()]
    source_ids = sorted(str(row["id"]) for row in sources)
    frozen_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    completed = json.loads(completion.read_text(encoding="utf-8"))
    checks = {
        "prompt_hash_matches": sum(indexed[qid, seed, "C_FULL"]["prompt_sha256"] == indexed[qid, seed, "C_LATE"]["prompt_sha256"] for qid, seed in paired),
        "input_hash_matches": sum(indexed[qid, seed, "C_FULL"]["input_ids_sha256"] == indexed[qid, seed, "C_LATE"]["input_ids_sha256"] for qid, seed in paired),
        "draft_span_matches": sum(indexed[qid, seed, "C_FULL"]["draft_token_span"] == indexed[qid, seed, "C_LATE"]["draft_token_span"] for qid, seed in paired),
        "first_token_matches": sum(indexed[qid, seed, "C_FULL"]["first_generated_token"] == indexed[qid, seed, "C_LATE"]["first_generated_token"] for qid, seed in paired),
        "paired_units": len(paired),
    }
    complete = (
        len(rows) == 32 and len(ids) == 8 and seeds == [927001, 927002]
        and not [key for key, count in counts.items() if count != 1]
        and set(keys) == expected and source_ids == ids
        and len(frozen_manifest) == 32 and completed.get("completed") == 32
        and all(row.get("correct_source_correctness") is True for row in sources)
        and all(row.get("correct_source_finish_reason") == "eos" for row in sources)
        and all(row.get("correct_source_thinking_status") == "parsable_thinking" for row in sources)
        and checks["prompt_hash_matches"] == len(paired)
        and checks["input_hash_matches"] == len(paired)
        and checks["draft_span_matches"] == len(paired)
        and checks["first_token_matches"] == len(paired)
    )
    return {
        "complete_factorial_and_source_gates": complete,
        "rows": len(rows), "questions": len(ids), "question_ids": ids, "seeds": seeds,
        "condition_counts": dict(sorted(Counter(r["condition"] for r in rows).items())),
        "duplicate_keys": [list(key) for key, count in counts.items() if count != 1],
        "missing_keys": [list(key) for key in sorted(expected - set(keys))],
        "finish_reasons": dict(sorted(Counter(r["finish_reason"] for r in rows).items())),
        "thinking_status": dict(sorted(Counter(r["thinking_status"] for r in rows).items())),
        "score_status": dict(sorted(Counter(r["score_status"] for r in rows).items())),
        "nonstandard_records": [
            {key: row[key] for key in ("id", "seed", "condition", "finish_reason", "thinking_status", "score_status", "generated_tokens")}
            for row in rows
            if row["finish_reason"] != "eos" or row["score_status"] == "unresolved"
        ],
        "access_modes": dict(sorted(Counter(f"{r['condition']}:{r['access_mode']}" for r in rows).items())),
        "same_text_and_boundary_checks": checks,
        "manifest_rows": len(frozen_manifest),
        "completion": completed,
        "correct_source_gate_count": sum(
            row.get("correct_source_correctness") is True
            and row.get("correct_source_finish_reason") == "eos"
            and row.get("correct_source_thinking_status") == "parsable_thinking"
            for row in sources
        ),
    }


def clustered_ci(values_by_question: dict[str, list[float]], draws: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    ids = sorted(values_by_question)
    estimates = []
    for _ in range(draws):
        sampled = [rng.choice(ids) for _ in ids]
        values = [value for qid in sampled for value in values_by_question[qid]]
        estimates.append(statistics.fmean(values))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def exact_question_signflip(values_by_question: dict[str, list[float]]) -> float:
    question_means = [statistics.fmean(values_by_question[qid]) for qid in sorted(values_by_question)]
    observed = abs(statistics.fmean(question_means))
    distribution = [
        abs(statistics.fmean(sign * value for sign, value in zip(signs, question_means)))
        for signs in itertools.product((-1, 1), repeat=len(question_means))
    ]
    return sum(value >= observed - 1e-12 for value in distribution) / len(distribution)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, default=root / "runs/game24_correct_draft_specificity_20260922_raw/results.jsonl")
    parser.add_argument("--manifest", type=Path, default=root / "runs/game24_correct_draft_specificity_20260922_raw/manifest.json")
    parser.add_argument("--completion", type=Path, default=root / "runs/game24_correct_draft_specificity_20260922_raw/completion.json")
    parser.add_argument("--sources", type=Path, default=root / "runs/game24_correct_draft_specificity_20260921/selected_correct_pairs.jsonl")
    parser.add_argument("--failed", type=Path, default=root / "runs/game24_batch02_validation_20260921_raw/results.jsonl")
    parser.add_argument("--output", type=Path, default=root / "runs/game24_correct_draft_specificity_20260922_analysis")
    parser.add_argument("--bootstrap-draws", type=int, default=50_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260922)
    args = parser.parse_args()

    control = load_control(args.control)
    integrity = audit(control, args.sources, args.manifest, args.completion)
    if not integrity["complete_factorial_and_source_gates"]:
        raise RuntimeError(f"integrity audit failed: {integrity}")
    cidx = {(r["id"], r["seed"], r["condition"]): r for r in control}
    ids = integrity["question_ids"]
    seeds = integrity["seeds"]

    conditions = {}
    for condition in CONDITIONS:
        selected = [r for r in control if r["condition"] == condition]
        by_question = defaultdict(list)
        for row in selected:
            by_question[row["id"]].append(row["correct"])
        tokens = [row["generated_tokens"] for row in selected]
        conditions[condition] = {
            "correct": sum(row["correct"] for row in selected), "n": len(selected),
            "accuracy": statistics.fmean(row["correct"] for row in selected),
            "question_cluster_bootstrap_95ci": clustered_ci(by_question, args.bootstrap_draws, args.bootstrap_seed),
            "generated_tokens_mean": statistics.fmean(tokens),
            "generated_tokens_median": statistics.median(tokens), "generated_tokens_max": max(tokens),
        }

    correct_by_question = defaultdict(list)
    transitions = Counter()
    for qid in ids:
        for seed in seeds:
            late = cidx[qid, seed, "C_LATE"]["correct"]
            full = cidx[qid, seed, "C_FULL"]["correct"]
            correct_by_question[qid].append(late - full)
            transitions[(late, full)] += 1
    correct_effect = {
        "definition": "C_LATE_minus_C_FULL",
        "estimate": statistics.fmean(v for values in correct_by_question.values() for v in values),
        "question_cluster_bootstrap_95ci": clustered_ci(correct_by_question, args.bootstrap_draws, args.bootstrap_seed + 1),
        "transitions": {f"late{a}_full{b}": transitions[a, b] for a, b in itertools.product((0, 1), repeat=2)},
        "exact_mcnemar_p_two_sided": exact_mcnemar_p(transitions[0, 1], transitions[1, 0]),
    }

    failed = load_failed_rows(args.failed)
    failed = [row for row in failed if row["condition"] in ("R2", "R3")]
    fidx = {(r["id"], r["seed"], r["condition"]): r for r in failed}
    failed_units = {(r["id"], r["seed"]) for r in failed}
    expected_units = {(qid, seed) for qid in ids for seed in seeds}
    if failed_units != expected_units:
        raise RuntimeError("failed-history and correct-history units do not match")
    failed_by_question = defaultdict(list)
    interaction_by_question = defaultdict(list)
    for qid in ids:
        for seed in seeds:
            failed_delta = fidx[qid, seed, "R3"]["correct"] - fidx[qid, seed, "R2"]["correct"]
            correct_delta = cidx[qid, seed, "C_LATE"]["correct"] - cidx[qid, seed, "C_FULL"]["correct"]
            failed_by_question[qid].append(failed_delta)
            interaction_by_question[qid].append(failed_delta - correct_delta)
    interaction = {
        "definition": "(R3_minus_R2)_failed_minus_(C_LATE_minus_C_FULL)_correct",
        "failed_effect": statistics.fmean(v for values in failed_by_question.values() for v in values),
        "correct_effect": correct_effect["estimate"],
        "estimate": statistics.fmean(v for values in interaction_by_question.values() for v in values),
        "question_cluster_bootstrap_95ci": clustered_ci(interaction_by_question, args.bootstrap_draws, args.bootstrap_seed + 2),
        "exact_question_cluster_signflip_p_two_sided": exact_question_signflip(interaction_by_question),
    }
    unresolved_units = {
        (row["id"], row["seed"]) for row in control if row["score_status"] == "unresolved"
    }

    def sensitivity(policy: str) -> dict[str, Any]:
        correct_values = defaultdict(list)
        interaction_values = defaultdict(list)
        failed_values = defaultdict(list)
        included = 0
        late_correct = 0
        full_correct = 0
        for qid in ids:
            for seed in seeds:
                if policy == "exclude" and (qid, seed) in unresolved_units:
                    continue
                full = cidx[qid, seed, "C_FULL"]["correct"]
                late_row = cidx[qid, seed, "C_LATE"]
                late = 1 if policy == "unresolved_correct" and late_row["score_status"] == "unresolved" else late_row["correct"]
                failed_delta = fidx[qid, seed, "R3"]["correct"] - fidx[qid, seed, "R2"]["correct"]
                correct_values[qid].append(late - full)
                failed_values[qid].append(failed_delta)
                interaction_values[qid].append(failed_delta - (late - full))
                included += 1; late_correct += late; full_correct += full
        correct_flat = [v for values in correct_values.values() for v in values]
        failed_flat = [v for values in failed_values.values() for v in values]
        interaction_flat = [v for values in interaction_values.values() for v in values]
        return {
            "policy": policy, "units": included,
            "C_FULL_accuracy": full_correct / included,
            "C_LATE_accuracy": late_correct / included,
            "correct_effect": statistics.fmean(correct_flat),
            "failed_effect": statistics.fmean(failed_flat),
            "interaction": statistics.fmean(interaction_flat),
            "interaction_question_cluster_bootstrap_95ci": clustered_ci(
                interaction_values, args.bootstrap_draws, args.bootstrap_seed + (3 if policy == "unresolved_correct" else 4)
            ),
        }

    sensitivity_results = {
        "unresolved_scored_correct": sensitivity("unresolved_correct"),
        "unresolved_unit_excluded": sensitivity("exclude"),
    }
    per_question = []
    for qid in ids:
        per_question.append({
            "id": qid,
            "C_FULL": sum(cidx[qid, seed, "C_FULL"]["correct"] for seed in seeds),
            "C_LATE": sum(cidx[qid, seed, "C_LATE"]["correct"] for seed in seeds),
            "correct_delta": sum(correct_by_question[qid]) / len(seeds),
            "failed_R2": sum(fidx[qid, seed, "R2"]["correct"] for seed in seeds),
            "failed_R3": sum(fidx[qid, seed, "R3"]["correct"] for seed in seeds),
            "failed_delta": sum(failed_by_question[qid]) / len(seeds),
            "interaction": sum(interaction_by_question[qid]) / len(seeds),
        })

    analysis = {
        "analysis_version": "game24_correct_specificity_v1_20260922",
        "inputs": {"control_sha256": sha256(args.control), "failed_sha256": sha256(args.failed), "source_pairs_sha256": sha256(args.sources)},
        "protocol": {"paired_unit": "question-seed", "uncertainty": "percentile bootstrap over question clusters", "bootstrap_draws": args.bootstrap_draws, "unresolved_policy": "incorrect"},
        "audit": integrity, "conditions": conditions, "correct_history_effect": correct_effect,
        "failed_vs_correct_interaction": interaction, "unresolved_sensitivity": sensitivity_results,
        "per_question": per_question,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output / "per_question.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_question[0]))
        writer.writeheader(); writer.writerows(per_question)

    def pct(value: float) -> str:
        return f"{100 * value:.1f}%"
    ci = correct_effect["question_cluster_bootstrap_95ci"]
    ii = interaction["question_cluster_bootstrap_95ci"]
    report = f"""# Game24 correct-history specificity control

Input SHA-256: `{analysis['inputs']['control_sha256']}`

## Integrity

- Complete 8-question × 2-seed × 2-condition factorial: `{integrity['complete_factorial_and_source_gates']}`
- Correct-source gates passed: `{integrity['correct_source_gate_count']}/8`
- Same prompt/input/draft span and first token: `{integrity['same_text_and_boundary_checks']}`
- Finish reasons: `{integrity['finish_reasons']}`; score status: `{integrity['score_status']}`

## Accuracy

- C_FULL: {conditions['C_FULL']['correct']}/{conditions['C_FULL']['n']} ({pct(conditions['C_FULL']['accuracy'])})
- C_LATE: {conditions['C_LATE']['correct']}/{conditions['C_LATE']['n']} ({pct(conditions['C_LATE']['accuracy'])})

## Correct-history blocking effect

- C_LATE - C_FULL: **{pct(correct_effect['estimate'])}**
- Question-cluster bootstrap 95% CI: [{pct(ci[0])}, {pct(ci[1])}]
- Exact paired McNemar p: {correct_effect['exact_mcnemar_p_two_sided']:.4g}
- Transitions: `{correct_effect['transitions']}`

## Failed-vs-correct specificity interaction

- Failed effect R3-R2: {pct(interaction['failed_effect'])}
- Correct effect C_LATE-C_FULL: {pct(interaction['correct_effect'])}
- Difference-in-differences: **{pct(interaction['estimate'])}**
- Question-cluster bootstrap 95% CI: [{pct(ii[0])}, {pct(ii[1])}]
- Exact question-cluster sign-flip p: {interaction['exact_question_cluster_signflip_p_two_sided']:.4g}

## Unresolved-output sensitivity

- Score the one unresolved C_LATE output as correct: interaction {pct(sensitivity_results['unresolved_scored_correct']['interaction'])}, CI {[pct(x) for x in sensitivity_results['unresolved_scored_correct']['interaction_question_cluster_bootstrap_95ci']]}
- Exclude its paired unit: interaction {pct(sensitivity_results['unresolved_unit_excluded']['interaction'])}, CI {[pct(x) for x in sensitivity_results['unresolved_unit_excluded']['interaction_question_cluster_bootstrap_95ci']]}
- Nonstandard record: `{integrity['nonstandard_records']}`
"""
    (args.output / "summary.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
