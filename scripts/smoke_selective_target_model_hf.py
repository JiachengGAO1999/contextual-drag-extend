"""Architecture-level HF selective-attention smoke for a target model.

Unlike a text-only output check, this smoke hooks the target model's attention
modules and verifies that decode-time R3 calls actually receive a 4-D additive
mask whose failed-draft key span is blocked.  It is engineering validation, not
scientific evidence.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from selective_context.hf_backend import SelectiveHFBackend
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
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20270923)
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
    prompt = render_chat_prompt(
        tokenizer,
        independent_prompt(pair["problem"], pair["traj1"], task),
        args.enable_thinking,
    )
    encoded = encode_prompt(tokenizer, prompt)
    requests = make_r2_r4_requests(encoded, args.seed)[:2]
    persist_request_bundle(args.output / "requests.json", encoded, requests)

    began = time.monotonic()
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        local_files_only=True,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        device_map="cuda:0",
    ).eval()
    load_seconds = time.monotonic() - began
    backend = SelectiveHFBackend(model, tokenizer)
    if backend.eos_token_ids != frozenset({1, 50, 106}):
        raise RuntimeError(
            f"Unexpected Gemma4 EOS token set: {sorted(backend.eos_token_ids)}"
        )

    observations: list[dict] = []
    active_condition: list[str | None] = [None]
    lo, hi = encoded.draft_token_span

    def hook(_module, _args, kwargs):
        mask = kwargs.get("attention_mask")
        if not isinstance(mask, torch.Tensor) or mask.ndim != 4 or mask.shape[-2] != 1:
            return
        key_length = mask.shape[-1]
        absolute_key_length = backend.last_absolute_key_length
        if absolute_key_length is None or absolute_key_length < len(encoded.input_ids):
            return
        key_offset = absolute_key_length - key_length
        overlap_lo = max(lo, key_offset)
        overlap_hi = min(hi, absolute_key_length)
        if overlap_lo >= overlap_hi:
            observations.append({
                "condition": active_condition[0],
                "shape": list(mask.shape),
                "absolute_key_length": absolute_key_length,
                "key_offset": key_offset,
                "draft_evicted_from_local_window": True,
                "draft_min": None,
                "draft_max": None,
                "draft_all_blocked": True,
            })
            return
        draft = mask[..., overlap_lo - key_offset : overlap_hi - key_offset]
        observations.append({
            "condition": active_condition[0],
            "shape": list(mask.shape),
            "absolute_key_length": absolute_key_length,
            "key_offset": key_offset,
            "draft_evicted_from_local_window": False,
            "draft_min": float(draft.float().min().item()),
            "draft_max": float(draft.float().max().item()),
            "draft_all_blocked": bool(torch.all(draft.float() < -1e20).item()),
        })

    handles = [
        module.register_forward_pre_hook(hook, with_kwargs=True)
        for module in model.modules()
        if type(module).__name__ == "Gemma4TextAttention"
    ]
    if not handles:
        raise RuntimeError("No Gemma4TextAttention modules found for runtime mask audit")

    rows = []
    try:
        for request in requests:
            before = len(observations)
            started = time.monotonic()
            active_condition[0] = request.condition_id
            result = backend.generate(
                request,
                max_new_tokens=args.max_new_tokens,
                temperature=0,
                top_p=1.0,
            )
            rows.append({
                "condition": request.condition_id,
                "access_mode": request.access_mode.value,
                "tokens": result.generated_token_ids,
                "text": result.text,
                "finish_reason": result.finish_reason,
                "seconds": time.monotonic() - started,
                "decode_mask_observations": len(observations) - before,
                "metadata": result.metadata,
            })
    finally:
        active_condition[0] = None
        for handle in handles:
            handle.remove()

    # Persist diagnostics even if a subsequent invariant fails.  This smoke is
    # specifically intended to make attention-mask failures inspectable.
    save(args.output / "results.json", rows)
    save(args.output / "mask_observations.json", observations)

    if not all(row["tokens"] for row in rows):
        raise RuntimeError("At least one condition generated no tokens")
    if rows[0]["tokens"][0] != rows[1]["tokens"][0]:
        raise RuntimeError("R2/R3 first-token boundary invariant failed")
    r2_observations = [item for item in observations if item["condition"] == "R2"]
    r3_observations = [item for item in observations if item["condition"] == "R3"]
    if not r2_observations or not r3_observations:
        raise RuntimeError(
            "Gemma4 runtime decode-mask audit observed no masks for one or more "
            f"conditions: R2={len(r2_observations)}, R3={len(r3_observations)}"
        )
    if not any(not item["draft_all_blocked"] for item in r2_observations):
        raise RuntimeError(f"R2 unexpectedly blocks the draft span: {r2_observations[:8]}")
    if not all(item["draft_all_blocked"] for item in r3_observations):
        raise RuntimeError(f"R3 failed to block the draft span: {r3_observations[:8]}")

    save(args.output / "status.json", {
        "engineering_smoke": "passed",
        "scientific_run_authorized": False,
        "backend": "hf_selective_eager",
        "eos_token_ids": sorted(backend.eos_token_ids),
        "conditions": [row["condition"] for row in rows],
        "r2_r3_first_token_equal": True,
        "gemma4_attention_modules_hooked": len(handles),
        "r2_decode_masks_observed": len(r2_observations),
        "r3_decode_masks_observed": len(r3_observations),
        "r3_draft_span_blocked_in_all_observed_masks": True,
        "model_load_seconds": load_seconds,
        "total_seconds": time.monotonic() - began,
    })
    print("GEMMA4_HF_SELECTIVE_SMOKE_PASSED", flush=True)


if __name__ == "__main__":
    main()
