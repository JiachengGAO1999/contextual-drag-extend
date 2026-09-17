# Fixed-draft R0–R4 validation: 2026-09-09 analysis

Source: `outputs/game24-qwen3-8b-thinking-fixed-r0-r4-20260908`. Normal completion marker verified. Three fixed problems, one generation per condition, 15 outputs; generation loop 3142.74 s (52m23s), plus model loading. Full raw artifacts and log synced locally. Paper Thinking sampling unchanged.

| Problem | Fixed draft | R0 | R1 | R2 | R3 | R4 |
|---|---|---|---|---|---|---|
|1189|1189/3|correct|wrong|wrong|wrong|correct|
|1358|1358/0|correct|wrong|wrong|wrong|wrong|
|804|804/1|correct|wrong|correct|wrong|wrong|
|Accuracy||100%|0%|33.3%|0%|33.3%|

All conditions: official score parse rate 100%, EOS completion 100%; no length truncation. Parse rate means a non-null official correctness result, not that the final expression satisfies the output contract. A boxed scalar 24 is parsed but fails Game24 number-use requirements.

| Effect | pp | Paired bootstrap 95% CI (pp) | Wrong→correct / correct→wrong (right-hand condition → left-hand condition) |
|---|---:|---|---|
|R0−R1|100|[100,100]|3 / 0|
|R0−R2|66.7|[0,100]|2 / 0|
|R3−R2|−33.3|[−100,0]|0 / 1|
|R4−R3|33.3|[0,100]|1 / 0|
|R4−R2|0|[−100,100]|1 / 1|

Problem-level paired percentile bootstrap: 10,000 resamples, seed 2027. With only three selected problems and one sample per condition, these intervals do not capture seed uncertainty or pool selection uncertainty. The degenerate [100,100] interval reflects three identical observed differences, not population certainty.

Recovery ratios: late −0.5; path 0. Ratio CIs omitted because bootstrap residual denominators can equal zero.

## Output-level audit

- 1189: R1 and R2 reproduce the invalid draft expression using four 12s instead of three. R3 also uses four 12s in its body and boxes scalar 24, so its failure is not format-only. R4 produces the valid `12*12-12*10` expression.
- 1358: R1/R2 identify repeated 7 yet return the same invalid draft expression. R3 constructs a different invalid expression that repeats 3. R4 repeats 7. Seeing the same expression after path blocking does not establish draft transmission; it can arise independently from the problem/model tendencies.
- 804: R2 produces a valid final expression despite incorrectly defending the original draft in its critique. R3 gives the correct three-step construction of `12*10/(10-5)`; R4 explicitly writes that valid expression. Both box only scalar 24 and thus fail official scoring. Their official losses relative to R2 are format-only at the final-answer level, not evidence of worse solution reasoning.
- Blocking outputs often describe the draft as missing/incomplete. This is compatible with blocked access, and illustrates that the retained critique prompt differs from R0 even when draft access is blocked. It is not evidence by itself of mask failure.

As a post-hoc diagnostic only, treating 804 R3/R4 as body-solution successes yields counts R0–R4 = 3,0,1,1,2. It removes the negative late difference and gives a +1/3 path difference vs R2. This is not the official benchmark score or a prespecified endpoint; do not replace the official result or assert recovery on this basis.

## Intervention checks

All three persisted R2–R4 bundles have identical input token sequences and matching recorded prompt/token hashes and per-problem seeds; single shared prompt text, no boundary spillover. Absolute positions remain implicit and unchanged under the existing backend. All three R2/R3 first-token assertions pass (151667). The run's actual attention sanity check covers the first pair, 36 layers: late/path blocked attention maximum 0; path postdraft logits change after draft-token mutation 0. Do not generalize the measured attention check as having been run separately for all pairs. R3 retains full-prefill first-token logits; logical attention blocking only.

## Decision

The sampled problems show contextual and residual drag in official scores; insufficient residual drag is not this batch's bottleneck. Official results do not demonstrate late recovery or net path recovery. However, the apparent late degradation is entirely one format-only outcome, and path's zero net effect combines a real recovery with a format-only loss.

Hold formal scaling and transmission-responsibility decomposition. Continue bounded validation rather than declare the claim falsified: retain these fixed drafts and official scoring, repeat with independent paired seeds, and record body-correct/boxed-format-only failures as a separate diagnostic. Do not silently modify prompts, scoring, or intervention semantics. No follow-up run launched in this analysis turn.
