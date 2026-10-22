"""Single-query attention diagnostics; the existing generation backend is untouched.

Prefill uses SDPA. Only continuation queries use the installed model's eager
attention implementation. VALUE_ZERO subtracts alpha_D V_D, without changing
the local softmax. MASK recomputes that softmax with selected draft edges removed.
"""
from __future__ import annotations

import copy
import importlib
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn.functional as F

from .hf_backend import GenerationResult, SelectiveHFBackend


@dataclass(frozen=True)
class Intervention:
    mode: str = "FULL"
    # None means all heads; an empty tuple is an identity intervention.
    heads: Optional[tuple] = None
    strength: float = 1.0
    # Half-open indices of generated queries; predicting token 0 uses prefill.
    query_window: Optional[tuple] = None

    def validate(self, layers, heads):
        if self.mode not in ("FULL", "MASK", "VALUE_ZERO", "NON_DRAFT_MATCHED", "PRE_DRAFT_MATCHED", "GENERATED_MATCHED", "PATCH", "PATCH_MASK"):
            raise ValueError("Unknown diagnostic intervention")
        if not 0 <= self.strength <= 1:
            raise ValueError("Intervention strength must be in [0, 1]")
        if self.query_window is not None:
            lo,hi=self.query_window
            if not isinstance(lo,int) or not isinstance(hi,int) or not 0<=lo<hi:
                raise ValueError("Invalid generated-query window")
        if self.heads is not None:
            if len(set(self.heads)) != len(self.heads):
                raise ValueError("Duplicate heads")
            if any(not 0 <= l < layers or not 0 <= h < heads for l, h in self.heads):
                raise ValueError("Head outside model")

    def selected(self, layer, count):
        return list(range(count)) if self.heads is None else [h for l, h in self.heads if l == layer]


def draft_contribution(weights, value, span):
    """Weights [B,H,Q,K], values [B,Hkv,K,D], including GQA expansion."""
    if weights.shape[1] % value.shape[1]:
        raise ValueError("Invalid GQA head count")
    expanded = value.repeat_interleave(weights.shape[1] // value.shape[1], dim=1)
    lo, hi = span
    contribution = torch.matmul(weights[..., lo:hi], expanded[..., lo:hi, :])
    return contribution, expanded


def matched_non_draft_contribution(full, draft):
    """Match each head's pre-o_proj norm, changing the removed source direction."""
    direction=full.float()-draft.float()
    source_norm=draft.float().norm(dim=-1,keepdim=True)
    other_norm=direction.norm(dim=-1,keepdim=True)
    return direction*(source_norm/other_norm.clamp_min(1e-8))


def partition_contributions(weights, expanded, span, prompt_length):
    """Disjoint P/D/F/G value sources; G includes the current query key."""
    lo, hi = span
    if not 0 <= lo <= hi <= prompt_length <= weights.shape[-1]:
        raise ValueError("Invalid source partition boundaries")
    ranges = dict(P=(0, lo), D=(lo, hi), F=(hi, prompt_length), G=(prompt_length, weights.shape[-1]))
    return {name: torch.matmul(weights[..., a:b], expanded[..., a:b, :])
            for name, (a, b) in ranges.items()}


def matched_source_contribution(direction, draft):
    return direction.float()*(draft.float().norm(dim=-1, keepdim=True)
        / direction.float().norm(dim=-1, keepdim=True).clamp_min(1e-8))


def source_geometry(module, full, parts, selected, token):
    """Aggregates at one FULL query; no attention matrices or vectors are saved."""
    draft = parts["D"].transpose(1, 2)
    directions = {k: v.transpose(1, 2) for k, v in parts.items()}
    directions["NON_DRAFT"] = full.float()-draft.float()
    target = draft[:, :, selected, :].float()
    norms = {k: float(v[:, :, selected, :].float().norm(dim=-1).mean()) for k, v in directions.items()}
    cosine = {k: float(F.cosine_similarity(target, v[:, :, selected, :].float(), dim=-1).mean())
              for k, v in directions.items() if k != "D"}
    projected = {}
    projected_vectors = {}
    for name in ("D", "NON_DRAFT", "P", "G"):
        delta = draft if name == "D" else matched_source_contribution(directions[name], draft)
        changed = full.clone()
        if name == "D":
            changed[:, :, selected, :] -= delta[:, :, selected, :]
        else:
            changed[:, :, selected, :] = (full[:, :, selected, :].float()-delta[:, :, selected, :]).to(full.dtype)
        actual = full-changed
        vector = F.linear(actual.flatten(2), module.o_proj.weight)
        projected_vectors[name] = vector.float().flatten()
        projected[name] = dict(pre_o_proj_norm=float(actual.float().norm()),
                               post_o_proj_norm=float(vector.float().norm()))
    reconstruction = sum(v.float() for v in parts.values()).transpose(1, 2)
    return dict(token=token, layer=module.layer_idx, heads=len(selected),
        mean_head_norm=norms, mean_head_cosine_with_draft=cosine,
        matched_actual_perturbation=projected,
        post_o_proj_cosine_with_draft={k: float(F.cosine_similarity(projected_vectors["D"], v, dim=0))
            for k, v in projected_vectors.items() if k != "D"},
        partition_reconstruction_relative_error=float((reconstruction-full.float()).norm()/full.float().norm().clamp_min(1e-8)))


class DiagnosticBackend(SelectiveHFBackend):
    def __init__(self, model, tokenizer, check_budget=lambda: None):
        super().__init__(model, tokenizer)
        # Older deployed HF backends do not initialize this attribute.
        # Honor the model's generation stop tokens as well as tokenizer EOS.
        stops = set()
        for source in (getattr(model, "generation_config", None), model.config, tokenizer):
            value = getattr(source, "eos_token_id", None)
            if value is not None:
                stops.update(value if isinstance(value, (list, tuple, set, frozenset)) else [value])
        self.eos_token_ids = frozenset(int(value) for value in stops)
        self.layers = model.model.layers
        self.n_heads = model.config.num_attention_heads
        self.check_budget = check_budget
        self.module = importlib.import_module(type(self.layers[0].self_attn).__module__)
        if not hasattr(self.module, "eager_attention_forward"):
            raise NotImplementedError("Requires HF eager_attention_forward interface")
        self.state = None

    @torch.inference_mode()
    def prefill(self, input_ids):
        self.check_budget()
        old = self.model.config._attn_implementation
        self.model.config._attn_implementation = "sdpa"
        try:
            ids = torch.tensor([input_ids], device=self.device)
            out = self.model(input_ids=ids, attention_mask=torch.ones_like(ids),
                             use_cache=True, logits_to_keep=1)
            return out.logits[:, -1].detach().clone(), out.past_key_values
        finally:
            self.model.config._attn_implementation = old

    @contextmanager
    def intervention(self, spec, span, *, collect=False, capture=False, donor=None,
                     prompt_length=None, geometry_tokens=()):
        spec.validate(len(self.layers), self.n_heads)
        if self.state is not None:
            raise RuntimeError("Diagnostic contexts cannot be nested")
        if (spec.mode in ("PRE_DRAFT_MATCHED", "GENERATED_MATCHED") or geometry_tokens) and (
                prompt_length is None or prompt_length < span[1]):
            raise ValueError("Source partitions require the original prompt length")
        original = self.module.eager_attention_forward
        old = self.model.config._attn_implementation
        state = dict(spec=spec, span=span, collect=collect, capture=capture,
                     donor=donor, step=0, metrics=[], outputs={}, geometry=[],
                     match_stats=None, geometry_tokens=set(geometry_tokens))
        self.state = state

        def attention(module, query, key, value, attention_mask, scaling, dropout=0., **kwargs):
            if query.shape[-2] != 1:
                raise RuntimeError("Intervention must never affect prefill")
            full, weights = original(module, query, key, value, attention_mask,
                                     scaling=scaling, dropout=dropout, **kwargs)
            layer = module.layer_idx
            active=spec.query_window is None or spec.query_window[0]<=state["step"]<spec.query_window[1]
            selected = spec.selected(layer, weights.shape[1]) if active else []
            contribution, expanded = draft_contribution(weights, value, span)
            if state["step"] in state["geometry_tokens"] and selected:
                parts = partition_contributions(weights, expanded, span, prompt_length)
                state["geometry"].append(source_geometry(module, full, parts, selected, state["step"]))
            if collect:
                lo, hi = span
                non = expanded.clone()
                non[..., lo:hi, :] = 0
                other = torch.matmul(weights, non)
                reconstruction = (contribution + other).transpose(1, 2)
                relative_error = ((reconstruction.float() - full.float()).norm()
                                  / full.float().norm().clamp_min(1e-8))
                projected = F.linear(contribution.transpose(1, 2).flatten(2), module.o_proj.weight)
                state["metrics"].append(dict(
                    token=state["step"], layer=layer,
                    mass=weights[..., lo:hi].sum(-1).flatten().float().cpu().tolist(),
                    value_norm=contribution.norm(dim=-1).flatten().float().cpu().tolist(),
                    projected_norm=float(projected.float().norm()),
                    reconstruction_relative_error=float(relative_error),
                ))
            output = full
            applied_weights = weights
            if spec.mode == "PATCH_MASK" and active:
                lo, hi = span
                mask = torch.zeros((query.shape[0], 1, 1, key.shape[-2]),
                                   device=query.device, dtype=query.dtype)
                if attention_mask is not None:
                    mask += attention_mask[..., :key.shape[-2]]
                mask[..., lo:hi] = torch.finfo(query.dtype).min
                output, applied_weights = original(module, query, key, value, mask,
                                                   scaling=scaling, dropout=dropout, **kwargs)
            if selected and spec.strength and spec.mode == "VALUE_ZERO":
                output = full.clone()
                output[:, :, selected, :] -= spec.strength * contribution.transpose(1, 2)[:, :, selected, :]
            elif selected and spec.strength and spec.mode == "NON_DRAFT_MATCHED":
                draft=contribution.transpose(1,2)
                delta=matched_non_draft_contribution(full,draft)
                output=full.clone()
                output[:,:,selected,:]=(full[:,:,selected,:].float()-spec.strength*delta[:,:,selected,:]).to(full.dtype)
                if collect:
                    target=draft[:,:,selected,:].float().norm(dim=-1)
                    removed=delta[:,:,selected,:].norm(dim=-1)
                    state["metrics"][-1]["matched_norm_relative_error_max"]=float(
                        ((removed-target).abs()/target.clamp_min(1e-8)).max())
            elif selected and spec.strength and spec.mode in ("PRE_DRAFT_MATCHED", "GENERATED_MATCHED"):
                a, b = (0, span[0]) if spec.mode == "PRE_DRAFT_MATCHED" else (prompt_length, weights.shape[-1])
                direction = torch.matmul(weights[..., a:b], expanded[..., a:b, :]).transpose(1, 2)
                draft = contribution.transpose(1, 2)
                delta = matched_source_contribution(direction, draft)
                output = full.clone()
                output[:, :, selected, :] = (full[:, :, selected, :].float()
                    - spec.strength*delta[:, :, selected, :]).to(full.dtype)
                source_norm = direction[:, :, selected, :].float().norm(dim=-1)
                target_norm = draft[:, :, selected, :].float().norm(dim=-1)
                zero = source_norm <= 1e-8
                bad = zero & (target_norm > 1e-8)
                scale = target_norm/source_norm.clamp_min(1e-8)
                if state["match_stats"] is None:
                    state["match_stats"] = dict(head_queries=0, zero_source=zero.sum(),
                        unmatched=bad.sum(), max_scale=scale.max())
                else:
                    state["match_stats"]["zero_source"] += zero.sum()
                    state["match_stats"]["unmatched"] += bad.sum()
                    state["match_stats"]["max_scale"] = torch.maximum(state["match_stats"]["max_scale"], scale.max())
                state["match_stats"]["head_queries"] += source_norm.numel()
            elif selected and spec.strength and spec.mode == "MASK":
                mask = torch.zeros((query.shape[0], weights.shape[1], 1, key.shape[-2]),
                                   device=query.device, dtype=query.dtype)
                if attention_mask is not None:
                    mask += attention_mask[..., :key.shape[-2]]
                lo, hi = span
                mask[:, selected, :, lo:hi] = torch.finfo(query.dtype).min
                masked, applied_weights = original(module, query, key, value, mask,
                                     scaling=scaling, dropout=dropout, **kwargs)
                output = full + spec.strength * (masked - full)
            elif selected and spec.strength and spec.mode in ("PATCH", "PATCH_MASK"):
                if donor is None or (state["step"], layer) not in donor:
                    raise ValueError("Missing same-prefix donor head output")
                replacement = donor[state["step"], layer].to(device=full.device, dtype=full.dtype)
                output = output.clone()
                output[:, :, selected, :] += spec.strength * (
                    replacement[:, :, selected, :] - output[:, :, selected, :])
            if collect:
                lo, hi = span
                state["metrics"][-1]["applied_mass"] = applied_weights[..., lo:hi].sum(-1).flatten().float().cpu().tolist()
            if capture and active:
                state["outputs"][state["step"], layer] = output.detach().cpu().clone()
            # No attention matrices escape the single query.
            return output, None

        self.module.eager_attention_forward = attention
        self.model.config._attn_implementation = "eager"
        try:
            yield state
        finally:
            self.module.eager_attention_forward = original
            self.model.config._attn_implementation = old
            self.state = None

    def _step(self, token, cache):
        self.check_budget()
        out = self.model(input_ids=torch.tensor([[token]], device=self.device),
                         past_key_values=cache, use_cache=True, logits_to_keep=1)
        return out.logits[:, -1], out.past_key_values

    @torch.inference_mode()
    def teacher_force(self, prefilled, tokens, span, spec=Intervention(), *,
                      collect=False, capture=False, donor=None, probes=(), geometry_tokens=()):
        logits, source_cache = prefilled
        cache = copy.deepcopy(source_cache)
        scores, probe_scores, entropy = [], [], []
        entropy_indices = {i+1 for i in geometry_tokens}
        probe_index = {p["index"]: p for p in probes}
        with self.intervention(spec, span, collect=collect, capture=capture, donor=donor,
                prompt_length=source_cache.get_seq_length(), geometry_tokens=geometry_tokens) as state:
            for i, token in enumerate(tokens):
                self.check_budget()
                logp = logits.float().log_softmax(-1)
                scores.append(float(logp[0, token]))
                if i in entropy_indices:
                    entropy.append(dict(prediction_token=i, entropy=float(-(logp.exp()*logp).sum())))
                if i in probe_index:
                    p = probe_index[i]
                    probe_scores.append(dict(index=i, margin=float(logp[0, p["preferred"]]
                                                                   - logp[0, p["alternative"]]),
                                             semantic=p.get("semantic", False)))
                if i + 1 < len(tokens):
                    state["step"] = i
                    logits, cache = self._step(token, cache)
            result = dict(log_probs=scores, nll=-sum(scores)/max(1, len(scores)),
                          probes=probe_scores, retrieval=state["metrics"])
            if capture:
                result["outputs"] = state["outputs"]
            if geometry_tokens:
                result["source_geometry"] = state["geometry"]
                result["target_entropy"] = entropy
            if state["match_stats"] is not None:
                result["source_match_stats"] = {k: v if isinstance(v, int) else float(v)
                    for k, v in state["match_stats"].items()}
            return result

    @torch.inference_mode()
    def generate_diagnostic(self, prefilled, request, spec, *, max_new_tokens,
                            temperature=.6, top_p=.95, top_k=20):
        logits, source_cache = prefilled
        cache = copy.deepcopy(source_cache)
        rng = torch.Generator(device=self.device).manual_seed(request.sample_seed)
        tokens, finish = [], "length"
        with self.intervention(spec, request.draft_token_span, prompt_length=len(request.input_ids)) as state:
            for step in range(max_new_tokens):
                self.check_budget()
                token = int(self._choose(logits, temperature, top_k, rng, top_p).item())
                tokens.append(token)
                if token in self.eos_token_ids:
                    finish = "eos"
                    break
                if step + 1 < max_new_tokens:
                    state["step"] = step
                    logits, cache = self._step(token, cache)
        return GenerationResult(tokens, self.tokenizer.decode(tokens, skip_special_tokens=False),
                                finish, dict(backend="hf_diagnostic", mode=spec.mode,
                                             heads=spec.heads, strength=spec.strength))
