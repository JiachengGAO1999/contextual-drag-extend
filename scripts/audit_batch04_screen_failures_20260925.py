"""Build a manual-review queue from completed Batch04 baseline chunks.

This script verifies saved chunk counts and computes expression diagnostics, but
never labels a scorer-false answer as a substantive failure. Human review is
still required before a question can enter the paired-evaluation pool.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

from analyze_batch03_partial_20260924 import (
    expression_measurement,
    sample_index,
    valid_response_expressions,
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen-dir", type=Path,
                    help="Directory containing model/chunk-NN/draft_candidates.jsonl")
    ap.add_argument("--model")
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--compact-queue", type=Path,
                    help="Write a compact human-readable view of an existing manual queue")
    ap.add_argument("--compact-output", type=Path)
    args = ap.parse_args()
    if args.compact_queue:
        if not args.compact_output:
            ap.error("--compact-output is required with --compact-queue")
        rows = [json.loads(line) for line in args.compact_queue.read_text(encoding="utf-8").splitlines() if line.strip()]
        lines = ["# Batch04 8B false-answer manual review", "",
                 "Every row is pending review. The expression diagnostics do not assign substantive-error labels.", ""]
        for number, row in enumerate(rows, 1):
            measurement = row["extracted_expression_measurement"]
            response_tail = (row.get("final_response") or "")[-900:]
            lines.extend([
                f"## {number}. Question {row['id']}, sample {row['sample_index']}", "",
                f"- Inputs: `{row['answer_numbers']}`; extracted: `{row['extracted_answer']}`",
                f"- Exact evaluation: `{measurement['evaluated_value']}`; operands: `{measurement['actual_operand_multiset']}`; exact Game24: `{measurement['exact_game24']}`",
                f"- Other exact solutions detected in final response: `{row['valid_solutions_found_in_final_response']}`",
                "- Final response ending:", "", "```text", response_tail, "```", "",
            ])
        args.compact_output.parent.mkdir(parents=True, exist_ok=True)
        args.compact_output.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps({"rows": len(rows), "compact_output": str(args.compact_output)}, ensure_ascii=False))
        return
    if not args.screen_dir or not args.model or not args.output_dir:
        ap.error("--screen-dir, --model, and --output-dir are required for a fresh audit")
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite audit output: {args.output_dir}")

    model_dir = args.screen_dir / args.model
    paths = sorted(model_dir.glob("chunk-*/draft_candidates.jsonl"))
    if not paths:
        raise FileNotFoundError(f"No completed chunks under {model_dir}")

    by_question: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    finish_score = collections.Counter()
    identities: set[tuple[str, str, int]] = set()
    queue: list[dict[str, Any]] = []
    files = []
    total = 0
    for path in paths:
        chunk_dir = path.parent
        summary_path = chunk_dir / "summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"Completed chunk lacks summary: {chunk_dir}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(records) != int(summary.get("generations", -1)):
            raise RuntimeError(f"Record/summary mismatch in {chunk_dir}: {len(records)}")
        chunk_counts = collections.Counter(str(r["id"]) for r in records)
        if any(count != int(summary["samples_per_question"]) for count in chunk_counts.values()):
            raise RuntimeError(f"Per-question count mismatch in {chunk_dir}: {chunk_counts}")
        files.append({"path": str(path), "sha256": digest(path), "generations": len(records),
                      "questions": sorted(chunk_counts, key=int), "summary": summary})
        for record in records:
            gen = record["init_response_generations"][0]
            alias = record["init_response_generations_metadata"].get("model_config_alias")
            qid = str(record["id"])
            index = sample_index(record)
            identity = (str(alias), qid, index)
            if identity in identities:
                raise RuntimeError(f"Duplicate sample identity: {identity}")
            identities.add(identity)
            finish = gen.get("finish_reason")
            score = gen.get("correctness")
            finish_score[(str(finish), str(score))] += 1
            by_question[qid]["total"] += 1
            valid = (finish == "eos" and record.get("thinking_status") == "parsable_thinking"
                     and bool((record.get("final_response") or "").strip()))
            if not valid:
                by_question[qid]["invalid_or_unresolved"] += 1
                continue
            by_question[qid]["valid"] += 1
            if score is True:
                by_question[qid]["valid_official_true"] += 1
                continue
            if score is not False:
                by_question[qid]["valid_official_null"] += 1
                continue

            by_question[qid]["valid_official_false_pending_manual_audit"] += 1
            extracted = gen.get("extracted_answer")
            numbers = record.get("answer") or []
            response = record.get("final_response") or ""
            queue.append({
                "model": alias,
                "id": qid,
                "sample_index": index,
                "draft_key": record.get("draft_key"),
                "problem": record.get("problem"),
                "answer_numbers": numbers,
                "finish_reason": finish,
                "extracted_answer": extracted,
                "extracted_expression_measurement": expression_measurement(extracted or "", numbers),
                "valid_solutions_found_in_final_response": valid_response_expressions(response, numbers),
                "final_response": response,
                "manual_status": "pending",
                "audit_note": "Diagnostics only; do not count as substantive failure before human review.",
                "source_file": str(path),
                "source_sha256": digest(path),
            })
            total += 1

    args.output_dir.mkdir(parents=True, exist_ok=False)
    queue_path = args.output_dir / "manual_review_queue.jsonl"
    queue_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in queue), encoding="utf-8")
    counts = {qid: dict(counter) for qid, counter in sorted(by_question.items(), key=lambda pair: int(pair[0]))}
    save_json(args.output_dir / "audit_manifest.json", {
        "status": "pending_manual_audit",
        "model": args.model,
        "screen_dir": str(args.screen_dir),
        "completed_generations": sum(int(item["generations"]) for item in files),
        "unique_sample_identities": len(identities),
        "valid_official_false_awaiting_human_review": len(queue),
        "validity_rule": "EOS finish, parsable thinking, nonempty final response",
        "finish_reason_by_official_score": {f"{finish}|{score}": n for (finish, score), n in sorted(finish_score.items())},
        "question_counts": counts,
        "source_files": files,
        "manual_review_queue": str(queue_path),
        "automatic_substantive_error_labels": 0,
    })
    print(json.dumps({"model": args.model, "completed_generations": sum(x["generations"] for x in files),
                      "valid_official_false_pending_manual_audit": len(queue),
                      "finish_reason_by_official_score": {f"{finish}|{score}": n for (finish, score), n in sorted(finish_score.items())},
                      "output_dir": str(args.output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
