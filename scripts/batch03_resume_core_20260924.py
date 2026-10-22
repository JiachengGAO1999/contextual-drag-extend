"""Dependency-light checkpoint primitives for the Batch03 recovery runner."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable


Identity = tuple[str, str, int]


def sample_seed(base_seed: int, sample_index: int) -> int:
    """Match vLLM n-way child seeds while keeping the mapping stable across resume gaps."""
    if sample_index < 0:
        raise ValueError("sample_index must be non-negative")
    return int(base_seed) + int(sample_index)


def contiguous_sample_runs(indices: Iterable[int]) -> list[list[int]]:
    """Partition sorted missing indices so vLLM child seeds stay aligned to sample IDs."""
    ordered = [int(index) for index in indices]
    if any(index < 0 for index in ordered):
        raise ValueError("sample indices must be non-negative")
    if ordered != sorted(set(ordered)):
        raise ValueError("sample indices must be unique and sorted")
    runs: list[list[int]] = []
    for index in ordered:
        if not runs or index != runs[-1][-1] + 1:
            runs.append([index])
        else:
            runs[-1].append(index)
    return runs


def sample_identity(record: dict[str, Any]) -> Identity:
    generation = record["init_response_generations"][0]
    model = record["init_response_generations_metadata"]["model_config_alias"]
    index = generation.get("response_id")
    if index is None:
        index = str(record["draft_key"]).rsplit("/", 1)[1]
    return str(model), str(record["id"]), int(index)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_completed(paths: Iterable[Path]) -> tuple[set[Identity], dict[Identity, str]]:
    """Load identities; allow byte-equivalent duplicate catalog entries, reject conflicts."""
    identities: set[Identity] = set()
    canonical: dict[Identity, str] = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        identities_in_file: set[Identity] = set()
        for record in read_jsonl(path):
            identity = sample_identity(record)
            if identity in identities_in_file:
                raise RuntimeError(f"Duplicate persisted identity inside {path}: {identity}")
            identities_in_file.add(identity)
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            previous = canonical.get(identity)
            if previous is not None and previous != encoded:
                raise RuntimeError(f"Conflicting persisted records for sample identity {identity} ({path})")
            identities.add(identity)
            canonical[identity] = encoded
    return identities, canonical


def missing_sample_indices(
    completed: set[Identity], model_alias: str, question_id: str, sample_count: int
) -> list[int]:
    return [index for index in range(sample_count)
            if (str(model_alias), str(question_id), index) not in completed]


def append_jsonl_once(
    path: Path,
    record: dict[str, Any],
    completed: set[Identity],
    canonical: dict[Identity, str],
) -> bool:
    identity = sample_identity(record)
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if identity in completed:
        if canonical.get(identity) != encoded:
            raise RuntimeError(f"Refusing conflicting duplicate sample identity {identity}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    completed.add(identity)
    canonical[identity] = encoded
    return True


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def finished_outputs(update: Any) -> list[Any]:
    return [output for output in update.outputs
            if getattr(output, "finish_reason", None) not in (None, "abort")]


async def consume_request_stream(
    engine: Any,
    prompt: Any,
    sampling_params: Any,
    request_id: str,
    target_sample_indices: list[int],
    persist: Callable[[int, Any], None],
    stop_event: asyncio.Event,
) -> tuple[set[int], bool]:
    """Persist each completed sequence; abort after the next checkpoint on safe stop."""
    completed_indices: set[int] = set()
    async for update in engine.generate(prompt, sampling_params, request_id=request_id):
        for output in finished_outputs(update):
            local_index = int(output.index)
            if local_index < 0 or local_index >= len(target_sample_indices):
                raise RuntimeError(f"Unexpected vLLM completion index {local_index} for {request_id}")
            sample_index = target_sample_indices[local_index]
            if sample_index not in completed_indices:
                persist(sample_index, output)
                completed_indices.add(sample_index)
        if stop_event.is_set():
            request_finished = bool(getattr(update, "finished", False))
            if not request_finished:
                await engine.abort(request_id=request_id)
            return completed_indices, request_finished
    return completed_indices, True
