"""Run the frozen Batch03 Game24 R0 acquisition on both Qwen anchors.

The fixed 32-question manifest and 16 samples/question/model are preserved.
This runner only acquires baseline generations and stops for pooled manual audit.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "scripts/baseline_manifest_batch03_20260919.json"
SCREEN_RUNNER = ROOT / "scripts/baseline_screen_vllm_20260917.py"
INPUT = Path("/data2/gaojc/data/game24-tot-8050e67/24.csv")
OUTPUT = ROOT / "outputs/game24-batch03-dual-anchor-20260924"
SOURCE_REVISION = "8050e67d0e3a0fddc424d7fa5801538722a4c4cc"
GPU_ID = "4"
EXTERNAL_GPU_MEMORY_LIMIT_MIB = 8192

ANCHORS = (
    {
        "alias": "Qwen3_8B_Thinking",
        "model": "/data2/huangrj/models/qwen3-8b",
        "chunk_questions": 4,
        "max_num_seqs": 16,
        "max_num_batched_tokens": 8192,
        "gpu_memory_utilization": "0.85",
    },
    {
        "alias": "Qwen3_32B",
        "model": "/data/zhaoyi/liujunyuan/models/Qwen3-32B",
        "chunk_questions": 2,
        "max_num_seqs": 4,
        "max_num_batched_tokens": 2048,
        "gpu_memory_utilization": "0.95",
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_gpu4() -> int:
    result = subprocess.run(
        ["nvidia-smi", "--id=" + GPU_ID, "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    used_mib = int(result.stdout.strip())
    if used_mib > EXTERNAL_GPU_MEMORY_LIMIT_MIB:
        raise RuntimeError(
            f"GPU4 has {used_mib} MiB in use (> {EXTERNAL_GPU_MEMORY_LIMIT_MIB} MiB); "
            "stop without touching any process"
        )
    return used_mib


def validate_inputs(manifest: dict[str, Any]) -> None:
    candidates = manifest["candidate_rows"]
    if manifest.get("candidate_count") != 32 or len(candidates) != 32:
        raise ValueError("Frozen Batch03 manifest must contain exactly 32 candidates")
    if manifest.get("samples_per_problem") != 16 or manifest.get("total_generations") != 1024:
        raise ValueError("Frozen Batch03 generation budget must remain 32 x 16 x 2 = 1024")
    if manifest.get("generate") is not False:
        raise ValueError("Unexpected mutation of the frozen source manifest")
    if len({str(row["id"]) for row in candidates}) != 32:
        raise ValueError("Duplicate candidate IDs in frozen manifest")
    if not INPUT.is_file() or not SCREEN_RUNNER.is_file():
        raise FileNotFoundError("Missing pinned Game24 input or baseline screen runner")
    for anchor in ANCHORS:
        if not (Path(anchor["model"]) / "config.json").is_file():
            raise FileNotFoundError(f"Missing read-only model config: {anchor['model']}")

    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = {str(row["Rank"]): row for row in csv.DictReader(handle)}
    for candidate in candidates:
        source = source_rows.get(str(candidate["id"]))
        if source is None:
            raise ValueError(f"Candidate {candidate['id']} is absent from pinned Game24 input")
        numbers = [int(item) for item in source["Puzzles"].split()]
        if sorted(numbers) != sorted(candidate["numbers"]):
            raise ValueError(f"Candidate numbers differ from pinned input: {candidate['id']}")


def run_anchor(
    manifest: dict[str, Any],
    manifest_hash: str,
    anchor: dict[str, Any],
    status: dict[str, Any],
    started: float,
) -> list[Path]:
    alias = anchor["alias"]
    anchor_root = OUTPUT / alias
    anchor_root.mkdir()
    chunk_paths: list[Path] = []
    candidates = manifest["candidate_rows"]
    samples = manifest["samples_per_problem"]
    chunk_size = anchor["chunk_questions"]

    for chunk_number, start in enumerate(range(0, len(candidates), chunk_size)):
        used_mib = check_gpu4()
        block = candidates[start : start + chunk_size]
        chunk_name = f"chunk-{chunk_number:02d}"
        chunk_manifest_path = OUTPUT / "chunk_manifests" / alias / f"{chunk_name}.json"
        chunk_manifest = dict(manifest)
        chunk_manifest.update(
            {
                "candidate_rows": block,
                "candidate_count": len(block),
                "total_generations": len(block) * samples,
                "generate": True,
                "execution_copy": True,
                "source_frozen_manifest_sha256": manifest_hash,
                "execution_authorization_date": "2026-09-24",
                "execution_anchor": alias,
                "execution_chunk": chunk_name,
            }
        )
        save_json(chunk_manifest_path, chunk_manifest)
        chunk_output = anchor_root / chunk_name
        if chunk_output.exists():
            raise FileExistsError(f"Refusing to overwrite existing chunk output: {chunk_output}")

        command = [
            os.environ.get("BATCH03_PYTHON", "/data2/gaojc/envs/contextual-drag-vllm/bin/python"),
            str(SCREEN_RUNNER),
            "--model", anchor["model"],
            "--model-alias", alias,
            "--input", str(INPUT),
            "--manifest", str(chunk_manifest_path),
            "--source-revision", SOURCE_REVISION,
            "--output", str(chunk_output),
            "--max-num-seqs", str(anchor["max_num_seqs"]),
            "--max-num-batched-tokens", str(anchor["max_num_batched_tokens"]),
            "--gpu-memory-utilization", anchor["gpu_memory_utilization"],
        ]
        status.update(
            {
                "state": "running",
                "current_anchor": alias,
                "current_chunk": chunk_name,
                "gpu4_used_mib_before_chunk": used_mib,
                "elapsed_seconds": time.monotonic() - started,
                "updated_utc": utc_now(),
            }
        )
        save_json(OUTPUT / "status.json", status)
        print(f"START {alias} {chunk_name} gpu4_used_mib={used_mib}", flush=True)
        with (anchor_root / f"{chunk_name}.log").open("w", encoding="utf-8") as log:
            subprocess.run(command, cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, check=True)

        summary_path = chunk_output / "summary.json"
        result_path = chunk_output / "draft_candidates.jsonl"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        records = [json.loads(line) for line in result_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        expected_count = len(block) * samples
        if summary.get("generations") != expected_count or len(records) != expected_count:
            raise RuntimeError(f"Unexpected output count for {alias}/{chunk_name}")
        per_question = collections.Counter(str(row["id"]) for row in records)
        if per_question != collections.Counter({str(row["id"]): samples for row in block}):
            raise RuntimeError(f"Per-question sample count mismatch for {alias}/{chunk_name}")

        status["completed_generations"] += expected_count
        status["completed_chunks"].append({"anchor": alias, "chunk": chunk_name, "generations": expected_count})
        status["elapsed_seconds"] = time.monotonic() - started
        status["updated_utc"] = utc_now()
        save_json(OUTPUT / "status.json", status)
        chunk_paths.append(result_path)
        print(f"COMPLETE {alias} {chunk_name} total={status['completed_generations']}/1024", flush=True)
    return chunk_paths


def merge_and_audit(manifest: dict[str, Any], paths_by_anchor: dict[str, list[Path]]) -> None:
    all_records: list[dict[str, Any]] = []
    for alias, paths in paths_by_anchor.items():
        merged_path = OUTPUT / alias / "draft_candidates.jsonl"
        lines: list[str] = []
        for path in paths:
            lines.extend(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        merged_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        all_records.extend(json.loads(line) for line in lines)

    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    samples: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    review_queue = []
    seen = set()
    for record in all_records:
        alias = record["init_response_generations_metadata"]["model_config_alias"]
        qid = str(record["id"])
        generation = record["init_response_generations"][0]
        key = (alias, qid, str(record["draft_key"]))
        if key in seen:
            raise RuntimeError(f"Duplicate generated draft key: {key}")
        seen.add(key)
        samples[qid][alias] += 1
        valid = generation.get("finish_reason") == "eos" and record.get("thinking_status") == "parsable_thinking"
        if valid and generation.get("correctness") is True:
            counts[qid]["correct"] += 1
        elif valid and generation.get("correctness") is False:
            counts[qid]["official_false_pending_audit"] += 1
            review_queue.append(
                {
                    "model": alias,
                    "id": qid,
                    "draft_key": record["draft_key"],
                    "extracted_answer": generation.get("extracted_answer"),
                    "final_response": record.get("final_response"),
                    "answer": record.get("answer"),
                    "source": str(OUTPUT / alias / "draft_candidates.jsonl"),
                    "manual_status": "pending",
                }
            )
        else:
            counts[qid]["excluded"] += 1

    expected_ids = {str(row["id"]) for row in manifest["candidate_rows"]}
    if len(all_records) != 1024 or {qid for qid, by_model in samples.items() if sum(by_model.values())} != expected_ids:
        raise RuntimeError("Merged Batch03 records do not match the frozen 1024-generation design")
    for qid in expected_ids:
        if samples[qid] != collections.Counter({"Qwen3_8B_Thinking": 16, "Qwen3_32B": 16}):
            raise RuntimeError(f"Pooled anchor count mismatch for question {qid}: {samples[qid]}")

    preaudit_eligible = [
        qid
        for qid, row_counts in counts.items()
        if row_counts["correct"] >= 2 and row_counts["official_false_pending_audit"] >= 2
    ]
    save_json(
        OUTPUT / "pooled_scorer_summary.json",
        {
            "question_counts": {qid: dict(counts[qid]) for qid in sorted(expected_ids)},
            "samples_by_model": {qid: dict(samples[qid]) for qid in sorted(expected_ids)},
            "preaudit_eligible_ids": sorted(preaudit_eligible, key=lambda value: int(value)),
            "eligibility_status": "official-false counts require manual substantive-failure audit",
            "intervention_generations": 0,
        },
    )
    save_json(OUTPUT / "manual_review_queue.json", review_queue)


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing Batch03 output: {OUTPUT}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_inputs(manifest)
    gpu_used_mib = check_gpu4()
    manifest_hash = sha256(MANIFEST_PATH)
    runner_hash = sha256(SCREEN_RUNNER)
    try:
        git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        git_head = "unavailable"

    OUTPUT.mkdir(parents=True, exist_ok=False)
    (OUTPUT / "chunk_manifests").mkdir()
    shutil.copyfile(MANIFEST_PATH, OUTPUT / "frozen_source_manifest.json")
    save_json(
        OUTPUT / "launch_record.json",
        {
            "authorized_utc_date": "2026-09-24",
            "purpose": "Increase the independent Game24 confirmation pool using the pre-frozen Batch03 candidates",
            "source_manifest_sha256": manifest_hash,
            "baseline_screen_runner_sha256": runner_hash,
            "project_git_head": git_head,
            "source_revision": SOURCE_REVISION,
            "candidate_count": 32,
            "samples_per_question_per_anchor": 16,
            "total_generation_budget": 1024,
            "models": ANCHORS,
            "gpu": GPU_ID,
            "gpu4_used_mib_before_launch": gpu_used_mib,
            "screening_only": True,
            "automatic_intervention": False,
            "automatic_candidate_filtering": False,
        },
    )
    status = {
        "state": "running",
        "completed_generations": 0,
        "total_generations": 1024,
        "completed_chunks": [],
        "started_utc": utc_now(),
        "started_unix": time.time(),
    }
    save_json(OUTPUT / "status.json", status)
    started = time.monotonic()
    paths_by_anchor: dict[str, list[Path]] = {}
    try:
        for anchor in ANCHORS:
            paths_by_anchor[anchor["alias"]] = run_anchor(manifest, manifest_hash, anchor, status, started)
        merge_and_audit(manifest, paths_by_anchor)
        status.update(
            {
                "state": "complete_awaiting_manual_pooled_audit",
                "completed_generations": 1024,
                "elapsed_seconds": time.monotonic() - started,
                "updated_utc": utc_now(),
            }
        )
        save_json(OUTPUT / "status.json", status)
        print("BATCH03_COMPLETE_1024_AWAITING_MANUAL_AUDIT", flush=True)
    except BaseException as exc:
        status.update(
            {
                "state": "failed_no_fallback",
                "error": repr(exc),
                "elapsed_seconds": time.monotonic() - started,
                "updated_utc": utc_now(),
            }
        )
        save_json(OUTPUT / "status.json", status)
        raise


if __name__ == "__main__":
    main()
