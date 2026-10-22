"""Byte-level audit of whether clean R0 is the matched prefill-deletion reset."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selective_context.tasks import independent_prompt


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def condition(record: dict) -> str:
    generation = record["init_response_generations"][0]
    request = generation.get("selective_context_metadata", {}).get("request", {})
    return request.get("condition_id") or record["init_response_generations_metadata"]["intervention"]["condition_id"]


def first_difference(left: str, right: str) -> int | None:
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index
    return None if len(left) == len(right) else min(len(left), len(right))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "runs" / "math_external_16q_20260920_raw" / "results.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runs" / "math_external_16q_20260920_analysis" / "reset_equivalence.json",
    )
    args = parser.parse_args()

    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    r0_records = [record for record in records if condition(record) == "R0"]
    checks = []
    for record in r0_records:
        expected = independent_prompt(record["problem"], draft=None, task="math500")
        actual = record["init_response_prompt"]
        offset = actual.find(expected)
        contains_expected_once = offset >= 0 and actual.find(expected, offset + 1) < 0
        prefix = actual[:offset] if contains_expected_once else ""
        suffix = actual[offset + len(expected):] if contains_expected_once else ""
        checks.append(
            {
                "id": str(record["id"]),
                "stratum": record["stratum"],
                "actual_sha256": digest(actual),
                "expected_reset_sha256": digest(expected),
                "byte_identical": actual == expected,
                "first_difference": first_difference(actual, expected),
                "actual_chars": len(actual),
                "expected_chars": len(expected),
                "contains_expected_once": contains_expected_once,
                "chat_prefix": prefix,
                "chat_suffix": suffix,
            }
        )

    wrappers = {(check["chat_prefix"], check["chat_suffix"]) for check in checks if check["contains_expected_once"]}
    all_content_identical = bool(checks) and all(check["contains_expected_once"] for check in checks)
    one_fixed_wrapper = len(wrappers) == 1
    reset_equivalent = all_content_identical and one_fixed_wrapper
    report = {
        "audit_version": "reset_equivalence_v1_20260921",
        "definition": (
            "Matched deletion/reset removes the entire failed-draft block before prefill, including "
            "the incorrect-answer label and draft delimiters, while retaining the original problem "
            "and the identical independent-solve suffix."
        ),
        "comparison": (
            "recorded chat-rendered R0 prompt contains independent_prompt(problem, "
            "draft=None, task='math500') under one fixed wrapper"
        ),
        "r0_records": len(checks),
        "questions": len({check["id"] for check in checks}),
        "all_full_prompt_byte_identical_to_unwrapped_text": all(check["byte_identical"] for check in checks),
        "all_user_content_byte_identical": all_content_identical,
        "one_fixed_chat_wrapper": one_fixed_wrapper,
        "chat_wrapper": (
            {"prefix": next(iter(wrappers))[0], "suffix": next(iter(wrappers))[1]}
            if one_fixed_wrapper else None
        ),
        "full_prompt_vs_unwrapped_text_differences": [
            check for check in checks if not check["byte_identical"]
        ],
        "decision": (
            "reuse_R0_as_matched_reset"
            if reset_equivalent
            else "run_distinct_reset_or_fix_prompt_mismatch"
        ),
        "scope_boundary": (
            "A condition that preserves an orphaned error label or draft delimiter is a different "
            "control and is not covered by this equivalence result."
        ),
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "r0_records", "questions", "all_user_content_byte_identical",
        "one_fixed_chat_wrapper", "chat_wrapper", "decision"
    )}, indent=2))


if __name__ == "__main__":
    main()
