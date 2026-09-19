# Gate A decision and baseline queue — 2026-09-18

## Scope audited

The completed pilot contains 7 questions × 2 paired seeds × 4 conditions = 56 generations. The conditions are R0, R2, whole `late_block` (R3), and whole `path_block` (R4), using the frozen independent-solve prompt and selective vLLM. All 56 generations reached EOS and were parseable.

The seven questions are an intervention/development set. They are not eligible for the formal validation pool.

## Results

| Condition | Correct | Accuracy |
|:---|---:|---:|
| R0 | 12/14 | 85.7% |
| R2 | 4/14 | 28.6% |
| R3 whole-late | 12/14 | 85.7% |
| R4 whole-path | 10/14 | 71.4% |

Question-cluster bootstrap effects:

- R0 − R2: +57.1 pp, 95% CI [+35.7, +78.6]
- R3 − R2: +57.1 pp, 95% CI [+28.6, +85.7]
- R4 − R3: −14.3 pp, 95% CI [−50.0, +14.3]
- R4 − R2: +42.9 pp, 95% CI [+14.3, +71.4]

Excluding question 41 gives the same directional conclusion: R0−R2 = +66.7 pp, R3−R2 = +66.7 pp, R4−R3 = −16.7 pp, and R4−R2 = +50.0 pp. The unit is the question; this is still pilot evidence with only six or seven clusters.

## Gate A decision

**Go for independent baseline acquisition.** The pilot shows a reproducible-looking R0→R2 residual drag and a large whole-late recovery signal. Whole-path also improves over R2, but is not better than whole-late in this pilot. Therefore no path-superiority claim and no new local mask taxonomy are authorized.

The result is not an exact reproduction of the upstream Contextual Drag three-anchor protocol: R0/R2 use the frozen independent-solve prompt. It is evidence for a fixed-error-context influence under this adapted protocol.

## Queued next batch

The first 24-question screen is retained as historical baseline-only data. It cannot enter the formal pool because it includes questions used by the current development/intervention work, and its 24 questions produced no question with at least two correct and two substantive failed drafts under the fixed audit rule.

The next queue uses the original fixed candidate order, excluding all development/intervention IDs and all 24 previously screened IDs. It contains 32 new questions, 16 R0 samples per question, and 512 ordinary-vLLM generations on Qwen3-8B. No R2/R3/R4 generation is included in this phase. The frozen candidate manifest is `scripts/baseline_screen_manifest_20260918_batch02.json`.

The queue waits for GPU4 on A100 to have no large non-`gaojc` process, stops only the exact `gaojc` selective resident, runs the baseline-only screen, persists an exit marker, and restores the selective resident. It does not kill or preempt another user's process.

After this batch, stop for baseline eligibility audit. Do not automatically start intervention or add Qwen3-32B; the latter requires a separate resource/authorization check.
