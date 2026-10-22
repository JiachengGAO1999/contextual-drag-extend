"""Frozen analysis for the eight-question Game24 confirmation experiment.

This is intentionally a thin, task-specific wrapper around the already audited
factorial/paired analysis utilities.  It consumes persisted scorer decisions,
never regenerates answers, and refuses incomplete factorials.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyze_continued_access_math_20260921 import (
    CONDITIONS,
    EFFECTS,
    analyze_scope,
    audit,
    load_rows,
    pct,
    sha256,
    write_csv,
)


def per_question(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["id"]][row["condition"]].append(row["correct"])
    return [
        {
            "id": qid,
            **{
                condition: {
                    "correct": sum(grouped[qid][condition]),
                    "n": len(grouped[qid][condition]),
                }
                for condition in CONDITIONS
            },
        }
        for qid in sorted(grouped)
    ]


def markdown(analysis: dict[str, Any]) -> str:
    result = analysis["result"]
    lines = [
        "# Frozen Game24 confirmation analysis",
        "",
        f"Input SHA-256: `{analysis['input']['sha256']}`",
        "",
        "Primary accuracy is `correctness is True` divided by all requests. Persisted",
        "generation-time scorer decisions are used without regeneration or relabeling.",
        "",
        "## Accuracy",
        "",
        "| R0 | R2 | R3 | R4 |",
        "|---:|---:|---:|---:|",
    ]
    cells = []
    for condition in CONDITIONS:
        stats = result["conditions"][condition]
        cells.append(f"{stats['correct']}/{stats['n']} ({pct(stats['accuracy'])}%)")
    lines.append("| " + " | ".join(cells) + " |")
    lines.extend([
        "",
        "## Paired effects (percentage points)",
        "",
        "| Effect | Estimate [question-cluster bootstrap 95% CI] | Exact McNemar p |",
        "|---|---:|---:|",
    ])
    for name in EFFECTS:
        effect = result["effects"][name]
        low, high = effect["question_cluster_bootstrap_95ci"]
        lines.append(
            f"| {name} | {pct(effect['estimate'])} [{pct(low)}, {pct(high)}] | "
            f"{effect['exact_mcnemar_p_two_sided']:.4g} |"
        )
    lines.extend([
        "",
        "## Precommitted continuation gate",
        "",
        f"- Observed drag (R0 > R2): `{result['interpretation_gate']['observed_drag_R0_gt_R2']}`",
        f"- Continued-access recovery (R3 > R2): `{result['interpretation_gate']['observed_R3_recovery_R3_gt_R2']}`",
        f"- Launch correct-draft specificity control: `{result['interpretation_gate']['strict_recovery_pattern']}`",
        "",
        "## Integrity audit",
        "",
        f"- Complete factorial: `{analysis['audit']['complete_factorial']}`",
        f"- Rows/questions/seeds: {analysis['audit']['rows']}/{analysis['audit']['questions']}/{analysis['audit']['seeds']}",
        f"- Finish reasons: {analysis['audit']['finish_reasons']}",
        f"- Score status: {analysis['audit']['score_status']}",
        f"- Same-text checks: {analysis['audit']['same_text_intervention_checks']}",
        "",
        "The gate is descriptive and fixed before reading the complete results. It does",
        "not replace uncertainty intervals or paired transition reporting.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "runs" / "game24_batch02_validation_20260921_raw" / "results.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "runs" / "game24_batch02_validation_20260921_analysis",
    )
    parser.add_argument("--bootstrap-draws", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260921)
    args = parser.parse_args()

    rows = load_rows(args.input)
    integrity = audit(rows)
    if integrity["questions"] != 8:
        raise RuntimeError(f"expected exactly eight frozen questions: {integrity['questions']}")
    if not integrity["complete_factorial"]:
        raise RuntimeError(f"factorial integrity audit failed: {integrity}")

    result = analyze_scope(rows, args.bootstrap_draws, args.bootstrap_seed)
    analysis = {
        "analysis_version": "game24_confirmation_v1_20260921",
        "input": {"path": str(args.input), "sha256": sha256(args.input)},
        "protocol": {
            "accuracy_unit": "request (two fixed seeds per question)",
            "paired_unit": "question-seed",
            "uncertainty": "percentile bootstrap over question clusters",
            "scoring": "persisted frozen scorer output; no rescoring",
            "continuation_gate": "launch specificity iff R0 > R2 and R3 > R2",
        },
        "audit": integrity,
        "result": result,
        "per_question": per_question(rows),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(rows, args.output / "request_level.csv")
    report = markdown(analysis)
    (args.output / "summary.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
