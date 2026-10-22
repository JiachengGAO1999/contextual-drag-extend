from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / 'docs/quick_validation/iclr2027_full_results_and_paper_map_20260925.md'
s = p.read_text(encoding='utf-8')
s = s.replace('不把 15 道 Game24 题拆成', '不把 Game24 题拆成').replace('runs/iclr2027_evidence_20260925/', 'runs/iclr2027_evidence_20260925_completed/')
s = s.replace('Game24 的 15 道题在三个目标模型上相同', 'Game24 的 Qwen3-8B 覆盖 23 道题，另外两个目标模型覆盖其中相同的 15 道题')
s = s.replace('| Qwen3-8B | 25/30 | 10/30 | 24/30 | 22/30 | +46.7 pp [26.7, 66.7] |', '| Qwen3-8B（23题） | 40/46 | 18/46 | 36/46 | 35/46 | +39.1 pp [23.9, 54.3] |')
s = s.replace('8B 的 R0−R2 为 +50.0 pp [33.3, 66.7]；R3−R2 为 16 次由错转对、2 次由对转错、8 次都对、4 次都错。', '8B 的 R0−R2 为 +47.8 pp [34.8, 60.9]；R3−R2 为 21 次由错转对、3 次由对转错、15 次都对、7 次都错。跨模型共同覆盖的 15 题上，8B 的 R3−R2 仍为 +46.7 pp [26.7, 66.7]。')
s = s.replace('−6.7 pp [−30.0, 13.3]', '−2.2 pp [−17.4, 13.0]').replace('117/120 次达到 EOS、2 次无法判分', '179/184 次达到 EOS、2 次无法判分').replace('上述 15 题中的 8 题', '上述 23 题中的 8 题')
s = s.replace('460 次生成：Game24 三模型 120+90+90', '524 次生成：Game24 三模型 184+90+90').replace('Game24 只有 15 道不同题', 'Game24 有 23 道不同题').replace('15 题中 ID 41', '23 题中 ID 41').replace('其余 14 题满足', '其余 22 题满足')
start = s.index('- 下一步 8 题、64 次')
end = s.index('\n\n## 论文叙事边界', start)
s = s[:start] + '''- 新增 8 题、64 次 Qwen3-8B 验证已于 2026-09-25 完成并纳入上述 23 题主表。R0/R2/R3/R4 为 15/8/12/13（各 16 次）；R3−R2 为 +25.0 pp [0.0, 43.8]，5 次改善、1 次伤害。64 条最终选式的精确算术和输入数字多重集复核均与保存评分一致；62 EOS、2 长度截断，截断保留分母。8 条工程探针不计入科学结果。首次启动失败未生成科学结果，重试输出完整。
- 题目 381 的草稿正文包含合法中间算式但最终选式错误，因此保留预先约定的排除敏感性分析：去除后 22 题的 R0/R2/R3/R4 为 38/17/34/33（各 44 次），R3−R2 为 +38.6 pp [22.7, 54.5]。新增部分去除 381 后仅 7 题，效应 +21.4 pp [−7.1, 42.9]，不能称为单独确证。
- 新增八题来自因耗时中断的筛题过程：32 个冻结候选中 22 个双模型采样完整，完整且合格的八题全部纳入；十个未完整候选没有补齐。此运行时间截断可能偏向较快的轨迹，不能把筛题写成全部完成。逐条审核、配对检查和来源见 [新增结果报告](batch03_validation_results_20260925.md) 与 [分析文件](../../runs/game24_batch03_validation_20260925_analysis/analysis.json)。
''' + s[end:]
p.write_text(s, encoding='utf-8')
p = root / 'texts/iclr-2027-style-files/iclr2027/DRAFT_CHECKLIST.md'
s = p.read_text(encoding='utf-8').replace('runs/iclr2027_evidence_20260925/', 'runs/iclr2027_evidence_20260925_completed/')
s = s.replace('Report the complete 15-question Game24 set as one sample, by target model and condition.', 'Report 23 Game24 questions for Qwen3-8B and the shared 15-question subset for the other targets, by target model and condition.')
s = s.replace('the 15-question Game24 table', 'the 23-question Game24 table (missing model coverage explicitly marked)')
s = s.replace('- [ ] When Batch03 validation finishes, audit its 64 outputs before deciding whether and how to add them. The current draft makes no claim based on that running experiment.', '- [x] Audit and include all 64 completed outputs; update the abstract, main table, Figure 2, diagnostics, and question-level appendix. Report completed-prefix coverage and the predeclared exclusion of question 381. See `texts/revisions/iclr2027_20260925_completed/revision_memo.md`.')
p.write_text(s, encoding='utf-8')
p = root / 'docs/RESEARCH_STATUS.md'
s = p.read_text(encoding='utf-8')
p.write_text('''**2026-09-25 — current completed evidence and manuscript:** All 64 additional Game24 outputs are complete and audited. The paper now covers 23 Qwen3-8B questions (R0/R2/R3/R4 = 40/18/36/35 of 46), with R3−R2 +39.1 pp [23.9, 54.3]; the other targets remain on the shared 15 questions. Total manuscript interventions: 524 outputs across 39 distinct questions. The new eight-question contrast and exclusion-of-381 sensitivity are disclosed. No independent/pilot split in the manuscript. [Current full ledger](quick_validation/iclr2027_full_results_and_paper_map_20260925.md), [completed evidence](../runs/iclr2027_evidence_20260925_completed/evidence.json). GPU4 resident was restored after completion; no new experiments launched during the paper update. Earlier entries below are historical and do not override this status.

''' + s, encoding='utf-8')
p = root / 'texts/revisions/iclr2027_20260925_completed/revision_memo.md'
p.write_text('''# Completed-result integration, 2026-09-25

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
''', encoding='utf-8')
print('Updated full ledger, checklist, research status, and revision memo.')
