"""Run a frozen R0-only capability gate with per-result durable writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

from selective_context.phase0.real_smoke import evaluate
from selective_context.phase0.thinking_pilot import extract_final_draft
from selective_context.prompting import load_request_bundle
from selective_context.hf_backend import GenerationResult


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class OrdinaryVLLMBackend:
    """Ordinary vLLM for R0, where no selective-attention worker is needed."""

    def __init__(self, model: str, *, max_model_len: int, max_num_seqs: int,
                 gpu_memory_utilization: float):
        from vllm import LLM
        self.engine = LLM(
            model=model,
            tokenizer=model,
            dtype="bfloat16",
            max_model_len=max_model_len,
            max_num_seqs=max_num_seqs,
            gpu_memory_utilization=gpu_memory_utilization,
            enable_prefix_caching=False,
            enable_chunked_prefill=True,
            max_num_batched_tokens=max_model_len,
            generation_config="vllm",
            disable_log_stats=False,
            seed=2027,
        )
        self.tokenizer = self.engine.get_tokenizer()
        self.max_model_len = max_model_len

    def generate_batch(self, requests, *, max_new_tokens: int, temperature: float,
                       top_p: float, top_k: int, on_result=None):
        from vllm import SamplingParams
        params = []
        for request in requests:
            request.validate()
            budget = min(max_new_tokens, self.max_model_len - len(request.input_ids))
            if budget < 1:
                raise ValueError("No generation budget")
            params.append(SamplingParams(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                seed=request.sample_seed,
                max_tokens=budget,
                skip_special_tokens=False,
                ignore_eos=False,
                stop_token_ids=[self.tokenizer.eos_token_id],
            ))
        began = time.monotonic()
        outputs = self.engine.generate(
            [dict(prompt_token_ids=request.input_ids) for request in requests],
            params,
            use_tqdm=False,
        )
        results = []
        for index, (request, output) in enumerate(zip(requests, outputs)):
            assert list(output.prompt_token_ids) == request.input_ids
            generated = output.outputs[0]
            tokens = list(generated.token_ids)
            # This runner defines no stop strings and its only stop token is
            # the tokenizer EOS, so every vLLM `stop` is an EOS completion.
            stopped_on_eos = generated.finish_reason == "stop"
            finish_reason = "eos" if stopped_on_eos else generated.finish_reason
            result = GenerationResult(
                tokens,
                self.tokenizer.decode(tokens, skip_special_tokens=False),
                finish_reason,
                {
                    "backend": "vllm_ordinary_0.11.0",
                    "batch_seconds": time.monotonic() - began,
                    "batch_size": len(requests),
                    "stop_reason": generated.stop_reason,
                    "sampling_rng": "vllm; not bitwise HF compatible",
                },
            )
            results.append(result)
            if on_result is not None:
                on_result(index, result)
        return results


class HFSequentialBackend:
    """Reference eager backend; all conditions can share this implementation."""

    def __init__(self, model: str, *, max_model_len: int):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from selective_context.hf_backend import SelectiveHFBackend

        tokenizer = AutoTokenizer.from_pretrained(
            model, local_files_only=True, use_fast=True
        )
        loaded = AutoModelForCausalLM.from_pretrained(
            model,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            device_map="cuda:0",
        )
        self.backend = SelectiveHFBackend(loaded, tokenizer)
        self.tokenizer = tokenizer
        self.max_model_len = max_model_len

    def generate_batch(self, requests, *, max_new_tokens: int, temperature: float,
                       top_p: float, top_k: int, on_result=None):
        results = []
        for index, request in enumerate(requests):
            budget = min(max_new_tokens, self.max_model_len - len(request.input_ids))
            if budget < 1:
                raise ValueError("No generation budget")
            result = self.backend.generate(
                request,
                max_new_tokens=budget,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )
            results.append(result)
            if on_result is not None:
                on_result(index, result)
        return results


def git_metadata(root: Path) -> tuple[str, str]:
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=root, text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable_non_git_snapshot", "unavailable_non_git_snapshot"
    return head, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--task", default="game24")
    parser.add_argument("--expected-questions", type=int, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.65)
    parser.add_argument("--max-new-tokens", type=int, default=32768)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--backend", choices=("selective", "ordinary", "hf"), default="selective")
    parser.add_argument(
        "--worker-cls",
        default="selective_context.vllm_worker.SelectiveWorker",
    )
    parser.add_argument(
        "--enable-thinking", action=argparse.BooleanOptionalAction, default=False
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    prepared = args.prepared.resolve()
    output = args.output.resolve()
    output.relative_to(root)
    if output.exists():
        raise RuntimeError("Refusing to overwrite an existing capability run")
    if len(set(args.seeds)) != len(args.seeds):
        raise RuntimeError("Duplicate seeds")

    full_manifest = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    selected = [row for row in full_manifest if row["condition"] == "R0"]
    expected = args.expected_questions * len(args.seeds)
    if len(selected) != expected:
        raise RuntimeError(f"Expected {expected} R0 requests, found {len(selected)}")

    jobs = []
    for item in selected:
        encoded, requests = load_request_bundle(root / item["bundle"])
        request = next(request for request in requests if request.condition_id == "R0")
        row = json.loads((root / item["pair"]).read_text(encoding="utf-8"))
        jobs.append((encoded, request, row, item))
    keys = [(str(row["id"]), request.sample_seed) for encoded, request, row, item in jobs]
    assert len(keys) == len(set(keys)) == expected
    assert len({key[0] for key in keys}) == args.expected_questions
    assert Counter(key[1] for key in keys) == Counter({seed: args.expected_questions for seed in args.seeds})
    assert all(row["audit_status"] == "substantive_failed" for _, _, row, _ in jobs)

    output.mkdir(parents=True)
    git_head, git_status = git_metadata(root)
    write_json(output / "manifest.json", selected)
    config = {
        "purpose": "target_model_R0_capability_gate_before_any_R2_or_R3_outcomes",
        "model": args.model,
        "model_config_alias": args.model_alias,
        "task": args.task,
        "questions": args.expected_questions,
        "seeds": args.seeds,
        "requests": expected,
        "sampling": {"temperature": 0.6, "top_p": 0.95, "top_k": 20},
        "context": args.max_model_len,
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "gate_frozen_before_outcomes": {
            "correct_at_least": 15,
            "normal_and_officially_parseable_at_least": 28,
            "denominator": 30,
            "failure_action": "do_not_run_or_inspect_R2_or_R3",
        },
        "prepared_manifest": str(prepared / "manifest.json"),
        "prepared_manifest_sha256": file_sha256(prepared / "manifest.json"),
        "git_head": git_head,
        "git_status": git_status,
        "durability": "each finished request is flushed and fsynced before progress is reported",
        "enable_thinking": args.enable_thinking,
        "backend": args.backend,
        "worker_cls": args.worker_cls if args.backend == "selective" else None,
        "eos_policy": (
            "HF backend stops on the union of model generation/config and tokenizer EOS token IDs"
            if args.backend == "hf"
            else "ignore_eos=False; tokenizer EOS also explicit stop token"
        ),
    }
    write_json(output / "config.json", config)

    if args.backend == "ordinary":
        backend = OrdinaryVLLMBackend(
            args.model,
            max_model_len=args.max_model_len,
            max_num_seqs=args.batch_size,
            gpu_memory_utilization=args.gpu_memory_utilization,
        )
    elif args.backend == "selective":
        from selective_context.vllm_backend import SelectiveVLLMBackend
        backend = SelectiveVLLMBackend(
            args.model,
            max_model_len=args.max_model_len,
            max_num_seqs=args.batch_size,
            gpu_memory_utilization=args.gpu_memory_utilization,
            worker_cls=args.worker_cls,
        )
    else:
        backend = HFSequentialBackend(args.model, max_model_len=args.max_model_len)
    began = time.monotonic()
    completed = 0
    correct_count = 0
    normal_parseable_count = 0
    with (output / "results.jsonl").open("a", encoding="utf-8") as handle:
        for start in range(0, len(jobs), args.batch_size):
            batch = jobs[start : start + args.batch_size]

            def save(index, generation):
                nonlocal completed, correct_count, normal_parseable_count
                encoded, request, row, _ = batch[index]
                record = evaluate(row, encoded, request, generation, task=args.task)
                if args.enable_thinking:
                    final_response, thinking_status = extract_final_draft(
                        generation.text, encoded.text, backend.tokenizer.eos_token
                    )
                else:
                    final_response = generation.text.strip()
                    thinking_status = "not_applicable_non_thinking_model"
                record.update(
                    final_response=final_response,
                    thinking_status=thinking_status,
                    stratum=row["stratum"],
                    benchmark=row["benchmark"],
                )
                record["init_response_generations_metadata"].update(
                    enable_thinking=args.enable_thinking, model_config_alias=args.model_alias
                )
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                completed += 1
                scored = record["init_response_generations"][0]["correctness"]
                correct_count += int(scored is True)
                normal_parseable_count += int(
                    generation.finish_reason == "eos" and scored is not None
                )
                print(json.dumps({
                    "event": "request_saved",
                    "completed": completed,
                    "total": expected,
                    "id": row["id"],
                    "seed": request.sample_seed,
                    "seconds": round(time.monotonic() - began, 1),
                }), flush=True)

            backend.generate_batch(
                [job[1] for job in batch],
                max_new_tokens=args.max_new_tokens,
                temperature=0.6,
                top_p=0.95,
                top_k=20,
                on_result=save,
            )
            remaining = expected - completed
            impossible_reason = None
            if correct_count + remaining < 15:
                impossible_reason = "correct_at_least_15_is_mathematically_impossible"
            if normal_parseable_count + remaining < 28:
                impossible_reason = "normal_parseable_at_least_28_is_mathematically_impossible"
            if impossible_reason:
                write_json(output / "gate_early_stop.json", {
                    "status": "failed",
                    "reason": impossible_reason,
                    "completed": completed,
                    "correct": correct_count,
                    "normal_parseable": normal_parseable_count,
                    "remaining": remaining,
                })
                raise RuntimeError(impossible_reason)
    write_json(output / "completion.json", {
        "completed": completed,
        "seconds": time.monotonic() - began,
    })
    write_json(output / "gate_decision.json", {
        "status": "passed" if correct_count >= 15 and normal_parseable_count >= 28 else "failed",
        "correct": correct_count,
        "normal_parseable": normal_parseable_count,
        "total": expected,
    })
    print(f"COMPLETE {completed}/{expected}; releasing GPU", flush=True)


if __name__ == "__main__":
    main()
