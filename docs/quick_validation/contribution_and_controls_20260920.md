# Contribution audit and next controls — 2026-09-20

## Evidence boundary

The experiments do not uniformly support a general benefit of blocking. The seven-question dual-anchor pilot supports drag and whole-late recovery (12/14,4/14,12/14,10/14 for R0/R2/R3/R4). UFT external20 does not exhibit drag (36/40,39/40,34/40,40/40); late blocking hurts relative to R2. The first three complete mathematical questions show recovery but are an incomplete, ordered prefix, not the sixteen-question result. Do not infer a length effect from these comparisons: source model, task, difficulty, selection and draft construction all differ.

Latest server check: math retry3 has34/128 persisted, GPU4 running; new Game24 eight-question64-request experiment remains queued. This is a snapshot, not a final result. User-approved additional budget<=176; scheduled168. No new generation is authorized by this discussion beyond that existing queue.

## Reviewer objection: why not delete the distraction?

This is a valid objection. If the claim is merely that hiding known bad history improves solving, attention blocking alone is a weak methodological contribution. We already know which draft failed using external scoring; this does not constitute automatic error detection or an end-to-end agent reset policy. No efficiency advantage over deletion/reset has been measured.

The potentially useful contribution is a controlled behavioral intervention on continued access. R2 and R3 have identical token sequences and positions. R3 preserves full prefill and its first-token logits, then blocks generated queries from directly attending to draft keys. The prefill-produced states of unblocked suffix tokens remain available and can already contain draft information. Generated states can also carry mediated information. Thus, any recovery shows that cutting these particular direct access edges changes behavior despite retained prefill exposure; it does not show that all draft information has been erased or that we located an internal error representation.

Deleting the draft before prefill changes both initial exposure and subsequent access, typically token positions, and possibly the instruction wrapper. R3 differs experimentally even if final accuracy matches deletion. Whole path additionally blocks specified downstream prefill access to the draft; it preserves within-draft computation. It is not a clean separate manipulation of every possible mediation pathway. R3/R4 comparisons are timing diagnostics, not proof that one internal propagation mechanism has been identified.

Input identity is a control, not a standalone novelty claim. Novelty relative to the literature remains to be checked; this note does not establish that selective attention interventions themselves are new.

## Most informative next comparisons (proposed, not launched)

1. Complete frozen new Game24 and mathematical experiments. Report accuracy, paired transitions, question-cluster uncertainty, completion and parse failures, and source strata.
2. Compare failed-draft R2 and late-block against a deletion/reset condition. First inspect actual wrappers: existing R0 may already instantiate clean reset. If a matched-wrapper deletion produces exactly the same input as R0, reuse R0 rather than generate a redundant condition. Otherwise freeze a coherent wrapper; do not require reviewing a nonexistent draft. Report remaining instruction/position differences. R0 is a useful performance reference but may not by itself isolate wrapper changes.
3. Use existing correct drafts on the same frozen questions for full-access versus whole-late control. This tests failure-related specificity, but correct/failed traces may differ in length/style/content: report these differences and avoid calling it a perfectly matched semantic control. Select drafts without consulting intervention outcomes.
4. If feasible, evaluate a second target model on the same frozen questions, after backend correctness acceptance. Different draft-source models do not constitute different-target-model validation.

Possible outcomes: if correct and failed histories benefit similarly, a broad history/distraction account becomes more plausible. If failed histories recover while correct histories lose useful information, the selective behavioral role of access is better supported. Matching reset performance would be scientifically compatible with access-driven drag but would not establish a superior practical method. If new questions fail to reproduce, report heterogeneity and weaken the general claim rather than selecting responsive questions.

## Defensible paper scope

Candidate question: under what conditions does continued attention access to a failed same-problem trajectory contribute to contextual drag? A credible contribution would combine independent replication, an operational separation between prefill exposure and later access, appropriate controls, and documented failure boundaries. Do not promise a new broadly superior decoding algorithm, complete transmission-responsibility localization, universal recovery, or lower runtime cost. Additional benchmarks alone cannot replace the deletion and specificity comparisons.

Raw run locations and frozen selection details: [overnight report](night_validation_20260920.md). Generated corpora remain in ignored outputs directories, not in Git; this repository records protocols, audited summaries, reproducibility instructions and status snapshots.
