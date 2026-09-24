"""Mark the manually stopped Batch03 run as interrupted without changing counts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


OUTPUT = Path("outputs/game24-batch03-dual-anchor-20260924")


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    status_path = OUTPUT / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("state") != "running":
        raise RuntimeError(f"Expected running state, found {status.get('state')!r}")
    if status.get("completed_generations") != 864 or status.get("current_chunk") != "chunk-11":
        raise RuntimeError("Live Batch03 state changed; refusing to write a stale interruption record")

    partial_dir = OUTPUT / "Qwen3_32B" / "chunk-11"
    forbidden_outputs = ["summary.json", "draft_candidates.jsonl", "results.jsonl", "raw_results.jsonl"]
    existing_outputs = [name for name in forbidden_outputs if (partial_dir / name).exists()]
    if existing_outputs:
        raise RuntimeError(f"Chunk 11 now has output files; re-audit before recording interruption: {existing_outputs}")

    recorded_utc = datetime.now(timezone.utc).isoformat()
    record = {
        "run": "Batch03 dual-anchor Game24 R0 acquisition",
        "state": "interrupted_by_user_request",
        "recorded_utc": recorded_utc,
        "verified_gpu_release_utc": "2026-09-24T11:55:56+00:00",
        "stop_window_utc": ["2026-09-24T11:55:26+00:00", "2026-09-24T11:55:56+00:00"],
        "stop_method": "Stopped the verified scheduler process first, then terminated its generation task; confirmed no Batch03 process or GPU4 compute process remained.",
        "verified_processes_before_stop": {
            "scheduler_pid": 2740555,
            "generation_pid": 3673360,
            "vllm_engine_pid": 3673624,
            "owner": "gaojc",
        },
        "gpu4_after_stop": {"memory_used_mib": 4, "utilization_percent": 0, "compute_processes": 0},
        "persisted_generations": 864,
        "planned_generations": 1024,
        "persisted_chunk_range": {
            "Qwen3_8B_Thinking": "chunk-00 through chunk-07 (512/512)",
            "Qwen3_32B": "chunk-00 through chunk-10 (352/512)",
        },
        "interrupted_chunk": {
            "model": "Qwen3_32B",
            "name": "chunk-11",
            "planned_generations": 32,
            "last_log_state": {
                "utc": "2026-09-24T11:55:26+00:00",
                "running": 4,
                "waiting": 15,
                "inferred_finished_but_unpersisted": 13,
                "kv_cache_percent": 100.0,
                "generation_tokens_per_second": 9.3,
            },
            "outputs_persisted": 0,
            "disposition": "Discarded in-memory partial generation results; retained config, requests, manifest snapshot, and chunk log.",
        },
        "unpersisted_planned_generations": 160,
        "unstarted_chunks": ["Qwen3_32B/chunk-12", "Qwen3_32B/chunk-13", "Qwen3_32B/chunk-14", "Qwen3_32B/chunk-15"],
        "completion_claim": False,
    }
    write_json_atomic(OUTPUT / "interruption_record.json", record)
    status.update(
        {
            "state": "interrupted",
            "interrupted_utc": recorded_utc,
            "completed_generations": 864,
            "unpersisted_planned_generations": 160,
            "completion_claim": False,
            "interruption_record": str(OUTPUT / "interruption_record.json"),
        }
    )
    write_json_atomic(status_path, status)
    print(json.dumps({"state": status["state"], "completed_generations": status["completed_generations"], "interrupted_utc": recorded_utc}, ensure_ascii=False))


if __name__ == "__main__":
    main()
