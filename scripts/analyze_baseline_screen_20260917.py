"""Analyze the fixed 24-question R0 baseline screen."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs" / "game24-baseline-screen-vllm-20260917-retry1"

# Manual audit of the official-false records. In these four records, the body
# contains a valid expression using the required multiset, but the final boxed
# field contains only the scalar 24. They are answer-format failures, not
# substantive failed reasoning traces for contextual-drag surgery.
NUMERIC_BOXED_VALID_BODY = {"753/0", "753/1", "1057/1", "125/2"}


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def extracted_digits(answer):
    if not answer:
        return []
    return [int(x) for x in re.findall(r"\d+", answer)]


def classify(record):
    item = record["init_response_generations"][0]
    if item.get("finish_reason") != "eos":
        return "length_limited"
    if record.get("thinking_status") != "parsable_thinking":
        return "unparseable_thinking"
    correctness = item.get("correctness")
    if correctness is True:
        return "correct"
    if correctness is not False:
        return "unscored"
    if record.get("draft_key") in NUMERIC_BOXED_VALID_BODY:
        return "numeric_boxed_valid_body"
    answer = item.get("extracted_answer")
    used = extracted_digits(answer)
    expected = sorted(int(x) for x in record["answer"])
    if sorted(used) != expected:
        return "wrong_number_multiset"
    return "wrong_arithmetic_or_expression"


def main():
    records = load_jsonl(RUN / "draft_candidates.jsonl")
    groups = defaultdict(list)
    for record in records:
        groups[str(record["id"])].append(record)
    groups = {key: sorted(value, key=lambda x: x["init_response_generations"][0]["response_id"])
              for key, value in groups.items()}

    status_counter = Counter(classify(record) for record in records)
    problem_rows = []
    mixed = []
    for problem_id, values in groups.items():
        status = Counter(classify(record) for record in values)
        valid_correct = status["correct"]
        valid_wrong = status["wrong_number_multiset"] + status["wrong_arithmetic_or_expression"]
        is_mixed = valid_correct > 0 and valid_wrong > 0
        if is_mixed:
            mixed.append(problem_id)
        problem_rows.append({
            "id": problem_id,
            "numbers": values[0]["answer"],
            "correct": status["correct"],
            "wrong": valid_wrong,
            "null_or_unscored": status["unscored"] + status["unparseable_thinking"],
            "length_limited": status["length_limited"],
            "mixed_success": is_mixed,
            "statuses": dict(status),
        })
    problem_rows.sort(key=lambda row: list(groups).index(row["id"]))

    wrong_examples = []
    for record in records:
        category = classify(record)
        if category not in {"wrong_number_multiset", "wrong_arithmetic_or_expression", "numeric_boxed_valid_body"}:
            continue
        item = record["init_response_generations"][0]
        final = record.get("final_response", "")
        wrong_examples.append({
            "draft_key": record.get("draft_key"),
            "id": record["id"],
            "sample_index": item.get("response_id"),
            "category": category,
            "extracted_answer": item.get("extracted_answer"),
            "final_tail": final[-1000:],
        })

    summary = json.loads((RUN / "summary.json").read_text(encoding="utf-8"))
    analysis = {
        "run": str(RUN),
        "summary": summary,
        "status_counts": dict(status_counter),
        "question_count": len(problem_rows),
        "mixed_success_question_ids": mixed,
        "mixed_success_count": len(mixed),
        "all_correct_count": sum(row["wrong"] == 0 and row["correct"] > 0 for row in problem_rows),
        "all_wrong_count": sum(row["correct"] == 0 and row["wrong"] > 0 for row in problem_rows),
        "no_valid_answer_count": sum(row["correct"] == 0 and row["wrong"] == 0 for row in problem_rows),
        "problem_rows": problem_rows,
        "wrong_examples": wrong_examples,
        "manual_adjudication": {
            "numeric_boxed_valid_body": sorted(NUMERIC_BOXED_VALID_BODY),
            "note": "These records are official-false because the final boxed field is scalar 24, although the body contains a valid expression; excluded from substantive failed-draft count.",
        },
    }
    (RUN / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Stage-1 baseline screen analysis",
        "",
        "This is baseline-only R0 data. No intervention outcome was used for selection.",
        "",
        "## Aggregate",
        "",
        f"- Generations: {summary['generations']}; questions: {summary['questions']}; samples/question: {summary['samples_per_question']}",
        f"- Complete: {summary['stopped']}/{summary['generations']}; length-limited: {summary['length_limited']}",
        f"- Complete + parseable: {summary['parseable_thinking']}; official correct: {summary['official_correct']}; official incorrect: {summary['official_incorrect']}; null/unscored: {summary['official_unparseable_or_null']}",
        f"- Error rate among complete generations: {summary['official_incorrect'] / summary['stopped']:.1%}",
        f"- Official mixed-success questions: {sum(row['statuses'].get('correct', 0) > 0 and (row['statuses'].get('wrong_number_multiset', 0) + row['statuses'].get('wrong_arithmetic_or_expression', 0) + row['statuses'].get('numeric_boxed_valid_body', 0)) > 0 for row in problem_rows)}/{len(problem_rows)}",
        f"- Substantive mixed-success questions after manual audit: {len(mixed)}/{len(problem_rows)}: {', '.join(mixed) if mixed else 'none'}",
        "",
        "## Per-question",
        "",
        "| ID | Numbers | Correct | Wrong | Null/unscored | Length | Mixed |",
        "|---:|:---|---:|---:|---:|---:|:---:|",
    ]
    for row in problem_rows:
        lines.append(f"| {row['id']} | {','.join(map(str, row['numbers']))} | {row['correct']} | {row['wrong']} | {row['null_or_unscored']} | {row['length_limited']} | {'yes' if row['mixed_success'] else 'no'} |")
    lines += ["", "## Error morphology (automatic extraction + manual adjudication)", "",
              "| Category | Count |", "|:---|---:|"]
    lines += [f"| {name} | {status_counter[name]} |" for name in ["wrong_number_multiset", "wrong_arithmetic_or_expression", "numeric_boxed_valid_body", "length_limited", "unscored", "unparseable_thinking"]]
    lines += ["", "## Interpretation", "",
              "- The pool is mostly correct: 11/93 complete generations are official-false, but manual audit separates 7 substantive constraint violations from 4 numeric-box formatting failures.",
              f"- There are {len(mixed)} baseline mixed-success questions after excluding the formatting-only cases. These are the candidates that can support a paired recovery comparison without outcome-based selection beyond the predeclared baseline criterion.",
              "- A complete wrong answer is not automatically a scientifically usable failed draft: it still requires manual verification that the trace is substantive, has a stable final error, and is suitable for the intervention prompt.",
              "- The three length-limited samples should not be treated as substantive failed drafts.",
              ""]
    (RUN / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status_counts": dict(status_counter), "mixed_success": mixed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
