# Batch03 dual-anchor Game24 acquisition — 2026-09-24

## Why this is next

The completed fresh Game24 confirmation batch has eight strictly eligible questions. The Qwen3-32B and Gemma 4E target-model checks and the correct-history specificity control are complete, so the largest remaining gap is independent-question coverage. Batch03 was already frozen as the next 32-question candidate set. On 2026-09-24 the user asked to continue the experiments and keep A100 GPU4 working, authorizing execution of that frozen acquisition despite the earlier September 21 acquisition timebox.

## Frozen design and execution boundary

- Source manifest: `scripts/baseline_manifest_batch03_20260919.json`; retain it unchanged. The execution runner checks its SHA-256 and stores a byte-preserving copy in the output directory.
- 32 fixed questions × 16 ordinary-vLLM R0 generations × two Qwen anchors = 1,024 generations. No question is dropped or reordered based on results.
- Qwen3-8B Thinking runs first, in four-question chunks; Qwen3-32B follows, in two-question chunks. Each chunk is persisted before the next. Both reuse the pinned Game24 input and ordinary-vLLM baseline screen path.
- 8B uses the previously validated settings: BF16, Thinking, temperature 0.6, top-p 0.95, top-k 20, 32,768 context, max sequences 16, batched tokens 8,192, memory utilization 0.85. 32B uses its previously validated settings: same sampling/context, max sequences 4, batched tokens 2,048, utilization 0.95. No quantization or model copy.
- GPU4 is the only visible device. A pre-chunk memory guard stops without touching any process if use exceeds 8,192 MiB. Other GPUs are not used.
- The run ends after both anchors and the pooled scorer summary. Official-false outputs remain in a manual-review queue; no failed draft is selected and no intervention is launched automatically.

## Artifacts

Server output: `/data2/gaojc/projects/contextual-drag-extend/outputs/game24-batch03-dual-anchor-20260924/`.

The status, launch record, frozen-manifest copy, per-chunk raw outputs and logs, merged anchor records, pooled counts, and manual-review queue are stored in that directory. Overall log: `outputs/batch03-dual-anchor-20260924.log`. tmux session: `batch03-dual-anchor-20260924`.

## Live status at launch verification

At 2026-09-23 17:08 UTC, the Qwen3-8B first chunk had finished model loading and started its 64 R0 generations. `status.json` showed 0/1,024 completed generations because progress is committed at chunk boundaries. GPU4 used about 16.3 GB. This is an execution status, not an experimental result; formal eligibility remains pending both acquisition and manual substantive-failure review.

## Timing correction and expected screening yield

The earlier 30.3-hour estimate for the previous Qwen3-32B batch was its overall elapsed status time. Its 16 completed chunk summaries sum to 59,550.8 seconds (16.54 hours) of actual chunk execution; the 13.75-hour gap includes the documented pause after 288/512 outputs and other between-chunk time. The previous Qwen3-8B 512-output run took 9,461.4 seconds (2.63 hours). With this Batch03 chunking and variation in response lengths, a roughly 18–24-hour uninterrupted acquisition is a more appropriate planning range than 32–35 hours. This remains an estimate until the new chunks finish.

The first 20-question dual-anchor screen had six questions meeting the later two-correct/two-substantive-failure threshold (five from 8B alone). Batch02 had eight strict questions among 32 (all eight already met the 8B-only threshold); its ninth scorer-eligible question was excluded by manual review. Across these 52 historical questions, dual-anchor strict yield was 14/52 (26.9%), giving a rough Batch03 expectation of eight to nine eligible questions among 32. This is a screening forecast, not a promised count; the initial 20-question cohort remains pilot data and is excluded from the independent confirmation denominator. The 32B anchor increased eligibility by one question across those 52 historical questions, though it also contributes alternative source drafts. If Batch03 yields eight to nine questions, the independent confirmation cohort would rise from eight to about 16–17 after manual audit and paired intervention.
