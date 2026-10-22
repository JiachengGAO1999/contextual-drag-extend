"""Freeze the 15-question Game24 pool used for target-model generalization."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite an existing frozen pool")

    initial = read_jsonl(args.initial)
    confirmation = read_jsonl(args.confirmation)
    assert len(initial) == 7, len(initial)
    assert len(confirmation) == 8, len(confirmation)

    rows = []
    for row in initial:
        # Every selected trajectory is manually audited as substantive.  The
        # question-level `strict_two_substantive` flag is a stronger pool
        # criterion (>=2 such failures); question 41 intentionally has one.
        assert row.get("strict_two_substantive") is True or str(row["id"]) == "41"
        rows.append({
            **row,
            "task": "game24",
            "audit_status": "substantive_failed",
            "draft_key": row["source_draft_key"],
            "stratum": "dual_anchor_initial7",
            "benchmark": "Game24",
            "source": row["source_file"],
            "audit_basis": (
                "selected_trajectory_manually_substantive_and_question_has_at_least_two_substantive_failures"
                if row.get("strict_two_substantive") is True
                else "selected_trajectory_manually_substantive; question_41_has_only_one_substantive_failure"
            ),
        })
    for row in confirmation:
        assert row.get("audit_status") == "substantive_failed"
        rows.append(row)

    ids = [str(row["id"]) for row in rows]
    assert len(ids) == len(set(ids)) == 15
    assert all(row["task"] == "game24" for row in rows)
    assert all(row["audit_status"] == "substantive_failed" for row in rows)
    assert all(row.get("problem") and row.get("answer") and row.get("traj1") for row in rows)

    args.output.mkdir(parents=True)
    pairs = args.output / "pairs.jsonl"
    pairs.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    manifest = {
        "purpose": "frozen_15_question_pool_for_target_model_generalization",
        "selection": "all 7 initial plus all 8 confirmation Game24 failed-draft pairs; no target-model outcome filtering",
        "counts": {"initial": 7, "confirmation": 8, "total": 15},
        "ids_in_frozen_order": ids,
        "sources": {
            "initial": {"path": str(args.initial), "sha256": sha256(args.initial)},
            "confirmation": {"path": str(args.confirmation), "sha256": sha256(args.confirmation)},
        },
        "pairs_sha256": sha256(pairs),
    }
    (args.output / "pool_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
