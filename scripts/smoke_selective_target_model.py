"""Bounded target-model compatibility smoke; never a scientific result run.

The prompt is rebuilt with the target model's own tokenizer and chat template.
This is necessary for cross-architecture checks: persisted Qwen token IDs must
not be reused for Gemma, GPT-OSS, or other tokenizer families.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from transformers import AutoTokenizer

from selective_context.prompting import (
    encode_prompt,
    make_r2_r4_requests,
    persist_request_bundle,
    render_chat_prompt,
)
from selective_context.tasks import independent_prompt, validate_pair_task


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--pair", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-num-seqs", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.94)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20270922)
    parser.add_argument(
        "--worker-cls",
        default="selective_context.vllm_worker.SelectiveWorker",
    )
    parser.add_argument("--enable-thinking", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    args.output.mkdir(parents=True)

    pair = json.loads(args.pair.read_text(encoding="utf-8"))
    task = pair.get("task", "game24")
    validate_pair_task(pair, task)
    if pair.get("audit_status") != "substantive_failed":
        raise ValueError("Smoke fixture must be an audited substantive failure")

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, local_files_only=True, use_fast=True, trust_remote_code=True
    )
    content = independent_prompt(pair["problem"], pair["traj1"], task)
    prompt = render_chat_prompt(tokenizer, content, args.enable_thinking)
    encoded = encode_prompt(tokenizer, prompt)
    if len(encoded.input_ids) + args.max_new_tokens > args.max_model_len:
        raise ValueError("Prompt and generation budget exceed max_model_len")
    requests = make_r2_r4_requests(encoded, args.seed)
    persist_request_bundle(args.output / "requests.json", encoded, requests)
    save(
        args.output / "config.json",
        {
            "purpose": "engineering_compatibility_only_not_scientific_evidence",
            "model": args.model,
            "pair": str(args.pair),
            "task": task,
            "prompt_tokens": len(encoded.input_ids),
            "draft_token_span": encoded.draft_token_span,
            "boundary_spillover": encoded.boundary_spillover,
            "max_model_len": args.max_model_len,
            "max_num_seqs": args.max_num_seqs,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "max_new_tokens": args.max_new_tokens,
            "enable_thinking": args.enable_thinking,
            "seed": args.seed,
            "worker_cls": args.worker_cls,
        },
    )

    from selective_context.vllm_backend import SelectiveVLLMBackend

    began = time.monotonic()
    backend = SelectiveVLLMBackend(
        args.model,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        gpu_memory_utilization=args.gpu_memory_utilization,
        worker_cls=args.worker_cls,
    )
    loaded_seconds = time.monotonic() - began
    generated = backend.generate_batch(
        requests,
        max_new_tokens=args.max_new_tokens,
        temperature=0,
        logprobs=5,
    )
    total_seconds = time.monotonic() - began
    rows = [
        {
            "condition": request.condition_id,
            "access_mode": request.access_mode.value,
            "tokens": result.generated_token_ids,
            "text": result.text,
            "finish_reason": result.finish_reason,
            "metadata": result.metadata,
        }
        for request, result in zip(requests, generated)
    ]
    save(args.output / "results.json", rows)

    if not all(row["tokens"] for row in rows):
        raise RuntimeError("At least one condition generated no tokens")
    if rows[0]["tokens"][0] != rows[1]["tokens"][0]:
        raise RuntimeError("R2/R3 first-token boundary invariant failed")
    save(
        args.output / "status.json",
        {
            "engineering_smoke": "passed",
            "scientific_run_authorized": False,
            "conditions": [row["condition"] for row in rows],
            "r2_r3_first_token_equal": True,
            "loaded_seconds": loaded_seconds,
            "total_seconds": total_seconds,
        },
    )
    print("SELECTIVE_TARGET_MODEL_SMOKE_PASSED", flush=True)


if __name__ == "__main__":
    main()
