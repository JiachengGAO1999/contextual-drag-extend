"""Freeze the next baseline-only acquisition batch.

This script selects by the already frozen candidate order only. It does not
inspect intervention outcomes and deliberately excludes every question used
by development/intervention work or by the earlier 24-question screen.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "quick_validation" / "protocol_prepared_generation_plan_20260917.json"
OLD_MANIFEST = ROOT / "scripts" / "baseline_screen_manifest_20260917.json"
DEFAULT_OUTPUT = ROOT / "scripts" / "baseline_screen_manifest_20260918_batch02.json"

# Development/intervention questions are never eligible for the formal pool.
DEVELOPMENT_IDS = {
    "1189", "1358", "804", "123", "577", "719", "1084", "71", "513", "1226",
    "170", "159", "1093",
    # The seven-question dual-anchor validation just completed.
    "44", "914", "1112", "41", "1057", "413", "509",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--samples-per-problem", type=int, default=16)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    old = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    previously_screened = {str(row["id"]) for row in old["candidate_rows"]}
    excluded = DEVELOPMENT_IDS | previously_screened

    selected = []
    skipped = []
    for row in source["candidates"]:
        qid = str(row["tot_rank"])
        if qid in excluded:
            skipped.append({"id": qid, "reason": "development_or_previous_screen"})
            continue
        selected.append({"id": qid, "numbers": row["numbers"]})
        if len(selected) == args.batch_size:
            break

    if len(selected) != args.batch_size:
        raise RuntimeError(f"only selected {len(selected)} of requested {args.batch_size}")

    manifest = {
        "manifest_version": 1,
        "status": "authorized_stage1_baseline_only",
        "purpose": "Fixed baseline-only acquisition before any intervention selection.",
        "source_plan": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_revision": source["sources_revision"],
        "selection_basis": (
            "First fixed-order candidates after excluding all development/intervention "
            "questions and all questions in baseline_screen_manifest_20260917.json; "
            "no intervention outcome was inspected."
        ),
        "excluded_development_ids": sorted(DEVELOPMENT_IDS),
        "excluded_previous_screen_ids": sorted(previously_screened),
        "skipped_prefix": skipped,
        "candidate_count": len(selected),
        "samples_per_problem": args.samples_per_problem,
        "total_generations": len(selected) * args.samples_per_problem,
        "condition": "R0",
        "backend": "ordinary_vllm_default_worker",
        "model_alias": "Qwen3_8B",
        "seed": 42,
        "candidate_rows": selected,
    }
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "candidate_count": len(selected),
        "samples_per_problem": args.samples_per_problem,
        "total_generations": manifest["total_generations"],
        "candidate_ids": [row["id"] for row in selected],
        "excluded_development": len(DEVELOPMENT_IDS),
        "excluded_previous_screen": len(previously_screened),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
