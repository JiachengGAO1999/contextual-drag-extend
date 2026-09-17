# Attention block scope audit

Source: actual saved bundles under `outputs/game24-qwen3-8b-thinking-fixed-r0-r4-20260908/bundles`, and `selective_context/masks.py`, `hf_backend.py`. Read-only analysis; no intervention changes.

| Problem | Prompt tokens | Blocked draft key span [start,end) | Draft tokens | Draft/prompt | Postdraft prompt tokens |
|---|---:|---|---:|---:|---:|
|1189|825|[315,714)|399|48.36%|111|
|1358|1069|[312,958)|646|60.43%|111|
|804|901|[314,790)|476|52.83%|111|

Mask is binary hard blocking: disallowed attention logits get the dtype's minimum finite value; measured blocked attention probability is zero in existing sanity checks. Mask head dimension is 1 and broadcasts across all attention heads; the same attention mask is used across all 36 decoder layers. No partial weighting or layer selection.

R3: ordinary complete prefill. Draft keys blocked only for generated query positions q >= prompt_length. First output token comes from complete prefill logits; blocking starts when processing that token to predict the next one.

R4: draft keys blocked for every query q >= draft_end, including all 111 postdraft prompt positions and generated queries. Draft tokens can still process earlier context and causally available draft tokens; their KV entries are not physically deleted. Original problem, pre-draft instructions, postdraft instructions and generated history remain readable under normal causality.

All three saved boundary spillovers are empty: mask exactly covers the draft character range. Scope includes the whole final-response draft (correct intermediate reasoning, incorrect reasoning, explanatory text and boxed answer), not just erroneous steps. Original draft Thinking was removed under the frozen upstream extraction policy; it is not part of the masked span.

Draft/prompt percentages count key positions, NOT fractions of attention probability, semantic information, or all matrix edges. For subsequent generation, draft-key count stays fixed while generated-history key count grows. R4 adds draft-to-suffix blocking during prefill; it does not hide the suffix itself.

Interpretation: no boundary overreach observed, but semantic intervention is broad. It removes access to useful and harmful draft content together and leaves a critique task requesting unreadable content. This can explain missing-draft language and may affect output behavior, but current evidence cannot establish it as the cause of low recovery. R0 solves without any draft, so draft removal alone is not sufficient to predict failure; retained task framing and positional structure matter. Any weaker-mask/changed-prompt experiment requires a separate decision, not a silent change to this batch.

Inspection: in each `<id>.r2_r4.json`, read `prompt_text`, `draft_character_span`, `masked_character_span`, `boundary_spillover`, and `requests[*].draft_token_span`. Pair files `<id>.json` hold the exact masked draft in `traj1`. Token spans are zero-based and end-exclusive.
