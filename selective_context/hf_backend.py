from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

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
        # Some chat models (including Gemma 4) define several valid stop
        # tokens in generation_config.  Stopping only on tokenizer.eos_token_id
        # can run past an end-of-turn marker all the way to the length limit.
        self.eos_token_ids = self._collect_eos_token_ids(model, tokenizer)
        self.last_absolute_key_length: Optional[int] = None

    @staticmethod
    def _collect_eos_token_ids(model: torch.nn.Module, tokenizer: Any) -> frozenset[int]:
        values: list[Any] = []
        for source in (
            getattr(model, "generation_config", None),
            getattr(model, "config", None),
            tokenizer,
        ):
            if source is not None:
                values.append(getattr(source, "eos_token_id", None))
        normalized: set[int] = set()
        for value in values:
            if value is None:
                continue
            if isinstance(value, (list, tuple, set, frozenset)):
                normalized.update(int(item) for item in value)
            else:
                normalized.add(int(value))
        return frozenset(normalized)

    def _prepare_attention_mask(self, mask: torch.Tensor) -> torch.Tensor | dict[str, torch.Tensor]:
        """Build Gemma-style per-layer masks when local and global KV lengths differ."""
        self.last_absolute_key_length = int(mask.shape[-1])
        config = getattr(self.model.config, "text_config", self.model.config)
        layer_types = set(getattr(config, "layer_types", ()) or ())
        sliding_window = getattr(config, "sliding_window", None)
        if (
            mask.ndim == 4
            and {"full_attention", "sliding_attention"}.issubset(layer_types)
            and isinstance(sliding_window, int)
            and sliding_window > 0
        ):
            if mask.shape[-2] != 1:
                raise NotImplementedError(
                    "Hybrid local/global custom prefill masks are not implemented; "
                    "the validated Gemma target protocol uses ordinary prefill and "
                    "a one-query late-block decode mask"
                )
            # Gemma4's local-attention cache retains only the most recent
            # sliding_window keys, while global layers retain the full cache.
            # Passing one full-width 4-D mask to both produces a shape error
            # once the sequence crosses the local window.
            return {
                "full_attention": mask,
                "sliding_attention": mask[..., -min(sliding_window, mask.shape[-1]) :],
            }
        return mask

    @torch.inference_mode()
    def generate(
        self,
        request: SelectiveContextRequest,
        *,
        max_new_tokens: int,
        temperature: float = 0.0,
        top_k: Optional[int] = None,
        top_p: float = 1.0,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> GenerationResult:
        request.validate()
        if max_new_tokens < 0:
            raise ValueError("max_new_tokens must be non-negative")
        if not 0 < top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
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
                mask_token_spans=request.mask_token_spans,
                path_block_units=request.path_block_units,
                access_mode=request.access_mode,
                prompt_length=prompt_length,
                dtype=model_dtype,
                device=self.device,
            )
        output = self.model(
            input_ids=prompt_ids,
            attention_mask=self._prepare_attention_mask(prefill_mask),
            use_cache=True,
            return_dict=True,
        )
        past = output.past_key_values
        next_logits = output.logits[:, -1, :]
        generated: List[int] = []
        generator = torch.Generator(device=self.device)
        generator.manual_seed(request.sample_seed)
        finish_reason = "length"
        stop_token_id: Optional[int] = None

        for step in range(max_new_tokens):
            next_token = self._choose(next_logits, temperature, top_k, generator, top_p)
            token_id = int(next_token.item())
            generated.append(token_id)
            if progress_callback is not None and len(generated) % 512 == 0:
                progress_callback(len(generated))
            if token_id in self.eos_token_ids:
                finish_reason = "eos"
                stop_token_id = token_id
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
                    mask_token_spans=request.mask_token_spans,
                    path_block_units=request.path_block_units,
                    access_mode=request.access_mode,
                    prompt_length=prompt_length,
                    dtype=model_dtype,
                    device=self.device,
                )
            output = self.model(
                input_ids=next_token.view(1, 1),
                attention_mask=self._prepare_attention_mask(decode_mask),
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
                "eos_token_ids": sorted(self.eos_token_ids),
                "stop_token_id": stop_token_id,
                "cache_type": type(past).__name__,
                "access_mode": request.access_mode.value,
                "draft_token_span": list(request.draft_token_span),
                "mask_token_spans": [list(x) for x in request.mask_token_spans],
                "path_block_units": [list(x) for x in request.path_block_units],
            },
        )

    @staticmethod
    def _choose(
        logits: torch.Tensor,
        temperature: float,
        top_k: Optional[int],
        generator: torch.Generator,
        top_p: float = 1.0,
    ) -> torch.Tensor:
        if temperature <= 0:
            return torch.argmax(logits, dim=-1)
        # Match HF generation's float32 sampling processors even for BF16 models.
        logits = logits.float() / temperature
        if top_k is not None and 0 < top_k < logits.shape[-1]:
            cutoff = torch.topk(logits, top_k, dim=-1).values[:, -1:]
            logits = logits.masked_fill(logits < cutoff, -torch.inf)
        if top_p < 1:
            sorted_logits, indices = torch.sort(logits, descending=True, dim=-1)
            remove = torch.softmax(sorted_logits, dim=-1).cumsum(dim=-1) > top_p
            remove[..., 1:] = remove[..., :-1].clone()
            remove[..., 0] = False
            logits = logits.scatter(-1, indices, sorted_logits.masked_fill(remove, -torch.inf))
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
