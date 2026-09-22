# Contextual Drag：Continued-Access 机制验证计划
**版本：2026-09-22（target-model 与 A100 执行决策已更新）**

## 1. 当前研究主线

当前项目不再继续追求 failed draft 内部某个局部 reasoning structure（如 X、CALC、validity 等）作为稳定的“错误 carrier”。

现阶段更清晰、可验证的核心问题是：

> **在模型已经于 prefill 阶段完整接触失败轨迹的情况下，后续生成阶段对该 failed trajectory 的持续直接访问，是否仍然对 contextual drag 具有可干预的因果贡献？**

对应的核心条件：

- **R0**：clean solve，无失败历史。
- **R2**：failed trajectory 完整存在，后续生成可持续访问。
- **R3**：failed trajectory 的文本、token、position 与 R2 完全相同；prefill 阶段完整可见，第一 token 也来自完整 prefill，但后续 generated queries 不再直接访问 failed-draft keys。
- **R4**：更早/更强的 whole-path blocking，作为 timing / stronger-access-control diagnostic，而不是默认优于 R3 的主假设。

核心不是“遮掉错误当然有用”，而是区分：

\[
\text{initial prefill exposure}
\]

与

\[
\text{continued direct access during generation}
\]

对 contextual drag 的不同作用。

---

## 2. 当前最重要的已有证据

### 2.1 7-question dual-anchor pilot

7 道题 × 2 paired seeds × R0/R2/R3/R4，共 56 次生成：

- R0：12/14 = 85.7%
- R2：4/14 = 28.6%
- R3 whole-late：12/14 = 85.7%
- R4 whole-path：10/14 = 71.4%

这组结果支持：

1. failed trajectory 在当前筛选条件下产生明显 drag；
2. 即使 prefill 已完整接触 failed trajectory，切断后续直接访问仍出现大幅恢复；
3. 因此 drag 不能简单理解为“错误历史一旦被读过就已经永久污染”。

但目前不能声称：

- prefill 没有作用；
- R3 清除了所有 failed-draft 信息；
- 已定位内部错误表示；
- R4 一定优于 R3；
- whole-trace blocking 普遍适用于所有错误历史。

---

## 3. 不合适外部构造实验的定位

UFT external 20：

- R0/R2/R3/R4 = 36/40, 39/40, 34/40, 40/40
- 没有出现正向 residual drag，R3 反而更差。

**这组结果不用于判断当前核心假设是否成立。**

原因是这批数据并不是按照 Contextual Drag 原论文的现象构造条件得到的：

- failed drafts 来自外部来源模型；
- 筛选规则不同；
- draft 长度、风格、难度和构造方式不同；
- 没有预先确认这些错误历史对 target model 会造成 drag。

因此，当

\[
R0 > R2
\]

这个前提本身不成立时，就没有必要把

\[
R3 > R2
\]

解释成“是否能恢复 contextual drag”。

该实验仅保留在内部审计记录中。由于其题目与 draft 构造没有先复现
contextual drag 前提，**不进入论文正文、附录、主实验链路或论文结论**，也不作为
continued-access 假设的正反证据。后续不再为该构造追加计算资源。

---

## 4. 当前核心科学问题

正式主问题建议收敛为：

> **Under what conditions does continued attention access to a failed same-problem trajectory contribute to contextual drag?**

其中最关键的可检验子问题是：

### RQ1：现象是否稳定复现？

在按 Contextual Drag 思路筛选的新独立问题上：

\[
R0 > R2 \ ?
\]

即 failed trajectory 是否确实导致性能下降。

### RQ2：continued access 是否有可干预贡献？

在同一批发生 drag 的问题上：

\[
R3 > R2 \ ?
\]

如果成立，则说明：

> 即使保留完整 prefill 暴露，只切断后续直接访问，也能缓解 drag。

### RQ3：这种恢复是否具有错误相关特异性？

比较 failed-draft 与 correct-draft：

\[
\Delta_{\text{fail}}
=
Acc(F_{\text{late}})-Acc(F_{\text{full}})
\]

\[
\Delta_{\text{correct}}
=
Acc(C_{\text{late}})-Acc(C_{\text{full}})
\]

重点检验：

\[
\Delta_{\text{fail}}-\Delta_{\text{correct}}>0
\]

如果 failed history 被 block 后受益，而 correct history 被 block 后没有同样收益、甚至受损，则更支持“failed-history-specific continued access”解释，而不是一般性的 attention disruption。

---

## 5. 后续实验优先级

### Phase 1：先完成独立复现

优先完成已经冻结的新实验，不新增新的 mask 类型。

#### Game24
使用新筛出的 dual-anchor 问题，统一跑：

- R0
- R2
- R3
- R4

目标：

- 复现 R0 > R2；
- 检验 R3 > R2；
- R4 仅作为 secondary timing diagnostic。

这一步决定核心现象能否从 7-question pilot 扩展到独立样本。

#### MATH
完成当前已经冻结的数学实验。

MATH 用于检验：

- 跨任务是否仍能观察到 drag；
- continued-access blocking 是否仍能恢复；
- 但与 Game24 分开报告，不直接合并。

---

### Phase 2：Deletion / Reset control

这是最重要的 reviewer control。

核心质疑：

> 如果已经知道历史错误，为什么不直接删掉？

需要比较：

- **D / reset**：failed draft 在 prefill 前就删除；
- **R2**：prefill 看见 + generation 持续访问；
- **R3**：prefill 看见 + generation 阶段切断直接访问。

如果当前 R0 与合理的 deletion/reset 输入完全等价，则优先复用 R0，不额外生成冗余条件。

最有信息量的模式：

\[
D \approx R3 > R2
\]

它支持：

> 初始暴露本身不足以解释全部 drag；continued direct access 是一个重要可干预因素。

但即使 R3 与 deletion 表现相当，也不能声称 R3 是更优的实用方法，因为目前没有效率优势证据。

---

### Phase 3：Correct-draft specificity control

在同一批冻结问题上选择正确草稿，不看 intervention outcome。

构造：

- Correct-full
- Correct-late
- Failed-full
- Failed-late

目标：

> 区分“屏蔽错误历史有益”与“任意破坏历史 attention 都可能改变结果”。

理想模式：

\[
F_{\text{late}}>F_{\text{full}}
\]

同时：

\[
C_{\text{late}}\le C_{\text{full}}
\]

重点报告 interaction，而不是只比较各条件 accuracy。

---

### Phase 4：Blocking-onset timing probe

如果 Phase 1–3 支持主线，再做小规模机制探针。

固定已经确认会发生 drag 的问题，改变 blocking onset，例如：

\[
t_{\text{block}}\in\{0,32,128,512,\infty\}
\]

其中：

- 0：生成开始后立即阻断，即当前 R3；
- 32/128/512：允许一段生成后再阻断；
- ∞：始终保持访问，即 R2。

要检验的不是必须严格单调，而是：

> continued access 持续时间是否系统性影响 drag 强度。

这比继续寻找 X/CALC 等人类定义局部错误区域更干净，因为 manipulated variable 明确。

---

## 6. 输出行为分析

行为分析作为 supporting evidence，不作为内部机制证明。

建议重点分析：

### 6.1 Failed-expression reuse

比较 R2 与 R3 中：

- 是否复用 failed draft 的错误表达式；
- 是否重复相同非法数字组合；
- 是否沿用相同候选路线。

若：

\[
Reuse(R3) < Reuse(R2)
\]

同时 R3 accuracy 恢复，则与“continued access 促进旧路线复用”的解释一致。

### 6.2 Solution-route novelty

比较 R2/R3：

- equation overlap；
- operator-tree similarity；
- first candidate overlap；
- token / n-gram overlap。

用于判断 R3 是否更容易转向新的求解路径。

### 6.3 First-token / divergence analysis

R3 第一 token 来自完整 prefill。

因此可以检查：

- R2/R3 第一 token 是否一致；
- 两条 generation 从第几个 token 开始分叉；
- 分叉是否发生在 blocking 生效之后。

这可以作为很好的方法学展示：

\[
same\ prompt
\rightarrow
same\ prefill
\rightarrow
same\ initial\ prediction
\rightarrow
different\ continued\ access
\rightarrow
different\ trajectory
\]

---

## 7. 第二 target model

如果前面结果成立，再增加 target-model generalization。

注意：

> 不同 draft-source model ≠ 不同 target model。

真正的 model generalization 必须是：

- 相同冻结题目；
- 相同 failed drafts；
- 换另一个 target model；
- 再比较 R0/R2/R3；R4 仅保留在主模型上作为 timing diagnostic。

### 7.1 2026-09-22 冻结的模型选择

在不新增模型下载、避免挤占几乎写满的服务器磁盘的约束下，冻结为：

1. **Qwen3-8B**：主模型；
2. **Qwen3-32B**：同架构、不同规模的 scale generalization；
3. **Meta-Llama-3.1-8B-Instruct**：不同架构的 architecture generalization 首选；
4. **GPT-OSS-20B**：仅当 Llama 的预注册 clean-capability gate 不通过时启用；
5. **Gemma-4-E4B-it**：当前暂缓，不为其新建环境或复制权重。

Qwen3-32B 与 Llama 权重已经存在于 A100 服务器，因此正式计算统一放在 A100，
不重新下载模型。GPT-OSS 权重当前仅在 A800；若触发后备方案，只允许在确认临时空间
安全后一次搬运一个模型，并在验收完成后释放临时副本。

### 7.2 已完成的 Qwen3-32B 工程验收

2026-09-22 已在 A100 GPU0 完成不计入论文统计的 bounded selective-vLLM smoke：

- vLLM 0.11.0 正确识别 `Qwen3ForCausalLM`；
- 单卡加载 61.03 GiB 权重；
- 8,192-token context 下剩余 11.93 GiB KV cache（48,864 tokens）；
- R2/R3/R4 均完成生成；
- R2/R3 第一生成 token 一致，late-block boundary invariant 通过；
- smoke 结束后 GPU 显存正常释放。

该结果只授权进入下一阶段验收，不是 scientific effect evidence。正式 target-model
实验仍须使用冻结题目、冻结 drafts、冻结 seeds，并在生成前写出 manifest。

### 7.3 Llama 的预注册准入 gate

Llama 首先运行与 Qwen3-32B 相同的 selective backend smoke。通过后，只在当前冻结的
8 个 Game24 confirmation 问题上运行 R0 capability gate（2 seeds，共 16 个单位），
不查看 R2/R3：

- R0 accuracy 至少 `8/16`；
- officially parseable 且正常完成至少 `15/16`；
- selective smoke 的 same-text contract、mask metadata 与 R2/R3 first-token invariant 全部通过。

满足全部条件才运行 Llama 的 R2/R3。若不满足，则按预先约定切换到 GPT-OSS-20B，
而不是根据 R2/R3 效应大小选择模型。

### 7.4 跨模型实验矩阵

- Qwen3-32B：冻结的 8 个 Game24 confirmation 问题 × 2 seeds × R0/R2/R3 = 48 requests；
- Llama（通过 gate 后）：同一 8 题、同一 drafts、同一 seeds × R0/R2/R3 = 48 requests；
- 各模型分别报告 `R0-R2` 与 `R3-R2`，再检验 model × access interaction；
- 不把不同模型的 requests 简单合并成扩大后的独立样本量。

target-model generalization 的优先级仍低于：

1. 独立复现；
2. deletion/reset；
3. correct-draft specificity。

---

## 8. 当前暂缓方向

在上述主链路完成之前，不再优先推进：

- X / CALC 局部 mask；
- validity / rejection / re-endorsement taxonomy；
- 新的人类定义错误结构；
- 为追求正结果继续扩 UFT short-draft；
- 额外 vLLM 性能优化；
- 无关第二任务扩展。

局部 mask 历史保留为 exploratory negative evidence：

> human-defined local error regions did not yield stable transmission responsibility.

---

## 9. 当前可防守的论文主张

如果后续实验支持，最终主张应保持克制：

> **Even after full prefill exposure to a failed trajectory, removing its direct accessibility during subsequent generation can substantially reduce contextual drag, indicating that continued access—not only initial exposure—can make a causal contribution to the effect.**

中文：

> **即使模型在 prefill 阶段已经完整接触失败轨迹，切断后续生成阶段对该轨迹的直接访问仍可能显著缓解 contextual drag，说明该效应并非完全由初始暴露决定，持续访问本身可以构成一个可干预的因果贡献。**

不能声称：

- prefill 不重要；
- failed information 被完全擦除；
- 已定位内部错误 representation；
- blocking 是普遍更优的 decoding method；
- 对所有错误历史都有效；
- 比 deletion/reset 更高效或更实用。

---

## 10. 当前执行顺序

冻结当前计划为：

1. **完成新 Game24 与 MATH 已冻结实验**
2. **确认 R0 > R2 与 R3 > R2 是否在独立样本上成立**
3. **加入 deletion/reset control**
4. **加入 correct-draft full vs late specificity control**
5. **若主效应稳定，再做 blocking-onset timing probe**
6. **在 A100 上依次做 Qwen3-32B 与 Llama target-model generalization**
7. **Llama 未通过预注册 R0 gate 时，才启用 GPT-OSS-20B 后备方案**
8. **不合适的外部构造实验仅留内部审计，不进入论文**

当前研究重点已经从：

> “whole-draft mask 是否有效”

推进到：

> **“当 contextual drag 确实发生时，continued access 是否是其中一个可干预因素，以及该效应是否具有错误特异性和时间依赖性。”**

这应作为后续实验设计和论文组织的主线。
