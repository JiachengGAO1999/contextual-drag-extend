# Completed-result integration, 2026-09-25

The user requested integration of the newly completed outputs and an update of the current paper. All 64 scientific outputs were audited before inclusion; eight engineering probes are excluded. Previous manuscript and abstract are preserved alongside this memo. The title remains unchanged. This update changes the local manuscript and abstract, not any external submission record.

## Evidence and changes

- Primary Game24 Qwen3-8B coverage is now 23 questions, two seeds and four conditions: 184 outputs. R0/R2/R3/R4 = 40/18/36/35 out of 46. R3−R2 = +39.1 pp, question-cluster 95% interval [23.9, 54.3].
- Qwen3-32B and Gemma remain on the same shared 15 questions; MATH and correct-history data are unchanged. The matched eight-question correctness interaction remains unchanged and is not recomputed using unmatched questions.
- Updated abstract, introduction, design, results, main table, Figure 2, limitations, R4 table, generation diagnostics, and question-level appendix. Report experiments by task, model and condition, without independent/pilot tiers.
- Total manuscript evidence is 524 outputs on 39 distinct questions. Source hashes, counts, pairing checks and bootstrap estimates are in `runs/iclr2027_evidence_20260925_completed/`; the previous evidence directory remains a historical snapshot.

## Claim boundaries

The new eight questions alone give +25.0 pp [0.0, 43.8], weaker than the shared 15-question subset. The appendix reports this heterogeneity. Removing question 381 gives +38.6 pp [22.7, 54.5] across the remaining 22; removing it within the new eight gives +21.4 pp [−7.1, 42.9]. Its valid intermediate expression and invalid final selection are disclosed. All eligible complete candidates were used, but ten of 32 screening candidates remained incomplete after the runtime cutoff. Intervals describe the selected set and do not account for adaptive acquisition.

Unresolved and length-stopped outputs remain in denominators. There are 20 length stops across all manuscript outputs: 16 unresolved and four parsed incorrect. R4 is not reliably superior to R3. Blocking correct history can harm accuracy. The UFT external20 results remain in the full internal ledger, including their negative access effect; they are not pooled with the differently selected main study. No claim of universal benefit is made.

## Validation

Rebuilt evidence and Figure 2 from persisted scores, then ran the manuscript evidence audit: 524 records, input hashes, figure provenance, updated abstract numbers and length-stop accounting passed. The manuscript compilation and visual review are recorded in `build_review.md` after completion.
