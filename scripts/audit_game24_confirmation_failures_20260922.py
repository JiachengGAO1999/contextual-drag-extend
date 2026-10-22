"""Outcome-blind-format audit of incorrect Game24 confirmation outputs.

This diagnostic uses persisted scorer labels.  It categorizes failed final
answers and checks only normalized textual reuse of the frozen failed answer;
it does not infer semantic or algebraic equivalence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selective_context.tasks import extract_math_box


def normalize_latex(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.replace("\\left", "").replace("\\right", "")
    text = text.replace("\\dfrac", "\\frac")
    return re.sub(r"\s+", "", text)


def condition(record: dict) -> str:
    generation = record["init_response_generations"][0]
    request = generation.get("selective_context_metadata", {}).get("request", {})
    return request.get("condition_id") or record["init_response_generations_metadata"]["intervention"]["condition_id"]


def seed(record: dict) -> int:
    generation = record["init_response_generations"][0]
    request = generation.get("selective_context_metadata", {}).get("request", {})
    return int(request.get("sample_seed") or record["init_response_generations_metadata"]["intervention"]["sample_seed"])


def category(answer: str | None, expected: list[int]) -> str:
    if answer is None:
        return "unparsed"
    if re.fullmatch(r"\s*24\s*", answer):
        return "scalar_24"
    numbers = sorted(int(value) for value in re.findall(r"(?<![A-Za-z])\d+", answer))
    if numbers != sorted(expected):
        return "number_multiset_violation"
    return "arithmetic_or_other"


def main() -> None:
    root = ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=root / "runs" / "game24_batch02_validation_20260921_raw" / "results.jsonl")
    parser.add_argument("--pairs", type=Path, default=root / "runs" / "game24_batch02_validation_source_pairs.jsonl")
    parser.add_argument("--output", type=Path, default=root / "runs" / "game24_batch02_validation_20260921_analysis" / "failure_audit.json")
    args = parser.parse_args()

    records = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = {str(row["id"]): row for row in (
        json.loads(line) for line in args.pairs.read_text(encoding="utf-8").splitlines() if line.strip()
    )}
    rows = []
    for record in records:
        generation = record["init_response_generations"][0]
        if generation.get("correctness") is True:
            continue
        qid = str(record["id"])
        source_answer = extract_math_box(pairs[qid]["traj1"])
        answer = generation.get("extracted_answer")
        rows.append({
            "id": qid,
            "seed": seed(record),
            "condition": condition(record),
            "correctness": generation.get("correctness"),
            "finish_reason": generation.get("finish_reason"),
            "extracted_answer": answer,
            "category": category(answer, [int(value) for value in record["answer"]]),
            "frozen_failed_answer": source_answer,
            "normalized_exact_failed_answer_reuse": (
                answer is not None
                and source_answer is not None
                and normalize_latex(answer) == normalize_latex(source_answer)
            ),
        })

    report = {
        "scope": "diagnostic; normalized textual equality is not algebraic equivalence",
        "incorrect_or_unparsed_n": len(rows),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "by_condition": {
            condition_id: {
                "n": len(selected),
                "categories": dict(sorted(Counter(row["category"] for row in selected).items())),
                "normalized_exact_failed_answer_reuse": sum(
                    row["normalized_exact_failed_answer_reuse"] for row in selected
                ),
            }
            for condition_id in ("R0", "R2", "R3", "R4")
            if (selected := [row for row in rows if row["condition"] == condition_id])
        },
        "rows": rows,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("incorrect_or_unparsed_n", "category_counts", "by_condition")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
