from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import torch

from .masks import build_additive_attention
from .schema import SelectiveContextRequest


@dataclass
class GenerationResult:
    generated_token_ids: List[int]
    text: str
    finish_reason: str
    metadata: Dict[str, Any]


class SelectiveHFBackend:
    """Small, explicit HF eager-attention backend for same-text interventions."""

    def __init__(self, model: torch.nn.Module, tokenizer: Any, device: Optional[torch.device] = None):
        self.model = model.eval()
        self.tokenizer = tokenizer
        self.device = device or next(model.parameters()).device

    @torch.inference_mode()
    def generate(
        self,
        request: SelectiveContextRequest,
        *,
        max_new_tokens: int,
        temperature: float = 0.0,
        top_k: Optional[int] = None,
    ) -> GenerationResult:
        request.validate()
        if max_new_tokens < 0:
            raise ValueError("max_new_tokens must be non-negative")
        prompt_ids = torch.tensor([request.input_ids], dtype=torch.long, device=self.device)
        prompt_length = prompt_ids.shape[1]
        model_dtype = next(self.model.parameters()).dtype
        prefill_positions = list(range(prompt_length))
        if request.access_mode.value in ("full", "late_block"):
            # R2 and R3 share the ordinary HF prefill path exactly.
            prefill_mask = torch.ones_like(prompt_ids)
        else:
            prefill_mask = build_additive_attention(
                batch_size=1,
                query_positions=prefill_positions,
                key_length=prompt_length,
                draft_token_span=request.draft_token_span,
                access_mode=request.access_mode,
                prompt_length=prompt_length,
                dtype=model_dtype,
                device=self.device,
            )
        output = self.model(input_ids=prompt_ids, attention_mask=prefill_mask, use_cache=True, return_dict=True)
        past = output.past_key_values
        next_logits = output.logits[:, -1, :]
        generated: List[int] = []
        generator = torch.Generator(device=self.device)
        generator.manual_seed(request.sample_seed)
        eos_token_id = getattr(self.tokenizer, "eos_token_id", None)
        finish_reason = "length"

        for step in range(max_new_tokens):
            next_token = self._choose(next_logits, temperature, top_k, generator)
            token_id = int(next_token.item())
            generated.append(token_id)
            if eos_token_id is not None and token_id == eos_token_id:
                finish_reason = "eos"
                break
            if step + 1 == max_new_tokens:
                break
            absolute_position = prompt_length + step
            key_length = absolute_position + 1
            if request.access_mode.value == "full":
                decode_mask = torch.ones((1, key_length), dtype=torch.long, device=self.device)
            else:
                decode_mask = build_additive_attention(
                    batch_size=1,
                    query_positions=[absolute_position],
                    key_length=key_length,
                    draft_token_span=request.draft_token_span,
                    access_mode=request.access_mode,
                    prompt_length=prompt_length,
                    dtype=model_dtype,
                    device=self.device,
                )
            output = self.model(
                input_ids=next_token.view(1, 1),
                attention_mask=decode_mask,
                past_key_values=past,
                use_cache=True,
                return_dict=True,
            )
            past = output.past_key_values
            next_logits = output.logits[:, -1, :]

        text = self.tokenizer.decode(generated, skip_special_tokens=False)
        return GenerationResult(
            generated_token_ids=generated,
            text=text,
            finish_reason=finish_reason,
            metadata={
                "backend": "hf_selective_eager",
                "logical_kv_blocking": True,
                "physical_kv_eviction": False,
                "prompt_tokens": prompt_length,
                "generated_tokens": len(generated),
                "cache_type": type(past).__name__,
                "access_mode": request.access_mode.value,
                "draft_token_span": list(request.draft_token_span),
            },
        )

    @staticmethod
    def _choose(
        logits: torch.Tensor,
        temperature: float,
        top_k: Optional[int],
        generator: torch.Generator,
    ) -> torch.Tensor:
        if temperature <= 0:
            return torch.argmax(logits, dim=-1)
        logits = logits / temperature
        if top_k is not None and 0 < top_k < logits.shape[-1]:
            cutoff = torch.topk(logits, top_k, dim=-1).values[:, -1:]
            logits = logits.masked_fill(logits < cutoff, -torch.inf)
        probabilities = torch.softmax(logits, dim=-1)
        return torch.multinomial(probabilities, 1, generator=generator).squeeze(-1)


def append_jsonl_resumable(path: Path, key: str, record: Dict[str, Any]) -> bool:
    """Append one record unless its key is already present. Returns whether written."""
    existing = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    value = json.loads(line)
                    existing.add(value[key])
    if record[key] in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True
