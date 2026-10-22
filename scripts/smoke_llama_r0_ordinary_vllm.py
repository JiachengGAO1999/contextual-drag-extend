"""One-prompt EOS/latency smoke for the ordinary R0 backend."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from selective_context.hf_backend import SelectiveHFBackend
from selective_context.phase0.real_smoke import evaluate
from selective_context.prompting import load_request_bundle
from selective_context.prompting import encode_direct_prompt, make_request, render_chat_prompt
from selective_context.schema import AccessMode
from scripts.run_target_r0_capability import OrdinaryVLLMBackend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--backend", choices=("ordinary", "selective", "hf"), default="ordinary")
    parser.add_argument("--temperature", type=float, default=0.6)
    args = parser.parse_args()
    load_began = time.monotonic()
    if args.backend == "ordinary":
        backend = OrdinaryVLLMBackend(
            args.model, max_model_len=32768, max_num_seqs=1, gpu_memory_utilization=0.65
        )
    elif args.backend == "selective":
        from selective_context.vllm_backend import SelectiveVLLMBackend
        backend = SelectiveVLLMBackend(
            args.model, max_model_len=32768, max_num_seqs=1, gpu_memory_utilization=0.65
        )
    else:
        tokenizer = AutoTokenizer.from_pretrained(
            args.model, local_files_only=True, use_fast=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            device_map="cuda:0",
        )
        backend = SelectiveHFBackend(model, tokenizer)
    loaded_seconds = time.monotonic() - load_began
    if args.prepared:
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((args.prepared / "manifest.json").read_text(encoding="utf-8"))
        item = next(row for row in manifest if row["condition"] == "R0")
        encoded, requests = load_request_bundle(root / item["bundle"])
        request = next(row for row in requests if row.condition_id == "R0")
        source_row = json.loads((root / item["pair"]).read_text(encoding="utf-8"))
    else:
        prompt = render_chat_prompt(
            backend.tokenizer,
            "Solve this arithmetic problem. Give a concise final answer: 1 + 1 = ?",
            False,
        )
        encoded = encode_direct_prompt(backend.tokenizer, prompt)
        request = make_request(encoded, "R0", AccessMode.FULL, 927001)
        source_row = {"id": "engineering-1-plus-1", "problem": "1+1", "answer": [1, 1]}
    began = time.monotonic()
    generation_args = dict(
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=0.95,
        top_k=20,
    )
    if args.backend == "hf":
        result = backend.generate(request, **generation_args)
    else:
        result = backend.generate_batch([request], **generation_args)[0]
    record = evaluate(source_row, encoded, request, result, task="game24") if args.prepared else None
    summary = {
        "passed": result.finish_reason == "eos" and len(result.generated_token_ids) < args.max_new_tokens,
        "backend": args.backend,
        "scientific_result": False,
        "purpose": "bounded backend diagnostic only",
        "finish_reason": result.finish_reason,
        "tokens": len(result.generated_token_ids),
        "loaded_seconds": loaded_seconds,
        "seconds": time.monotonic() - began,
        "temperature": args.temperature,
        "text": result.text,
        "metadata": result.metadata,
        "official_correctness": record["init_response_generations"][0]["correctness"] if record else None,
    }
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite smoke output")
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not summary["passed"] and not args.prepared:
        raise RuntimeError("Ordinary vLLM did not stop normally in the bounded smoke")


if __name__ == "__main__":
    main()
