"""Run a frozen fresh-question, two-anchor Batch04 R0 screen in short chunks."""
from __future__ import annotations

import collections
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "scripts/baseline_manifest_batch04_20260925.json"
SCREEN_RUNNER = ROOT / "scripts/baseline_screen_vllm_20260917.py"
INPUT = Path("/data2/gaojc/data/game24-tot-8050e67/24.csv")
OUTPUT = ROOT / "outputs/game24-batch04-dual-anchor-screen-20260925"
SOURCE_REVISION = "8050e67d0e3a0fddc424d7fa5801538722a4c4cc"
GPU_ID = "4"
GPU_IDLE_LIMIT_MIB = 8192
EXPECTED_TOTAL = 512

ANCHORS = (
    {"alias": "Qwen3_8B_Thinking", "model": "/data2/huangrj/models/qwen3-8b",
     "chunk_questions": 4, "max_num_seqs": 16, "max_num_batched_tokens": 8192,
     "gpu_memory_utilization": "0.85"},
    {"alias": "Qwen3_32B", "model": "/data/zhaoyi/liujunyuan/models/Qwen3-32B",
     "chunk_questions": 2, "max_num_seqs": 4, "max_num_batched_tokens": 2048,
     "gpu_memory_utilization": "0.95"},
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def gpu4_used_mib() -> int:
    raw = subprocess.check_output(
        ["nvidia-smi", "--id=" + GPU_ID, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True
    ).strip()
    return int(raw)


def validate_inputs(manifest: dict[str, Any]) -> None:
    rows = manifest.get("candidate_rows", [])
    if manifest.get("status") != "frozen_pending_execution" or manifest.get("generate") is not False:
        raise RuntimeError("Expected the frozen, non-executable source manifest")
    if manifest.get("candidate_count") != 32 or len(rows) != 32:
        raise RuntimeError("Batch04 source manifest must contain exactly 32 candidates")
    if manifest.get("samples_per_problem") != 8 or manifest.get("total_generations") != EXPECTED_TOTAL:
        raise RuntimeError("Frozen generation budget must be 32 x 8 x 2 = 512")
    ids = [str(row["id"]) for row in rows]
    multisets = [tuple(sorted(int(x) for x in row["numbers"])) for row in rows]
    if len(set(ids)) != len(rows) or len(set(multisets)) != len(rows):
        raise RuntimeError("Candidate IDs or number multisets are not unique")
    if not INPUT.is_file() or not SCREEN_RUNNER.is_file():
        raise FileNotFoundError("Missing pinned Game24 source or baseline screen runner")
    if sha256(INPUT) != manifest.get("source_sha256"):
        raise RuntimeError("Pinned Game24 source hash differs from the frozen manifest")
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        import csv
        source = {str(row["Rank"]): row for row in csv.DictReader(handle)}
    for item in rows:
        row = source.get(str(item["id"]))
        if row is None or tuple(sorted(int(x) for x in row["Puzzles"].split())) != tuple(sorted(item["numbers"])):
            raise RuntimeError(f"Frozen candidate does not match pinned source: {item['id']}")
    for anchor in ANCHORS:
        if not (Path(anchor["model"]) / "config.json").is_file():
            raise FileNotFoundError(f"Missing authorized read-only model: {anchor['model']}")


def check_gpu4() -> int:
    used = gpu4_used_mib()
    if used > GPU_IDLE_LIMIT_MIB:
        raise RuntimeError(f"GPU4 has {used} MiB in use; stop without touching another process")
    return used


def read_chunk(output: Path, ids: list[str], samples: int) -> list[dict[str, Any]]:
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (output / "draft_candidates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = collections.Counter(str(row["id"]) for row in records)
    if summary.get("generations") != len(ids) * samples or len(records) != len(ids) * samples:
        raise RuntimeError(f"Chunk record count mismatch in {output}")
    if counts != collections.Counter({qid: samples for qid in ids}):
        raise RuntimeError(f"Chunk question counts mismatch in {output}: {counts}")
    return records


def run_anchor(manifest: dict[str, Any], manifest_hash: str, anchor: dict[str, Any], status: dict[str, Any], started: float) -> list[Path]:
    alias = anchor["alias"]
    root = OUTPUT / alias
    root.mkdir(parents=True, exist_ok=True)
    candidates = manifest["candidate_rows"]
    samples = int(manifest["samples_per_problem"])
    paths: list[Path] = []
    for chunk_index, start in enumerate(range(0, len(candidates), anchor["chunk_questions"])):
        rows = candidates[start:start + anchor["chunk_questions"]]
        chunk = f"chunk-{chunk_index:02d}"
        chunk_output = root / chunk
        chunk_manifest_path = OUTPUT / "chunk_manifests" / alias / f"{chunk}.json"
        ids = [str(row["id"]) for row in rows]
        if chunk_output.exists():
            if not (chunk_output / "summary.json").is_file() or not (chunk_output / "draft_candidates.jsonl").is_file():
                raise RuntimeError(f"Incomplete pre-existing chunk; no automatic retry: {chunk_output}")
            read_chunk(chunk_output, ids, samples)
            paths.append(chunk_output / "draft_candidates.jsonl")
            continue
        if chunk_manifest_path.exists():
            raise RuntimeError(f"Refusing to overwrite chunk manifest: {chunk_manifest_path}")
        used = check_gpu4()
        chunk_manifest = dict(manifest)
        chunk_manifest.update(candidate_count=len(rows), candidate_rows=rows,
                              total_generations=len(rows) * samples, generate=True,
                              status="execution_copy", source_manifest_sha256=manifest_hash,
                              execution_anchor=alias, execution_chunk=chunk)
        save_json(chunk_manifest_path, chunk_manifest)
        command = [
            os.environ.get("BATCH04_PYTHON", "/data2/gaojc/envs/contextual-drag-vllm/bin/python"),
            str(SCREEN_RUNNER), "--model", anchor["model"], "--model-alias", alias,
            "--input", str(INPUT), "--manifest", str(chunk_manifest_path),
            "--source-revision", SOURCE_REVISION, "--output", str(chunk_output),
            "--max-num-seqs", str(anchor["max_num_seqs"]),
            "--max-num-batched-tokens", str(anchor["max_num_batched_tokens"]),
            "--gpu-memory-utilization", anchor["gpu_memory_utilization"],
        ]
        status.update(state="running", current_anchor=alias, current_chunk=chunk,
                      gpu4_used_mib_before_chunk=used, elapsed_seconds=time.monotonic() - started,
                      updated_utc=utc_now())
        save_json(OUTPUT / "status.json", status)
        print(f"START {alias} {chunk} questions={ids} gpu4_mib={used}", flush=True)
        with (root / f"{chunk}.log").open("w", encoding="utf-8") as log:
            subprocess.run(command, cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, check=True)
        read_chunk(chunk_output, ids, samples)
        paths.append(chunk_output / "draft_candidates.jsonl")
        status["completed_generations"] += len(rows) * samples
        status["completed_chunks"].append({"anchor": alias, "chunk": chunk, "questions": ids,
                                           "generations": len(rows) * samples})
        status.update(elapsed_seconds=time.monotonic() - started, updated_utc=utc_now())
        save_json(OUTPUT / "status.json", status)
        print(f"COMPLETE {alias} {chunk} total={status['completed_generations']}/{EXPECTED_TOTAL}", flush=True)
    return paths


def merge_and_queue(manifest: dict[str, Any], paths_by_anchor: dict[str, list[Path]]) -> None:
    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    samples: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    review: list[dict[str, Any]] = []
    total = 0
    for alias, paths in paths_by_anchor.items():
        lines: list[str] = []
        for path in paths:
            lines.extend(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        merged = OUTPUT / alias / "draft_candidates.jsonl"
        merged.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for line in lines:
            row = json.loads(line)
            total += 1
            qid = str(row["id"])
            gen = row["init_response_generations"][0]
            valid = gen.get("finish_reason") == "eos" and row.get("thinking_status") == "parsable_thinking" and bool(row.get("final_response", "").strip())
            samples[qid][alias] += 1
            if valid and gen.get("correctness") is True:
                counts[qid]["valid_official_true"] += 1
            elif valid and gen.get("correctness") is False:
                counts[qid]["valid_official_false_pending_manual_audit"] += 1
                review.append({"model": alias, "id": qid, "sample_index": gen.get("response_id"),
                               "draft_key": row.get("draft_key"), "answer": row.get("answer"),
                               "extracted_answer": gen.get("extracted_answer"),
                               "final_response": row.get("final_response"),
                               "source": str(merged), "manual_status": "pending"})
            else:
                counts[qid]["invalid_or_unresolved"] += 1
    expected_ids = {str(row["id"]) for row in manifest["candidate_rows"]}
    if total != EXPECTED_TOTAL or set(samples) != expected_ids:
        raise RuntimeError(f"Unexpected merged output: {total} generations for {len(samples)} questions")
    for qid in expected_ids:
        if samples[qid] != collections.Counter({"Qwen3_8B_Thinking": 8, "Qwen3_32B": 8}):
            raise RuntimeError(f"Two-anchor count mismatch for {qid}: {samples[qid]}")
    preaudit = [qid for qid in expected_ids if counts[qid]["valid_official_true"] >= 2 and counts[qid]["valid_official_false_pending_manual_audit"] >= 2]
    save_json(OUTPUT / "pooled_scorer_summary.json", {
        "question_counts": {qid: dict(counts[qid]) for qid in sorted(expected_ids, key=int)},
        "samples_by_model": {qid: dict(samples[qid]) for qid in sorted(expected_ids, key=int)},
        "preaudit_candidate_ids_pending_manual_audit": sorted(preaudit, key=int),
        "eligibility_status": "every official-false candidate requires manual substantive-error review",
        "intervention_generations": 0,
    })
    save_json(OUTPUT / "manual_review_queue.json", review)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_inputs(manifest)
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing existing Batch04 output; review before restart: {OUTPUT}")
    used = check_gpu4()
    manifest_hash = sha256(MANIFEST_PATH)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    (OUTPUT / "chunk_manifests").mkdir()
    with (OUTPUT / "frozen_source_manifest.json").open("wb") as dst, MANIFEST_PATH.open("rb") as src:
        dst.write(src.read())
    save_json(OUTPUT / "launch_record.json", {
        "authorized_utc_date": "2026-09-25",
        "purpose": "Expand the independent Game24 pool with fewer screening draws per anchor per question",
        "source_manifest_sha256": manifest_hash,
        "baseline_screen_runner_sha256": sha256(SCREEN_RUNNER),
        "project_git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_revision": SOURCE_REVISION,
        "candidate_count": 32, "samples_per_question_per_anchor": 8,
        "total_generation_budget": EXPECTED_TOTAL,
        "models": ANCHORS, "gpu": GPU_ID, "gpu4_used_mib_before_launch": used,
        "screening_only": True, "automatic_intervention": False,
        "automatic_candidate_filtering": False, "manual_false_answer_audit_required": True,
    })
    status = {"state": "running", "completed_generations": 0,
              "total_generations": EXPECTED_TOTAL, "completed_chunks": [],
              "started_utc": utc_now(), "started_unix": time.time()}
    save_json(OUTPUT / "status.json", status)
    started = time.monotonic()
    try:
        by_anchor: dict[str, list[Path]] = {}
        for anchor in ANCHORS:
            by_anchor[anchor["alias"]] = run_anchor(manifest, manifest_hash, anchor, status, started)
        merge_and_queue(manifest, by_anchor)
        status.update(state="complete_awaiting_manual_pooled_audit", completed_generations=EXPECTED_TOTAL,
                      elapsed_seconds=time.monotonic() - started, updated_utc=utc_now())
        save_json(OUTPUT / "status.json", status)
        print("BATCH04_SCREEN_COMPLETE_512_AWAITING_MANUAL_AUDIT", flush=True)
    except BaseException as exc:
        status.update(state="failed_no_automatic_retry", error=repr(exc),
                      elapsed_seconds=time.monotonic() - started, updated_utc=utc_now())
        save_json(OUTPUT / "status.json", status)
        raise


if __name__ == "__main__":
    main()
