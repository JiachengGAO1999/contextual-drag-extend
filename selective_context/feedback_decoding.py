"""Paired-feedback contrastive decoding; the contrastive formula is established ID/CFG.

Each request has two prompts and one generated prefix, shared only as token values.
KV rows remain independent. No attention intervention or verification oracle runs
during decoding. This module deliberately leaves the existing generation API alone.
"""
from __future__ import annotations

import time
import torch


def feedback_logits(actual, counterfactual, strength):
    return actual.float() + strength * (actual.float() - counterfactual.float())


def sample(logits, generator, *, temperature, top_k, top_p):
    if temperature == 0:
        return logits.argmax()
    scores = logits.float() / temperature
    if top_k:
        scores = scores.masked_fill(scores < torch.topk(scores, min(top_k, scores.numel())).values[-1], -torch.inf)
    if top_p < 1:
        ordered, indices = torch.sort(scores, descending=True)
        remove = torch.softmax(ordered, -1).cumsum(-1) > top_p
        remove[1:] = remove[:-1].clone()
        remove[0] = False
        scores = scores.scatter(0, indices, ordered.masked_fill(remove, -torch.inf))
    return torch.multinomial(torch.softmax(scores, -1), 1, generator=generator).squeeze(0)


@torch.inference_mode()
def generate_batch(model, tokenizer, requests, *, max_new_tokens, sampling, eos_ids,
                   on_finish, heartbeat=lambda *_: None):
    """Run up to four requests (eight independent KV rows), persisting each at EOS.

Both FULL and GUIDED use the same two-row layout, including strength=0 FULL.
The extra FULL branch is an explicit compute cost, included in the budget.
"""
    device = next(model.parameters()).device
    prompts = [ids for r in requests for ids in r["prompt_ids"]]
    width = max(map(len, prompts))
    pad = tokenizer.pad_token_id
    if pad is None:
        pad = min(eos_ids)
    ids = torch.full((len(prompts), width), pad, dtype=torch.long, device=device)
    mask = torch.zeros_like(ids)
    for row, tokens in enumerate(prompts):
        ids[row, -len(tokens):] = torch.tensor(tokens, device=device)
        mask[row, -len(tokens):] = 1
    positions = (mask.cumsum(-1) - 1).clamp_min(0)
    output = model(input_ids=ids, attention_mask=mask, position_ids=positions,
                   use_cache=True, return_dict=True, logits_to_keep=1)
    past, logits = output.past_key_values, output.logits[:, -1, :]
    generated = [[] for _ in requests]
    active = [True] * len(requests)
    generators = [torch.Generator(device=device).manual_seed(r["seed"]) for r in requests]
    begun = time.monotonic()
    for step in range(max_new_tokens):
        heartbeat(step, sum(active))
        next_ids = torch.full((len(prompts), 1), pad, dtype=torch.long, device=device)
        next_mask = torch.zeros_like(next_ids)
        for i, r in enumerate(requests):
            if not active[i]:
                continue
            scores = feedback_logits(logits[2*i], logits[2*i+1], r["strength"])
            token = int(sample(scores, generators[i], **sampling).item())
            generated[i].append(token)
            next_ids[2*i:2*i+2, 0] = token
            next_mask[2*i:2*i+2, 0] = 1
            finished = token in eos_ids or step + 1 == max_new_tokens
            if finished:
                active[i] = False
                on_finish(r, generated[i], "eos" if token in eos_ids else "length",
                          time.monotonic() - begun)
        if not any(active):
            break
        mask = torch.cat((mask, next_mask), dim=-1)
        positions = (mask.sum(-1, keepdim=True) - 1).clamp_min(0)
        output = model(input_ids=next_ids, attention_mask=mask, position_ids=positions,
                       past_key_values=past, use_cache=True, return_dict=True, logits_to_keep=1)
        past, logits = output.past_key_values, output.logits[:, -1, :]
