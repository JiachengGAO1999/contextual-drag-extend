# ICLR 2027 定稿修订记录

日期：2026-09-25。修订基于当前 23 题稿件及已保存输出，没有新增生成或重评分，也没有重构研究问题、方法或 Results 顺序。

## 风格复用与篇幅

参考 `D:\Learning\PhD\Research\cot-server\docs\EMNLP写作风格拆解与ICLR2027复用指南.md` 和匿名 EMNLP 稿件。沿用其段落习惯：段首给出问题或发现，接着交代比较设计与指标，再给数值，最后限定解释范围；Results 先放主结果，再报告跨模型、正确历史和 MATH 等次级证据；图表后保留正文解释；Discussion、Conclusion、Limitations 分工明确。

当前稿有三幅主文图（干预示意图、聚合效应 forest plot、Qwen3-8B Game24 逐题配对结果）、三张主文表（条件定义、Game24、MATH），以及 Appendix E 的敏感性表。Figure 2 保留失败历史比较、正确历史对照和各自区间；新增 Figure 3 展示 23 道题上 R2/R3 的配对结果。对照正式发表论文后的结构调整及最新页码见文末。ICLR 2027 投稿主文上限为 9 页，参考文献与附录另计；官方说明见 [ICLR 2027 Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)。

## 修改段落 before / after

以下 before 片段在原文可准确恢复时逐字引用；标为“摘要”的条目概述旧写法而非逐字引文；新增段落标为“原无此段”。After 为最终稿对应表达，完整正文以 LaTeX 源文件为准。

### 1. 标题

**Before**

> After Error Feedback: Continued Access to Failed Reasoning Sustains Contextual Drag

**After**

> After Error Feedback: Continued Access to Failed Reasoning Contributes to Contextual Drag

### 2. Abstract

**Before（本轮要求修正的摘要表述）**

> Qwen3-32B and Gemma 4 E4B show positive effects on a shared 15-question subset; two MATH source groups show positive effects under longer reasoning.

**After（完整摘要）**

> When a failed reasoning trace remains in context, explicit feedback that its answer is wrong may not prevent it from influencing a new solution. Does this influence depend only on having processed the trace, or also on continued access during generation? We isolate continued direct access with a same-text attention intervention: the model processes the full prompt normally, but later generated queries cannot attend to the failed-draft keys. Across 23 Game24 questions and two seeds per question, Qwen3-8B accuracy is 40/46 without a draft, 18/46 with full access to a failed draft, and 36/46 when generation-time access is blocked. The paired access effect is +39.1 percentage points (95% question-cluster bootstrap interval: +23.9 to +54.3). Qwen3-32B and Gemma 4 E4B show positive point estimates on a shared 15-question subset; two MATH source groups show positive point estimates as a cross-task directional check under longer-form reasoning. On an eight-question correct-history control, blocking instead lowers accuracy from 16/16 to 13/16. These results identify continued direct access as an interventionally identifiable contributor to contextual drag after full initial exposure and explicit error feedback, while leaving open other information paths and the effects of imperfect error feedback.

### 3. Figure 1 图注

**Before（原时序表述）**

> Blocking begins with the query for \(y_1\), which predicts \(y_2\).

**After**

> Same-text intervention isolating continued access after full exposure. The prompt itself is unchanged. In R2, every generated query retains ordinary causal access to the known-wrong draft. In R3, the complete prompt is still processed with ordinary causal attention and \(y_1\) is sampled from the same full-prefill logits. Blocking begins only after \(y_1\) has been sampled from the shared full-prefill logits; the query at the \(y_1\) position, used to predict \(y_2\), is the first affected query. This and subsequent generated queries cannot directly attend to the failed-draft key–value positions. Dashed arrows and crosses denote the removed attention edges; access to the problem, error signal, and independent-solve instruction is preserved.

Figure 1 保留原图；复核确认 shared-logits / sampled-\(y_1\) 标签和干预边界可辨。Figure 2 保留原尺度、区间和 Gemma 触零区间，并保留失败历史与正确历史分隔线及行标签。

### 4. Game24 样本获取段

**Before（旧版叙事风险摘要，非逐字引文）**

题目获取说明较长，且前后批次的描述容易被读成“15 题开发 + 8 题确认”。

**After**

> We evaluate 23 distinct Game24 questions with Qwen3-8B, each with one failed draft and two paired seeds; Qwen3-32B and Gemma 4 E4B cover a shared 15-question subset. Candidate questions were screened with ordinary baseline generations from Qwen3-8B and Qwen3-32B. Eligibility required at least two completed, parseable, verified correct trajectories and two substantive incorrect trajectories in the pooled screening audit. One question, ID 41, was admitted under an earlier rule; the other 22 meet the final rule. Screening and intervention data were collected in successive batches, so the pooled analysis describes one selected set rather than a preregistered replication. Eight additional questions were obtained from the completed portion of a larger screening run that ended early for runtime reasons. All completed candidates satisfying the frozen eligibility rule were retained, and intervention outcomes were not used for selection. Draft text is the source model's visible final response; no private thinking trace is transferred. The frozen draft for a question is shared wherever multiple target models are evaluated.

主 Results 保持单一 23-question pooled analysis。早停带来的 shorter/faster screening trajectory 选择风险移至 Limitations。

### 5. 主效应与配对转移

**Before**

> R3 recovers 18 of the 22 net successes lost in R2 (81.8%, descriptively).

**After**

> The 39.1-point access effect [+23.9, +54.3] recovers most of the 47.8-point aggregate R0–R2 gap. Paired outcomes: 21 trials move from wrong to correct, three from correct to wrong, 15 remain correct, and seven remain wrong.

全文保留 R3 与 R0 相差 8.7 points、该区间不是等价性检验的说明；不声称完全恢复。

### 6. 新增 Related Work：多轮退化与先前尝试持续影响

**Before**

原无此主题段落。

**After**

> Recent work studies broader degradation as tasks unfold across dialogue turns. Laban et al. find that models can over-rely on early, sometimes incorrect answer attempts when instructions are revealed incrementally. Huang et al. document cases in which errors or other artifacts in an assistant's earlier responses persist into later turns, and evaluate context-filtering alternatives on real conversations. These studies establish that prior attempts can affect subsequent dialogue behavior, but their multi-turn settings change what information is available over time and, under filtering, what history is processed. We ask a narrower question in a controlled same-problem setting: given an externally identified failed trace and explicit error feedback, does continued direct access matter after the full trace has already been processed?

### 7. 新增 Related Work：Transformer 内部因果干预

**Before**

原无此主题段落。

**After**

> Causal tracing and activation patching intervene on internal activations to test which computations affect model outputs; path patching tests effects along selected edges in a model's computational graph. Recent work extends activation patching across generated positions to study temporally distributed effects in chain-of-thought reasoning. These methods typically exchange or perturb internal activations to localize components or pathways. Our intervention changes a different variable: it preserves the complete prompt, full prefill, and first-token computation while manipulating whether later generated queries retain direct attention access to a designated prompt span. Although implemented as an attention mask, this is not a context-pruning comparison: all conditions retain identical prompt tokens, positions, full prefill, and first-token computation; only later direct access differs. It does not patch internal activations or identify an internal representation of the error. The contribution is an access intervention that separates initial exposure from later direct accessibility in a controlled comparison.

### 8. Correct-history 标题

**Before**

> BLOCKING IS NOT GENERICALLY BENEFICIAL

**After**

> Blocking can harm correct history

该小节数字与 matched eight-question difference-in-differences 保持不变，正文仍说明它不单独识别 truth value。

### 9. MATH 定位

**Before（摘要措辞）**

> The MATH source groups show positive effects under longer reasoning.

**After**

> The MATH source groups show positive point estimates as a cross-task directional check under longer-form reasoning.

正文仍写明两来源组同时改变题目来源与 draft-source model，且受 termination imbalance 限制；不把 MATH 提升为与 Game24 同等级的主证据。

### 10. Limitations

**Before**

> Increasing distinct question coverage is more informative about that population than adding many seeds to the same questions.

**After**

> Broader coverage of independently selected questions is needed to characterize how the effect generalizes beyond this selected sample.

另补充：八道新增题来自因 runtime stop 未完成的较大 screening run 的已完成部分；该 cutoff 可能偏向较短或较快的 screening trajectories。没有隐去十个候选题未完成这一事实。

### 11. Appendix E：ID 41 敏感性和新增表

**Before**

> Appendix E did not report the exclusion sensitivity for question 41.

**After**

> Excluding question 41, which was admitted under an earlier rule, leaves 22 questions with R2/R3 accuracy of 16/44 and 34/44. The access effect is +40.9 points (95% question-cluster bootstrap interval: [+25.0, +56.8]), close to the pooled estimate. This confirms that the main conclusion does not depend on the single earlier-rule inclusion.

结果由冻结证据文件中保存的输出计算：22 questions、176 requests；R2 = 16/44，R3 = 34/44；R3−R2 = +18/44 = +40.9 pp；50,000 次题目聚类 percentile bootstrap，95% CI [+25.0,+56.8]。同 Appendix E 的 question 381 sensitivity 并列，新增 Table 8 对比 pooled、exclude 381、exclude 41 三行。

### 12. Reproducibility 与 Data Availability

**Before**

> An anonymous public artifact link can be added at submission.

**After**

> The paper specifies prompts, model and inference versions, random seeds, scoring rules, and implementation checks. The local evidence manifest records raw-file hashes and connects the reported summaries to persisted output records. R2–R4 bundles also preserve token IDs, spans, and hashes.

Data Availability 仅说明公开 benchmark 的许可/来源及模型权重标识，不声称未附上的匿名补充包已经准备好。检查后没有将不相关 ZIP 描述为本稿 artifact。

## 新增文献与 BibTeX

新增的两组文献只用于定位相关方向，不声称本文优先权。对应条目已经写入 `contextual_drag_continued_access.bib`。

```bibtex
@inproceedings{laban2026lostconversation,
  title        = {{LLMs} Get Lost in Multi-Turn Conversation},
  author       = {Laban, Philippe and Hayashi, Hiroaki and Zhou, Yingbo and Neville, Jennifer},
  booktitle    = {The Fourteenth International Conference on Learning Representations},
  year         = {2026},
  url          = {https://proceedings.iclr.cc/paper_files/paper/2026/hash/59f6421e64707225fdf5b28840679a07-Abstract-Conference.html}
}

@article{huang2026ownwords,
  title        = {Do {LLMs} Benefit From Their Own Words?},
  author       = {Huang, Jenny Y. and Choshen, Leshem and Sun, Wei and Khattab, Omar and {Fernandez Astudillo}, Ram{\'o}n and Damani, Mehul and Broderick, Tamara and Andreas, Jacob},
  journal      = {arXiv preprint arXiv:2602.24287},
  year         = {2026},
  doi          = {10.48550/arXiv.2602.24287},
  url          = {https://arxiv.org/abs/2602.24287v2}
}

@inproceedings{meng2022causaltracing,
  title        = {Locating and Editing Factual Associations in {GPT}},
  author       = {Meng, Kevin and Bau, David and Andonian, Alex and Belinkov, Yonatan},
  booktitle    = {Advances in Neural Information Processing Systems},
  volume       = {35},
  pages        = {17359--17372},
  year         = {2022},
  url          = {https://proceedings.neurips.cc/paper_files/paper/2022/hash/6f1d43d5a82a37e89b0665b33bf3a182-Abstract-Conference.html}
}

@article{goldowsky2023pathpatching,
  title        = {Localizing Model Behavior with Path Patching},
  author       = {Goldowsky-Dill, Nicholas and MacLeod, Chris and Sato, Lucas and Arora, Aryaman},
  journal      = {arXiv preprint arXiv:2304.05969},
  year         = {2023},
  doi          = {10.48550/arXiv.2304.05969},
  url          = {https://arxiv.org/abs/2304.05969}
}

@inproceedings{zhang2024activationpatching,
  title        = {Towards Best Practices of Activation Patching in Language Models: Metrics and Methods},
  author       = {Zhang, Fred and Nanda, Neel},
  booktitle    = {The Twelfth International Conference on Learning Representations},
  year         = {2024},
  url          = {https://openreview.net/forum?id=Hf17y6u9BC}
}

@article{dura2026sequentialpatching,
  title        = {Mechanistic Interpretability of Chain-of-Thought Reasoning via Sequential Activation Patching},
  author       = {Dura, Murat and {\"O}zt{\"u}rk, Serkan and Tekir, Selma},
  journal      = {arXiv preprint arXiv:2608.22332},
  year         = {2026},
  doi          = {10.48550/arXiv.2608.22332},
  url          = {https://arxiv.org/abs/2608.22332}
}
```

## 数字与提交检查

- Qwen3-8B Game24 主分析：23 道不同题；每个条件 46 个请求/试次（23 × 2 seeds）；R0/R2/R3 = 40/46、18/46、36/46；R3−R2 = +39.1 pp，95% CI [+23.9,+54.3]。
- 以上计数在 Abstract、Results、Table 2、Figure 2 provenance 和逐题 Appendix 中一致；新增 Figure 3 的 23 行与逐题 Appendix 表逐题核对一致。Qwen3-32B / Gemma 的共享子集仍为 15 题；不将它们误写成主分析 n。
- 整篇已有证据包含 524 条已完成模型输出，覆盖 39 道不同问题（23 Game24 + 16 MATH；正确历史控制重复使用其中 8 道 Game24 题）。这与主结果的 46 个配对试次是不同统计口径。
- ID 41 排除 sensitivity：22 题；R2 16/44、R3 34/44；+40.9 pp [+25.0,+56.8]。
- 当前 PDF 共 14 页；Conclusion 位于第 8 页，参考文献也从第 8 页开始（参考文献不计入主文页数），之后为附录。主文共 8 页。复编译无未解析 citation 或 overfull hbox；参考文献网址仍有模板常见的 underfull 行。
- 双盲：主文件继续使用匿名作者信息；摘要、标题和核心 claim 与全文一致。Data Availability 未承诺尚未附加的 artifact。保留必需的 AI-use statement；移除可选的 Ethics statement，相关部署风险仍在 Discussion 与 Limitations 中说明。

## 对照正式发表论文后的结构调整（2026-09-25）

参考文件为工作区根目录的 `42_Contextual_Drag_How_Errors_.pdf`。该文正文结束于第 8 页，参考文献从第 9 页开始，附录从第 12 页开始；37 页总长度主要来自附录，不能作为主文篇幅比较。其叙事顺序是：引言提出研究问题并用 Main Findings 映射后续证据；随后先给跨模型/任务的实证评估，再检验错误信号和缓解；最后安排 Related Work 与 Conclusion，细节及局限放在附录。

本稿据此改成单一研究问题、分段 Main Findings、合并的 Evaluation Setup 主节，以及独立的 Empirical Evaluation of Continued Access 主节。Results 六个证据点和数据顺序保留；Discussion 后移至 Related Work，再接 Limitations 与 Conclusion。实现验证等可复现细节压缩到主文并指向附录，避免方法说明占用过多篇幅。新增逐题 Figure 3 后，主文内容结束于第 9 页，保留三幅主文图和三张主文表；所有数值仍来自原有冻结证据，没有新增实验或扩大样本口径。

调整后的页码分配为：引言第 1–2 页，Evaluation Setup 第 3–4 页，实证结果第 5–7 页，Discussion/Related Work/Limitations/Conclusion 第 7–8 页；参考文献从第 8 页开始并不计入主文页数。主文共 8 页，低于 ICLR 2027 投稿版的 9 页上限。

## 新增逐题配对 Figure 3（2026-09-25）

Figure 3 展示冻结数据中 Qwen3-8B 在 Game24 的 23 道题上、R2（full access）与 R3（late access block）的正确 seed 数（每题 0–2）。每行对应一道题，横轴为正确 seed 数；相同题目的两种条件由细线连接。题目按 R2→R3 变化分组，组内按 question ID 升序排列。图中有 4 题从 0/2 提升到 2/2，11 题增加一个正确 seed，7 题不变，1 题下降；结果描述限于这组已选题目。

数据来自 `runs/iclr2027_evidence_20260925_completed/game24_per_question.csv`，并已逐行与保留的 Appendix 完整题目表核对；18/46 与 36/46 的聚合计数也和 evidence manifest 相符。未生成新样本。图表、源 CSV、生成脚本及来源哈希记录分别保存在 `texts/iclr-2027-style-files/iclr2027/figure3_question_level_recovery.pdf`、`.png`、`.csv`、`_provenance.json` 和 `scripts/plot_iclr2027_question_recovery_20260925.py`。静态修订审计已验证 23 行、Appendix 一致性、聚合总数与冻结输入哈希。
