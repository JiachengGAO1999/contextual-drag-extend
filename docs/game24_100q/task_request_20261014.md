# 研究任务：重建 Contextual Drag 的 Game24 数据池，获取至少 100 道独立合格题，并开展初步机制探索

## 一、任务背景与目标

我们决定重新推进此前提交 ICLR 2027 的 Contextual Drag after Error Feedback 研究。

此前的核心实验是：

- R0：无历史的 clean solve。
- R2：完整失败草稿 + 明确错误反馈，生成期间持续访问失败草稿。
- R3：保持完整文本、位置和 prefill 不变，从第二个生成 token 起，阻断对失败草稿 KV 的直接访问。

此前在 23 道经过筛选的 Game24 题目上观察到：

- R0：87.0%
- R2：39.1%
- R3：78.3%

但我们目前面临的首要瓶颈不是干预方法，而是基础数据池过小、筛选成本过高，导致后续机制探索缺少足够的独立样本。

**本次任务的第一优先级，是建立至少包含 100 道独立合格 Game24 题目的高质量数据池。**

在完成这个目标之前，不再投入大量资源尝试新的 attention mask 或局部机制。

完成数据建设后，再进行一次有明确边界的小规模后续探索。

本次允许实际修改代码、运行必要的 baseline 生成、执行数据审计和有限的后续实验。不要停留在提出计划。所有计算都必须有日志、断点续跑和资源控制。

---

## 二、首先审计已有仓库和历史数据

项目仓库：

`JiachengGAO1999/contextual-drag-extend`

原论文仓库：

`princeton-pli/Contextual-Drag`

开始前：

1. 检查当前实际工作目录、Git 状态、服务器最新结果和已有实验文件。GitHub 远端可能没有同步最新实验。
2. 阅读 `docs/RESEARCH_STATUS.md`、`MASTER_EXPERIMENT_LOG.md` 以及 `docs/quick_validation/` 中的协议和数据采集报告。
3. 重点审查：
   - `protocol_parity_report_20260917.md`
   - `batch03_interrupted_audit_20260924.md`
   - `batch04_sampling_decision_20260924.md`
4. 核对已有 Batch02、Batch03 及其他 baseline pool，确认哪些数据可以合法复用。
5. 核查已经进入论文、开发或机制探索的题目，防止混入新的独立验证集。
6. 不修改或覆盖原 ICLR 投稿实验的已冻结数据、manifest 和结果。

请先得出明确结论：

- 当前究竟有多少道未受干预结果影响、满足统一资格条件的独立题目？
- 哪些已有生成输出能够直接复用？
- 哪些题目存在缺失 anchor、采样配额不完整或错误标签待审查的问题？
- 重新筛选到 100 道需要哪些额外计算？

不要因为以前已经筛过某道题，就自动认为它具有正式合格资格。

## 三、严格复核原论文筛选协议

请阅读原论文 Game24 实验相关章节，并以官方代码为主要实现参照。

我们此前已经确认的原论文主要设置包括：

- Game24 原始题目共 1,362 道。
- 原论文合格题目共 653 道。
- Anchor 模型为 Qwen3-8B、Qwen3-32B 和 Nemotron-32B。
- 官方初始采样脚本默认每个 anchor 对每道题生成 16 次。
- 跨 anchor 合并同题响应。
- 每道 eligible question 至少需要 2 条正确响应和 2 条错误响应。
- 允许 cross-model failed drafts。
- 需要正确处理 Thinking 解析、生成完成状态与答案评分。

注意：公开脚本的默认值不必然等于作者实际全部运行的设置。不可声称我们已经恢复了作者未公开的完整原始数据。

特别核对以下问题：

1. 题目 ID 与数字 multiset 的映射。
2. 各 anchor 的 prompt、采样参数和 max tokens。
3. 正确/错误响应的分类规则。
4. scorer 返回 False 与 None 的区别。
5. incomplete / malformed / truncated responses 的处理。
6. Thinking 与 final answer 的拆分。
7. 原始错误草稿是否为实质性错误，而非单纯格式错误。
8. 生成草稿的 source model 与被测试的 target model 是否一致。

建议建立两套明确区分的资格统计：

**Protocol-compatible eligibility：** 尽可能按照原论文公开代码和规则判断。

**Strict substantive-error eligibility：** 至少 2 条真正正确的完整响应，以及至少 2 条完整、可解析、人工审计或可靠程序验证的实质性错误响应。

新研究主要使用第二套结果，但必须同时报告两套结果之间的差异。

如果必须调整原论文协议，明确标为 adapted protocol，不得称为 exact reproduction。

---

## 四、优化采样策略，优先获取更多独立题目

我们已有 Batch03 的历史证据：

在 22 道完成双 anchor 采样的题目上，每模型采样 4、8、12、16 次时，分别得到 2、6、7、7 道满足严格资格的题目。

这提示：一味提高每题生成次数可能不如扩大独立题目的覆盖范围划算。

因此，不要直接运行：

`1362 questions × 3 models × 16 samples`

请优先完成以下工作。

### Step A：历史采样效率复盘

对现有完整数据重放每 anchor 4、8、12、16 次的采样前缀。

计算：

- 每个阶段新增的 eligible question 数量。
- 每个阶段的独立题目合格率。
- 各 anchor 的边际贡献。
- 各阶段生成 token 总量。
- 实测 GPU-hours / eligible question。
- 不同采样次数下的漏检率。
- 追加采样的边际收益。

尽可能用实际运行日志衡量成本，不要只用模型参数量或理论 tokens/s 推算。

### Step B：制定正式采样策略

优先考虑双 anchor：

- Qwen3-8B
- Qwen3-32B

两者已有工程基础和模型资源。

Nemotron-32B 如果已有合法可访问的模型资源，可以纳入；否则不要因为缺少第三个模型就卡住整个数据建设，也不要未经授权下载大型模型。

可以选择：

- 每模型固定 8 次的广覆盖筛选。
- 每模型固定 12 次。
- 预先定义的 adaptive sampling：先用较少次数广泛筛选，再给接近资格门槛的题目补充生成。

选择依据必须是历史数据支持的 **eligible questions / GPU-hour**，而不是个人直觉。

Adaptive sampling 的补样规则、样本顺序、停止条件和最大配额必须在新批次开始前冻结。不得为了某道题出现期望结果而临时追加生成。

### Step C：分批执行采集

先执行一个有限的新题 pilot，检验实际合格率、吞吐和成本。

通过 pilot 审计后，再逐批扩大到 100 道合格独立题。

每批完成后自动生成报告，包括：

- 已处理原始题数。
- 新增合格题数。
- 累计合格题数。
- 正确、实质性错误、格式错误、None、截断等数量。
- 各模型贡献。
- 实际生成 tokens 和 GPU 耗时。
- 达到 100 道目标的剩余成本预测。

不要把不同随机 seed 的同一道题算作不同独立题目。

如果已经覆盖可用的题目宇宙仍无法获得 100 道，或达到目标的估计计算成本明显超出可用资源，应暂停并报告实际结果、原因和替代方案，不得降低资格标准硬凑数量。

---

## 五、计算资源与工程要求

我们主要只有一张 80GB 级别 GPU 可用，不能假设存在额外计算资源。

优先复用已有的 vLLM baseline 推理管线，不要为了 baseline 采样使用低效的逐 token HF 实现。

注意：

1. Baseline 生成不需要运行 selective-attention backend。
2. 保留 selective backend 供后续 R2/R3 实验使用。
3. 按模型顺序加载与执行，不得假设 Qwen3-8B 和 Qwen3-32B 能同时常驻同一卡。
4. 对大模型先做小批次完整生成测速。
5. 使用合理 batching，但保证每条记录的 seed、模型、生成参数和采样顺序可追踪。
6. 每条生成及时持久化。
7. 必须支持 interrupted run 的幂等恢复。
8. 不重复生成已完成且符合相同协议的记录。
9. 磁盘不足时暂停，不自动删除已有研究数据和模型权重。
10. 不擅自占用其他用户 GPU，不擅自搬运或下载大型模型。

先完成 pilot 成本测量，再判断能否在当前资源条件下完成 100 道。

禁止为了赶数量省略必要的生成完成性检查、错误审计和题目去重。

所有长任务需要周期性更新机器可读进度；出现异常时只停止相关作业，不影响其他进程。

---

## 六、最终数据资产要求

最终不只需要一份 100 道题目 ID 列表。

请建立可重复使用的数据资产，包括：

### 1. Question Manifest

每道题包含：

- Canonical question ID
- 原始数字组合
- 来源及去重信息
- 各 anchor 采样次数
- 各 anchor 正确、错误、无效响应数量
- Protocol-compatible eligibility
- Strict eligibility
- 是否属于历史开发集
- 是否已被用于后续干预
- 是否纳入新数据池
- 纳入或排除原因

### 2. Trajectory Pool

保留所有原始生成响应与元信息，包括：

- 模型名称与 checkpoint
- prompt
- sampling parameters
- seed 和 response ID
- 完整生成文本
- final answer
- Thinking parsing status
- finish reason
- correctness
- substantive-error classification
- 原始文件路径及记录标识

不要只保留评分后的公式，因为未来仍需要回溯实际错误轨迹。

### 3. Frozen Eligible Dataset

目标至少 100 道独立合格题。

每题至少关联两条有效正确响应和两条有效错误响应，并确保可以追溯到原始生成。

不要根据后续 R2/R3 的效果挑选草稿。

需要额外标注 source model、target model 及 self/cross-model 属性。

### 4. Data Split

将新的合格题目按照固定随机种子划分为：

- Development：20 道左右，用于探索。
- Held-out：其余约 80 道，用于后续确认和复现。

如实际最终多于 100 道，可以相应扩大 held-out。

所有划分必须在查看新干预结果之前完成。

以前 23 道已用于论文的筛选样本保留为 historical/development evidence，不计为全新 held-out。

---

## 七、完成 100 道后，进行有限的后续探索

在基础数据采集完成、数据冻结和审计通过后，才进入这个阶段。

不要马上开展复杂的局部 mask 研究。

先在新 development set 上回答三个问题。

### RQ1：原来的 R0/R2/R3 效应能否在新数据上重复出现？

对 development set 运行：

- R0：clean solve
- R2：failed draft + error feedback + full continued access
- R3：相同文本、prefill 和 first token 的 late blocking

初步采用每题 2 个 paired seeds。

如果 development set 为 20 道，则基础实验约为：

`20 questions × 2 seeds × 3 conditions = 120 generations`

如果资源有限，可以先执行 10 道题的冻结子批次，审计后再完成其余题。

报告：

- R0、R2、R3 正确率。
- R0−R2（是否发生 drag）。
- R3−R2（是否得到恢复）。
- 配对恢复和损伤案例。
- Question-level bootstrap confidence intervals。
- Finish reason 和生成长度等诊断指标。

特别注意：100 道 eligible 题不意味着其中全部存在 contextual drag。必须报告全体结果，不能只留下 R3 恢复的题目。

### RQ2：不同错误草稿是否产生不同的干预效应？

利用每道题已有的多个 failed drafts，探索：

- 同一题不同 draft 的 R2 表现是否一致。
- self-model draft 与 cross-model draft 是否存在明显差异。
- 错误类型和错误草稿长度是否与 drag 相关。
- 不同 draft 是否导致 R3 恢复、无变化或损伤。

优先使用已有生成结果和 CPU 统计。

如果需要额外生成，限定在少量事先固定的题目和草稿组合中。

不能依据某份 draft 的干预表现决定是否将它纳入主分析。

### RQ3：是否存在值得继续研究的稳定异质性？

可探索的维度包括：

- Failed draft source model。
- Draft length。
- Error morphology。
- Clean solving capability。
- Baseline error frequency。
- 历史内容是否存在可验证的有用信息。
- Drag severity 和 recovery magnitude。

这些首先是关联性探索，不要直接解释为内部因果机制。

如果看到稳定、有足够样本支持的现象，再提出一个成本可控的机制假设。

暂时不要重新启动以前已经失败的 X/CALC 大规模局部 masking，也不要重复尝试未通过 Gate 0 的候选评分方案，除非有新的证据证明其测量有效性。

本阶段输出一份探索报告即可，不要求马上实现新方法。

**保留 held-out set，不在这一轮上做探索性调参。**

---

## 八、输出报告与研究决策

请最终提供以下成果：

1. `DATA_ACQUISITION_AUDIT.md`  
   原论文与本项目协议对照、旧数据复用、历史采样效率审计。

2. `GAME24_100Q_ACQUISITION_REPORT.md`  
   新题采集策略、实际运行规模、计算成本、各阶段产率、100 道完成情况。

3. `game24_question_manifest.jsonl`  
   题目级 manifest。

4. `game24_trajectory_pool.jsonl`  
   保留原始生成的可追溯索引；若完整文本量较大，可采用分片文件并提供统一索引。

5. `game24_eligible_100.jsonl`  
   新冻结合格数据集。

6. `game24_split_manifest.json`  
   Development/held-out 划分。

7. `INITIAL_EXPLORATION_REPORT.md`  
   100 道完成后，在 development subset 上对 R0/R2/R3 和异质性的初步探索。

8. `NEXT_RESEARCH_DECISION.md`  
   根据实际结果，评估后续是否值得继续投入 Contextual Drag 机制研究。

文件可集中放在新建的 `docs/game24_100q/` 目录下，路径与已有仓库结构冲突时自行合理调整。

报告中必须包括：

- 已经完成什么。
- 哪些结果来自真实实验。
- 哪些只是估计或探索性观察。
- 实验规模、生成次数与 GPU-hours。
- 失败和异常情况。
- 数据选择偏差及其他方法学限制。
- 最值得追的 1–3 个后续问题。
- 明确 GO / NO-GO 判断。

对实验不成功、合格率低或新数据中 R3 恢复不明显等情况，也必须如实报告，不能为了延续旧论文结论而改变筛选规则。

---

## 九、执行优先级与最终要求

执行顺序必须是：

**现有数据审计 → 原文协议复核 → 采样效率优化 → 分批获取 100 道 → 数据冻结 → 小规模 R0/R2/R3 探索 → 下一步研究决策。**

本轮的主要交付物是可靠的 Game24 数据集，而不是新的论文故事。

100 道独立合格题是第一目标，不是允许无限增加 GPU 使用量的理由。所有扩大计算都应依据实际采样成本，并在达到资源、权限或科学有效性方面的阻塞条件时停止。

请尽量自主执行已经明确授权且资源允许的步骤，完成每阶段审计后继续推进，不要只提交计划或反复询问已知信息。

如果遇到必须由我决定的重大取舍，例如额外占用 GPU、下载新的 32B 模型、预计产生明显超出预算的计算成本，先提供明确的成本与收益分析，再停止在安全检查点。

**最终验收标准：**

- 有至少 100 道经过统一协议审计的独立合格 Game24 题目；如达不到，必须给出经验证的原因和实际最大成果。
- 数据集与原有开发数据和干预结果筛选相隔离。
- 所有题目和草稿完整可追溯、可复现。
- 具有明确的真实采样效率及 GPU 成本报告。
- 在冻结 development subset 上完成有限但真实的后续探索。
- 基于新数据判断 Contextual Drag 是否值得进一步做机制研究。

本次最重要的原则：

**先建立足够可靠的数据，再让实验结果决定研究方向，而不是让预期结论决定数据筛选。**