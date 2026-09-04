# ICLR 2027 Idea Memo：Beyond Contextual Drag

## 0. 研究定位

这项工作以 **Contextual Drag: How Errors in the Context Affect LLM Reasoning** 为直接起点，不重新搭建一个完整的新 benchmark 或训练框架，而是在其现有问题设定、失败 reasoning trace、evaluation pipeline 和结构相似性分析基础上，继续追问：

> **错误 reasoning 为什么会在后续多轮交互中持续影响模型？这种 persistence 究竟来自 token 距离、conversation turns、后续 reasoning activity，还是模型无法真正利用 error awareness 更新其 reasoning state？**

需要特别说明：本项目**不以此前被 EMNLP 拒稿的工作作为方法学或质量背书**。此前经验最多用于提醒实验中要谨慎处理 context length 等 confound，但本项目本身需要独立建立贡献和实验可信度。

---

## 1. 为什么不能只做 “How long does contextual drag last?”

最简单的想法是：

\[
E \rightarrow Q
\]

\[
E \rightarrow H_1 \rightarrow Q
\]

\[
E \rightarrow H_1 \rightarrow H_2 \rightarrow Q
\]

其中：

- \(E\)：错误 reasoning trace；
- \(H_i\)：插入的中间历史；
- \(Q\)：重新求解原目标问题。

然后画 contextual drag 随 turn 数 \(k\) 的 recovery curve。

**这个版本本身不够稳。**

主要风险：

1. reviewer 可能认为只是 **recency / lost-in-the-middle**；
2. 加入 \(H\) 会同时改变 context length；
3. 已有 multi-turn error persistence 工作已经表明错误状态可能持续；
4. 容易被概括成“换了几个 prompt，观察 accuracy 变化”。

因此，论文不应把贡献定位为：

> 错误 context 隔几轮以后还会不会影响模型。

而应升级为：

> **对 contextual drag 的 persistence 做 controlled causal decomposition。**

---

# 2. 推荐的核心问题

## What Makes Contextual Drag Persist?

### Disentangling Distance, Interaction, Reasoning Activity, and Error Awareness

核心研究问题：

### RQ1 — Persistence
错误 reasoning 对后续 target reasoning 的影响是否会跨 conversational turns 持续？

### RQ2 — Mechanism
这种 persistence 主要由什么产生？

- token distance；
- turn boundary / conversational displacement；
- intervening reasoning activity；
- error awareness。

### RQ3 — Recovery
明确知道原 reasoning 错误后：

> 是立即 reset，还是只改变后续 recovery trajectory？

### RQ4 — Helpful vs Harmful History
正确 reasoning 和错误 reasoning 的影响是否以相同速度衰减？

如果 harmful history 比 helpful history 更持久，这会比普通 recency explanation 更有意义。

---

# 3. 核心实验设计

仍然保持 Contextual Drag 的基本形式：

\[
Q + \text{prior reasoning trace}
\]

只改变 history condition，不训练模型。

## 3.1 Baselines

### Direct

\[
Q
\]

clean baseline。

### Failed History

\[
E \rightarrow Q
\]

复现 contextual drag。

### Failed History + Correction

\[
E \rightarrow C \rightarrow Q
\]

其中 \(C\) 只用于明确指出：

> previous reasoning is incorrect.

不要把 correction prompt 本身做成新的研究主题。

---

# 4. 最关键的 causal decomposition

不要只改变 \(k\)，而要把中间 history \(H\) 拆成不同机制。

## Condition A — Token Displacement

\[
E \rightarrow F \rightarrow Q
\]

其中 \(F\) 是 token-matched neutral filler。

目的：

> 只改变 erroneous trace 到最终 generation 的 token distance。

---

## Condition B — Conversational Displacement

\[
E \rightarrow F^{user}
\rightarrow F^{assistant}
\rightarrow Q
\]

尽量与 Condition A 匹配总 token 数，但拆成真实 message turns。

比较：

\[
\text{single-block filler}
\]

vs.

\[
\text{multi-turn filler}
\]

用于判断：

> conversational turn boundary 本身是否改变 contextual persistence。

---

## Condition C — Reasoning Displacement

\[
E
\rightarrow Q'
\rightarrow R'
\rightarrow Q
\]

中间真正完成一个独立 reasoning task。

尽量做到：

\[
Tokens(B) \approx Tokens(C)
\]

\[
Turns(B) = Turns(C)
\]

主要变化只剩：

> 是否发生 intervening reasoning activity。

这一步是避免整篇工作退化成“position ablation”的关键。

---

# 5. Error Awareness：最值得强调的扩展

比较：

\[
E\rightarrow H_k\rightarrow Q
\]

和：

\[
E\rightarrow C\rightarrow H_k\rightarrow Q
\]

重点不是只比较 immediate accuracy，而是比较两条 persistence curve。

问题变成：

> **Error awareness 是只帮助当前一次回答，还是改变错误信息之后的长期影响？**

如果 correction 在 \(k=0\) 时帮助有限，但随着后续交互：

\[
D_C(k) < D(k)
\]

且差距逐渐扩大，那么可以得到很有意思的结论：

> error recognition does not immediately reset reasoning, but alters subsequent recovery dynamics.

---

# 6. 一个很有价值的实验：Correction Timing

保持 context 中包含的信息基本一致，只改变 correction 出现时间。

### Early Correction

\[
E
\rightarrow C
\rightarrow H_1
\rightarrow H_2
\rightarrow Q
\]

### Late Correction

\[
E
\rightarrow H_1
\rightarrow H_2
\rightarrow C
\rightarrow Q
\]

它可以区分两类解释。

### Hypothesis A：Correction 主要是 instruction recency

预期：

\[
Late > Early
\]

### Hypothesis B：Correction 真正改变后续 reasoning-state evolution

则 early correction 可能具有持续保护作用：

\[
Early \approx Late
\]

甚至：

\[
Early > Late
\]

如果出现后者，会是很有辨识度的 finding。

---

# 7. Correct-History Control 必须保留

把错误 draft \(E\) 换成正确 reasoning \(T\)：

\[
T\rightarrow H_k\rightarrow Q
\]

定义：

### Harmful persistence

\[
D(k)=Acc_{Direct}-Acc_{Failed,k}
\]

### Helpful persistence

\[
B(k)=Acc_{Correct,k}-Acc_{Direct}
\]

重点看：

\[
D(k)
\quad\text{vs.}\quad
B(k)
\]

如果只是普通 context aging，两者应该大体共同衰减。

但如果出现：

\[
B(k)\rightarrow 0
\]

而：

\[
D(k)>0
\]

则可以提出：

> **harmful reasoning traces persist longer than useful reasoning traces.**

这会显著增强论文的新颖性和理论意义。

---

# 8. Structural Recovery：继续复用 Contextual Drag 的 TED

不要重新发明复杂指标。

继续使用原文的 reasoning-structure similarity / Tree Edit Distance 思路：

\[
TED(E,R_k)
\]

其中：

- \(E\)：原 failed reasoning；
- \(R_k\)：经过不同 intervening history 后重新生成的 reasoning。

这样可以区分：

## Behavioral Recovery

\[
Acc(R_k)\rightarrow Acc_{Direct}
\]

和：

## Structural Recovery

重新生成的 reasoning 是否仍结构性接近 \(E\)。

最有意思的结果之一是：

> **Answer recovery does not imply reasoning recovery.**

即 accuracy 已恢复，但 reasoning trajectory 仍保留错误历史的结构痕迹。

---

# 9. 为什么这不应被写成 Prompt Engineering

危险 framing：

> We propose several prompting strategies and compare which one works better.

应该避免。

正确 framing：

> We construct controlled contextual interventions to identify which factors determine the persistence of erroneous reasoning.

也就是说：

- prompt/context 是实验载体；
- 研究变量是 distance / turns / reasoning activity / awareness；
- 目标不是找“最好 prompt”；
- 目标是识别模型行为规律和因果因素。

论文中建议使用：

- **controlled intervention**
- **factorized contextual condition**
- **causal decomposition**

而不是：

- prompting strategy；
- prompt optimization；
- best prompt。

---

# 10. 什么结果才比较像 ICLR 级贡献？

## 强结果

以下 4 类结果中，如果有 2–3 类能跨模型、跨任务稳定出现，就具有较强投稿价值：

### 1. Distance 与 interaction dissociation

在严格控制 token budget 后：

\[
E+\text{token filler}
\neq
E+\text{multi-turn filler}
\]

说明 persistence 不只是 recency。

### 2. Reasoning activity effect

\[
E+\text{multi-turn filler}
\neq
E+\text{intervening reasoning}
\]

说明新的 reasoning activity 本身会改变旧 reasoning trace 的影响。

### 3. Error-awareness dynamics

Correction 不一定立即消除 drag，却显著改变后续 persistence / recovery rate。

### 4. Helpful–harmful asymmetry

\[
D(k)\not\propto B(k)
\]

尤其 harmful history 比 helpful history 更持久。

### 5. Behavioral–structural dissociation

accuracy 已恢复，但 TED 仍显示新 reasoning 明显继承旧的失败结构。

---

## 弱结果 / 高风险结果

如果最终只有：

> 错误 context 离目标越远，影响越弱；correction 有一点帮助。

那么 reviewer 很容易解释为：

- recency；
- lost-in-the-middle；
- ordinary context aging。

这种情况下 ICLR 新颖性会比较弱。

---

# 11. 最小 Pilot：先判断这个题值不值得继续

不要一开始就跑完整 \(k=0,1,2,4,8\) recovery curve。

先用：

- 1 个主模型（如 Qwen3-8B）；
- 2 个 Contextual Drag 已支持、可稳定自动评价的任务；
- 一小批已有 failed cases。

比较六个条件：

1. **Direct**
2. **\(E\)**
3. **\(E+C\)**
4. **\(E+\) token-matched filler**
5. **\(E+\) multi-turn filler**
6. **\(E+\) intervening reasoning**

后三个尽量严格匹配 token budget。

### Go / No-Go Criterion

如果：

\[
E+\text{token filler}
\approx
E+\text{multi-turn filler}
\approx
E+\text{reasoning}
\]

则大概率只是 distance effect，及时停止或换题。

如果发现：

\[
E+\text{token filler}
\neq
E+\text{multi-turn filler}
\]

或尤其：

\[
E+\text{multi-turn filler}
\neq
E+\text{reasoning}
\]

则说明存在 Contextual Drag 原文尚未分解的机制，值得扩大实验。

---

# 12. 当前最合适的 scope

为赶 ICLR 2027，暂时不要加入：

- RL；
- SFT；
- learned controller；
- hidden-state probing；
- 新 benchmark；
- 多种 error provenance；
- 大量 error taxonomy；
- 10–20 turn 超长 horizon；
- 新 memory architecture。

这些都可以成为后续工作。

当前论文最好保持为：

> **基于 Contextual Drag testbed，对 erroneous reasoning persistence 做一个严格、可解释、factorized 的 inference-only study。**

---

# 13. 推荐标题

首选：

## **What Makes Contextual Drag Persist?**
### Disentangling Distance, Interaction, and Error Awareness in LLM Reasoning

备选：

## **Beyond Contextual Drag: Disentangling the Persistence of Erroneous Reasoning**

如果结果强到能够支持：

## **Reasoning Errors Outlive Their Corrections**
### On the Persistence of Erroneous Context in LLM Reasoning

---

# 14. 一句话 Paper Story

> Contextual Drag shows that erroneous reasoning can bias a model's immediate subsequent reasoning even when its incorrectness is known. We ask what makes this influence persist across later interactions. Through controlled, token-matched interventions, we disentangle token distance, conversational transitions, intervening reasoning, and error awareness, and examine whether behavioral recovery coincides with structural recovery.

---

# 15. 当前判断

### 单纯 Recovery Curve

- 新颖性：中等偏弱；
- prompt-work 风险：高；
- ICLR：不建议以此直接投稿。

### Controlled Persistence Decomposition

- 新颖性：较强；
- 与 Contextual Drag 衔接：非常直接；
- 不需要训练；
- 工程量相对可控；
- prompt-work 风险：明显降低；
- 是否值得继续，主要取决于最小 pilot 能否发现 **非平凡的 factor dissociation**。

因此当前最合理的路线是：

\[
\boxed{
\text{Contextual Drag}
\rightarrow
\text{Persistence}
\rightarrow
\text{Causal Decomposition}
\rightarrow
\text{Recovery Dynamics}
}
\]

而不是：

\[
\text{Contextual Drag}
\rightarrow
\text{再设计几个 prompt 看 accuracy}
\]

