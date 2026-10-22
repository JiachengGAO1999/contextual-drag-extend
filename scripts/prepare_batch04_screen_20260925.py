"""Freeze fresh Game24 candidates for the deadline-driven Batch04 screen."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "8050e67d0e3a0fddc424d7fa5801538722a4c4cc"
RECORD_NAMES = {"draft_candidates.jsonl", "results.jsonl", "raw_results.jsonl", "pairs.jsonl", "sample.jsonl"}
MANIFEST_WORDS = ("manifest", "candidate", "sample", "pool", "review_candidates", "plan")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def is_game24_record(row: dict[str, Any], path: Path, source_ids: set[str], source_multisets: set[tuple[int, ...]]) -> bool:
    task = str(row.get("task", row.get("benchmark", ""))).lower()
    if "game24" in task or "game_of_24" in task:
        return True
    if "game24" in str(path).lower():
        return True
    answer = row.get("answer")
    if isinstance(answer, list) and len(answer) == 4:
        try:
            if tuple(sorted(int(x) for x in answer)) in source_multisets:
                return True
        except (TypeError, ValueError):
            pass
    return str(row.get("id", "")) in source_ids and isinstance(answer, list)


def collect_manifest_ids(value: Any, source_ids: set[str], out: set[str]) -> None:
    if isinstance(value, dict):
        for key in ("id", "qid", "question_id", "Rank"):
            item = value.get(key)
            if item is not None and str(item) in source_ids:
                out.add(str(item))
        for key in ("candidate_ids", "question_ids", "ids_in_frozen_order", "excluded_ids",
                    "excluded_development_ids", "excluded_previous_screen_ids"):
            items = value.get(key)
            if isinstance(items, list):
                out.update(str(item) for item in items if str(item) in source_ids)
        for child in value.values():
            collect_manifest_ids(child, source_ids, out)
    elif isinstance(value, list):
        for child in value:
            collect_manifest_ids(child, source_ids, out)


def prepare(input_path: Path, destination: Path, candidate_count: int, samples: int, seed: int) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite a frozen manifest: {destination}")
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    by_id = {str(row["Rank"]): row for row in source_rows}
    if len(by_id) != len(source_rows):
        raise ValueError("Duplicate Rank values in the pinned Game24 source")
    source_ids = set(by_id)
    numbers_by_id = {qid: tuple(sorted(int(v) for v in row["Puzzles"].split())) for qid, row in by_id.items()}
    source_multisets = set(numbers_by_id.values())

    excluded_ids: set[str] = set()
    evidence: list[dict[str, Any]] = []
    roots = [p for p in (ROOT / "scripts", ROOT / "outputs", ROOT / "runs") if p.exists()]
    files = sorted({path for root in roots for path in root.rglob("*") if path.is_file()})
    for path in files:
        name = path.name.lower()
        if path.suffix.lower() == ".json" and any(word in name for word in MANIFEST_WORDS) and path.stat().st_size <= 32 * 1024 * 1024:
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            found: set[str] = set()
            collect_manifest_ids(parsed, source_ids, found)
            if found:
                excluded_ids.update(found)
                evidence.append({"path": path.relative_to(ROOT).as_posix(), "kind": "json_manifest_or_plan",
                                 "sha256": sha256(path), "question_ids_found": len(found)})
        elif name in RECORD_NAMES:
            found: set[str] = set()
            try:
                with path.open(encoding="utf-8") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        qid = str(row.get("id", ""))
                        if qid in source_ids and is_game24_record(row, path, source_ids, source_multisets):
                            found.add(qid)
            except UnicodeDecodeError:
                continue
            if found:
                excluded_ids.update(found)
                evidence.append({"path": path.relative_to(ROOT).as_posix(), "kind": "generated_or_pair_records",
                                 "sha256": sha256(path), "question_ids_found": len(found)})

    excluded_numbers = {numbers_by_id[qid] for qid in excluded_ids}
    rows = sorted(source_rows, key=lambda row: int(row["Rank"]))
    random.Random(seed).shuffle(rows)
    selected: list[dict[str, Any]] = []
    selected_numbers: set[tuple[int, ...]] = set()
    for row in rows:
        qid = str(row["Rank"])
        values = [int(v) for v in row["Puzzles"].split()]
        key = tuple(sorted(values))
        if qid in excluded_ids or key in excluded_numbers or key in selected_numbers:
            continue
        selected.append({"id": qid, "numbers": values})
        selected_numbers.add(key)
        if len(selected) == candidate_count:
            break
    if len(selected) != candidate_count:
        raise RuntimeError(f"Only {len(selected)} fresh independent questions remain; need {candidate_count}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": 1,
        "status": "frozen_pending_execution",
        "generate": False,
        "purpose": "Fresh independent Game24 baseline screen before any intervention selection",
        "selection": "Seeded shuffle of source rows remaining after excluding every Game24 question ID and number multiset found in prior scripts, plans, screening, runs, outputs, or pairs; no response-outcome ranking.",
        "source": str(input_path),
        "source_revision": SOURCE_REVISION,
        "source_sha256": sha256(input_path),
        "order_seed": seed,
        "seed": 20270925,
        "candidate_count": candidate_count,
        "samples_per_problem": samples,
        "anchor_models": ["Qwen3_8B_Thinking", "Qwen3_32B"],
        "condition": "R0",
        "backend": "ordinary_vLLM_default_worker; no selective mask",
        "total_generations": candidate_count * samples * 2,
        "eligibility_rule": "Pool valid EOS and parseable-thinking outputs across both anchors; require at least two official scorer True and at least two manually confirmed substantive errors. Scorer False remains pending manual review and never counts as an error automatically.",
        "sampling_design_note": "Eight samples per anchor use the measured fixed-order Batch03 prefix where pooled eligibility rose from 2/22 at n=4 to 7/22 at n=8, 8/22 at n=12, and remained 8/22 at n=16. This is a planning estimate, not a guaranteed yield.",
        "exclusion_audit": {
            "excluded_unique_question_ids": len(excluded_ids),
            "excluded_unique_number_multisets": len(excluded_numbers),
            "excluded_ids_sha256": hashlib.sha256("\n".join(sorted(excluded_ids, key=int)).encode()).hexdigest(),
            "evidence_files": evidence,
        },
        "candidate_rows": selected,
    }
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--candidate-count", type=int, default=32)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20270925)
    args = ap.parse_args()
    manifest = prepare(args.input, args.output, args.candidate_count, args.samples, args.seed)
    print(json.dumps({"manifest": str(args.output), "status": manifest["status"],
                      "candidate_count": len(manifest["candidate_rows"]),
                      "samples_per_anchor": manifest["samples_per_problem"],
                      "total_generations": manifest["total_generations"],
                      "excluded_unique_question_ids": manifest["exclusion_audit"]["excluded_unique_question_ids"],
                      "excluded_unique_number_multisets": manifest["exclusion_audit"]["excluded_unique_number_multisets"],
                      "candidate_ids": [r["id"] for r in manifest["candidate_rows"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
