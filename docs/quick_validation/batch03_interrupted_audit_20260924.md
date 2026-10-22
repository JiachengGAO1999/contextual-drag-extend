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
| Substantive mathematical or number-use error | 61 | Counts toward the failed-answer pool |
| Correct expression missed by answer extraction/scoring | 3 | Reclassified as correct; excluded from the failed pool |
| Invalid for eligibility | 4 | Excluded because EOS/parseability criteria fail |
| Uncertain, awaiting manual confirmation | 0 | None remained unresolved after review |

In addition to 771 scorer-True answers, three extraction misses are confirmed correct: Qwen3-8B q445/sample13 and q395/samples7,12. In each case the extracted answer is only scalar `24`, while the response presents an endorsed expression that uses the exact four inputs. The two questioned Qwen3-8B q122 rows are **not** extraction misses: samples4 and9 evaluate to24 but use `[8,8,9,12,12]` and `[8,9,12,12,12]` against `[8,9,12,12]`. Along with q122/sample11, these give q122 three substantive errors and 13 valid correct answers, so q122 passes on its available 8B data.

Question381 contains mixed responses, and the binary rule is now explicit: score the expression marked as the final answer. For samples5 and10, the final selected expression evaluates to24 but uses `[6,8,11,11,11]` instead of `[6,8,11,11]`. Both responses also contain `11 + 11 + 8 - 6 = 24` as an earlier alternative. Since each then explicitly selects the invalid expression as its Final Answer, the response counts as a substantive error; the earlier alternative does not rescue it. This makes q381 qualify with 29 valid correct and three substantive errors pooled across the models. Under the more permissive alternative rule (“any clearly endorsed valid expression anywhere counts”), q381 would fail with only one wrong answer; that sensitivity gives seven dual-complete questions and a five-question shortfall instead.

After the primary review, eligibility uses **774 valid correct responses** and **61 confirmed substantive errors**; 29 outputs are invalid and excluded, with zero unresolved cases. The initial automatic-screen gate was 9 dual-complete and 5 partial-only questions. After review, 8 dual-complete and 5 partial-only questions meet the unchanged pooled two-correct/two-substantive-error rule.

**Dual-anchor complete (22 candidate questions; 8 eligible):** `195, 434, 215, 144, 1281, 395, 1206, 381`.

**8B-only partial coverage (10 candidate questions; 5 pass the response-count rule on available data):** `1171, 764, 1019, 200, 122`. They are not counted as dual-anchor-complete until 32B coverage is completed.

The row-level evidence is in `error_review.csv`; full saved responses remain in `failure_review_queue.json`. `extraction_miss_audit.csv` isolates the three confirmed misses. `expression_verification.csv` evaluates 852 extracted/body/manual-evidence expressions with exact rational arithmetic and records each operand multiset; all 771 scorer-True rows have a verified exact equation. The two q122 corrections have exact value24 but fail the input-multiset check. `eligibility_boundary_audit.json/.csv` lists per-question model counts and the sample identities supporting each threshold. The 8 dual-complete and 5 partial-only passing questions are separated. The near-boundary dual-complete questions with only one confirmed error are `1051, 445, 580, 1133`; q381 now passes under the stated final-answer rule.

## Fixed-order prefix replay on the 22 dual-complete questions

For each model, samples were replayed in ascending saved `response_id`; eligibility pooled the two anchors and counted only valid correct answers plus manually confirmed substantive failures.

| Per-model prefix | 8B-alone eligible | 32B-alone eligible | Both alone | Pooled eligible | Newly pooled eligible | Newly eligible IDs |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 0 | 0 | 0 | 2 | 2 | `215, 1281` |
| 8 | 3 | 5 | 2 | 7 | 5 | `195, 434, 395, 1206, 381` |
| 12 | 3 | 5 | 2 | 8 | 1 | `144` |
| 16 | 3 | 5 | 2 | 8 | 0 | — |

At prefix 4, neither model alone qualifies a question; pooling complementary answers qualifies 215 and 1281. At prefix 8, 8B alone qualifies `195, 215, 1281`; 32B alone qualifies `434, 215, 1281, 1206, 381`; both independently qualify `215, 1281`. Pooling also qualifies `395`, which neither model alone qualifies at that prefix. The five new pooled questions over prefix 4 are `195` (8B alone), `434` and `1206` (32B alone), `395` (combined anchors), and `381` (32B alone). At prefix 12, the two anchors together add `144`; prefix 16 adds no question.

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

The current sprint plan explicitly targets **20–30 new independent Game24 questions**. Batch02 contributes eight strict questions; Batch03 now contributes eight dual-anchor-complete questions, for **16 currently countable questions**, four below the lower bound. Five more 8B-only partial questions already pass the pooled 2+2 rule: `1171, 764, 1019, 200, 122`.

**Superseding recommendation after independent review:** do not launch the proposed outcome-selected 64/80-response 32B completion. Ranking questions by observed 8B error counts conflicts with the frozen no-8B-outcome-filtering acquisition rule. Keep all existing samples and leave the ten incomplete questions explicitly partial. Prepare an eight-question Qwen3-8B paired R0/R2/R3/R4 validation (two seeds; 64 generations) on the fully sampled, audited prefix. The stopping decision and potentially informative runtime truncation must be disclosed; this is a revised cohort, not a completed original Batch03. See [the next-experiment plan](batch03_next_experiment_20260924.md). No generation has been launched.

If acquisition is later resumed, full completion of all ten missing 32B groups at n=16 costs 160 responses and preserves the original sampling design. A uniform n=8 alternative across all ten costs 80, but is an explicitly revised uneven-budget design. Neither is launched. The prior 20–30-question target is not a requirement to keep sampling until a desired count or effect appears. The three manual extraction corrections are descriptive; the prepared next plan independently requires at least two original official-True valid responses, and obtains the same eight complete and five partial passing questions.

## Resumable implementation and verification

The original runner is unchanged. `scripts/batch03_dual_anchor_resumable_20260924.py` is an isolated recovery runner; `scripts/batch03_resume_core_20260924.py` holds dependency-light identity/checkpoint functions. It loads frozen prompt token IDs from `requests.json`, takes one or more existing result files as the identity catalog, skips saved `(model, question, sample_index)` tuples, writes each completed response as JSONL with `fsync`, and safely aborts at a completed-sample boundary on SIGINT/SIGTERM. A recovery output must be a new directory; restarting that recovery uses the same directory and matching config. A later extension uses another directory and lists the earlier recovery JSONL among existing results.

The runner defaults to the original prefix16 and constrains 32B to `max_num_seqs=1`. A seed audit found a recovery bug: the old runner restarted every missing subset at seed42 and remapped local output index0 to the next missing global sample. In vLLM0.11, n-way children receive `parent_seed + child_index`; resuming global IDs3–7 as a five-output request at seed42 would reuse seeds42–46, including seeds already assigned to IDs0–2. The revised runner groups missing indices into contiguous runs and starts each run at `base_seed + first_sample_index`; vLLM then assigns each child the stable seed `42 + frozen_sample_index`. Gaps become separate runs, so no seed is reused or relabeled. Changed scheduling still means token-for-token reproduction is not promised.

Independent no-model verification: all eight recovery tests and six new audit regression tests pass. The audit tests check the actual saved q122/q381 responses, the three true extraction misses, invalid-answer exclusion, mixed-answer handling, and every one of the 771 official-True extracted expressions. The installed A100 vLLM0.11 source confirms `child_seed = parent_seed + index`. Removed a contradictory fallback that could rescue an explicitly wrong extracted expression using a scalar-only manual override. No GPU/model validation or generation was run in this review.

Machine-readable interruption/revision, partial summary, file manifest, manual review, and prefix analysis are stored in the original run output directory under unique new filenames. No original chunk file is overwritten.
