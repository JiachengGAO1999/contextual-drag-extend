# Stage B result — 2026-09-12

Completed Sep 12 04:30:02 CST; started Sep 11 21:39:17 CST (6h50m45s). All 112 requested outputs persisted: 7 new questions × 4 paired seeds × R0/R2/R3/R4. Raw files are in `outputs/game24-stage-b-paired-20260911/seed-*/results.jsonl`, synced locally. GPU4 model residency restored after completion. No further experiment launched.

## Primary: seven new questions

| Condition | Correct / 28 | Accuracy | Parse/scorable | EOS completion |
|---|---:|---:|---:|---:|
| R0 direct | 22 | 78.6% | 100% | 96.4% |
| R2 error signal, full attention | 14 | 50.0% | 100% | 100% |
| R3 late_block | 22 | 78.6% | 96.4% | 96.4% |
| R4 path_block | 22 | 78.6% | 96.4% | 96.4% |

Unparseable outputs remain in the denominator and count as unsuccessful. R1 was deliberately omitted; this batch cannot estimate R0−R1 contextual drag.

| Paired contrast | Effect (pp) | 95% question-cluster bootstrap CI (pp) | Wrong→correct | Correct→wrong |
|---|---:|---:|---:|---:|
| R0−R2 residual drag | +28.6 | [3.6, 53.6] | 11 | 3 |
| R3−R2 late recovery | +28.6 | [7.1, 50.0] | 10 | 2 |
| R4−R2 path recovery | +28.6 | [−7.1, 64.3] | 13 | 5 |
| R4−R3 extra path recovery | 0.0 | [−25.0, 28.6] | 6 | 6 |

Transitions go from the right-hand condition to the left-hand condition; “wrong” includes unscorable outputs. Bootstrap: 10,000 paired resamples of whole questions, retaining all four seeds, random seed 2027. Independent question count is seven, not 28. Intervals are exploratory for this selected small pool and do not separately resample within-question seed uncertainty.

Both recovery ratios are 1.00: aggregate accuracy closes the measured R0−R2 gap. This does not mean every damaged example recovered or that the interventions are equivalent to R0. Ratio CIs are omitted because bootstrap residual-drag denominators can be zero or negative.

## Heterogeneity

Correct counts out of four seeds:

| Question | R0 | R2 | R3 | R4 |
|---|---:|---:|---:|---:|
| 123 | 4 | 1 | 3 | 3 |
| 577 | 3 | 4 | 4 | 2 |
| 71 | 3 | 3 | 3 | 3 |
| 719 | 2 | 1 | 1 | 4 |
| 513 | 4 | 3 | 4 | 3 |
| 1084 | 3 | 2 | 4 | 3 |
| 1226 | 3 | 0 | 3 | 4 |

R3 improves the question-level average versus R2 on 4/7 questions, ties on 3/7, and worsens on none (individual seed harms still occur). R4 improves on 4/7, ties on 2/7, worsens on 577. Question 719 favors path blocking, whereas 577 favors late blocking. Thus recovery extends beyond the original 804/1189, but stronger blocking is not uniformly better.

## Checks and limitations

All 28 paired bundles passed input token/hash/span/seed equality checks across R2–R4; R2/R3 first sampled tokens match. Four run-level attention sanity files (first question 123 per run) each report 36 layers checked, zero blocked attention for late/path, and zero postdraft logits change under draft-token mutation for path_block. Positions remain implicit unchanged absolute positions. R3's first token remains from full-prefill logits. This is logical attention blocking, not KV eviction; actual attention probes were not repeated for every question.

Three length terminations all occur on question 71: R4 seed base 2027 and R3 base 12027 are unscorable; R0 base 22027 has an extractable but incorrect expression and repeated final-output loops. They remain unsuccessful; no retries or exclusions. One R2 output (123, base 2027) ends with boxed 24; its preceding expression also repeats 5, so this is not merely a correct reasoning trace lost to formatting. No scorer changes were made.

Thinking settings: temperature 0.6, top_p 0.95, top_k 20, context 32768; HF eager BF16 with float32 sampling. Frozen independent-solve prompt and masks. Deviations from original reproduction remain: HF instead of vLLM, single-model mixed-success selection instead of the 653 anchor subset, and the independent-solve prompt. No inference from this batch alone establishes full mediation or superiority over reset.

## Supplement and decision

Combining these seven with the original three at the preselected first four seed groups gives 10 questions / 40 evaluations per condition: R0 70.0%, R2 45.0%, R3 72.5%, R4 77.5%. R3−R2 +27.5pp; R4−R2 +32.5pp; R4−R3 +5.0pp. Old questions are descriptive supplementation, not new independent confirmation.

Stage B supports a **Go for continuing investigation of recovery through restricted draft access**: residual drag is substantial and recovery recurs on new questions. It does **not** support a general R4>R3 claim: new-question net difference is zero and path blocking has more paired harms. A targeted follow-up could contrast path-sensitive 719 with path-harmed 577, but no attribution implementation or new run is authorized by this report. The current result is preliminary evidence on selected Game24 questions, not a broad benchmark claim.

Machine-readable statistics and anomaly outputs: `stage_b_report_20260912.json`. Analysis script: `.tmp-smoke/analyze_stage_b.py` (run with UTF-8 mode on Windows).
