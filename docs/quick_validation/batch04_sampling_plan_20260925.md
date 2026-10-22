# Batch04 fresh-question screen (2026-09-25)

**Status: frozen and authorized for baseline screening. No intervention request is part of this run.**

## Design

- Source: Tree of Thoughts Game24 `24.csv` at revision `8050e67d0e3a0fddc424d7fa5801538722a4c4cc`; the executable manifest and source SHA-256 are in [`baseline_manifest_batch04_20260925.json`](../../scripts/baseline_manifest_batch04_20260925.json).
- Freshness: preparation scanned prior scripts, manifests, plans, screening outputs, experiment runs, and pair records. It excluded all 194 previously seen question IDs and their number multisets, then drew 32 unique remaining questions with order seed `20270925`.
- Budget: 8 baseline generations per question from each of Qwen3-8B Thinking and Qwen3-32B; 32 × 8 × 2 = **512 generations**. Sampling stays at temperature 0.6, top-p 0.95, top-k 20, Thinking enabled, and the pinned 32,768-token context. Only the per-question screening count changes from 16 to 8.
- Inclusion for a later evaluation pool: pool both anchors; require at least two valid EOS/parseable official-correct responses and at least two valid, manually confirmed substantive errors. Official scorer-false outputs stay pending review and do not count as errors without manual review. A failed sample is selected only after screening and audit, without inspecting intervention outcomes.
- Historical planning evidence: the audited fixed-order Batch03 replay yielded 2/22 pooled eligible at prefix 4, 7/22 at 8, 8/22 at 12, and 8/22 at 16. Applying 7/22 to 32 candidates suggests roughly 10 eligible questions; this is only a runtime/budget estimate, not a promised yield.

## Execution and bounds

The runner uses the existing ordinary-vLLM baseline screen with the same model paths, decoding, scorer, and prompt builder as Batch03. GPU4's owned selective resident will be stopped only after checking that it is the sole compute owner, then restored in the same tmux session after success or failure. The run is chunked (4 questions for 8B, 2 for 32B), persists completed chunks, and has no automatic retry, question expansion, candidate acceptance, or intervention launch.

Estimated baseline-screen time is about 9 hours, extrapolated from Batch03's measured generation seconds and adjusted for the extra 32B chunks. It does not include manual error review or any later paired evaluation. Output: `outputs/game24-batch04-dual-anchor-screen-20260925/`; launch log: `outputs/batch04-dual-anchor-screen-20260925.launch.log`.

Frozen candidate IDs: 1109, 637, 50, 346, 871, 928, 920, 990, 285, 353, 28, 1073, 438, 1262, 740, 643, 1269, 801, 193, 756, 487, 35, 921, 141, 988, 750, 130, 555, 666, 562, 1119, 421.
