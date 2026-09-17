# Multi-region path boundary — 2026-09-13

## Frozen definition

For each compiled half-open token interval `[a_i,b_i)`, deny attention from every
query `q >= b_i` to every key `a_i <= k < b_i`, at every layer. Intersect with the
ordinary causal mask. This starts at each interval's end, including subsequent
draft text, later selected intervals, the prompt suffix, and generated queries.
Queries within that same interval retain ordinary causal access to its tokens.
Unselected keys remain accessible subject to causality and the other intervals.

Example: intervals `[2,4)` and `[7,9)` mean queries 4 onward cannot read keys 2–3,
and queries 9 onward cannot read keys 7–8. Query 8 can read key 7 but not key 2.
The gap 4–6 is retained; it cannot acquire the earlier selected information via
attention because those edges were already blocked during prefill.

Use the frozen compiler's merged intervals (overlap and adjacency are merged).
Do not reinterpret individual evidence entries as separate boundaries after
compilation. Empty explicit intervals retain the legacy whole-draft behavior;
a single interval equal to the draft reproduces original R4 exactly.

Late uses the same selected keys, but begins only at generated queries
`q >= prompt_length`. Its full prefill and first-token logits remain unchanged.
Path changes prefill, so its first-token logits may change. Neither deletes text,
renumbers tokens, nor physically evicts KV. Copies or paraphrases outside selected
intervals remain readable: this is not a guarantee of removing an error concept.

## Implementation and checks

- `selective_context/schema.py`: accepts explicit regions for late and path;
  rejects explicit regions for full access.
- `selective_context/masks.py`: per-interval path boundary, common causal mask.
- `selective_context/hf_backend.py`: passes regions into both prefill and decode.
- `tests/selective_context/test_multi_region.py`: boundary matrix, gaps,
  intra-interval visibility, legacy equivalence, serialization, actual small-model
  attention, mutation invariance with a full-access positive control, cached
  decoding, and backend mask routing.
- Local targeted tests: 22 passed. Local full collection lacks `math_verify`;
  server full suite: **51 passed**, no scorer fallback used.
- Local/server HEAD: `7fc7245527ff81ffc2a5ee3f88db26d6e52d1540` plus synchronized
  uncommitted overlay, SCP archive successfully extracted.
- Real Qwen3-8B eager/BF16 check: fixed M_X regions on 1226, 719, 577, 1358;
  all 36 layers have exactly zero blocked prefill/decode attention. Mutating only
  selected input tokens gives exactly zero maximum logit change from the final
  interval end onward and on one fixed cached decode query. Unselected draft
  attention remains positive at every layer. Full detail in
  `multi_path_sanity_20260913.json`; reproducible command:
  `python -m selective_context.phase0.multi_path_sanity`.

This is a bounded implementation check, not a Thinking accuracy experiment.
The check temporarily loaded a second model in free GPU4 memory and exited;
the existing resident was left running. Old four annotations, coverage and controls
were not edited. No new paired evaluation generations were launched. The remaining
six annotations/controls and ten-question paired runner still need their planned
freeze/preflight before the proposed 128 new generations.
