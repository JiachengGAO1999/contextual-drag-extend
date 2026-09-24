# Batch03 interruption, screening audit, and continuation decision

**Status: interrupted after a recorded mid-course plan revision review. No follow-up generation or intervention was started.** The original runner and source result chunks remain untouched.

## Stop and preservation record

On 2026-09-24, the Batch03 parent scheduler and its Qwen3-32B generation/engine processes were re-identified from live process data before stopping. The scheduler was terminated first to prevent it from scheduling another chunk; the remaining processes in this run then exited. No unrelated job was targeted. GPU4 was rechecked at 11:55:56 UTC (19:55:56 China time): 4 MiB used, 0% utilization, and no running process. A second read-only check at 13:14:26 UTC still showed GPU4 idle at 4 MiB/0%; no Batch03 processes remained. Other GPUs had unrelated compute processes, but their GPU UUIDs did not match GPU4. The interruption record was written at 11:59:59 UTC. The scheduler, generator, and vLLM engine are absent; the original status is `interrupted`, not complete.

The frozen run planned 1,024 responses. It had persisted 864:

- Qwen3-8B Thinking: 512/512 across eight completed chunks.
- Qwen3-32B: 352/512 across eleven completed chunks (`chunk-00`–`chunk-10`).
- 32B `chunk-11` had begun but had no result JSONL or summary at stop. Its config, request list, and logs are preserved. Any unsaved in-memory responses are excluded. `chunk-12`–`chunk-15` had not started.
- Thus 160 planned response slots were not persisted; this is not a claim that every one of those tokens had not begun generation.

Original raw chunks remain under the run output directory. Process IDs, interruption timestamp, persisted counts, and GPU release check are in `runs/batch03_interrupted_20260924/interruption_record.json`; the audited raw copy, status, and file hashes are also preserved under `runs/batch03_interrupted_20260924/` locally.

## Recomputed results and manual false-answer review

The 864 persisted records contain 771 scorer-True, 68 scorer-False, and 25 scorer-None outputs. Applying the predeclared complete-EOS plus parseable-thinking filter leaves 771 automatically correct, 64 valid scorer-False answers for review, and 29 invalid/unresolved outputs. The 68 scorer-False rows were individually checked against the full response, the exact four input numbers, and the final expression:

| Manual disposition | Count | Treatment |
|---|---:|---|
| Substantive mathematical or number-use error | 57 | Counts toward the failed-answer pool |
| Correct expression missed by answer extraction/scoring | 7 | Reclassified as correct; excluded from the failed pool |
| Invalid for eligibility | 4 | Excluded because EOS/parseability criteria fail |
| Uncertain, awaiting manual confirmation | 0 | None remained unresolved after review |

In addition to 771 scorer-True answers, the seven extraction false negatives are valid correct answers. Two of these were Qwen3-32B responses for question 381: the final selected expression reused an input number, but the same response explicitly gave `11 + 11 + 8 - 6 = 24` as a valid alternative. The extractor selected only the final expression. Eligibility therefore uses 778 valid correct responses and 57 confirmed substantive errors; invalid outputs never count toward either threshold. The initial automatic-screen gate was 9 dual-complete and 5 partial-only questions. After review, 7 dual-complete and 4 partial-only questions meet the unchanged pooled two-correct/two-substantive-error rule.

**Dual-anchor complete (22 candidate questions; 7 eligible):** `195, 434, 215, 144, 1281, 395, 1206`.

**8B-only partial coverage (10 candidate questions; 4 pass the response-count rule on available data):** `1171, 764, 1019, 200`. These four are not dual-anchor-complete and are not counted as formal dual-anchor questions before the missing 32B samples are addressed.

The row-level evidence table is `error_review.csv`; it records model, question/sample identity, classification, reason, extracted expression, and source chunk/line/hash. `failure_review_queue.json` retains the full saved response evidence. `partial_results_manifest.json` lists all 864 unique `(model, question, sample_index)` identities with source line and file hash; analysis fails on any duplicate identity. The seven extraction false negatives include valid expressions present in the body when the extractor returned scalar `24`, two expressions for question 122 that were valid as extracted, and the two question381 alternatives described above. The other valid false answers fail arithmetic or reuse/omit input numbers.

## Fixed-order prefix replay on the 22 dual-complete questions

For each model, samples were replayed in ascending saved `response_id`; eligibility pooled the two anchors and counted only valid correct answers plus manually confirmed substantive failures.

| Per-model prefix | 8B-alone eligible | 32B-alone eligible | Both alone | Pooled eligible | Newly pooled eligible | Newly eligible IDs |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 0 | 0 | 0 | 2 | 2 | `215, 1281` |
| 8 | 3 | 4 | 2 | 6 | 4 | `195, 434, 395, 1206` |
| 12 | 3 | 4 | 2 | 7 | 1 | `144` |
| 16 | 3 | 4 | 2 | 7 | 0 | — |

At prefix 4, neither model alone qualifies a question; pooling complementary answers qualifies 215 and 1281. At prefix 8, 8B alone qualifies `195, 215, 1281`; 32B alone qualifies `434, 215, 1281, 1206`; both independently qualify `215, 1281`. Pooling also qualifies `395`, which neither model alone qualifies at that prefix. The four new pooled questions over prefix 4 are `195` (8B alone), `434` and `1206` (32B alone), and `395` (combined anchors). At prefix 12, the two anchors together add `144`; prefix 16 adds no question. The reclassified question 381 no longer meets the two-substantive-error threshold.

The per-question/per-model counts and identities are in `prefix_yield_analysis.json`. Chunk summaries record duration only at the chunk level. They do not support accurate GPU-time attribution to prefixes 4/8/12/16, so this report does not calculate prefix-specific eligible-per-hour rates.

## Measured runtime evidence

Summing persisted chunk summaries only:

| Model | Saved outputs | Generation seconds | Model-load seconds | Sum of reported chunk totals | Weighted generation throughput |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B Thinking | 512 | 8,522.619 s (2 h 22 m) | 357.200 s | 8,891.686 s (2 h 28 m) | 497.2 tokens/s |
| Qwen3-32B | 352 | 37,157.073 s (10 h 19 m) | 755.995 s | 37,923.732 s (10 h 32 m) | 60.1 tokens/s |
| **Total saved chunks** | **864** | **45,679.692 s (12 h 41 m)** | **1,113.195 s** | **46,815.418 s (13 h 00 m)** | — |

The sums above exclude the incomplete `chunk-11`, for which no completed summary exists. Its last preserved vLLM log showed active and waiting sequences and a full KV cache, but does not yield a reliable per-sample GPU-time total. No prefix-level timing or time-per-eligible-question figure is inferred.

## Scale target and recommendation

The current sprint plan explicitly targets **20–30 new independent Game24 questions**, excluding the seven-question pilot and old development set. The preceding Batch02 contributed eight strict questions. This Batch03 audit contributes seven additional dual-anchor-complete questions, for **15 currently countable strict questions**. That is five below the lower end of the planned range. Four of the ten 8B-only partial questions already pass the pooled 2+2 rule on their saved 8B responses, but none can be counted as dual-anchor-complete until their second-anchor evidence is generated and reviewed.

**Recommendation: keep the original run interrupted and, if continuing, use a documented reduced-prefix completion for the ten frozen 8B-only questions.** Generate only Qwen3-32B sample identities 0–7 for each of those ten questions: 80 responses rather than the original 160 remaining slots. This retains every candidate and the same prompt-token archive, temperature/top-p/top-k, seed 42, and per-question token budget; it changes the planned 32B sample count for those ten questions from 16 to 8 and must be recorded as a mid-course revision. Use `max_num_seqs=1` for 32B. Then manually audit all new outputs and count how many of those ten satisfy the same 2+2 rule. The four questions already meeting 2+2 from 8B alone will remain eligible when the second anchor is added, bringing the count to at least 19 if they also pass dual-anchor completion. At least one of the other six must qualify to reach the target floor of 20; that outcome is uncertain, not guaranteed.

This reduced-prefix choice is supported by the retrospective replay: among the 22 already complete questions, moving from 8 to 12 samples per model added one eligible question, while 12 to 16 added none. That observation is not a time-normalized yield and does not predict the ten uncompleted questions. All ten should receive the same prefix so the result is not selected by 8B outcomes. If the resulting audited pool remains below 20, decide on a new fresh-question batch with a frozen candidate list and initial prefix before generating it. Do not auto-continue to sample 16, and do not start downstream interventions as part of this recovery task.

Completing the original 160 missing 32B slots remains the strict-protocol alternative if preserving the original per-question `n=16` design is prioritized. It is not the recommended default: 32B is the dominant measured cost, and the existing prefix replay shows diminishing screening returns by 12. Choosing the reduced plan changes the acquisition budget, not the 2+2 eligibility threshold, and does not make the interrupted 1,024-response plan complete.

## Resumable implementation and verification

The original runner is unchanged. `scripts/batch03_dual_anchor_resumable_20260924.py` is an isolated recovery runner; `scripts/batch03_resume_core_20260924.py` holds dependency-light identity/checkpoint functions. It loads frozen prompt token IDs from `requests.json`, takes one or more existing result files as the identity catalog, skips saved `(model, question, sample_index)` tuples, writes each completed response as JSONL with `fsync`, and safely aborts at a completed-sample boundary on SIGINT/SIGTERM. A recovery output must be a new directory; restarting that recovery uses the same directory and matching config. A later extension uses another directory and lists the earlier recovery JSONL among existing results.

The runner defaults to the original prefix 16; `--sample-limit 8` is available to implement the proposed revised prefix. 32B is constrained to `max_num_seqs=1`. The run keeps the base seed and sampling settings, but changed scheduling, request n, and batch order mean token-for-token reproduction is not promised.

No-model validation: `scripts/test_batch03_resume_core_20260924.py` passed all five tests (saved-ID skipping, cross-file de-duplication, conflicting/within-file duplicate rejection, immediate persistence, and stop/restore). Python compileall passed for the analyzer, runner, core, and tests. No GPU/model validation was run; the 32B engine configuration still needs a later zero-generation preflight or an explicitly approved smoke before any formal recovery launch.

Machine-readable interruption/revision, partial summary, file manifest, manual review, and prefix analysis are stored in the original run output directory under unique new filenames. No original chunk file is overwritten.
