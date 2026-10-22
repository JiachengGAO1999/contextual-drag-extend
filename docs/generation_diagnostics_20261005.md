# Failed-history transmission diagnostics

2026-10-05 first execution: acceptance passed; the run stopped after eight shortlisted
heads failed to improve a lexical first-divergence metric. This does not establish
absence of causal heads. Occupied GPU time: 1233.285 seconds.

The next execution uses `scripts/run_semantic_rejection_20261005.py` through
`scripts/launch_generation_diagnostics_20261005.py --semantic`, in tmux
`game24-semantic-rejection-20261005`. It shares the original 24-hour budget and
preserves all first-run outputs. Progress persists in `semantic_diagnostics.jsonl`;
the frozen probes, summary and report have the `semantic_` prefix.

Four discovery questions have reviewed endorsements of invalid repeated-number
constructions within 512 tokens: 434 (296), 956 (424), 1305 (420), 230 (260),
using zero-based token positions. Others remain missing, without replacement.
The candidates reject versus endorse the same construction on the identical
historical wrong-prefix context. Score is the difference of candidate sequence
log probabilities; per-token averages are also recorded. This measures construction
rejection, not successful construction discovery or natural generation accuracy.
Candidate length makes absolute margins uncalibrated; intervention effects use
within-question FULL comparisons. This corrected screen precedes any localization,
validation or additional behavioural generation.

Reviewed validation probes are frozen separately before observing intervention
effects: 44 (416), 1057 (435), 717 (505), 413 (300), 1112 (288). All other
validation questions remain missing for this diagnostic, without replacement.
The follow-up tmux session is `game24-semantic-localization-20261005`, launched
by `scripts/run_semantic_rejection_gpu4.sh`. It waits for the existing semantic
screen, exits without loading if the screen fails, otherwise resumes completed
requests and continues the following gates:

- Choose the larger positive discovery effect of VALUE_ZERO versus MASK; scan
  four layer groups using the reviewed rejection metric.
- Recursively split the best group into two collective subsets, comparing both
  with FULL. Stop splitting when neither improves or at most eight heads remain.
  Freeze the proper subset with the largest observed positive discovery mean.
  A positive singleton is never required. The frozen subset can contain more
  than eight heads; its claim is explicitly collective, a revision of the first
  run's singleton shortlist rule. No new mass/norm head shortlist is used.
- Content branch: bidirectional same-prefix donor patches must support forward
  improvement and reverse harm. Mask branch: compare local MASK and VALUE_ZERO.
- Validate the frozen subset on all available validation probes. Use one matched
  random set from its parent group, seed 20261005; overlap is allowed. Stop if
  the candidate mean is nonpositive or no better than this control.
- Only after validation: the original 24-generation bridge, optionally 48 under
  the original net-correctness and reduced-reuse rule. Behaviour records are in
  `semantic_behaviour/behaviour.jsonl`. Every stage shares the original budget.
Discovery IDs: 434, 144, 956, 754, 1305, 230, 1281, 339. Validation: 381, 1214,
1342, 1206, 509, 914, 44, 41, 1057, 195, 215, 717, 413, 1112, 395. Wrong
continuations are missing for 754, 1206, 41 and 195; no questions were replaced.

This implements the approved mechanism-first plan: Qwen3-8B Thinking, BF16,
one A100 (GPU4), at most 24 occupied GPU hours including loading and acceptance.
Waiting is excluded. No training, source generation, operator fitting, or UFT expansion.

## Entry points

- Prepare: `python scripts/run_generation_diagnostics_20261005.py --prepare`
- Monitor without GPU use: `python scripts/run_generation_diagnostics_20261005.py --status`
- A100 launch: `bash scripts/run_generation_diagnostics_gpu4.sh` in a tmux session.
- Resume only after resolving a failure: use the same launcher/output directory.
- Results: `outputs/generation-diagnostics-20261005/` (manifest, acceptance,
  diagnostics JSONL, frozen candidate, validation, behaviour JSONL, budget, report).

The launcher checks UUID, process ownership, resident command, active-job metadata,
and an idle interactive prompt. Only this project's resident may be stopped.
Other GPU4 work is left alone; the launcher waits. The resident is restored when
GPU4 is free after completion/failure. No scientific failure is automatically retried.

## Frozen protocol

Sort the completed 23 question IDs numerically, shuffle with Python seed 20261005,
use first 8 for discovery and the remaining 15 for validation. Historical behavioural
outcomes have already been observed. No intervention-based question selection.

Continuations are the first seed-ordered completed R0 correct / R2 substantively
incorrect outputs whose extracted expression passes the narrow exact-arithmetic audit.
Scalar-24 and unparseable wrong answers need manual judgement and are marked missing.
There is no replacement or replenishment. Original R2 token IDs and draft spans are reused.
Behaviour uses the same two historical seeds, sampling .6/.95/20, and 32768 minus prompt
length as the original generation budget. Official scoring follows upstream thinking removal.

## First-run computation and gates (superseded by the semantic follow-up above)

Prefill uses SDPA once per question; branches independently clone its cache. Decode
uses the installed HF eager function on one query. FULL, VALUE_ZERO (subtract draft
alpha-V without renormalization), and MASK (remove draft edges then recompute softmax)
share this backend. Interventions never affect the first prediction.

Acceptance on first two discovery questions: 32 tokens, unchanged first prediction,
zero blocked mass, cache independence under reversed order, identity intervention,
and contribution reconstruction (BF16 relative error < .02). Tiny-model regression
checks run on the A100 within the same budget. Local tests skip model checks.

Screen 128 tokens; record token likelihoods, draft mass, value norm, projected contribution
norm and reconstruction. An automatic candidate probe exists only at the first divergence
of the two existing continuations, where their preceding tokens are identical. It measures
lexical preference, not reasoning correctness. If all probes are at the unchanged first
prediction, correct-continuation negative NLL is the explicit fallback proxy.

If early proxies show no positive effect, stop. A single construction-probe pass may run
only when `probes.json` has reviewed probes keyed by discovery question ID; maximum 512
tokens. Probe fields: `index`, `preferred`, `alternative`, `semantic`, `reason`. Preferred
token must match that position in the correct continuation. Semantically reviewed probes
must explain why the alternatives differ in validity. No arbitrary trajectory alignment.

Follow one branch: VALUE_ZERO if it improves the chosen proxy, otherwise MASK. Scan
four contiguous layer groups, shortlist at most 8 heads by discovery retrieval mass/norm,
test their individual effects, and compare unions of the positive heads. This shortlist
limits search; it does not prove other heads are irrelevant. Freeze best union and strength 1.
Content branch adds bidirectional same-prefix head-output patching; redistribution branch
compares localized MASK and VALUE_ZERO. PATCH_MASK means global MASK plus selected
head replacement with the FULL donor, keeping the reverse experiment explicit.

Validate on remaining questions against FULL, global MASK and one seeded matched
random-head set from the selected layer group. Candidate is not reselected. Stop if its
mean improvement is nonpositive or no better than control. Report question bootstrap CIs
(5000 draws); these are exploratory gates, not a significance/novelty claim.

Bridge first four validation questions x two seeds x FULL/MASK/candidate = 24 outputs,
including missing-continuation questions. Rerun all conditions on the same backend.
Count truncation/unresolved in denominator. Expand only if candidate gives a net accuracy
gain and reduces normalized exact old-expression reuse, to the next four questions,
maximum 48 outputs. Reports include recoveries, harms, EOS, length and unresolved counts.

Budget persists across restarts. A wall-clock alarm and per-token checks enforce the
remaining budget; crashes conservatively add one heartbeat interval (30 seconds).
Outputs persist per request, and there are no retries or automatic scope expansion.

## Interpretation

Separate access effects, value-content effects, and local component effects. Fixed-prefix
likelihood and lexical margins do not establish natural reasoning correctness. Even a
validated harmful head ablation alone does not exceed *Overthinking the Truth*; a next
round needs a substantive reasoning/temporal prediction or useful/harmful information
separation. Low rank and operators remain optional future questions.
