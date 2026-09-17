# Independent-solve control: result

Completed normally, 12 outputs, generation loop 3994.33s (66m34s). Raw run and log synced locally to outputs/game24-independent-control-20260910. HF residency restored, PID776658, tmux qwen3-control-gpu4. No new evaluation launched.

| Problem | R0 | R2 | R3 | R4 |
|---|---|---|---|---|
|1189|wrong|wrong|wrong|correct|
|1358|wrong|wrong|wrong|wrong|
|804|correct|wrong|correct|correct|
|Accuracy|1/3|0/3|1/3|2/3|

All score parse and EOS completion rates100%. R1 not run. Official metrics unchanged. Residual R0−R2 +33.3pp; late R3−R2 +33.3pp; extra path R4−R3 +33.3pp; net path R4−R2 +66.7pp. Problem-paired percentile bootstrap 10,000 resamples gives [0,100]pp for each contrast. Right-to-left wrong→correct/correct→wrong counts respectively 1/0,1/0,1/0,2/0. Recovery ratios1 and2; CIs omitted due to zero bootstrap denominators. Ratio2 reflects low observed R0 and R4 exceeding it; not a bounded fraction or evidence of 200% mechanistic recovery.

Final-response audit: 1189 R0/R2/R3 all use four12s rather than three; R4 valid12*12−12*10. 1358 all conditions violate number-use constraints (repeated7 or3); R0 independently generates the same error family. 804 R2 reproduces original repeated10 expression, while R0/R3/R4 give valid12*10/(10−5). No boxed-scalar-only failures in this batch. Correct final answers do not mean every exploratory statement is correct (e.g.804 R4 includes erroneous trial equalities before valid final solution).

R3/R4 final bodies no longer describe missing/incomplete drafts in the way observed under critique prompts; no full Thinking-level absence claim. First-pair36-layer attention sanity: late/path blocked probability0, path postdraft logits change under draft mutation0; same original R3 first-token boundary. Three R2/R3 first-token assertions passed through normal runner completion.

Decision: positive exploratory direction R4>R3>R2 in this new setting; warrants bounded replication under frozen prompts, not formal scaling or attribution yet. Only three problems and one seed per condition. R0 fell from3/3 in the initial old-prompt sample to1/3 with new prompt at the same seed base, indicating substantial prompt/sampling sensitivity. New framing and explicit boxed-expression instruction changed together; cannot uniquely attribute improvement to removal of critique mismatch. Keep separate from original four-seed results. Prior full repeated-output audit still pending.
