"""Audit the fixed 32-question baseline-only acquisition batch."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs" / "game24-baseline-screen-vllm-20260918-batch02"


def load_records():
    path = RUN / "results.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def item(record):
    return record["init_response_generations"][0]


def classify(record):
    response = item(record)
    if response.get("finish_reason") != "eos":
        return "length_limited"
    if record.get("thinking_status") != "parsable_thinking":
        return "unparseable_thinking"
    correctness = response.get("correctness")
    if correctness is True:
        return "correct"
    if correctness is not False:
        return "unscored"
    answer = response.get("extracted_answer") or ""
    if re.fullmatch(r"\s*24\s*", answer):
        return "scalar_boxed_24_format_only_candidate"
    numbers = [int(value) for value in re.findall(r"(?<![A-Za-z])\d+", answer)]
    expected = sorted(int(value) for value in record["answer"])
    if sorted(numbers) != expected:
        return "wrong_number_multiset"
    return "wrong_arithmetic_or_expression"


def row_for(record, category):
    response = item(record)
    text = record.get("final_response", "")
    return {
        "id": str(record["id"]),
        "numbers": record["answer"],
        "sample_index": response.get("response_id"),
        "category": category,
        "finish_reason": response.get("finish_reason"),
        "thinking_status": record.get("thinking_status"),
        "extracted_answer": response.get("extracted_answer"),
        "tail": text[-1200:].replace("\n", " "),
    }


def main():
    records = load_records()
    groups = defaultdict(list)
    for record in records:
        groups[str(record["id"])].append(record)
    categories = {id_: [classify(record) for record in values] for id_, values in groups.items()}
    status_counts = Counter(classify(record) for record in records)
    rows = []
    review = []
    for id_, values in groups.items():
        counts = Counter(categories[id_])
        substantive = counts["wrong_number_multiset"] + counts["wrong_arithmetic_or_expression"]
        eligible = counts["correct"] >= 2 and substantive >= 2
        rows.append({
            "id": id_,
            "numbers": values[0]["answer"],
            "n": len(values),
            "correct": counts["correct"],
            "substantive_failed": substantive,
            "format_only_candidate": counts["scalar_boxed_24_format_only_candidate"],
            "length_limited": counts["length_limited"],
            "unparseable_or_unscored": counts["unparseable_thinking"] + counts["unscored"],
            "eligible_before_manual_audit": eligible,
            "categories": dict(counts),
        })
        for record in values:
            category = classify(record)
            if category != "correct":
                review.append(row_for(record, category))
    rows.sort(key=lambda row: int(row["id"]))
    review.sort(key=lambda row: (int(row["id"]), row["sample_index"] or -1))

    summary = json.loads((RUN / "summary.json").read_text(encoding="utf-8"))
    analysis = {
        "run": str(RUN),
        "summary": summary,
        "status_counts": dict(status_counts),
        "question_count": len(rows),
        "eligible_before_manual_audit": [row["id"] for row in rows if row["eligible_before_manual_audit"]],
        "eligible_count_before_manual_audit": sum(row["eligible_before_manual_audit"] for row in rows),
        "question_rows": rows,
        "review_rows": review,
        "interpretation": {
            "primary_unit": "question",
            "selection_rule": "at least 2 correct and at least 2 EOS+parsable substantive failed traces",
            "intervention_outcomes_used": False,
            "manual_audit_required": True,
        },
    }
    (RUN / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUN / "manual_review_queue.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Batch-02 baseline-only acquisition audit",
        "",
        "No intervention outcome was used. This report is an eligibility audit only.",
        "",
        "## Aggregate",
        "",
        f"- Generations: {summary['generations']} across {summary['questions']} questions; samples/question: {summary['samples_per_question']}",
        f"- EOS: {summary['stopped']}/{summary['generations']}; length-limited: {summary['length_limited']}",
        f"- Thinking parseable: {summary['parseable_thinking']}/{summary['generations']}",
        f"- Official correct/incorrect/unscored: {summary['official_correct']}/{summary['official_incorrect']}/{summary['official_unparseable_or_null']}",
        f"- Automatic categories: {dict(status_counts)}",
        f"- Questions eligible before manual audit: {analysis['eligible_count_before_manual_audit']}/{len(rows)}: {', '.join(analysis['eligible_before_manual_audit']) or 'none'}",
        "",
        "## Question-level eligibility",
        "",
        "| ID | Correct | Substantive failed | Scalar/format candidate | Length | Unparseable/unscored | Eligible pre-audit |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['correct']} | {row['substantive_failed']} | "
            f"{row['format_only_candidate']} | {row['length_limited']} | "
            f"{row['unparseable_or_unscored']} | {'yes' if row['eligible_before_manual_audit'] else 'no'} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The primary unit is the question; 16 generations are repeated measurements, not 16 independent questions.",
        "- Length-limited, unparseable, and unscored records are not promoted to failed drafts.",
        "- `scalar_boxed_24_format_only_candidate` is kept separate because a scalar final answer may hide a valid expression in the body; it requires manual review before exclusion or promotion.",
        "- A question is not formally frozen for intervention until the pre-audit candidates are manually confirmed as substantive failed traces and provenance is recorded.",
        "",
    ]
    (RUN / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "summary": summary,
        "status_counts": dict(status_counts),
        "eligible_before_manual_audit": analysis["eligible_before_manual_audit"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
