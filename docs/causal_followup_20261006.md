# Same-site source control and query-window verification

Launched on `sjtu-a100`, GPU4 A100, tmux `game24-source-and-timing-20261006`.
Entry: `python scripts/launch_generation_diagnostics_20261005.py --causal-followup`.
Progress without GPU use: `python scripts/run_causal_followup_20261006.py --status`.
All files remain in `outputs/generation-diagnostics-20261005/` and share its
original cumulative 24 GPU-hour budget; waiting is excluded. No new heads,
strengths, models or training. Candidate remains the frozen 144-head set.

## Frozen events and measurement

Review the original discovery trajectories, not their intervention effects.
Four questions have an expansion/replay event followed by explicit endorsement
of an invalid repeated-number construction within 512 tokens. Quoting the draft
alone is not called commitment. Other discovery questions remain missing.

| Question | Reference onset | Expansion onset | Endorsement probe |
|---|---:|---:|---:|
| 434 | 97 | 190 | 296 |
| 956 | 281 | 309 | 424 |
| 1305 | 75 | 189 | 420 |
| 230 | 63 | 96 | 260 |

Numbers are zero-based generated-token positions. Score the existing reviewed
reject/endorse candidate sequences on identical natural wrong prefixes. This is
an endorsement diagnostic, not calibrated correctness or an independent route
discovery metric. It is more closely linked to acceptance than synthetic literal
number counting. No new continuation generation is used for these annotations.

No unambiguous later adoption decision has been reviewed within 512 tokens, so
post-acceptance windows are recorded missing. A window after a scored decision
cannot affect that decision; its zero effect would not demonstrate specificity.

## Gate 1: source direction at the same sites

FULL, persistent candidate VALUE_ZERO, and NON_DRAFT_MATCHED on the exact same
heads. The control removes a vector in the direction of non-draft attention-value
output (`full - draft`), scaled separately for each head to match the draft vector
norm before o_proj. Float32 scaling avoids avoidable BF16 normalization errors.
The control preserves the local attention weights. It matches pre-projection
magnitude, not projected norm, vector direction or which information is lost.

Twelve completed requests maximum (four questions x three conditions), each
scoring both candidates. Gate: candidate mean improvement over FULL must be
positive and exceed this control. Otherwise stop; do not redefine the candidate.

## Gate 2: equal-length time windows

All windows are 32 generated queries. Query index i feeds token i into the model
and affects prediction i+1; prefill prediction 0 stays unchanged.

- EARLY: [0,32).
- EXPANSION: [reviewed expansion, expansion+32).
- PRE_ACCEPT: [endorsement-32, endorsement).
- NEUTRAL: deterministic disjoint interval between expansion and acceptance.

For each question, also measure FULL and persistent candidate. Compare semantic
windows against FULL, EARLY and NEUTRAL on identical question sets. Freeze the
better eligible expansion/pre-acceptance window by discovery mean; both contrasts
and FULL improvement must be positive. No fallback for missing neutral windows.

This localizes effects in time. A pre-acceptance window is closer to the scoring
position, so a stronger effect alone does not prove semantic event specificity;
multiple outcome positions would be needed to distinguish recency from event
type. These diagnostics are exploratory temporal tests, not final mechanism
identification. No late-window intervention is falsely evaluated against an
earlier outcome.

## Gate 3: windowed bidirectional patch

MASK-window outputs into FULL at selected heads should improve preference;
FULL outputs into MASK-window should weaken it. Both donors replay identical
tokens. Capture only the window's head outputs, not all-prefix outputs or any
full attention matrices. Failure of either predicted direction stops the bridge.

## Behaviour bridge only after gates

Freeze one absolute 32-query interval: the median discovery onset of the chosen
window type. Same interval on all bridge questions/seeds, not an oracle that
knows where the sampled continuation will use the old route. This limits how
directly event-aligned discovery timing can transfer to natural generation.

First four of the seven questions without current natural-generation outputs:
1057, 195, 215, 717. Do not replace missing historical continuations. Some had
earlier semantic diagnostics, so this is not fully unseen external validation.

Four questions x two seeds x FULL / persistent CANDIDATE / WINDOW / windowed
NON_DRAFT_MATCHED CONTROL = at most 32 new outputs. Rerun all four conditions
on the same backend; retain historical sampling/output limits. Report accuracy,
structural reuse, EOS/length, and actual generated-token counts. Equal output
limits do not imply equal compute. No automatic generation expansion.

## Artifacts

Frozen annotations/settings: `causal_followup_config.json`.
Raw requests: `causal_diagnostics.jsonl`.
Stage results: `causal_source_control.json`, `causal_timing.json`,
`causal_window_candidate.json`, `causal_window_patch.json`.
Behaviour: `causal_behaviour/behaviour.jsonl`, `causal_behaviour_summary.json`.
State/report: `causal_summary.json`, `causal_report.md`; shared `budget.json`.

New norm control and window/donor semantics have targeted A100 regression checks
alongside prior backend checks. Their cost is inside the same budget. Existing
scientific results are retained. Only the authorized idle project resident is
stopped, and it is restored when GPU4 is free. No automatic failure retries.
