# ICLR 2027 draft checklist

This file is an editorial checklist, outside the submission PDF. The active evidence ledger is `docs/quick_validation/iclr2027_full_results_and_paper_map_20260925.md`; reproducible counts and source hashes are in `runs/iclr2027_evidence_20260925_completed/evidence.json`.

## Completed in the current draft

- [x] Apply the Astra revision instructions; record abstract changes, claim audit, and future experiment priorities in `texts/revisions/iclr2027_20260925/revision_memo.md`.
- [x] Add the six-contrast access-effect figure and the complete generation-diagnostics appendix from persisted evidence, without changing scores.

- [x] Report 23 Game24 questions for Qwen3-8B and the shared 15-question subset for the other targets, by target model and condition. Do not label collection batches as separate evidentiary tiers in the paper.
- [x] Report Qwen3-8B, Qwen3-32B, and Gemma 4 E4B within-model contrasts and question-cluster intervals.
- [x] Report the 16-question MATH evaluation by source/draft-model group, including EOS, length, and unresolved outcomes.
- [x] Report the eight-question correct-history comparison and its paired interaction.
- [x] Generate and include the 23-question Game24 table (missing model coverage explicitly marked) directly from persisted scores.
- [x] State the reset-to-R0 prompt-equivalence audit, precise access semantics, acquisition exception for Game24 question 41, and limits of the selected sample.
- [x] Remove result placeholders; compile the LaTeX and bibliography with the ICLR style; inspect representative PDF pages.
- [x] Keep UFT external20 in the internal ledger, outside manuscript empirical claims under the current project decision.

## Needed before submission

- [ ] Add an anonymous public artifact URL and verify release rights for benchmark examples and model responses.
- [x] Prepare complete MATH question-level and seed-level tables in the anonymous supplementary artifact, with prompt/input hashes and source-record manifests (`supplementary/analysis/` and `supplementary/evidence_manifest/`). CPU reconstruction from all 524 records completed. Uploading `supplementary_code.zip` remains a submission action.
- [ ] Inspect all PDF pages, table width, figure legibility, and anonymous metadata; confirm the main text meets the venue's current page rules.
- [ ] Recheck citations and the official ICLR 2027 requirements close to submission.
- [ ] Obtain the submitting authors' review of the AI-use wording, CRediT roles, funding, conflicts, and acknowledgments.
- [x] Audit and include all 64 completed outputs; update the abstract, main table, Figure 2, diagnostics, and question-level appendix. Report completed-prefix coverage and the predeclared exclusion of question 381. See `texts/revisions/iclr2027_20260925_completed/revision_memo.md`.
