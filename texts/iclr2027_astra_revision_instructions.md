# ICLR 2027 论文修改指令（给 Astra）

请仔细阅读我提供的当前论文 PDF，并基于**现有论文内容、已有实验结果和现有 causal claim**，重写一版更接近 **ICLR 2027 main conference** 水准的稿件。

这次任务的目标不是重新发明研究方向，也不是人为扩大 novelty，而是提升：

- scientific framing
- argument hierarchy
- storytelling
- section organization
- reviewer-facing clarity
- empirical presentation
- claim precision
- writing quality

当前工作的核心 idea 和 causal design 已经基本确定。请优先保护这个已经相对干净的研究问题，而不是通过加入更大的术语、更泛的理论框架或更多未经验证的机制解释来制造贡献。

---

## 一、必须保持不变的核心研究定位

当前论文研究的问题不是泛泛的：

> failed reasoning 会不会造成 contextual drag？

而是更具体的：

> **当一个错误推理轨迹已经被模型完整处理，并且模型已经收到明确的 error feedback 之后，这个错误轨迹为什么仍然能够影响后续独立求解？**

论文需要明确区分两个可能的影响来源：

\[
\textbf{initial exposure}
\]

和

\[
\textbf{continued direct access during generation}.
\]

Contextual Drag 已经建立了 failed reasoning history 会损害后续 reasoning 的现象。本文不需要重新把这个现象作为主要 novelty。

本文真正的新问题应该表述为：

> **Does continued computational access to an already-seen, explicitly marked-wrong trajectory make an additional causal contribution to contextual drag?**

当前论文已经在 Introduction 中基本形成这一问题：普通 deletion / rewriting 会同时改变 initial exposure、prompt text、positions 和 later accessibility，因此无法单独识别 continued access；R2/R3 的 same-text intervention 则试图隔离这个变量。

这一点应成为整篇论文最核心的 intellectual contribution。

---

## 二、全文应围绕一条单一故事线组织

希望最终论文呈现如下逻辑：

### Phenomenon

Failed reasoning can remain harmful even after explicit error feedback.

↓

### Unresolved mechanism

这种持续影响至少可能来自两条路径：

\[
\text{having already processed the failed trace}
\]

和

\[
\text{continuing to access the failed trace during decoding}.
\]

↓

### Identification problem

普通 prompt deletion、rewriting 或 reset 会同时改变：

- content
- context length
- positions
- prefill computation
- accessibility

因此无法单独判断 continued access 是否有独立作用。

↓

### Controlled intervention

让模型：

1. 完整读取相同 prompt；
2. 正常完成 full prefill；
3. 保持相同 token IDs 和 positions；
4. 从相同 full-prefill logits 产生第一个 token；
5. 仅在后续 generation 中，阻断 generated queries 对 failed-draft key/value positions 的直接 attention。

↓

### Main result

R2 → R3 出现大幅 recovery。

↓

### Specificity

blocking correct history 反而能够降低表现，因此 masking 并非 generic benefit。

↓

### Generalization

同方向 effect 出现在不同模型、不同 inference implementation 和 MATH task 中。

↓

### Conclusion

> **Initial exposure and continued accessibility are distinct computational factors. Continued direct access remains causally consequential even after full exposure and explicit error feedback.**

整篇论文所有 section 都应该服务这条主线。

不要写成：

> contextual drag + attention mask + 几个 benchmark。

---

## 三、Abstract：只允许保守修改

这一点非常重要。

**当前 Abstract 已经提交给 ICLR 2027 作为 abstract registration / 占位版本，因此不能把 Abstract 重写成看起来像另一篇论文。**

当前 Abstract 已经包含：

- failed reasoning remains influential after explicit feedback；
- same-text attention intervention；
- full prompt normally processed；
- later generated queries blocked；
- Game24 主结果；
- Qwen3-32B / Gemma / MATH；
- correct-history control；
- continued access is a contributor 的最终 claim。

因此 Abstract **不要大改 substantive content**。

允许的修改：

- 优化前 2–3 句；
- 更早明确 initial exposure vs continued access 的 distinction；
- 改善逻辑连接；
- 精炼措辞；
- 让 conceptual question 更锋利；
- 保持相同实验数字和相同结论。

推荐的开头逻辑是保留当前第一句思想：

> When a failed reasoning trace remains in context, explicit feedback that its answer is wrong may not prevent it from influencing a new solution.

然后增加/改写一句：

> Is this residual influence simply a consequence of having already processed the failed trace, or does its continued accessibility during generation make an additional contribution?

之后继续当前的：

> We isolate the role of continued direct access with a same-text attention intervention...

不要：

- 把 paper 改写成 general agent memory paper；
- 改成新的 decoding algorithm paper；
- 改成“we solve contextual drag”；
- 新增尚未完成的实验；
- 大幅改变 title/abstract 所对应的领域和研究问题。

Abstract 目标是：

> **polish and sharpen, not reframe.**

---

## 四、Introduction：需要明显加强

Introduction 可以比 Abstract 更大胆地重构。

当前 Introduction 的技术逻辑是好的，但应该更加突出“大问题”。

现在从 iterative refinement / verbal-feedback agents 开始是合理的。

请把它抽象成一个广泛存在的 inference pattern：

\[
\text{generate}
\rightarrow
\text{receive feedback}
\rightarrow
\text{retain previous trajectory}
\rightarrow
\text{reason again}.
\]

这种模式存在于：

- iterative refinement
- verifier feedback
- self-correction
- agentic workflows
- repeated reasoning with retained context

然后提出一个非常直接的问题：

> **Does telling a model that prior reasoning is wrong actually neutralize that reasoning as computational context?**

再引入 Contextual Drag。

关键 framing：

不要让 Cheng et al. 看起来只是“我们复现并扩展的前作”。

更好的关系是：

> **Contextual Drag establishes the behavioral phenomenon; we use that phenomenon to ask a downstream mechanistic question.**

即：

> conditional on a failed trajectory producing contextual drag, what portion of the residual effect depends on that trajectory remaining directly accessible during decoding?

可以把这个思想更早移入 Introduction。

---

## 五、Introduction 中必须明确提出两个 competing explanations

最好显式描述：

### Explanation A: initial-exposure effect

错误轨迹在 full prefill 阶段已经改变了后续可访问 states，因此即使后面不再直接访问 failed draft，drag 仍可能存在。

### Explanation B: continued-access effect

即使已经完成 full prefill，生成阶段反复直接访问 failed draft 本身仍会持续影响 reasoning。

然后指出：

> deletion cannot distinguish A from B.

这一段是论文最重要的 causal identification motivation。

不要把 mask 写成一个工程 trick。

mask 的意义是：

> **holding exposure fixed while intervening on later accessibility.**

---

## 六、Contributions 需要重写

当前 contribution 中有一条比较像 experiment inventory，例如列出 15 Game24、three models、MATH。

请改成三个层次：

### 1. Conceptual contribution

We distinguish **initial exposure** from **continued accessibility** as two routes through which failed reasoning can influence subsequent generation.

### 2. Methodological / identification contribution

We introduce a **same-text, post-prefill attention intervention** that manipulates continued direct access while preserving:

- prompt text
- token IDs
- positions
- full initial exposure
- first-token full-prefill computation

### 3. Empirical contribution

We show that blocking continued access recovers a substantial portion of contextual-drag loss across models/tasks, while blocking verified correct history can instead reduce performance.

Contribution 应该形成：

\[
\boxed{\text{concept}}
+
\boxed{\text{causal identification}}
+
\boxed{\text{finding}}.
\]

不要把：

> “we implemented FlexAttention in vLLM”

作为主要 scientific contribution。

它是重要 implementation，但不是 novelty 本身。

---

## 七、Figure 1：基本保留当前设计

当前 Figure 1 已经比较成熟。

它很好地表达了：

- same prompt
- full prefill
- same first-token logits / sampled first token
- R2 retains access
- R3 blocks later direct access

不要重新做成大量文字框的机械流程图。

Figure 1 应继续承担：

> **causal design intuition**

而不是实验结果展示。

如果要微调，只需要：

- 强化“full exposure first”
- 强化“intervention begins only after first token”
- visually emphasize that prompt itself is unchanged
- 保持高水平 ML conference figure 的简洁风格

---

## 八、Problem Setup / Method：总体已经比较严谨，重点是提高可读性

当前 formulation：

\[
A_{\text{full}}
\]

\[
A_{\text{late}}
\]

\[
A_{\text{path}}
\]

整体是合适的。

请保持 formal definitions。

但在 equation 前后增加更直觉的解释：

- FULL = normal access
- LATEBLOCK = full prefill, then block generated-query access
- PATHBLOCK = earlier/stronger timing diagnostic

尤其强调：

> R3 is the primary causal contrast.

> R4 is secondary.

不要让三个 mask 看起来是三个并列的新 method。

---

## 九、必须继续强调 R2/R3 的 parity

当前论文已经记录：

R2–R4 share identical：

- prompt text
- token IDs
- absolute positions
- draft span
- error signal
- sampling configuration

并且实现中保存 token IDs、positions、prompt hash 和 draft span。

这些不是 appendix-level engineering trivia。

它们直接支撑 causal identification。

请确保正文简洁但明确地让 reviewer 知道：

> R2 and R3 are not two prompts.

它们是：

> **the same prompt under two accessibility regimes.**

---

## 十、跨 inference implementation 是 robustness，而不是工程负担

Qwen3-8B 和 Qwen3-32B 使用：

> vLLM + FlexAttention

Gemma 使用：

> separate eager Hugging Face implementation for hybrid attention.

请把这一点适度提升为 robustness evidence：

> The observed direction is not tied to one custom inference backend.

但只能说：

> independent implementations support robustness.

不能说 bitwise equivalence。

当前论文对此已经很谨慎，应保持。

---

## 十一、Results 必须从“按 benchmark 汇报”改成“按 scientific claim 汇报”

这是正文最重要的结构修改之一。

当前结构是：

- Game24
- MATH
- correct-history specificity

建议改为：

### 6.1 Failed reasoning remains harmful despite explicit error feedback

先 establish prerequisite：

\[
\Delta_{\text{drag}}
=
Acc(R0)-Acc(R2)>0.
\]

解释：

只有在 R2 相对 R0 确实存在 residual drag 时，R3−R2 才有“recovery”意义。

### 6.2 Blocking continued access recovers most of the lost performance

这是全文 **hero result**。

重点突出 Qwen3-8B：

\[
R0=25/30
\]

\[
R2=10/30
\]

\[
R3=24/30
\]

以及：

\[
R3-R2=+46.7pp
\]

95% CI：

\[
[+26.7,+66.7].
\]

然后解释：

\[
\Delta_{\text{drag}}=50.0pp
\]

而 recovery 是：

\[
46.7pp.
\]

不要直接说“完全恢复”，因为 R3 仍略低于 R0 且 uncertainty 存在。

更准确：

> recovered most of the observed loss.

同时强调 paired transitions：

Qwen3-8B：

- 16 wrong → correct
- 2 correct → wrong
- 8 both correct
- 4 both wrong

这比 aggregate accuracy 更能说明 effect 是系统性的 paired change。

### 6.3 The access effect transfers across target models and implementations

报告：

Qwen3-8B：

\[
+46.7pp
\]

Qwen3-32B：

\[
+26.7pp
\]

Gemma 4 E4B：

\[
+16.7pp
\]

叙述方式：

> same direction, different magnitude and uncertainty.

Gemma CI touching zero 应明确写。

不要说：

- larger models are more robust
- access effect scales down with size
- model scale explains the difference

只有三个模型，不足以推 scaling conclusion。

### 6.4 Blocking is not generically beneficial

把 correct-history control 提升为主要 specificity result。

核心论述：

> If late blocking merely helped by regularizing decoding, shortening effective context, or forcing independent reasoning, one might expect it to help regardless of history quality.

但事实上：

> blocking failed history helps;

而：

> blocking correct history hurts.

因此：

> **history access is behaviorally useful when the history itself is useful.**

这使得 failed-history recovery 更具有 specificity。

但是必须保持论文当前的限制：

correct 和 failed histories 并不是除 correctness 外完全 identical，所以不能声称：

> we isolate truth value.

### 6.5 Earlier blocking provides no consistent additional benefit

最后再处理 R4。

R4 不应被写成失败，而应定位为：

> secondary timing diagnostic.

当前 R4 并没有稳定优于 R3，这应该帮助收缩机制 claim，而不是制造 narrative disappointment。

更好的 framing：

> Earlier blocking provides no consistent additional benefit beyond late access blocking.

R4 的作用是：

> probe whether intervening earlier on post-draft states improves recovery.

结果：

> it does not consistently do so.

因此它约束理论：

> data do not justify a stronger claim about fully tracing mediated propagation paths.

R4 应是 mechanism boundary，而不是论文第二主贡献。

---

## 十二、MATH 应定位成 cross-task replication，而不是第二主实验

当前 MATH effect 很大：

MATH500 / 1.7B draft：

\[
R3-R2=+75pp
\]

MATH-train / 4B draft：

\[
+50pp.
\]

这个结果方向很好。

但现在存在明显 nuisance：

- 14 length-limit stops
- 13 unresolved scores
- termination imbalance concentrated in R3/R4

因此请明确定位为：

> cross-task replication under longer-form mathematical reasoning.

不要让 reviewer 误以为：

> MATH provides an equally clean causal experiment.

如果没有新增实验，只能诚实报告这一 limitation。

不要文字上掩盖。

---

## 十三、Correct-history control 要大幅提升叙事地位

这是目前论文最重要的 control 之一。

当前 correct-history control：

\[
16/16 \rightarrow 13/16
\]

blocking effect：

\[
-18.8pp.
\]

failed-history effect 在相同八题上为正。

difference-in-differences：

\[
+56.2pp.
\]

建议独立成为：

### 6.4 Blocking is not generically beneficial

核心论述：

> If late blocking merely helped by regularizing decoding, shortening effective context, or forcing independent reasoning, one might expect it to help regardless of history quality.

但事实上：

> blocking failed history helps;

而：

> blocking correct history hurts.

因此：

> **history access is behaviorally useful when the history itself is useful.**

这使得 failed-history recovery 更具有 specificity。

但是必须保持论文当前的限制：

correct 和 failed histories 并不是除 correctness 外完全 identical，所以不能声称：

> we isolate truth value.

---

## 十四、增加一张 Figure 2：effect summary

建议制作一个 forest-style effect plot。

纵轴：

- Qwen3-8B / Game24 failed history
- Qwen3-32B / Game24 failed history
- Gemma 4 E4B / Game24 failed history
- MATH500 failed history
- MATH-train failed history
- Qwen3-8B / correct history

横轴：

\[
\Delta_{\text{access}}
\]

或：

\[
Acc(\text{blocked})-Acc(\text{full access})
\]

带 95% CI。

零点画竖线。

最希望形成的视觉结果：

- failed-history conditions 在右边；
- correct-history 在左边。

这张 Figure 2 应成为全文 empirical takeaway。

不要为了美观隐藏 uncertainty。

---

## 十五、Tables 可以更紧凑

Table 2 / Table 3 当前信息基本够。

但可以考虑：

主文保留：

- R0
- R2
- R3
- effect
- CI

把一些更细的：

- EOS
- unresolved
- request-level diagnostics
- R4 detailed breakdown

放 appendix 或 supplementary table。

正文目标是让 reviewer 一眼看懂主 contrast。

---

## 十六、Discussion：重点从“masking”升华到“exposure ≠ accessibility”

当前 Discussion 最严谨的一段必须保留：

R3：

- does not erase the draft from prefill
- does not prevent accessible states from carrying draft-derived information
- therefore identifies causal relevance of direct access edges, not total forgetting

请把 conceptual takeaway 再明确一层：

> **Exposure and accessibility are separate computational variables.**

模型完全可能：

1. 已经处理过某段信息；
2. 该信息已经影响部分 hidden states；
3. 但之后是否仍能直接访问原始 representation，依然额外影响 behavior。

这是整篇论文最值得让读者带走的 conceptual message。

---

## 十七、不要把论文写成 practical mitigation paper

当前文章已经正确写道：

> deleting a known-wrong trajectory is simpler than custom masking.

请继续保持。

当前论文不是要证明：

> R3 is the best deployment solution.

而是：

> R3 is an experimental intervention enabling causal identification.

不要新增：

- production claims
- efficiency claims
- practical superiority claims
- safety guarantee claims

除非已有数据支持。

---

## 十八、Limitations：保持诚实，但不要自我削弱过度

当前最重要限制：

- oracle knowledge of wrong trajectory
- only 15 Game24 questions
- selected mixed-outcome population
- adaptive protocol development
- two inference implementations
- information can persist through unblocked states
- MATH termination imbalance
- small correct-history subset

都应该保留。

但是语言要区别：

### Claim boundary

这是科学范围限定。

vs.

### Fatal flaw

不要把所有限制写成“因此结果可能无意义”。

特别是：

> selected sample

意味着 effect size 不能泛化到 arbitrary problems；

但它并不否定：

> 在这些有 residual drag 的 samples 中，continued access 的 intervention 有 causal effect。

请写清楚这一层区别。

---

## 十九、Conclusion 应非常短，并回到 causal question

Conclusion 不要重新罗列所有 benchmark。

建议压缩为：

1. 我们分离 full initial exposure 与 later direct access；
2. blocking later access recovers substantial performance；
3. effect appears across additional models/tasks；
4. correct-history blocking can hurt；
5. 因而 continued direct accessibility is a causal contributor, but not necessarily the only pathway.

---

## 二十、必须严格遵守的 claim boundaries

不允许把当前证据升级为以下说法：

### 不要说

> the model forgets the failed trace.

### 不要说

> blocking removes the error information.

### 不要说

> continued access is the only mechanism.

### 不要说

> initial exposure is irrelevant.

### 不要说

> R3 isolates all information flow from the failed trace.

### 不要说

> we identify the internal representation of errors.

### 不要说

> masking universally improves reasoning.

### 不要说

> this solves contextual drag.

### 不要说

> stronger models are less susceptible.

### 不要说

> this is a practical deployment solution.

允许的 strongest main claim 应接近：

> **Continued direct access to a failed reasoning trace makes an interventionally identifiable contribution to contextual drag after full initial exposure and explicit error feedback.**

---

## 二十一、关于目前实验规模：只提出修改建议，不得虚构结果

目前 paper 有：

- 15 Game24 questions；
- 2 paired seeds；
- 3 target models；
- 16 MATH questions；
- 8-question correct-history control。

这些是真实已有结果。

不要把正在进行或计划中的 Batch03 / Batch04 写进 paper。

但是在修改说明中，请指出未来最值得增加的实验，优先级为：

### 第一优先：扩大 independent Game24 question count

目标最好达到：

\[
30\text{–}50
\]

independent questions。

independent questions 的增加优先于在已有 15 题上大量增加 seeds。

### 第二优先：扩大 correct-history control

最好随着主 set 增加。

### 第三优先：保持 Qwen3-8B / Qwen3-32B / Gemma 三模型的 R0/R2/R3 comparison

无需为了对称性给所有模型跑 R4。

### 第四优先：如果算力允许，解决或敏感性分析 MATH termination imbalance。

### 第五优先：可考虑一个 generic/non-draft span blocking control

用于检验：

> blocking arbitrary historical span 是否本身造成 recovery。

但这属于 future experiment recommendation，不能在重写稿中假装已经完成。

---

## 二十二、写作风格要求

请按高水平 ICLR / NeurIPS empirical-mechanistic paper 风格重写。

要求：

- concise
- technically precise
- claim-driven
- understated rather than promotional
- avoid repeated caveats
- avoid generic AI prose
- avoid excessive section-level summaries
- avoid rhetorical overclaim
- reduce unnecessary implementation detail in main narrative
- preserve reproducibility details where scientifically necessary

尤其不要使用大量：

> “Importantly,” “Notably,” “Crucially,” “Interestingly”

来人为制造重要性。

让实验设计和结果本身体现重要性。

---

## 二十三、最终 reviewer 应该能够这样复述本文

希望最终稿阅读完成后，一个 reviewer 可以准确地用下面六句话描述这篇 paper：

> **1.** Failed reasoning can remain harmful even after explicit error feedback.

> **2.** Existing prompt-level interventions cannot distinguish whether this persistence comes from having already processed the failed trace or from continuing to access it.

> **3.** The authors isolate continued access by allowing full initial processing and only then blocking generated-query attention to the failed trace.

> **4.** Blocking this access recovers most of the observed contextual-drag loss in the main experiment.

> **5.** The direction transfers across additional models/tasks, while blocking correct history can instead hurt.

> **6.** Continued computational accessibility is therefore a causal contributor to contextual drag after feedback, although it is not necessarily the only information pathway.

如果论文不能自然地让 reviewer 得出这六点，请继续调整结构。

---

## 二十四、最终请输出以下内容

请给我：

1. **完整修改后的论文正文**，可以直接替换当前 LaTeX 内容；
2. **Abstract 单独列出 before/after**，并说明修改幅度为何仍属于 conservative polishing；
3. **新的 section organization**；
4. **Figure 1 是否需要调整，以及具体调整建议**；
5. **Figure 2 的完整设计方案和 caption 草稿**；
6. **Tables 的调整建议**；
7. **一个 revision memo**，逐项说明：
   - 原稿问题；
   - 修改方式；
   - 修改目的；
8. 明确标记：
   - `[WRITING ONLY]`：仅需文字修改；
   - `[STRUCTURE]`：需要结构重排；
   - `[EXPERIMENT NEEDED]`：必须等新实验才能补；
   - `[OPTIONAL]`：有时间再做；
9. 最后做一次 **claim audit**，逐条检查修改后的论文是否存在：
   - causal overclaim
   - generalization overclaim
   - scaling overclaim
   - mitigation overclaim
   - unsupported mechanism claim。

---

## 二十五、最重要的总原则

> **宁可把现有的 narrow causal claim 讲得更锋利，也不要通过增加更大的理论术语来制造 novelty。**

这篇论文当前最值得保护的是：

\[
\boxed{
\text{full exposure}
\neq
\text{continued accessibility}
}
\]

以及我们有一个相对干净的 intervention 来区分二者。

接下来论文质量的提升应该主要来自：

\[
\textbf{better identification narrative}
+
\textbf{stronger evidence}
+
\textbf{better presentation},
\]

而不是继续扩大理论野心。
