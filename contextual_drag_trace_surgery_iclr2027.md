# ICLR 2027 研究方向建议：从 Contextual Drag 到 Trace-Level Causal Anatomy
> 历史方向讨论，随后局部结构干预未形成稳定主线。当前论文研究完整预填充后持续直接访问错误草稿的作用；现行结果和结论见 `docs/quick_validation/iclr2027_full_results_and_paper_map_20260925.md`。

## 1. 总体判断

如果目标是：

1. 尽量直接 follow up **Contextual Drag: How Errors in the Context Affect LLM Reasoning**；
2. 尽量复用原论文的任务、失败 trace、evaluation 和 TED 管线；
3. 在较短时间内形成一篇具有 ICLR 水准潜力的工作；
4. 避免被质疑成 prompt engineering 或重新搭建复杂 framework；

那么当前最合适的路线不是强行把问题改造成 multi-turn conversation，而是：

> **继续留在 Contextual Drag 原本的 failed-draft-in-context 设定中，进一步研究错误 reasoning trace 中到底哪些部分真正造成 contextual drag。**

推荐主线：

# **Causal Anatomy of Contextual Drag**
## Localizing and Intervening on Error-Carrying Structure in Failed Reasoning

核心问题从：

> failed reasoning trace 会不会影响后续 reasoning？

推进到：

> **failed reasoning trace 中究竟什么部分在造成这种影响？**

---

## 2. 为什么不建议把 multi-turn 作为主框架

Contextual Drag 原论文的核心形式是：

\[
Q + E ightarrow R
\]

其中：

- \(Q\)：目标问题；
- \(E\)：一个 prior failed reasoning draft；
- \(R\)：模型在看到这个 draft 后重新生成的 reasoning。

原论文已经证明：

- 错误 draft 会显著降低后续正确率；
- 即使模型被明确告知 draft 错误，drag 仍然存在；
- 后续 reasoning 在结构上会继承错误 draft，TED 更接近失败轨迹。

真正自然的 follow-up 是：

> **错误 trace 为什么会产生这种 drag？**

如果现在把框架改成：

\[
Eightarrow H_1ightarrow H_2ightarrow Q
\]

就会同时引入：

- role label；
- chat template；
- turn boundary；
- target repetition；
- context distance；
- intermediate generated content；
- multi-turn interaction structure。

为了控制这些变量，又必须增加 static-to-multiturn bridge、token-matched filler、segmented filler、live vs replay、correction timing 等额外设计。

结果是：为了研究 multi-turn，重新搭起了一套比原论文复杂很多的新 framework。这与“尽量 follow up Contextual Drag，而不是重新搭框架”的目标相冲突。

因此：

> **multi-turn 不应成为主实验的必要条件。**

---

## 3. 博士方向也不必被形式上的“多轮”限制

研究主线可以更一般地定义为：

\[
oxed{	ext{prior reasoning context}ightarrow	ext{subsequent reasoning reliability}}
\]

或者：

> **How prior reasoning context shapes subsequent reasoning, and how that influence can be controlled.**

不同论文可以分别研究：

- multi-turn conversation history；
- failed reasoning drafts；
- intra-CoT abandoned branches；
- agent memory；
- compressed reasoning state；
- verified / unverified reasoning context。

真正共享的问题是：

> **过去的 reasoning 如何影响现在的 reasoning。**

而不是每篇论文都必须是：

\[
turn_1ightarrow turn_2ightarrow turn_3.
\]

---

## 4. 推荐的新核心问题

# **Where Does Contextual Drag Come From?**

Contextual Drag 已经建立：

\[
E_{	ext{failed}}ightarrow	ext{downstream performance drop}.
\]

但它没有回答：

> **失败 reasoning trace 中到底是哪一部分产生 drag？**

一个失败 trace 可以写成：

\[
E=(s_1,s_2,s_3,s_4,s_5)
\]

其中：

- \(s_1,s_2\)：正确 reasoning prefix；
- \(s_3\)：first erroneous step；
- \(s_4,s_5\)：基于错误继续生成的 coherent downstream reasoning。

核心问题包括：

### RQ1
**Drag 是由错误最终答案造成，还是由 reasoning trajectory 造成？**

### RQ2
**第一处错误本身是否已经足够制造 drag？**

### RQ3
**错误之后的 coherent continuation 是否会放大 drag？**

### RQ4
**只修复第一处错误，是否足以消除后续影响？**

### RQ5
**原论文观察到的 structural inheritance 是相关现象，还是可以通过结构性 intervention 改变？**

---

## 5. 核心方法：Trace Surgery

对同一条 failed reasoning trace 做受控“手术”，而不是重新设计 prompt framework。

假设：

\[
E=(s_1,s_2,\color{red}{s_3},s_4,s_5)
\]

构造以下条件：

| Condition | Context 中保留的内容 | 回答的问题 |
|---|---|---|
| Full Failed | \(s_1,s_2,\color{red}{s_3},s_4,s_5\) | 原始 contextual drag |
| Correct Prefix | \(s_1,s_2\) | 正确部分本身是否有帮助 |
| First-Error Truncated | \(s_1,s_2,\color{red}{s_3}\) | first error 是否已经足够产生 drag |
| Error Descendants | \(\color{red}{s_3},s_4,s_5\) | 错误及其后续结构能否独立产生 drag |
| Wrong Answer Only | final wrong answer | 排除简单 answer anchoring |
| Remove First Error | \(s_1,s_2,s_4,s_5\) | drag 是否分布在整条 downstream structure |
| Minimal Repair | \(s_1,s_2,\color{green}{s'_3},s_4,s_5\) | 修复第一处 causal error 是否足够 |
| Remove Error Descendants | \(s_1,s_2\) 或 repaired continuation | 去掉错误后续结构是否恢复 |

这些 intervention 的目的不是寻找最好 prompt，而是：

> **定位 failed trace 中真正承载 contextual drag 的部分。**

---

## 6. 最重要的核心假设

最值得验证的 hypothesis 是：

> **Contextual drag 的主要来源可能不是“一个错误事实”本身，而是错误被继续发展成 coherent reasoning trajectory 后形成的 structural commitment。**

例如：

\[
Drag(	ext{first error only}) \ll Drag(	ext{full failed chain})
\]

如果出现这种结果，则说明：

> 一个 isolated error 并不一定非常危险；真正危险的是模型在错误基础上继续形成完整、连贯、结构化的 reasoning chain。

这可以自然解释：

1. 为什么明确告诉模型 draft 错了仍然无法完全恢复；
2. 为什么新的 reasoning 在 TED 上仍然继承原失败结构。

因为：

> **error awareness 解决的是“模型知道它错了没有”；**
>
> **contextual drag 可能来自已经形成的 reasoning structure 本身。**

---

## 7. 可能非常强的 finding：Error Correction ≠ Context Correction

假设：

\[
E=[s_1,s_2,\color{red}{s_3},s_4,s_5]
\]

只把 first error 修正：

\[
s_3ightarrow s'_3
\]

但保留原来基于错误形成的 downstream continuation \(s_4,s_5\)。

如果 contextual drag 仍然明显存在，就可以得到：

> **Repairing the originating error is insufficient once its downstream consequences remain in context.**

即：

\[
oxed{	ext{error correction}
eq	ext{context correction}}
\]

这能进一步解释为什么 explicit correction / successful verification 并不等于真正 reset reasoning。

---

## 8. 从 TED correlation 推进到 structural intervention

Contextual Drag 原论文用 Tree Edit Distance 说明：

> 后续 reasoning 在结构上更接近 failed draft。

但 TED 在原论文中主要是 descriptive evidence。

自然的 follow-up 是：

> **这种结构相似性只是相关，还是结构本身真的参与造成 drag？**

可以进一步构造：

### Structure-preserving intervention
尽量保留错误 trace 的 reasoning skeleton，同时修正局部语义。

### Structure-breaking intervention
保留类似信息量，但重组 reasoning path，使结构显著不同。

如果 structure-preserving repaired trace 仍产生较强 drag，而 structure-breaking trace 明显减弱 drag，则可以开始支持：

> **structural organization itself contributes to contextual drag.**

也就是从：

\[
	ext{structural correlation}
\]

推进到：

\[
	ext{structural intervention}.
\]

---

## 9. 为什么 Game of 24 特别适合

Game of 24 天生可以映射成 arithmetic tree，因此特别适合做：

- first incorrect operation；
- error descendants；
- subtree removal；
- structure-preserving repair；
- alternative correct structure；
- TED。

因此 Game of 24 可以承担：

> **mechanistic / structural testbed**

第二个任务则负责验证结论是否不限于 arithmetic-tree reasoning。

---

## 10. 第二任务建议

AIME24 可以保留用于：

- faithful reproduction；
- prompt/evaluator sanity check；
- 快速验证原论文 Direct → 1F drag。

但它不适合作为扩展论文的主要第二任务，因为 hard subset 太小。

更适合作为正式第二任务的是：

## **CRUXEval-I**

理由：

- target 数量更足；
- 属于 code reasoning，和 Game of 24 domain 差异明显；
- 已在 Contextual Drag 原论文中使用；
- 可以继续复用原论文的 failed/correct draft construction。

正式论文可以形成：

- **Game of 24**：结构机制主分析 + TED；
- **CRUXEval-I**：跨任务 generalization。

---

## 11. 与已有工作的区别

### Contextual Drag
回答：

> Failed reasoning context 是否会拖累后续 reasoning？

你的工作回答：

> **Failed reasoning context 中到底哪些部分在制造 drag？**

关系是：

\[
	ext{phenomenon discovery}ightarrow	ext{causal decomposition}.
\]

### Error Localization / Self-Correction
已有工作更多研究：

> 模型能不能找到第一处错误并回退修正？

这里研究的是：

> **一个已经失败的 reasoning trace 作为 context 时，第一处错误及其 downstream descendants 分别对下一次 generation 造成多少影响？**

---

## 12. 推荐的主实验结构

### Phase A — Faithful Reproduction

复现：

- Direct；
- 1F；
- external error signal；
- Game of 24 TED。

目的：

> 确认官方 pipeline 和模型环境工作正常。

### Phase B — Trace Localization

主条件：

1. Direct
2. Full Failed
3. Wrong Answer Only
4. Correct Prefix
5. First-Error Truncated
6. Error + Descendants / post-error continuation

核心问题：

> contextual drag 是否集中在特定 trace region？

### Phase C — Counterfactual Repair

重点比较：

1. Full Failed
2. First-Error Repair
3. Remove Error Descendants
4. Full Correct Trace

核心问题：

> **What must actually be repaired to eliminate contextual drag?**

### Phase D — Structural Intervention

仅在 Phase B/C 结果支持后进行：

- structure-preserving repair；
- structure-breaking repair；
- TED 与 accuracy 联合分析。

### Phase E — Cross-Task / Cross-Model Confirmation

在：

- Game of 24；
- CRUXEval-I；

上使用多个模型确认最核心的 2–3 个 contrast。

不需要把所有 exploratory 条件都扩展到全部模型。

---

## 13. Multi-turn 应该放在哪里？

multi-turn 仍然有价值，但不应成为论文主 framework。

更合理的是把它放到最后做：

## External Validity / Generalization

例如只挑最核心的两个 context：

\[
E_{	ext{full}}
\]

vs.

\[
E_{	ext{surgically repaired}}
\]

把它们改造成真实 previous assistant history，再测试：

> trace-level mechanism 是否还能泛化到 conversational history？

这样 multi-turn 回答的是：

> **原本在 external draft setting 中发现的机制，是否也存在于真实 conversation history？**

而不是重新定义整篇论文。

---

## 14. Intra-CoT 是另一个自然后续

Contextual Drag 原文还明确提出：

> extended CoT 中 abandoned hypotheses / failed intermediate branches 是否会对后续 exploration 产生类似 drag？

因此如果 trace surgery 主结果成立，可以进一步做一个小型 secondary study：

\[
	ext{external failed draft}ightarrow	ext{intra-CoT failed branch}
\]

问：

> 同样的 error-descendant mechanism 是否也存在于单次长 reasoning trajectory 内？

这比强行做 full multi-turn framework 更直接继承原论文的 future-work 方向。

---

## 15. 什么结果可以形成强 paper story

理想结果包括：

1. Wrong final answer alone 只能解释很小部分 drag；
2. First error 本身造成部分 drag，但明显弱于完整 failed chain；
3. Post-error coherent continuation 显著放大 contextual drag；
4. 只修 first error 不足以恢复，必须删除或重写 error descendants；
5. Accuracy recovery 与 structural recovery 同步，或出现有意义的 dissociation。

如果能稳定得到其中 3 个左右，paper story 可以是：

> Contextual Drag established that failed reasoning traces bias subsequent reasoning. We show that this influence is not uniformly distributed across a failed trace. The originating error explains only part of the effect; coherent reasoning built downstream of that error amplifies and preserves the bias. Counterfactual trace interventions further show that correcting the first error alone is insufficient when its descendants remain in context, revealing a distinction between error correction and context correction.

---

## 16. 为什么这比当前 multi-turn persistence 方案更适合 ICLR 2027

| 维度 | Trace Surgery | Multi-turn Persistence |
|---|---:|---:|
| 与 Contextual Drag 的直接性 | ★★★★★ | ★★★ |
| 新颖性潜力 | ★★★★★ | ★★★★ |
| 复用官方 pipeline | ★★★★★ | ★★★ |
| 新 framework 工作量 | ★★ | ★★★★★ |
| role/template confound | 低 | 高 |
| prompt-work 风险 | 低–中 | 中 |
| 三周可执行性 | ★★★★☆ | ★★☆ |
| 机制贡献潜力 | 高 | 中高 |

当前排序建议：

1. **Trace-level causal anatomy / surgery**
2. Intra-CoT contextual drag
3. Multi-turn persistence decomposition

---

## 17. 推荐标题

首选：

# **From First Error to Persistent Bias**
### Localizing the Sources of Contextual Drag in LLM Reasoning

备选：

# **The Causal Anatomy of Contextual Drag**
### Which Parts of Failed Reasoning Bias Subsequent Reasoning?

如果结果支持 error descendants：

# **Errors Leave Descendants**
### Why Correcting the First Mistake Does Not Eliminate Contextual Drag

---

## 18. 一句话研究定位

> **Contextual Drag showed that failed reasoning traces bias subsequent reasoning. This work asks which parts of those traces actually carry the bias, using controlled trace-level interventions to distinguish the originating error from the coherent reasoning built downstream of it.**

---

## 19. 最终建议

当前不应为了延续此前的 multi-turn 形式而强行把新工作设计成多轮对话。

更合适的路线是：

\[
oxed{
	ext{Contextual Drag}
ightarrow
	ext{Trace Localization}
ightarrow
	ext{Counterfactual Repair}
ightarrow
	ext{Structural Intervention}
}
\]

主论文继续严格依赖 Contextual Drag 的原始 testbed。

multi-turn 只作为：

\[
oxed{	ext{secondary external-validity experiment}}
\]

这样既最大化和原论文的连续性，又避免为了形式上的多轮研究重新搭建复杂 framework，同时更有机会把论文从：

> “又发现一个 context effect”

推进成：

> **“解释 contextual drag 的组成与机制，并通过 intervention 证明哪些 reasoning structure 真正承载这种影响。”**
