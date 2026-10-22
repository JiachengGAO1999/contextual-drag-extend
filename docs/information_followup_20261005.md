# Random control and information separation

This follow-up keeps Qwen3-8B Thinking, BF16, GPU4, historical sampling and output
limits, the frozen 144-head VALUE_ZERO candidate, and the original cumulative
24 GPU-hour budget. No new source screening, models, training or head search.

Launch: `python scripts/launch_generation_diagnostics_20261005.py --information-followup`.
Tmux: `game24-random-and-information-20261005` on `sjtu-a100`.
Read-only progress: `python scripts/run_information_followup_20261005.py --status`.
All artifacts remain under `outputs/generation-diagnostics-20261005/`.

## First: natural-generation random control

The same eight validation questions and two historical seeds: exactly 16 new
outputs, condition CONTROL. Reuse the already frozen random heads from
`semantic_validation.json`, same count and parent layer group as the candidate;
do not draw another seed or tune the control. FULL/MASK/CANDIDATE reuse the
completed 48 outputs. Resume persists per request.

Gate, frozen before the new outputs: candidate question-mean correctness must
exceed CONTROL. Otherwise stop this follow-up without information-separation
GPU work. Structural old-expression reuse, gains/harms and output length are
descriptive checks, not additional arbitrary thresholds. Correctness has only
eight independent question clusters; intervals remain exploratory.

## Second: useful partial calculation plus invalid construction

Use the first four frozen discovery questions, without intervention-based
selection: 434, 144, 956, 754. Each has a reviewed partial result that can support
a valid full solution, and its original invalid draft construction. Useful work
is respectively `5*5=25`, `11+11=22`, `7+8=15`, `9+9=18`. Full reference solutions
are arithmetic-audited and stored only in metadata, never in the model prompt.

Two paired history variants hold useful work and the invalid expression fixed.
ENDORSED states a false number-use count and says the constraint is satisfied.
DIAGNOSED states the true repeated-number count and says it is violated. The
outer failure feedback and historical chat wrapper stay the same. Both retain
the old invalid final expression. Text is frozen in `information_materials.json`.

First measure FULL/MASK/CANDIDATE on two explicit, short, identical-prefix
queries: retrieval of the tagged verified calculation versus an untagged but
arithmetically valid alternative; actual operand count versus the false count.
These measure retrieval and counting, not full solution correctness. No attention
matrices are saved. All replays are below 512 tokens.

Gate before behaviour, fixed in advance: on ENDORSED histories, candidate must
improve true-count preference over FULL and useful-clue retrieval preference over
MASK. No signal: stop and report the absence of information-separation evidence.
Signal: 4 questions x 2 history variants x 2 seeds x 3 conditions = at most 48
new generations. Report correctness, structural old-expression reuse, harms,
termination, length, and correct answers containing the useful arithmetic subtree.

Clue-aligned answers do not prove causal use of history: models can independently
discover the same computation. MASK blocks direct generated-query access, while
shared prefill can encode draft information in other positions. This is a small
exploratory test of selectivity, not a demonstration that all history information
has been removed. The new task has hand-constructed histories, so transfer from
the historical trajectory probes is itself part of the test.

## Artifacts and stopping

- Frozen settings: `information_followup_config.json`, `information_materials.json`.
- Random outputs: `random_behaviour/behaviour.jsonl`, `random_generation_summary.json`.
- Probes: `information_probes.jsonl`, `information_probe_summary.json`.
- Mixed outputs: `information_behaviour/behaviour.jsonl`, `information_behaviour_summary.json`.
- Current state: `information_summary.json`; cumulative use: original `budget.json`.

Maximum 64 new generations across both stages. Stop at gates or the original
24-hour budget. No automatic retries or scope expansion. The launcher only
stops the authorized project's idle resident and restores it if GPU4 is free.
