# Ten-question M_X late/path experiment — frozen 2026-09-13

User authorized launch following the verified per-interval path implementation.
Ten fixed failed drafts, four original paired seeds per question, unchanged
independent-solve prompt, scorer and official Qwen3-8B Thinking sampling:
temperature 0.6, top_p 0.95, top_k 20, context 32768. HF eager BF16 and float32
sampling remain the same as prior runs; these are not vLLM results.

| Condition | Selected keys | Timing |
|---|---|---|
| M_X | Frozen selected complete erroneous-expression copies | late_block |
| M_CX | Equal-token audited pre-error prefix | late_block |
| P_X | Exactly the same keys as M_X | per-interval path_block |
| P_CX | Exactly the same keys as M_CX | per-interval path_block |

Total 160 records. Reuse exactly 32 M_X/M_CX records from 1226,719,577,1358
in `game24-multi-late-20260912`; newly generate 128. Existing records are copied
without relabeling, rescoring or changing annotations. Manifest records their
original paths. Existing R2 and whole-draft R3/R4 remain reference conditions.

## Six-question annotation/control audit

Recompile and compare M_X against the previously saved ten-question coverage;
do not regenerate annotations or tune them based on outputs. Six additional
questions retain the same full-expression-family logic. ID123 includes the
plain-text full-expression copy; ID71 excludes the different fraction expression
with the same operands; ID513 selects one repeated erroneous family rather than
all failed candidates. No V or XV interventions in this run.

| ID | M_X tokens | Audited control prefix available tokens |
|---|---:|---:|
| 1189 | 56 | 103 |
| 804 | 90 | 118 |
| 123 | 60 | 108 |
| 71 | 356 | 492 |
| 513 | 109 | 111 |
| 1084 | 44 | 163 |

Select the first N eligible tokens, the same rule used in the frozen four-question
controls. Audit stops are fixed in `multi_late_path.SAFE_END`. The ID71 prefix
includes arithmetically correct trials explicitly rejected for failing to reach 24;
it stops before the invalid repeated-number continuation. ID513 prefix ends before
its first candidate. Controls can end inside a word/number by token-budget design;
the prompt is not truncated or retokenized. Controls match amount, not location,
fragmentation, or semantic function. Path starts at each compiled interval end;
thus timing/location differences between target and control remain a confound.
Do not interpret P_X−P_CX as pure semantic responsibility.

## Preflight / execution / analysis

All 160 jobs pass frozen text/token/seed/coverage and existing-result identity
checks. Persist all request bundles and source manifest before generation.
Before evaluation, verify 40 question-condition attention cases on the real model:
late decode blocks; path prefill and decode blocks, retained draft access, and
final-prefill logit invariance when selected tokens are mutated. Failure stops
evaluation with no fallback. Late first generated token must equal matching R2;
path first-token logits may change by definition.

Primary report: accuracy, paired M_X−R2, P_X−R2, P_X−M_X, target−control at each
timing, and comparisons with whole R3/R4; wrong→correct/correct→wrong counts;
question-cluster bootstrap CI retaining the four seeds; parse/completion rates.
Report old diagnostic four and additional six separately as well as combined.
Keep all length/unparseable outcomes in the denominator. Do not change masks,
select seeds, or stop early on favorable results. Ten selected questions remain
exploratory evidence, not generalization to the full task pool.

Output: `outputs/game24-qwen3-mx-late-path-20260913`.
tmux: `qwen3-mx-late-path`; log: `mx_late_path_20260913.log`.
GPU4 only; weights loaded read-only from `/data2/huangrj/models/qwen3-8b`.
Estimated 8–12 hours (prior comparable mean 217 seconds ×128 ≈7.72 hours,
plus sanity checks and new-question/path variation). No further experiments
auto-launch; resident restarts after success or visible failure.
