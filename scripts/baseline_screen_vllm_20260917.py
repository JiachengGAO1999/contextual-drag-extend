"""Fixed Stage-1 R0 baseline screen using ordinary vLLM.

This runner intentionally does not import the selective vLLM worker or run any
intervention. It generates the manifest-specified samples for the fixed manifest and
writes records compatible with the existing audit/manual-review pipeline.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import subprocess
import time
from pathlib import Path


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def problem_text(numbers):
    return (f"Use the numbers {', '.join(map(str, numbers))} exactly once each, with addition, "
            "subtraction, multiplication, division and parentheses, to make 24. "
            "Provide an expression using the original four numbers.")


def official_score(record, task="game24"):
    if task != "game24":
        from selective_context.tasks import score_record
        return score_record(record, task)
    """Use the official scorer; retain the repo's narrow Game24 fallback only if math_verify is absent."""
    try:
        from utils.verifiable_evaluation.math_eval.utils.evaluation_utils import evaluate_single_entry
        from utils.verifiable_evaluation.math_eval.utils.verification_utils import is_correct_game_of_24
        return evaluate_single_entry(record, "answer", "init_response_generations", is_correct_game_of_24)
    except ModuleNotFoundError as exc:
        if exc.name != "math_verify":
            raise
        from selective_context.official_compat import evaluate_game24_record
        return evaluate_game24_record(record)


def parse_final(raw_text, prompt, eos_token):
    from data_generation.initial_sampling_postprocess import parse_thinking_steps
    final, status = parse_thinking_steps(raw_text, prompt, max_response_length=32768 * 20)
    if eos_token:
        final = final.replace(eos_token, "")
    return final.strip(), status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-input-only", action="store_true", help="Check dataset/manifest/scorer without loading a model or generating")
    ap.add_argument("--task", choices=["game24", "math500"], default="game24")
    ap.add_argument("--model", required=True)
    ap.add_argument("--model-alias", choices=["Qwen3_8B_Thinking", "Qwen3_32B"], default="Qwen3_8B_Thinking")
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--source-revision", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--max-num-seqs", type=int, default=16)
    ap.add_argument("--max-num-batched-tokens", type=int, default=8192)
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    args = ap.parse_args()
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite an existing baseline screen")
    repo = Path(__file__).resolve().parents[1]
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    candidates = manifest["candidate_rows"]
    if len(candidates) != manifest["candidate_count"]:
        raise RuntimeError("Manifest candidate count mismatch")

    if manifest.get("task", "game24") != args.task:
        raise ValueError("Manifest task mismatch")
    if args.task == "math500":
        from selective_context.tasks import validate_pair_task
        source_rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_id = {r["id"]: r for r in source_rows}
        if len(by_id) != len(source_rows):
            raise ValueError("Duplicate MATH500 source IDs")
        rows = []
        for item in candidates:
            row = by_id[item["id"]]
            validate_pair_task(row, args.task)
            if hashlib.sha256(row["problem"].encode()).hexdigest() != item["problem_sha256"]:
                raise ValueError("MATH500 problem fingerprint mismatch")
            if hashlib.sha256(row["answer"].encode()).hexdigest() != item["answer_sha256"]:
                raise ValueError("MATH500 reference fingerprint mismatch")
            rows.append(row)
    else:
        with args.input.open(encoding="utf-8-sig") as handle:
            csv_rows = list(csv.DictReader(handle))
        by_id = {str(row["Rank"]): row for row in csv_rows}
        rows = []
        for item in candidates:
            row = by_id.get(str(item["id"]))
            if row is None:
                raise RuntimeError(f"Manifest id {item['id']} missing from input CSV")
            numbers = [int(x) for x in row["Puzzles"].split()]
            if sorted(numbers) != sorted(item["numbers"]):
                raise RuntimeError(f"Number mismatch for {item['id']}: CSV={numbers}, manifest={item['numbers']}")
            rows.append({"id": str(item["id"]), "answer": numbers, "problem": problem_text(numbers)})

    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate candidate IDs")
    if args.task == "math500":
        from utils.verifiable_evaluation.math_eval.utils.math_utils import is_equivalent_math
        if not is_equivalent_math("0.5", r"\frac{1}{2}"):
            raise RuntimeError("Official math scorer preflight failed")
    if args.validate_input_only:
        print(json.dumps({"task": args.task, "validated_rows": len(rows), "generation_started": False}))
        return
    args.output.mkdir(parents=True)

    # These are deliberate ordinary-vLLM settings. Do not inherit a custom
    # selective worker/backend from the resident service.
    os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
    os.environ["VLLM_USE_V1"] = "1"
    from vllm import LLM, SamplingParams
    from selective_context.prompting import render_chat_prompt, render_official_prompt

    cfg = json.loads((repo / "utils/general_inference/eval_models_params.json").read_text())[args.model_alias]
    context = int(cfg["context_length"])
    sample = cfg["sampling_params"]
    tokenizer_probe = None
    started = time.monotonic()
    llm = LLM(model=args.model, tokenizer=args.model, dtype="bfloat16",
              max_model_len=context, max_num_seqs=args.max_num_seqs,
              max_num_batched_tokens=args.max_num_batched_tokens,
              gpu_memory_utilization=args.gpu_memory_utilization,
              enable_prefix_caching=False, enable_chunked_prefill=True,
              enforce_eager=True, generation_config="vllm", disable_log_stats=False,
              seed=manifest["seed"])
    loaded = time.monotonic()
    tokenizer = llm.get_tokenizer()
    prompts = [render_chat_prompt(tokenizer, render_official_prompt(repo, "R0", row["problem"]),
                                  enable_thinking=True) for row in rows]
    prompt_ids = [tokenizer.encode(prompt, add_special_tokens=False) for prompt in prompts]
    if any(len(ids) >= context for ids in prompt_ids):
        raise RuntimeError("At least one prompt leaves no generation budget")
    params = [SamplingParams(n=manifest["samples_per_problem"], temperature=sample["temperature"],
                             top_p=sample["top_p"], top_k=sample.get("top_k", -1),
                             seed=manifest["seed"], max_tokens=context - len(ids),
                             skip_special_tokens=False) for ids in prompt_ids]

    provenance = {
        "run_name": args.output.name,
        "task": args.task,
        "purpose": "Stage-1 baseline-only acquisition; no intervention and no outcome-based selection",
        "source_revision": args.source_revision,
        "input": str(args.input),
        "manifest": str(args.manifest),
        "candidate_ids": [row["id"] for row in rows],
        "candidate_count": len(rows),
        "samples_per_problem": manifest["samples_per_problem"],
        "total_generations": len(rows) * manifest["samples_per_problem"],
        "model": args.model,
        "model_alias": args.model_alias,
        "condition": "R0",
        "backend": "ordinary vLLM default worker; no selective mask",
        "attention_backend": os.environ["VLLM_ATTENTION_BACKEND"],
        "context_length": context,
        "sampling": dict(sample),
        "seed": manifest["seed"],
        "max_num_seqs": args.max_num_seqs,
        "max_num_batched_tokens": args.max_num_batched_tokens,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "enable_prefix_caching": False,
        "enable_chunked_prefill": True,
        "enforce_eager": True,
        "vllm_version": importlib.metadata.version("vllm"),
        "prompt_sha256": [hashlib.sha256(p.encode("utf-8")).hexdigest() for p in prompts],
        "prompt_tokens": [len(ids) for ids in prompt_ids],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=repo, text=True),
    }
    save(args.output / "config.json", provenance)
    save(args.output / "manifest_snapshot.json", manifest)
    save(args.output / "requests.json", [
        {"id": row["id"], "problem": row["problem"], "answer": row["answer"],
         "prompt": prompt, "prompt_token_ids": ids, "max_tokens": context - len(ids)}
        for row, prompt, ids in zip(rows, prompts, prompt_ids)
    ])
    print(json.dumps({"event": "generation_start", "total": len(rows) * manifest["samples_per_problem"],
                      "questions": len(rows), "loaded_seconds": loaded - started}, ensure_ascii=False), flush=True)
    generation_started = time.monotonic()
    outputs = llm.generate([{"prompt_token_ids": ids} for ids in prompt_ids], params, use_tqdm=False)
    generation_seconds = time.monotonic() - generation_started
    records = []
    raw_records = []
    for row, prompt, ids, request_output in zip(rows, prompts, prompt_ids, outputs):
        if len(request_output.outputs) != manifest["samples_per_problem"]:
            raise RuntimeError(f"Unexpected output count for {row['id']}: {len(request_output.outputs)}")
        for generation in request_output.outputs:
            raw_finish = generation.finish_reason
            normalized_finish = "eos" if raw_finish == "stop" else raw_finish
            generated = generation.text
            final, thinking_status = parse_final(generated, prompt, tokenizer.eos_token)
            metadata = {
                "backend": "ordinary_vllm_default_worker",
                "condition_id": "R0",
                "access_mode": "full",
                "sample_seed": manifest["seed"],
                "vllm_finish_reason": raw_finish,
                "stop_reason": generation.stop_reason,
                "prompt_tokens": len(ids),
                "generated_tokens": len(generation.token_ids),
            }
            record = {
                "id": row["id"],
                "task": args.task,
                "problem": row["problem"],
                "answer": row["answer"],
                "draft_key": f"{row['id']}/{generation.index}",
                "init_response_generations": [{
                    "response_id": generation.index,
                    "generated_response": generated,
                    "finish_reason": normalized_finish,
                    "vllm_finish_reason": raw_finish,
                    "stop_reason": generation.stop_reason,
                    "selective_context_metadata": metadata,
                }],
                "init_response_prompt": prompt,
                "init_response_generations_metadata": {
                    "num_responses": 1,
                    "template_path": "prompt_templates/init_response_prompt_templates.json",
                    "template_key": "qwen_math_prompt",
                    "enable_thinking": True,
                    "partition_id": 0,
                    "num_partitions": 1,
                    "model_config_alias": args.model_alias,
                    "intervention": {"condition_id": "R0", "access_mode": "full",
                                      "backend": "ordinary_vllm_default_worker",
                                      "sample_seed": manifest["seed"]},
                },
                "generated_token_ids": list(generation.token_ids),
                "final_response": final,
                "thinking_status": thinking_status,
                "generation_seconds": generation_seconds,
                "tokens": len(generation.token_ids),
            }
            scored = official_score(record, args.task)
            records.append(scored)
            raw_records.append({"id": row["id"], "sample_index": generation.index,
                                "text": generated, "token_ids": list(generation.token_ids),
                                "finish_reason": raw_finish, "stop_reason": generation.stop_reason,
                                "tokens": len(generation.token_ids)})

    with (args.output / "draft_candidates.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (args.output / "results.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (args.output / "raw_results.jsonl").open("w", encoding="utf-8") as handle:
        for record in raw_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    correct = sum(r["init_response_generations"][0].get("correctness") is True for r in records)
    failed = sum(r["init_response_generations"][0].get("correctness") is False for r in records)
    parseable = sum(r.get("thinking_status") == "parsable_thinking" for r in records)
    stopped = sum(r["init_response_generations"][0]["finish_reason"] == "eos" for r in records)
    total_tokens = sum(r["tokens"] for r in records)
    summary = {
        "generations": len(records), "questions": len(rows), "samples_per_question": manifest["samples_per_problem"],
        "stopped": stopped, "length_limited": len(records) - stopped, "parseable_thinking": parseable,
        "official_correct": correct, "official_incorrect": failed,
        "official_unparseable_or_null": len(records) - correct - failed,
        "tokens": total_tokens, "mean_tokens": total_tokens / len(records),
        "generation_seconds": generation_seconds, "load_seconds": loaded - started,
        "total_seconds": time.monotonic() - started,
        "tokens_per_second": total_tokens / generation_seconds if generation_seconds else None,
        "automatic_expansion": False, "interventions_run": False,
    }
    save(args.output / "summary.json", summary)
    print("BASELINE_SCREEN_COMPLETE " + json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
