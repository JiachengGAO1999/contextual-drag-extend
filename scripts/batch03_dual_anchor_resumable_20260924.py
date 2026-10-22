"""Resumable Batch03 R0 sampling runner. Never merges into or overwrites the source run."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import importlib.metadata
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from batch03_resume_core_20260924 import (
    append_jsonl_once,
    atomic_write_json,
    contiguous_sample_runs,
    consume_request_stream,
    load_completed,
    missing_sample_indices,
    sample_seed,
)
from baseline_screen_vllm_20260917 import official_score, parse_final, problem_text


RUNNER_VERSION = "2026-09-24-resumable-v2-per-sample-seed"
DEFAULT_CONTEXT = 32768


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows_by_id(input_path: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        source = {str(row["Rank"]): row for row in csv.DictReader(handle)}
    rows = []
    for item in manifest["candidate_rows"]:
        qid = str(item["id"])
        source_row = source.get(qid)
        if source_row is None:
            raise RuntimeError(f"Manifest question {qid} missing from {input_path}")
        numbers = [int(value) for value in source_row["Puzzles"].split()]
        if sorted(numbers) != sorted(int(value) for value in item["numbers"]):
            raise RuntimeError(f"Input/manifest number mismatch for {qid}: {numbers} != {item['numbers']}")
        rows.append({"id": qid, "answer": numbers, "problem": problem_text(numbers)})
    if len({row["id"] for row in rows}) != len(rows):
        raise RuntimeError("Manifest contains duplicate question IDs")
    return rows


def load_request_archive(paths: list[Path], expected_ids: set[str]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in paths:
        for request in read_json(path):
            qid = str(request["id"])
            if qid not in expected_ids:
                raise RuntimeError(f"Request archive has unexpected question id {qid}: {path}")
            if not request.get("prompt_token_ids") or not request.get("prompt"):
                raise RuntimeError(f"Prompt/token archive is incomplete for {qid}: {path}")
            previous = by_id.get(qid)
            if previous is not None and previous != request:
                raise RuntimeError(f"Conflicting frozen prompts for question {qid}")
            by_id[qid] = request
    missing = expected_ids - set(by_id)
    if missing:
        raise RuntimeError(f"No frozen request archive for questions: {sorted(missing)}")
    return by_id


def get_plan(args: argparse.Namespace) -> tuple:
    manifest = read_json(args.manifest)
    reference = read_json(args.reference_config)
    if manifest.get("task", "game24") != "game24":
        raise ValueError("This recovery runner only supports the frozen Game24 task")
    sample_count = int(manifest["samples_per_problem"])
    if sample_count != 16 or len(manifest["candidate_rows"]) != int(manifest["candidate_count"]):
        raise RuntimeError("Unexpected frozen Batch03 manifest shape")
    target_sample_count = sample_count if args.sample_limit is None else args.sample_limit
    if not 1 <= target_sample_count <= sample_count:
        raise ValueError(f"--sample-limit must be in [1, {sample_count}]")
    model_alias = args.model_alias
    if reference.get("model_alias") != model_alias:
        raise RuntimeError(f"Reference config alias {reference.get('model_alias')} != {model_alias}")
    if int(reference["seed"]) != int(manifest["seed"]):
        raise RuntimeError("Reference config seed differs from frozen manifest")
    model_path = args.model or reference["model"]
    if args.model and str(args.model) != str(reference["model"]):
        raise RuntimeError("Explicit model path differs from the original Batch03 model path")
    rows = rows_by_id(args.input, manifest)
    request_by_id = load_request_archive(args.request_archive, {row["id"] for row in rows})
    for row in rows:
        archived = request_by_id[row["id"]]
        if archived.get("problem") != row["problem"] or archived.get("answer") != row["answer"]:
            raise RuntimeError(f"Archived request content differs from the frozen manifest for {row['id']}")
        if int(archived["max_tokens"]) != int(reference["context_length"]) - len(archived["prompt_token_ids"]):
            raise RuntimeError(f"Archived generation length budget is inconsistent for {row['id']}")
    if int(reference["context_length"]) != DEFAULT_CONTEXT:
        raise RuntimeError("Unexpected Batch03 context length")
    existing_paths = list(args.existing_results)
    completed, canonical = load_completed(existing_paths)
    tasks = []
    for row in rows:
        missing = missing_sample_indices(completed, model_alias, row["id"], target_sample_count)
        if missing:
            tasks.append({"row": row, "request": request_by_id[row["id"]], "sample_indices": missing})
    return manifest, reference, rows, request_by_id, completed, canonical, tasks, model_path


def make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-alias", required=True, choices=["Qwen3_8B_Thinking", "Qwen3_32B"])
    parser.add_argument("--model", help="Must match the original run model path; defaults to reference config")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="Frozen full 32-question manifest")
    parser.add_argument("--reference-config", type=Path, required=True, help="A completed original chunk config for this model")
    parser.add_argument("--request-archive", type=Path, action="append", required=True,
                        help="Original requests.json files; pass all question prompts, usually from the completed 8B chunks")
    parser.add_argument("--existing-results", type=Path, action="append", default=[],
                        help="Original and previous recovery draft_candidates.jsonl files; repeat for multiple paths")
    parser.add_argument("--output", type=Path, required=True,
                        help="New isolated recovery directory; reused only when its config matches this run")
    parser.add_argument("--max-num-seqs", type=int, default=None)
    parser.add_argument("--max-num-batched-tokens", type=int, default=None)
    parser.add_argument("--gpu-memory-utilization", type=float, default=None)
    parser.add_argument("--sample-limit", type=int, default=None,
                        help="Maximum fixed-prefix sample index per question (default 16); set explicitly for a recorded mid-course revision")
    parser.add_argument("--plan-only", action="store_true", help="Validate and print missing sample identities without creating output or loading vLLM")
    return parser


async def run_generation(args: argparse.Namespace) -> int:
    manifest, reference, rows, request_by_id, completed, canonical, tasks, model_path = get_plan(args)
    output_dir: Path = args.output
    sample_count = (int(manifest["samples_per_problem"]) if args.sample_limit is None
                    else args.sample_limit)
    planned_count = sum(len(task["sample_indices"]) for task in tasks)
    max_num_seqs = args.max_num_seqs
    if max_num_seqs is None:
        max_num_seqs = 1 if args.model_alias == "Qwen3_32B" else int(reference["max_num_seqs"])
    if args.model_alias == "Qwen3_32B" and max_num_seqs != 1:
        raise RuntimeError("The proposed Batch03 32B recovery configuration requires max_num_seqs=1")
    max_batched_tokens = args.max_num_batched_tokens or int(reference["max_num_batched_tokens"])
    gpu_memory_utilization = args.gpu_memory_utilization or float(reference["gpu_memory_utilization"])
    output_file = output_dir / "draft_candidates.jsonl"
    existing_run = output_dir.exists()
    manifest_hash = sha256_file(args.manifest)
    frozen_config = {
        "runner_version": RUNNER_VERSION,
        "run_state_origin": "interrupted_batch03",
        "output_scope": "isolated recovery samples for one model alias; does not complete or rewrite the original run",
        "model": str(model_path), "model_alias": args.model_alias,
        "manifest": str(args.manifest), "manifest_sha256": manifest_hash,
        "input": str(args.input), "seed": int(manifest["seed"]),
        "seed_policy": "sample_seed = base_seed + frozen_sample_index; contiguous missing-index runs use vLLM n-way child seeds",
        "input_sha256": sha256_file(args.input),
        "reference_config_sha256": sha256_file(args.reference_config),
        "request_archive_sha256": {str(path): sha256_file(path) for path in args.request_archive},
        "samples_per_question": sample_count,
        "original_samples_per_question": int(manifest["samples_per_problem"]),
        "context_length": int(reference["context_length"]),
        "sampling": dict(reference["sampling"]),
        "max_num_seqs": max_num_seqs,
        "original_max_num_seqs": int(reference["max_num_seqs"]),
        "max_num_batched_tokens": max_batched_tokens,
        "gpu_memory_utilization": gpu_memory_utilization,
        "enable_prefix_caching": False, "enable_chunked_prefill": True,
        "enforce_eager": True, "attention_backend": reference.get("attention_backend", "FLASH_ATTN"),
        "vllm_version_reference": reference.get("vllm_version"),
        "reproducibility_note": "Per-sample seed is fixed by frozen sample index, preventing seed reuse or relabeling across resume gaps. Each contiguous missing-index run starts with base_seed + first_index, matching vLLM n-way child seeds. Scheduling changes still mean token-for-token replay is not guaranteed.",
        "prompt_source": "frozen requests.json archives, using the exact stored prompt_token_ids and per-question max_tokens",
        "planned_targets": [{"id": task["row"]["id"], "sample_indices": task["sample_indices"]} for task in tasks],
        "planned_generations": planned_count,
    }
    signature_fields = ("runner_version", "model", "model_alias", "manifest_sha256", "seed", "samples_per_question")
    if existing_run:
        config_path = output_dir / "config.json"
        if not config_path.is_file() or not output_file.exists():
            raise RuntimeError(f"Output exists but is not a resumable recovery directory: {output_dir}")
        prior = read_json(config_path)
        if any(prior.get(key) != frozen_config.get(key) for key in signature_fields):
            raise RuntimeError("Recovery output signature changed; choose a new output directory")
        for field in ("sampling", "max_num_seqs", "max_num_batched_tokens", "gpu_memory_utilization",
                      "input_sha256", "reference_config_sha256", "request_archive_sha256",
                      "planned_targets", "planned_generations"):
            if prior.get(field) != frozen_config.get(field):
                raise RuntimeError(f"Recovery configuration changed at {field}; choose a new output directory")

    output_file = output_dir / "draft_candidates.jsonl"
    result_catalog_paths = list(args.existing_results)
    if output_file.exists():
        result_catalog_paths.append(output_file)
    completed_all, canonical_all = load_completed(result_catalog_paths)
    planned_identity_set = {
        (args.model_alias, task["row"]["id"], sample_index)
        for task in tasks for sample_index in task["sample_indices"]
    }
    own_completed = load_completed([output_file])[0] if output_file.exists() else set()
    unexpected_own = own_completed - planned_identity_set
    if unexpected_own:
        raise RuntimeError(f"Recovery output contains identities outside its frozen plan: {sorted(unexpected_own)[:5]}")
    pending_tasks = []
    for task in tasks:
        pending = [index for index in task["sample_indices"]
                   if (args.model_alias, str(task["row"]["id"]), index) not in completed_all]
        if pending:
            pending_tasks.append({**task, "sample_indices": pending})
    pending_count = sum(len(task["sample_indices"]) for task in pending_tasks)

    plan_payload = {
        "state": "prepared" if planned_count else "no_work_remaining",
        "model_alias": args.model_alias,
        "original_completed_for_model": len([x for x in completed if x[0] == args.model_alias]),
        "planned_missing_generations": planned_count,
        "pending_generations_after_recovery_checkpoint": pending_count,
        "persisted_in_recovery_directory": len(load_completed([output_file])[0]) if output_file.exists() else 0,
        "target_tasks": [{"id": task["row"]["id"], "sample_indices": task["sample_indices"]} for task in pending_tasks],
        "original_batch_completion_claim": False,
    }
    if args.plan_only:
        print(json.dumps(plan_payload, ensure_ascii=False, indent=2))
        return 0

    if not existing_run:
        output_dir.mkdir(parents=True)
        atomic_write_json(output_dir / "config.json", frozen_config)
        atomic_write_json(output_dir / "manifest_snapshot.json", manifest)
        atomic_write_json(output_dir / "requests.json", [
            {"id": task["row"]["id"], "problem": task["row"]["problem"],
             "answer": task["row"]["answer"], "prompt": task["request"]["prompt"],
             "prompt_token_ids": task["request"]["prompt_token_ids"],
             "max_tokens": task["request"]["max_tokens"],
             "sample_indices_planned": task["sample_indices"]}
            for task in tasks
        ])
    if not output_file.exists():
        output_file.touch()
    if planned_count == 0:
        atomic_write_json(output_dir / "status.json", plan_payload)
        print(json.dumps(plan_payload, ensure_ascii=False, indent=2))
        return 0
    if pending_count == 0:
        finished_payload = {**plan_payload, "state": "recovery_scope_finished", "remaining_in_recovery_plan": 0}
        atomic_write_json(output_dir / "status.json", finished_payload)
        print(json.dumps(finished_payload, ensure_ascii=False, indent=2))
        return 0

    signal_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    old_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, lambda _signum, _frame: loop.call_soon_threadsafe(signal_event.set))

    os.environ["VLLM_ATTENTION_BACKEND"] = frozen_config["attention_backend"]
    os.environ["VLLM_USE_V1"] = "1"
    from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams

    engine_args = AsyncEngineArgs(
        model=str(model_path), tokenizer=str(model_path), dtype="bfloat16",
        max_model_len=int(reference["context_length"]), max_num_seqs=max_num_seqs,
        max_num_batched_tokens=max_batched_tokens, gpu_memory_utilization=gpu_memory_utilization,
        enable_prefix_caching=False, enable_chunked_prefill=True, enforce_eager=True,
        generation_config="vllm", disable_log_stats=False, seed=int(manifest["seed"]),
    )
    engine = None
    started = time.monotonic()
    generation_started = None
    persisted_this_run = 0
    request_durations = []
    run_state = "interrupted"
    atomic_write_json(output_dir / "status.json", {**plan_payload, "state": "running"})
    try:
        engine = AsyncLLMEngine.from_engine_args(engine_args)
        tokenizer = await engine.get_tokenizer()
        generation_started = time.monotonic()
        for task in pending_tasks:
            if signal_event.is_set():
                break
            row, request = task["row"], task["request"]
            sample_indices = task["sample_indices"]
            params = dict(reference["sampling"])
            params.pop("max_tokens", None)
            for sample_run in contiguous_sample_runs(sample_indices):
                if signal_event.is_set():
                    break
                run_seed = sample_seed(int(manifest["seed"]), sample_run[0])
                sampling = SamplingParams(
                    n=len(sample_run), temperature=params["temperature"], top_p=params["top_p"],
                    top_k=params.get("top_k", -1), seed=run_seed,
                    max_tokens=int(request["max_tokens"]), skip_special_tokens=False,
                )
                request_id = (f"batch03-resume-{args.model_alias}-{row['id']}-"
                              f"s{sample_run[0]}-e{sample_run[-1]}")
                request_started = time.monotonic()

                def persist(completion_sample_index: int, completion: Any) -> None:
                    nonlocal persisted_this_run
                    if completion_sample_index not in sample_run:
                        raise RuntimeError(f"vLLM child mapped outside planned sample run: {completion_sample_index}")
                    seed = sample_seed(int(manifest["seed"]), completion_sample_index)
                    raw_finish = completion.finish_reason
                    generated = completion.text
                    try:
                        final, thinking_status = parse_final(generated, request["prompt"], tokenizer.eos_token)
                        postprocess_error = None
                    except Exception as exc:
                        final, thinking_status = generated, "parse_error"
                        postprocess_error = f"{type(exc).__name__}: {exc}"
                    token_ids = list(completion.token_ids)
                    elapsed = time.monotonic() - request_started
                    metadata = {
                        "backend": "ordinary_vllm_v1_async_default_worker",
                        "condition_id": "R0", "access_mode": "full",
                        "sample_seed": seed, "base_seed": int(manifest["seed"]),
                        "resume_seed_policy": "base_seed_plus_frozen_sample_index",
                        "resume_sample_index": completion_sample_index,
                        "vllm_finish_reason": raw_finish, "stop_reason": getattr(completion, "stop_reason", None),
                        "prompt_tokens": len(request["prompt_token_ids"]), "generated_tokens": len(token_ids),
                        "resume_local_completion_index": int(completion.index),
                        "resume_parent_seed": run_seed,
                        "resume_child_seed_index": int(completion.index),
                        "resume_schedule_note": "contiguous missing-index run; vLLM child seed equals run seed plus local index",
                    }
                    record = {
                        "id": row["id"], "task": "game24", "problem": row["problem"], "answer": row["answer"],
                        "draft_key": f"{row['id']}/{completion_sample_index}",
                        "init_response_generations": [{
                            "response_id": completion_sample_index, "generated_response": generated,
                            "finish_reason": "eos" if raw_finish == "stop" else raw_finish,
                            "vllm_finish_reason": raw_finish, "stop_reason": getattr(completion, "stop_reason", None),
                            "selective_context_metadata": metadata,
                        }],
                        "init_response_prompt": request["prompt"],
                        "init_response_generations_metadata": {
                            "num_responses": 1, "template_path": "prompt_templates/init_response_prompt_templates.json",
                            "template_key": "qwen_math_prompt", "enable_thinking": True,
                            "partition_id": 0, "num_partitions": 1, "model_config_alias": args.model_alias,
                            "intervention": {"condition_id": "R0", "access_mode": "full",
                                             "backend": "ordinary_vllm_v1_async_default_worker",
                                             "sample_seed": seed, "base_seed": int(manifest["seed"])},
                        },
                        "generated_token_ids": token_ids, "final_response": final,
                        "thinking_status": thinking_status, "generation_seconds": elapsed, "tokens": len(token_ids),
                    }
                    try:
                        scored = official_score(record, "game24")
                    except Exception as exc:
                        scored = record
                        scored["init_response_generations"][0]["correctness"] = None
                        postprocess_error = "; ".join(filter(None, [postprocess_error,
                            f"scoring {type(exc).__name__}: {exc}"]))
                    if postprocess_error:
                        scored["postprocess_error"] = postprocess_error
                    wrote = append_jsonl_once(output_file, scored, completed_all, canonical_all)
                    if wrote:
                        persisted_this_run += 1
                        request_durations.append(elapsed)
                        now = time.monotonic()
                        saved_in_output = len(load_completed([output_file])[0])
                        remaining = planned_count - saved_in_output
                        atomic_write_json(output_dir / "status.json", {
                            "state": "running", "model_alias": args.model_alias,
                            "planned_missing_generations": planned_count,
                            "persisted_in_recovery_directory": saved_in_output,
                            "remaining_in_recovery_plan": max(0, remaining),
                            "last_persisted_identity": [args.model_alias, row["id"], completion_sample_index],
                            "last_sample_seed": seed,
                            "last_persisted_at_unix": time.time(),
                            "elapsed_seconds": round(now - started, 3),
                            "original_batch_completion_claim": False,
                        })
                        print(json.dumps({"event": "sample_persisted", "model": args.model_alias,
                                          "id": row["id"], "sample_index": completion_sample_index, "sample_seed": seed,
                                          "saved_in_recovery": saved_in_output, "planned": planned_count}, ensure_ascii=False), flush=True)

                _, request_finished = await consume_request_stream(
                    engine, {"prompt_token_ids": request["prompt_token_ids"]}, sampling,
                    request_id, sample_run, persist, signal_event,
                )
                if not request_finished:
                    break
            if signal_event.is_set():
                break

        saved_in_output = len(load_completed([output_file])[0])
        complete = saved_in_output >= planned_count and not signal_event.is_set()
        run_state = "recovery_scope_finished" if complete else "interrupted"
        total_wall = time.monotonic() - started
        generation_wall = (time.monotonic() - generation_started) if generation_started is not None else 0.0
        summary = {
            "state": run_state, "model_alias": args.model_alias,
            "planned_missing_generations": planned_count,
            "persisted_in_recovery_directory": saved_in_output,
            "remaining_in_recovery_plan": max(0, planned_count - saved_in_output),
            "request_completion_wall_seconds_sum": round(sum(request_durations), 3),
            "run_generation_wall_seconds": round(generation_wall, 3),
            "run_total_wall_seconds": round(total_wall, 3),
            "mean_completed_sample_latency_seconds": round(sum(request_durations) / len(request_durations), 3) if request_durations else None,
            "original_batch_state": "interrupted",
            "original_batch_completion_claim": False,
            "automatic_expansion": False, "interventions_run": False,
        }
        atomic_write_json(output_dir / "summary.json", summary)
        atomic_write_json(output_dir / "status.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        return 0 if complete else 75
    except BaseException as exc:
        run_state = "interrupted" if signal_event.is_set() else "failed"
        saved_in_output = len(load_completed([output_file])[0]) if output_file.exists() else 0
        atomic_write_json(output_dir / "status.json", {
            "state": run_state, "model_alias": args.model_alias,
            "planned_missing_generations": planned_count,
            "persisted_in_recovery_directory": saved_in_output,
            "remaining_in_recovery_plan": max(0, planned_count - saved_in_output),
            "original_batch_completion_claim": False,
            "exception_type": type(exc).__name__, "exception": str(exc),
        })
        raise
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        if engine is not None:
            shutdown = getattr(engine, "shutdown", None)
            if shutdown is not None:
                shutdown()


def main() -> None:
    parser = make_arg_parser()
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(run_generation(args))
    except Exception as exc:
        print(f"RESUMABLE_RUNNER_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
