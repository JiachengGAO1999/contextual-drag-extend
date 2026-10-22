"""Same-text early/late access contrast using the existing R4 mask, without hooks."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import torch

from .masks import build_additive_attention
from .schema import AccessMode


@dataclass
class State:
    logits: torch.Tensor
    cache: Any
    length: int


class RouteRevocationBackend:
    def __init__(self, model, heartbeat=lambda: None):
        self.model = model.eval()
        parameter = next(model.parameters())
        self.device, self.dtype = parameter.device, parameter.dtype
        self.heartbeat = heartbeat

    def mask(self, positions, length, span, condition, cutoff):
        mode = {"FULL": AccessMode.FULL, "LATE_BLOCK": AccessMode.LATE_BLOCK,
                "REBUILD_BLOCKED": AccessMode.PATH_BLOCK}[condition]
        return build_additive_attention(batch_size=1, query_positions=positions, key_length=length,
            draft_token_span=tuple(span), access_mode=mode, prompt_length=cutoff,
            dtype=self.dtype, device=self.device)

    @torch.inference_mode()
    def advance(self, ids, state, span, condition, cutoff):
        if not ids: return state
        self.heartbeat()
        start = state.length if state else 0
        length = start + len(ids)
        out = self.model(input_ids=torch.tensor([ids], device=self.device),
            attention_mask=self.mask(list(range(start, length)), length, span, condition, cutoff),
            position_ids=torch.arange(start, length, device=self.device).view(1, -1),
            past_key_values=state.cache if state else None, use_cache=True, return_dict=True)
        return State(out.logits[:, -1, :], out.past_key_values, length)

    @torch.inference_mode()
    def prefill_pair(self, history):
        ids, span, cutoff = history["input_ids"], history["draft_token_span"], history["cutoff"]
        # The final critique query is already blocked in BOTH comparison conditions.
        base = self.advance(ids[:-1], None, span, "FULL", cutoff)
        early = self.advance(ids[:-1], None, span, "REBUILD_BLOCKED", cutoff)
        states = {}
        for condition in ("FULL", "LATE_BLOCK", "REBUILD_BLOCKED"):
            source = early if condition == "REBUILD_BLOCKED" else base
            states[condition] = self.advance(ids[-1:], copy.deepcopy(source), span, condition, cutoff)
        return states

    @torch.inference_mode()
    def score(self, state, history, condition, readout):
        span, cutoff = history["draft_token_span"], history["cutoff"]
        prefix = self.advance(readout["stem_ids"], copy.deepcopy(state), span, condition, cutoff)
        scores = {}
        for name, candidate in readout["candidates"].items():
            branch = copy.deepcopy(prefix)
            log_probs = []
            for i, token in enumerate(candidate["ids"]):
                log_probs.append(float(branch.logits.float().log_softmax(-1)[0, token]))
                if i + 1 < len(candidate["ids"]):
                    branch = self.advance([token], branch, span, condition, cutoff)
            total = sum(log_probs)
            scores[name] = dict(log_probability=total, mean_log_probability=total/len(log_probs),
                                tokens=len(log_probs), token_log_probabilities=log_probs)
        return scores
