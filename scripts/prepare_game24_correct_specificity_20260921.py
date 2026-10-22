"""Freeze same-question, same-source correct drafts without reading intervention outcomes."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAILED_PAIRS = ROOT / "runs" / "game24_batch02_validation_source_pairs.jsonl"
SOURCE_8B = ROOT / "outputs" / "game24-baseline-screen-vllm-20260918-batch02" / "draft_candidates.jsonl"
SOURCE_32B_ROOT = ROOT / "outputs" / "game24-batch02-qwen32b-20260919"
OUT = ROOT / "runs" / "game24_correct_draft_specificity_20260921"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def eligible_correct(record: dict) -> bool:
    generation = record["init_response_generations"][0]
    return (
        generation.get("finish_reason") == "eos"
        and record.get("thinking_status") == "parsable_thinking"
        and generation.get("correctness") is True
        and bool(record.get("final_response"))
    )


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite frozen output: {OUT}")

    failed_rows = load_jsonl(FAILED_PAIRS)
    if len(failed_rows) != 8 or len({str(row["id"]) for row in failed_rows}) != 8:
        raise ValueError("expected exactly eight unique frozen failed pairs")

    pools: dict[tuple[str, str], list[dict]] = defaultdict(list)
    source_files = [("Qwen3_8B_Thinking", SOURCE_8B)]
    source_files.extend(
        ("Qwen3_32B", path)
        for path in sorted(SOURCE_32B_ROOT.glob("chunk-*/draft_candidates.jsonl"))
    )
    if not SOURCE_8B.exists() or not any(alias == "Qwen3_32B" for alias, _path in source_files):
        raise FileNotFoundError("complete frozen 8B/32B source pools are required")

    for alias, path in source_files:
        for record in load_jsonl(path):
            if eligible_correct(record):
                pools[(str(record["id"]), alias)].append(record)

    selected = []
    audit = []
    for failed in sorted(failed_rows, key=lambda row: str(row["id"])):
        qid = str(failed["id"])
        alias = failed["source_model"]
        candidates = pools[(qid, alias)]
        if not candidates:
            raise ValueError(f"no eligible correct draft for {qid} from {alias}")
        failed_text = failed["traj1"]
        ranked = sorted(
            candidates,
            key=lambda row: (
                abs(len(row["final_response"]) - len(failed_text)),
                str(row["draft_key"]),
            ),
        )
        chosen = ranked[0]
        chosen_generation = chosen["init_response_generations"][0]
        selected.append(
            {
                "id": qid,
                "task": "game24",
                "problem": failed["problem"],
                "answer": failed["answer"],
                "failed_traj": failed_text,
                "failed_draft_key": failed["draft_key"],
                "failed_sha256": sha256_text(failed_text),
                "correct_traj": chosen["final_response"],
                "correct_draft_key": chosen["draft_key"],
                "correct_sha256": sha256_text(chosen["final_response"]),
                "source_model": alias,
                "stratum": failed["stratum"],
                "benchmark": failed["benchmark"],
                "correct_source_finish_reason": chosen_generation["finish_reason"],
                "correct_source_correctness": chosen_generation["correctness"],
                "correct_source_thinking_status": chosen["thinking_status"],
                "selection_rank": "minimum absolute final_response character-length difference; draft_key tie-break",
            }
        )
        audit.append(
            {
                "id": qid,
                "source_model": alias,
                "eligible_correct_candidates": len(candidates),
                "failed_chars": len(failed_text),
                "selected_correct_chars": len(chosen["final_response"]),
                "absolute_char_difference": abs(len(chosen["final_response"]) - len(failed_text)),
                "selected_correct_draft_key": chosen["draft_key"],
            }
        )

    OUT.mkdir(parents=True)
    with (OUT / "selected_correct_pairs.jsonl").open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    protocol = {
        "protocol_version": "game24_correct_specificity_v1_20260921",
        "frozen_before_specificity_generation": True,
        "intervention_outcomes_read_for_selection": False,
        "questions": len(selected),
        "conditions_to_generate": ["Correct-full", "Correct-late"],
        "fixed_seeds": [927001, 927002],
        "planned_requests": len(selected) * 2 * 2,
        "candidate_gate": "same question; same source model as failed draft; EOS; parsable thinking; correctness=True",
        "selection_rule": "minimum absolute final_response character-length difference; draft_key lexical tie-break",
        "primary_estimand": "(Failed-late - Failed-full) - (Correct-late - Correct-full)",
        "primary_question_set": "all eight frozen questions",
        "length_matched_sensitivity": {
            "rule": "absolute character-length difference <= 25% of failed-draft characters",
            "rationale": "outcome-blind diagnostic for residual draft-length mismatch",
            "included_ids": [
                row["id"]
                for row, check in zip(selected, audit)
                if check["absolute_char_difference"] <= 0.25 * check["failed_chars"]
            ],
            "excluded_ids": [
                row["id"]
                for row, check in zip(selected, audit)
                if check["absolute_char_difference"] > 0.25 * check["failed_chars"]
            ],
        },
        "failed_conditions_reused": {"Failed-full": "R2", "Failed-late": "R3"},
        "source_model_counts": dict(sorted(Counter(row["source_model"] for row in selected).items())),
        "audit": audit,
    }
    (OUT / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: protocol[key] for key in (
        "questions", "planned_requests", "source_model_counts", "primary_estimand"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
