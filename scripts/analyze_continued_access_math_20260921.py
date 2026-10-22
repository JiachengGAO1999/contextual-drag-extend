"""Analyze the frozen 16-question continued-access MATH experiment.

This script is CPU-only and uses the correctness decisions persisted by the
frozen generation-time scorer. It never regenerates or rescored responses.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


CONDITIONS = ("R0", "R2", "R3", "R4")
EFFECTS = {
    "drag_R0_minus_R2": ("R0", "R2"),
    "continued_access_R3_minus_R2": ("R3", "R2"),
    "whole_path_R4_minus_R2": ("R4", "R2"),
    "timing_R4_minus_R3": ("R4", "R3"),
    "R3_minus_R0": ("R3", "R0"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def exact_mcnemar_p(discordant_a0_b1: int, discordant_a1_b0: int) -> float:
    n = discordant_a0_b1 + discordant_a1_b0
    if n == 0:
        return 1.0
    smaller = min(discordant_a0_b1, discordant_a1_b0)
    tail = sum(math.comb(n, k) for k in range(smaller + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            generations = raw.get("init_response_generations") or []
            if len(generations) != 1:
                raise ValueError(f"line {line_number}: expected exactly one generation")
            generation = generations[0]
            metadata = generation.get("selective_context_metadata") or {}
            request = metadata.get("request") or {}
            condition = request.get("condition_id")
            seed = request.get("sample_seed")
            correctness = generation.get("correctness")
            if condition not in CONDITIONS:
                raise ValueError(f"line {line_number}: invalid condition {condition!r}")
            if not isinstance(seed, int):
                raise ValueError(f"line {line_number}: missing integer sample_seed")
            if correctness not in (True, False, None):
                raise ValueError(f"line {line_number}: invalid correctness value {correctness!r}")
            rows.append(
                {
                    "id": str(raw["id"]),
                    "seed": seed,
                    "condition": condition,
                    "stratum": str(raw["stratum"]),
                    "benchmark": str(raw.get("benchmark", "")),
                    # The frozen evaluator uses null when no complete final
                    # last-box answer can be extracted. The primary metric fixes
                    # unparsed outputs as incorrect and reports parse rate apart.
                    "correct": int(correctness is True),
                    "score_status": (
                        "correct" if correctness is True else "incorrect" if correctness is False else "unresolved"
                    ),
                    "extracted_answer": generation.get("extracted_answer"),
                    "finish_reason": str(generation.get("finish_reason")),
                    "thinking_status": str(raw.get("thinking_status")),
                    "generated_tokens": len(raw.get("generated_token_ids") or []),
                    "first_generated_token": (raw.get("generated_token_ids") or [None])[0],
                    "response_chars": len(generation.get("generated_response") or ""),
                    "prompt_sha256": request.get("prompt_sha256"),
                    "input_ids_sha256": request.get("input_ids_sha256"),
                    "access_mode": metadata.get("access_mode"),
                    "draft_token_span": request.get("draft_token_span"),
                    "mask_token_spans": request.get("mask_token_spans"),
                    "scorer_version": generation.get("scorer_version"),
                    "gold_answer": raw.get("answer"),
                    "generated_response": generation.get("generated_response"),
                }
            )
    return rows


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [(r["id"], r["seed"], r["condition"]) for r in rows]
    duplicates = [list(key) for key, count in Counter(keys).items() if count != 1]
    question_ids = sorted({r["id"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    expected = {(qid, seed, condition) for qid in question_ids for seed in seeds for condition in CONDITIONS}
    observed = set(keys)
    strata_by_question: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        strata_by_question[row["id"]].add(row["stratum"])
    inconsistent_strata = {qid: sorted(values) for qid, values in strata_by_question.items() if len(values) != 1}
    counts = Counter((r["stratum"], r["condition"]) for r in rows)
    indexed = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    paired_units = sorted({(r["id"], r["seed"]) for r in rows})
    r2_r3_prompt_hash_matches = sum(
        indexed[(qid, seed, "R2")]["prompt_sha256"] == indexed[(qid, seed, "R3")]["prompt_sha256"]
        for qid, seed in paired_units
    )
    r2_r3_input_hash_matches = sum(
        indexed[(qid, seed, "R2")]["input_ids_sha256"] == indexed[(qid, seed, "R3")]["input_ids_sha256"]
        for qid, seed in paired_units
    )
    r2_r3_first_token_matches = sum(
        indexed[(qid, seed, "R2")]["first_generated_token"]
        == indexed[(qid, seed, "R3")]["first_generated_token"]
        for qid, seed in paired_units
    )
    return {
        "rows": len(rows),
        "questions": len(question_ids),
        "seeds": seeds,
        "conditions": list(CONDITIONS),
        "duplicate_keys": duplicates,
        "missing_keys": [list(key) for key in sorted(expected - observed)],
        "unexpected_keys": [list(key) for key in sorted(observed - expected)],
        "inconsistent_question_strata": inconsistent_strata,
        "counts_by_stratum_condition": {
            f"{stratum}:{condition}": count for (stratum, condition), count in sorted(counts.items())
        },
        "finish_reasons": dict(sorted(Counter(r["finish_reason"] for r in rows).items())),
        "thinking_status": dict(sorted(Counter(r["thinking_status"] for r in rows).items())),
        "scorer_versions": dict(sorted(Counter(str(r["scorer_version"]) for r in rows).items())),
        "score_status": dict(sorted(Counter(r["score_status"] for r in rows).items())),
        "unresolved_by_stratum_condition": {
            f"{stratum}:{condition}": count
            for (stratum, condition), count in sorted(
                Counter(
                    (r["stratum"], r["condition"])
                    for r in rows
                    if r["score_status"] == "unresolved"
                ).items()
            )
        },
        "complete_factorial": not duplicates and observed == expected and not inconsistent_strata,
        "same_text_intervention_checks": {
            "paired_question_seed_units": len(paired_units),
            "R2_R3_prompt_sha256_matches": r2_r3_prompt_hash_matches,
            "R2_R3_input_ids_sha256_matches": r2_r3_input_hash_matches,
            "R2_R3_first_generated_token_matches": r2_r3_first_token_matches,
            "all_R2_R3_prompt_hashes_match": r2_r3_prompt_hash_matches == len(paired_units),
            "all_R2_R3_input_ids_match": r2_r3_input_hash_matches == len(paired_units),
            "all_R2_R3_first_tokens_match": r2_r3_first_token_matches == len(paired_units),
            "access_mode_counts": dict(sorted(Counter(f"{r['condition']}:{r['access_mode']}" for r in rows).items())),
        },
    }


def cluster_bootstrap_accuracy(
    rows: list[dict[str, Any]], condition: str, rng: random.Random, draws: int
) -> tuple[float, float]:
    by_question: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if row["condition"] == condition:
            by_question[row["id"]].append(row["correct"])
    question_ids = sorted(by_question)
    samples: list[float] = []
    for _ in range(draws):
        chosen = [rng.choice(question_ids) for _ in question_ids]
        values = [value for qid in chosen for value in by_question[qid]]
        samples.append(statistics.fmean(values))
    return percentile(samples, 0.025), percentile(samples, 0.975)


def paired_records(rows: list[dict[str, Any]], left: str, right: str) -> list[tuple[str, int, int, int]]:
    indexed = {(r["id"], r["seed"], r["condition"]): r["correct"] for r in rows}
    pairs: list[tuple[str, int, int, int]] = []
    for qid, seed in sorted({(r["id"], r["seed"]) for r in rows}):
        pairs.append((qid, seed, indexed[(qid, seed, left)], indexed[(qid, seed, right)]))
    return pairs


def cluster_bootstrap_effect(
    pairs: list[tuple[str, int, int, int]], rng: random.Random, draws: int
) -> tuple[float, float]:
    by_question: dict[str, list[int]] = defaultdict(list)
    for qid, _seed, left, right in pairs:
        by_question[qid].append(left - right)
    question_ids = sorted(by_question)
    samples: list[float] = []
    for _ in range(draws):
        chosen = [rng.choice(question_ids) for _ in question_ids]
        values = [value for qid in chosen for value in by_question[qid]]
        samples.append(statistics.fmean(values))
    return percentile(samples, 0.025), percentile(samples, 0.975)


def analyze_scope(rows: list[dict[str, Any]], bootstrap_draws: int, bootstrap_seed: int) -> dict[str, Any]:
    rng = random.Random(bootstrap_seed)
    condition_stats: dict[str, Any] = {}
    for condition in CONDITIONS:
        selected = [r for r in rows if r["condition"] == condition]
        ci_low, ci_high = cluster_bootstrap_accuracy(selected, condition, rng, bootstrap_draws)
        token_values = [r["generated_tokens"] for r in selected]
        unresolved = sum(r["score_status"] == "unresolved" for r in selected)
        correct = sum(r["correct"] for r in selected)
        condition_stats[condition] = {
            "correct": correct,
            "n": len(selected),
            "accuracy": statistics.fmean(r["correct"] for r in selected),
            "unresolved": unresolved,
            "accuracy_sensitivity_bounds": [
                correct / len(selected),
                (correct + unresolved) / len(selected),
            ],
            "accuracy_cluster_bootstrap_95ci": [ci_low, ci_high],
            "finish_reasons": dict(sorted(Counter(r["finish_reason"] for r in selected).items())),
            "thinking_status": dict(sorted(Counter(r["thinking_status"] for r in selected).items())),
            "generated_tokens_mean": statistics.fmean(token_values),
            "generated_tokens_median": statistics.median(token_values),
            "generated_tokens_max": max(token_values),
        }

    effects: dict[str, Any] = {}
    for name, (left, right) in EFFECTS.items():
        pairs = paired_records(rows, left, right)
        transitions = Counter((left_value, right_value) for _qid, _seed, left_value, right_value in pairs)
        ci_low, ci_high = cluster_bootstrap_effect(pairs, rng, bootstrap_draws)
        effects[name] = {
            "left": left,
            "right": right,
            "estimate": statistics.fmean(a - b for _qid, _seed, a, b in pairs),
            "question_cluster_bootstrap_95ci": [ci_low, ci_high],
            "paired_n": len(pairs),
            "transitions": {
                "left0_right0": transitions[(0, 0)],
                "left0_right1": transitions[(0, 1)],
                "left1_right0": transitions[(1, 0)],
                "left1_right1": transitions[(1, 1)],
            },
            "exact_mcnemar_p_two_sided": exact_mcnemar_p(transitions[(0, 1)], transitions[(1, 0)]),
        }

    return {
        "questions": len({r["id"] for r in rows}),
        "rows": len(rows),
        "conditions": condition_stats,
        "effects": effects,
        "interpretation_gate": {
            "observed_drag_R0_gt_R2": condition_stats["R0"]["accuracy"] > condition_stats["R2"]["accuracy"],
            "observed_R3_recovery_R3_gt_R2": condition_stats["R3"]["accuracy"] > condition_stats["R2"]["accuracy"],
            "strict_recovery_pattern": (
                condition_stats["R0"]["accuracy"] > condition_stats["R2"]["accuracy"]
                and condition_stats["R3"]["accuracy"] > condition_stats["R2"]["accuracy"]
            ),
        },
    }


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}"


def write_csv(rows: Iterable[dict[str, Any]], path: Path) -> None:
    rows = list(rows)
    public_fields = [
        "id", "seed", "condition", "stratum", "benchmark", "correct", "score_status",
        "extracted_answer", "finish_reason", "thinking_status", "generated_tokens",
        "response_chars", "prompt_sha256", "input_ids_sha256", "access_mode", "scorer_version",
        "first_generated_token",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=public_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Frozen MATH continued-access analysis",
        "",
        f"Input SHA-256: `{analysis['input']['sha256']}`",
        "",
        "The persisted frozen scorer decisions are analyzed without regeneration or rescoring.",
        "MATH500 and MATH-train strata are primary and are not pooled for the paper claim;",
        "the combined row is descriptive only.",
        "",
        "## Accuracy",
        "",
        "| Scope | R0 | R2 | R3 | R4 |",
        "|---|---:|---:|---:|---:|",
    ]
    for scope, result in analysis["scopes"].items():
        values = []
        for condition in CONDITIONS:
            stats = result["conditions"][condition]
            values.append(f"{stats['correct']}/{stats['n']} ({pct(stats['accuracy'])}%)")
        lines.append(f"| {scope} | " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "## Termination and unresolved scores",
            "",
            "| Scope | Condition | EOS | Length | Unresolved | Accuracy bounds | Mean tokens |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for scope, result in analysis["scopes"].items():
        for condition in CONDITIONS:
            stats = result["conditions"][condition]
            low, high = stats["accuracy_sensitivity_bounds"]
            finishes = stats["finish_reasons"]
            lines.append(
                f"| {scope} | {condition} | {finishes.get('eos', 0)} | "
                f"{finishes.get('length', 0)} | {stats['unresolved']} | "
                f"{pct(low)}--{pct(high)}% | {stats['generated_tokens_mean']:.1f} |"
            )
    lines.extend(
        [
            "",
            "## Paired effects (percentage points)",
            "",
            "| Scope | R0-R2 (drag) | R3-R2 (continued access) | R4-R2 | R4-R3 | R3-R0 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    effect_order = list(EFFECTS)
    for scope, result in analysis["scopes"].items():
        values = []
        for effect_name in effect_order:
            effect = result["effects"][effect_name]
            low, high = effect["question_cluster_bootstrap_95ci"]
            values.append(f"{pct(effect['estimate'])} [{pct(low)}, {pct(high)}]")
        lines.append(f"| {scope} | " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "Intervals are percentile 95% bootstrap intervals resampling questions as clusters;",
            "both seeds remain together within a sampled question. Exact paired transition counts",
            "and two-sided exact McNemar p-values are in `analysis.json`.",
            "",
            "## Integrity audit",
            "",
            f"- Complete factorial: `{analysis['audit']['complete_factorial']}`",
            f"- Rows/questions: {analysis['audit']['rows']}/{analysis['audit']['questions']}",
            f"- Seeds: {analysis['audit']['seeds']}",
            f"- Finish reasons: {analysis['audit']['finish_reasons']}",
            f"- Thinking status: {analysis['audit']['thinking_status']}",
            f"- Score status: {analysis['audit']['score_status']}",
            f"- Unresolved by stratum/condition: {analysis['audit']['unresolved_by_stratum_condition']}",
            f"- Same-text intervention checks: {analysis['audit']['same_text_intervention_checks']}",
            "- Primary accuracy is frozen as correctness=True divided by all requests;",
            "  a missing complete final box counts as incorrect and is separately reported as unparsed.",
            "- The diagnostic queue must not overwrite primary labels from intermediate prose.",
            "",
        ]
    )
    return "\n".join(lines)


def build_latex(analysis: dict[str, Any]) -> str:
    lines = [
        "% Auto-generated by scripts/analyze_continued_access_math_20260921.py",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Stratum & R0 & R2 & R3 & R4 \\\\",
        "\\midrule",
    ]
    labels = {
        "MATH500_Qwen3_1.7B": "MATH500 / Qwen3-1.7B draft",
        "MATH_train_Qwen3_4B": "MATH-train / Qwen3-4B draft",
        "combined16_exploratory": "Combined (descriptive)",
    }
    for scope, result in analysis["scopes"].items():
        cells = []
        for condition in CONDITIONS:
            stats = result["conditions"][condition]
            cells.append(f"{stats['correct']}/{stats['n']}")
        lines.append(f"{labels.get(scope, scope)} & " + " & ".join(cells) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "runs" / "math_external_16q_20260920_raw" / "results.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "runs" / "math_external_16q_20260920_analysis",
    )
    parser.add_argument("--bootstrap-draws", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260921)
    args = parser.parse_args()

    rows = load_rows(args.input)
    integrity = audit(rows)
    if not integrity["complete_factorial"]:
        raise RuntimeError(f"factorial integrity audit failed: {integrity}")

    args.output.mkdir(parents=True, exist_ok=True)
    scopes: dict[str, Any] = {}
    for index, stratum in enumerate(sorted({r["stratum"] for r in rows})):
        scopes[stratum] = analyze_scope(
            [r for r in rows if r["stratum"] == stratum],
            args.bootstrap_draws,
            args.bootstrap_seed + index,
        )
    scopes["combined16_exploratory"] = analyze_scope(
        rows, args.bootstrap_draws, args.bootstrap_seed + 100
    )

    analysis = {
        "analysis_version": "continued_access_math_v1_20260921",
        "input": {"path": str(args.input), "sha256": sha256(args.input)},
        "protocol": {
            "primary_reporting": "source-stratified",
            "combined16": "exploratory_descriptive_only",
            "accuracy_unit": "request (two fixed seeds per question)",
            "paired_unit": "question-seed",
            "uncertainty": "percentile bootstrap over question clusters",
            "bootstrap_draws": args.bootstrap_draws,
            "bootstrap_seed": args.bootstrap_seed,
            "scoring": "persisted frozen scorer output; no rescoring",
        },
        "audit": integrity,
        "scopes": scopes,
    }
    (args.output / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(rows, args.output / "request_level.csv")
    with (args.output / "unparsed_diagnostic_queue.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            if row["score_status"] == "unresolved":
                review = {
                    key: row[key]
                    for key in (
                        "id", "seed", "condition", "stratum", "gold_answer",
                        "extracted_answer", "finish_reason", "thinking_status", "generated_response",
                    )
                }
                handle.write(json.dumps(review, ensure_ascii=False) + "\n")
    (args.output / "summary.md").write_text(build_markdown(analysis), encoding="utf-8")
    (args.output / "accuracy_table.tex").write_text(build_latex(analysis), encoding="utf-8")
    print(build_markdown(analysis))


if __name__ == "__main__":
    main()
