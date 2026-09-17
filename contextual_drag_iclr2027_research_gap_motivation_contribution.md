# Contextual Drag 新方向：Research Gap、Motivation、Main Contribution 与 ICLR 2027 实验判据

## 0. 核心判断

当前这条线真正有 ICLR 2027 潜力的核心，不再只是 “trace surgery”，也不是 “selective attention mask”，而是一个更清楚的问题定义：

> **一个错误为什么会在已经被识别之后，仍然通过后续 computational state 影响下一次 reasoning？这种“传播责任”在 failed trace 内部如何分布？**

真正值得守住的概念边界是：

\[
\boxed{
\text{Failure Responsibility}
\neq
\text{Drag Transmission Responsibility}
}
\]

也就是说：

- **failure responsibility**：哪一步导致原 trajectory 最终做错；
- **drag transmission responsibility**：当这段 failed reasoning 被留在 context 中时，究竟哪些部分继续把错误影响传给下一次 reasoning。

这一区分是当前方案最重要、最可能成为论文主贡献的理论中心。

---

# 1. 现有研究地图

可以把邻近工作分成四条线，而不是逐篇论文机械比较。

| 研究线 | 已经解决的问题 | 尚未解决的问题 |
|---|---|---|
| **Contextual Drag** | failed reasoning 留在 context 中会使后续 reasoning 下降，并继承类似错误结构；即使提供 error signal / verification，也不能完全解决 | **failed trace 中什么东西真正把 drag 传递下去？** |
| **CausalFlow / REFLECT / TRI 等 trace attribution / repair** | 定位“原 trajectory 为什么失败”，找到错误 step 并修复 | **某一步导致原答案失败，不等于它也是最主要的 downstream contamination carrier** |
| **MEMENTO / KV management** | KV 可以承载过去 reasoning 的信息；即使原始 block 不再直接存在，信息仍可能经 cache 保留下来 | 没有专门研究 **已知错误 reasoning 的 harmful transmission attribution** |
| **multi-turn memory error propagation** | 错误可以沿 memory update 等路径跨轮传播 | 没有回答 **failed reasoning trace 内部的 source → descendant/cache carrier → subsequent solve** |

因此，以下几种 novelty 不够：

- “错误会传播”；
- “错误历史会影响后续 reasoning”；
- “mask bad context 有用”；
- “KV 会保留过去的信息”；
- “我们能定位 first error”。

这些方向都已有较近的工作覆盖。

真正尚可守住的空白是：

> **一次失败的 reasoning 作为后续 context 时，错误的“产生责任”和“传播责任”是否是两件不同的事，以及传播责任如何沿 descendant / cache state 分布。**

---

# 2. 真正的 Research Gap

## 2.1 Failure responsibility

已有错误定位工作通常问：

> 哪一个错误导致了原来的 reasoning trajectory 最终失败？

例如：

\[
s_1\rightarrow s_2\rightarrow \color{red}{s_3}\rightarrow s_4\rightarrow s_5
\]

如果 counterfactually 修复 \(s_3\) 后，原答案变正确，那么 \(s_3\) 具有高 failure responsibility。

这是传统 trace attribution / error localization 的问题。

---

## 2.2 Drag transmission responsibility

当前工作问的是另一个问题：

> 当整条 failed reasoning 被放进 context，模型重新 solve 时，**到底是哪部分历史 computation 在继续把 bias 传给新的 generation？**

答案未必是 \(s_3\)。

可能反而是：

\[
s_4,s_5
\]

因为它们已经把一个局部错误展开成一个：

- 连贯的；
- 结构化的；
- 内部自洽的；

错误 reasoning state。

于是有可能出现：

\[
\text{source of error}
\neq
\text{carrier of downstream influence}.
\]

这就是当前最值得追的 research gap。

---

# 3. 为什么 MEMENTO 是威胁，但也帮助我们澄清边界

MEMENTO 已经说明 reasoning information 可以通过至少两类 channel 保留：

\[
\text{textual representation}
\]

以及：

\[
\text{KV / downstream state}.
\]

因此不能把以下内容当成主要 novelty：

> “我们发现即使原始文本不再直接访问，过去的信息仍可通过 KV 留下。”

但 MEMENTO 的目标主要是：

\[
\text{context compression / efficiency / useful information preservation}.
\]

当前工作的目标是：

\[
\text{harmful failed context}
\rightarrow
\text{downstream error transmission}.
\]

更准确的区分应该是：

> **MEMENTO asks what information survives context compression.  
> We ask what erroneous computation remains behaviorally influential, where that influence is carried, and which access paths must be interrupted to stop contextual drag.**

这个差异是可以守住的。

---

# 4. Motivation 应该怎么写

## 4.1 第一层：现代 reasoning system 隐含假设“识别错误后即可继续利用 context”

典型 self-refinement：

\[
\text{draft}
\rightarrow
\text{recognize error}
\rightarrow
\text{try again}
\]

隐含假设：

> 模型只要知道 prior reasoning 错了，就能忽略它。

但 Contextual Drag 已经说明，这个假设并不总成立。

---

## 4.2 第二层：error recognition 不等于 computational disengagement

真正值得研究的是：

\[
\boxed{
\text{error recognition}
\neq
\text{computational disengagement}
}
\]

模型可能已经知道：

> “previous reasoning is wrong”

但错误 computation 仍然存在于：

- accessible context；
- KV state；
- downstream-derived contextual state；

之中。

因此它仍然可能参与新的 attention / generation computation。

这就是机制层面的核心 motivation。

---

## 4.3 第三层：现有 error localization 找的是“谁把上一题做错了”

传统工作问：

> 谁导致了上一条 reasoning 失败？

当前工作问：

> **谁还在污染下一次求解？**

这两个 responsibility 可能发生分离。

这是整篇论文最重要的 conceptual distinction。

---

## 4.4 第四层：full reset 太粗暴

如果直接 reset 全部历史：

\[
\text{harmful context}\downarrow
\]

但同时：

\[
\text{useful context}\downarrow.
\]

所以更有价值的问题是：

> **Can reliability-aware context control suppress harmful computation without discarding verified useful reasoning?**

这就自然导向 selective control，而不是简单 full reset。

---

# 5. 推荐的 Main Contributions

如果最终实验支持，正文最好只保留 3 个主贡献。

## Contribution 1 — A new attribution target

提出并 operationalize：

\[
\boxed{\text{Drag Transmission Responsibility (DTR)}}
\]

明确区分：

\[
\text{failure responsibility}
\]

和：

\[
\text{downstream transmission responsibility}.
\]

回答：

> failed reasoning 的哪些 components 实际参与了后续 contextual drag？

---

## Contribution 2 — Same-text causal access intervention

保持以下因素不变：

- same textual prompt；
- same tokens；
- same token positions；
- same error signal；
- same wrapper；

只改变：

\[
\boxed{\text{computational accessibility}}
\]

尤其区分：

### Late KV eviction

测试：

> 一个已有 KV region 作为**直接 carrier**的贡献。

### Path-complete blocking

测试：

> 一个 source span 经 direct + downstream paths 的**总传播影响**。

这种 decomposition 比普通 “删文本 / 改 prompt” 更接近机制性 intervention。

---

## Contribution 3 — Structural finding + control implication

理想结果是：

> **Drag is not concentrated at the originating error. Error-dependent descendants and downstream cache states carry a substantial fraction of its downstream influence.**

并进一步证明：

> oracle selective reset 可以在阻断 failed context harm 的同时保留 verified context utility。

注意：

**selective reset 本身不应成为 headline novelty。**

它更适合作为：

> 对 mechanism finding 的 functional validation。

---

# 6. 最关键的实验趋势

## 6.1 第一组：Recognition vs Computational Accessibility

定义：

- \(R0\)：Direct
- \(R1\)：failed draft，full access
- \(R2\)：failed draft + explicit error signal
- \(R3\)：same text + error signal + whole-draft late eviction
- \(R4\)：path-complete block

首先应复现：

\[
R0 > R1
\]

即 contextual drag 存在。

然后最好看到：

\[
R2 > R1
\]

但：

\[
R2 < R0
\]

说明：

> error recognition 有帮助，但不足以彻底恢复。

真正关键的是：

\[
\boxed{
R3 > R2
}
\]

这意味着：

> 在错误已经被显式识别的情况下，仅仅改变其 computational accessibility，就还能继续恢复性能。

它直接支持：

\[
\boxed{
\text{recognition}\neq\text{disengagement}
}
\]

---

## 6.2 更强结果：R4 > R3

理想情况：

\[
\boxed{
R0 \approx R4 > R3 > R2 > R1
}
\]

解释：

### \(R1 \rightarrow R2\)

告诉模型错误存在，有一定帮助。

### \(R2 \rightarrow R3\)

禁止 generation 直接访问 bad KV，又恢复一部分。

### \(R3 \rightarrow R4\)

把 bad information 已进入 downstream state 的间接路径也切掉，进一步恢复。

于是形成完整机制链：

\[
\text{Error recognition}
\]

\[
\downarrow
\]

\[
\text{Direct computational disengagement}
\]

\[
\downarrow
\]

\[
\text{Downstream-mediated disengagement}
\]

如果稳定出现：

\[
\boxed{
R4 > R3
}
\]

论文的机制性会显著增强。

---

# 7. 第二个关键趋势：first error 不能解释全部 drag

把 failed trace 划成：

\[
P | E | D | A
\]

其中：

- \(P\)：verified prefix
- \(E\)：first error
- \(D\)：error-dependent descendants
- \(A\)：wrong answer

最有价值的趋势是：

\[
\Delta_E > 0
\]

但同时：

\[
\boxed{
\Delta_D > \Delta_E
}
\]

或者至少：

\[
\Delta_D
\]

提供一个清楚、稳定、显著的额外 effect。

理想的 incremental harm：

\[
\boxed{
\text{descendant increment}
>
\text{first-error increment}
>
\text{answer increment}
}
\]

不一定必须严格满足这个排序，但需要证明：

> wrong final answer anchoring 不能解释 contextual drag，first error 也不能解释全部 effect。

---

# 8. 更漂亮的结果：Source–Carrier Dissociation

非常值得追的现象是：

### 直接 block first-error token

恢复很小。

### Path-complete block first error

恢复明显。

这意味着：

> first error 作为原始 source 很重要，但它的影响已经被 descendants / downstream state 携带走。

可以表示为：

\[
\boxed{
\text{small direct-carrier DTR}
+
\text{large source-level DTR}
}
\]

对应一个很强的 finding：

> **The originating error and the states that carry its downstream influence need not coincide.**

这是最有可能形成 “aha” 的机制结果之一。

---

# 9. Selective Reset 最理想的趋势

一定要同时做：

\[
Failed\ History
\]

和：

\[
Correct\ History.
\]

理想结果：

| Policy | Failed context | Correct context |
|---|---:|---:|
| Full Access | 差 | 好 |
| Full Reset | 好 | 差一些 |
| Selective Reset | 接近 Full Reset | 接近 Full Access |

即：

\[
Acc^{failed}_{selective}
\approx
Acc^{failed}_{fullreset}
\]

同时：

\[
Acc^{correct}_{selective}
\approx
Acc^{correct}_{fullaccess}.
\]

如果成立，就是非常漂亮的：

\[
\boxed{\text{Pareto improvement}}
\]

或者至少接近 Pareto improvement。

如果 selective reset 只是在 failed history 上变好，但 correct history 同样损失很大，那么 mitigation contribution 会明显变弱。

---

# 10. 必须防住的替代解释：只是 mask 了更多 token

这是非常危险的 confound。

如果：

\[
mask(descendants)
>
mask(first\ error)
\]

可能只是因为 descendants token 更多。

所以必须加入：

- length-matched benign span；
- random span；
- position-matched span；
- verified span；

等 control。

真正需要看到的是：

\[
\boxed{
\text{error-dependent span intervention}
>
\text{length-matched benign/random span intervention}
}
\]

如果 intervention effect 主要由：

\[
\#masked\ tokens
\]

解释，那么机制 story 基本会塌掉。

---

# 11. Structural Metric 要和 Accuracy 闭环

不能只看 accuracy。

如果 full failed context 下：

\[
TED(new,failed)\downarrow
\]

同时：

\[
Acc\downarrow
\]

而 selective block descendants 后：

\[
TED(new,failed)\uparrow
\]

同时：

\[
Acc\uparrow
\]

那么就能把：

> behavioral harm

与：

> structural inheritance

连起来。

还可以进一步观察：

- first erroneous operation reuse；
- erroneous subtree reuse；
- operator-path reuse。

理想关系：

\[
\boxed{
DTR(S)\uparrow
\Rightarrow
\text{structural reuse attributable to }S\uparrow
}
\]

这样整篇论文会从“现象 + masking”变成“结构继承 + causal intervention + behavior recovery”。

---

# 12. 跨模型 / 跨任务怎么做才够

不需要一开始铺：

> 8 tasks × 10 models × 全条件

更合理的是两阶段。

## Mechanistic Testbed

推荐：

### Game of 24

做完整 decomposition：

\[
P,E,D,A
\]

以及：

- late access intervention；
- path-complete access intervention；
- source / carrier decomposition。

它的优势是：

- executable trace；
- first error 明确；
- arithmetic dependency tree 清楚；
- descendants 更容易定义。

## 第二任务

选择一个可独立求解、结构更不同的任务，例如：

- code reasoning；
- symbolic reasoning；
- CRUXEval-I 类任务。

只验证最核心的 2–3 个 contrast：

- full failed；
- + error signal；
- + full block；
- + selective block。

## 模型

至少做：

\[
2\text{ 个不同 model families}
\]

比做 4 个同架构 scale 更有价值。

核心目标不是“模型数量多”，而是：

\[
\boxed{\text{effect direction replicates}}
\]

---

# 13. 什么结果可以认为是比较 solid 的 ICLR 2027 级别工作

## A 档：明显有 ICLR 主会竞争力

如果同时出现：

\[
R4>R3>R2
\]

说明：

- recognition；
- direct access；
- mediated access；

三者可以分离。

同时：

\[
\Delta_D
\]

是稳定的大 effect，first error / wrong answer 都解释不了全部 drag。

再有：

\[
\text{selective reset}
\]

在 robustness–utility 上明显优于：

- full reset；
- full access。

并且：

- length control 过关；
- random span control 过关；
- verified span control 过关；
- 第二模型 / 第二任务复现核心 contrast。

这时 paper story 很完整：

> **Contextual drag is not merely a failure to recognize errors. Erroneous reasoning remains computationally influential after recognition, and that influence is redistributed into downstream contextual states. We distinguish failure responsibility from drag transmission responsibility and show that reliability-aware selective access can suppress harmful transmission while retaining useful reasoning.**

这是“机制发现 + 方法验证”类型的论文。

---

## B 档：可以投 ICLR，但竞争力一般

如果：

\[
R3>R2
\]

但：

\[
R4\approx R3
\]

说明主要是 direct access，没有明显 downstream-mediated effect。

同时：

- descendants 有一定额外 harm；
- selective reset 有一定 robustness–utility benefit。

仍然可以写成：

> computational accessibility explains persistent contextual drag.

但 novelty 会少一层。

---

## C 档：比较危险

如果只有：

\[
whole\ draft\ mask
>
full\ access
\]

而：

- first error / descendants 没区别；
- late / path-complete 没区别；
- random span mask 也差不多；
- selective reset 没明显优于 full reset；

那么最后很容易退化成：

> Contextual Drag + MEMENTO + attention masking。

这种形态不太像一个 strong ICLR 2027 main contribution。

---

# 14. 哪些结果会直接削弱甚至反驳主假设

## 情况 1

如果：

\[
R2\approx R0
\]

即 explicit error signal 已经完全恢复。

那么：

\[
\text{recognition–disengagement gap}
\]

基本不成立。

---

## 情况 2

如果：

\[
R3\approx R2
\quad\text{and}\quad
R4\approx R2
\]

那么 computational accessibility 不是主要原因。

---

## 情况 3

如果 span intervention effect 几乎只由：

\[
\text{span length}
\]

预测，而与 error dependency 无关，那么 DTR story 很难成立。

---

## 情况 4

如果：

\[
first\ error\ intervention
\]

几乎完全恢复全部 drag，而 descendants 没额外 effect，那么当前“错误影响被 descendants 携带”的假设不成立。

但这个结果本身并非完全无价值。

论文可能改写成：

> contextual drag is highly localized at the originating error.

只是 story 会和当前预期完全不同。

---

# 15. 推荐的 Paper-Level Framing

暂时不建议直接使用：

> **The Causal Anatomy of Contextual Drag**

因为 “Causal Anatomy” 暗示已经比较完整地定位内部 causal mechanism。

在结果出来之前，更稳的 framing 是：

> **From Failure Responsibility to Transmission Responsibility: How Erroneous Reasoning Continues to Bias LLM Inference**

三个核心 RQ 可以压缩为：

\[
\boxed{
RQ1:\ Why\ is\ error\ recognition\ insufficient?
}
\]

\[
\boxed{
RQ2:\ Where\ is\ downstream\ drag\ actually\ carried?
}
\]

\[
\boxed{
RQ3:\ Can\ harmful\ influence\ be\ selectively\ disengaged
without\ discarding\ useful\ reasoning?
}
\]

对应：

\[
\boxed{
\text{Phenomenon}
\rightarrow
\text{Mechanism}
\rightarrow
\text{Control}
}
\]

---

# 16. 最值得追求的 Figure 1 趋势

可以提前把论文最重要的一张图想象成：

横轴：

\[
Direct
\rightarrow
Failed
\rightarrow
+ErrorSignal
\rightarrow
+LateBlock
\rightarrow
+PathCompleteBlock
\]

accuracy 趋势：

\[
\boxed{
\text{high}
\rightarrow
\text{low}
\rightarrow
\text{slightly recover}
\rightarrow
\text{strong recover}
\rightarrow
\text{near baseline}
}
\]

再配第二张 DTR decomposition：

- Wrong Answer
- First Error
- **Descendants**

理想情况是 descendants 明显占更大的 transmission effect。

最后配 robustness–utility 图：

- Full Access：保留 utility，但 robustness 差；
- Full Reset：robustness 好，但 utility 损失；
- Selective Reset：尽量位于更优的 Pareto frontier。

如果最终能得到这三组图，并且 controls 全部过关，那么这项工作就会具有一个比较完整的 ICLR 2027 论文骨架。

---

# 17. 当前最重要的早期判据

在扩大实验之前，最应该先用：

- Game24；
- Qwen3-8B；

判断两个最核心的符号是否成立：

\[
\boxed{
R3>R2
}
\]

以及更关键的：

\[
\boxed{
R4>R3
}
\]

它们分别对应：

### \(R3>R2\)

> 错误被识别以后，computational accessibility 仍然决定其 downstream influence。

### \(R4>R3\)

> 错误影响不只存在于其原始表示，还已经通过 downstream state / descendants 被继续携带。

如果只有第一个成立，这仍然是一个不错的 access-control paper。

如果两个都稳定成立，再加上：

- descendant-level DTR；
- source–carrier dissociation；
- selective reset 的 robustness–utility 优势；

那么它才真正升级成一篇 **transmission-mechanism paper**。

---

# 18. 一句话总结

当前最值得守住的论文主张不是：

> “错误 context 会让模型变差。”

也不是：

> “mask 错误 reasoning 可以提高 accuracy。”

而是：

> **The reasoning step responsible for producing a failure need not be the same computational state responsible for transmitting that failure forward. Contextual drag therefore requires distinguishing failure responsibility from transmission responsibility, and controlling the latter rather than merely recognizing the former.**

这应该成为后续实验设计、related work、motivation 和 contribution 判断的统一标准。
