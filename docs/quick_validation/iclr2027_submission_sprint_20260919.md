# ICLR 2027 一周冲刺计划

版本：v1，2026-09-19。用户已确认摘要提交，并同意后续尽量按此计划执行；发生调整时更新本文件及研究入口。本文为当前时间与范围的主计划，取代此前“先取得30–50题再开始其他验证”的顺序；既定科学配置与数据保留规则仍有效。

全文截止：2026-09-26 19:59，北京时间（Sep 25 23:59 AoE）。内部主要结果冻结目标：9月24日。官方入口：https://iclr.cc/Conferences/2027/AuthorGuidelines 。

## 研究问题与交付目标

主线：trajectory-level failed-trace computational access control。

- H1：R0 > R2，验证适配prompt、error signal下的residual drag。不能忽略两条件提示语不同，也不能声称已排除所有提示语效应。
- H2：R3 whole late_block > R2，验证持续访问阻断能否改善后续解题。不能据此证明唯一传播机制。
- R4 whole path_block是干预时机诊断，不预设优于R3。
- 源草稿暴露范围是最终答复正文，不包含源模型的Thinking段；文本/token/position保持不变，logical attention blocking不是KV删除。R3首token仍来自完整prefill logits。

目标交付：一个独立新题主实验，一个正确草稿控制，两项有边界的跨任务/模型验证。实验数量不是论文质量或录用的保证。旧局部X/CALC/validity等作为exploratory history，不继续增加局部mask类型。

## 时间与执行顺序

| 北京日期 | 任务与停点 |
|---|---|
| 9月19–20日 | 完成当前Batch02整批32B；pooled人工审计；冻结首批草稿后启动主实验。准备正确草稿控制、第二任务管线和32B selective correctness smoke。 |
| 9月20–21日 | 最多再补一个已冻结的32题双anchor批次；同步写方法、设置与pilot结果。 |
| 9月21日晚上 | 停止继续发起Game24筛题，冻结届时完整、已审计的合格题集；在途批次若不能按时完成，记录并决定完整处理方式，不以输出成败挑选部分题。 |
| 9月22–23日 | 完成主实验、正确草稿控制和可行的第二任务/模型验证。 |
| 9月24日 | 冻结主要结果；核查question-cluster CI、paired transitions、输出异常、图表与原始记录。 |
| 9月25日至截止 | 正文、局限性与复现说明；只处理影响结论的correctness问题，任何追加生成需单独记录理由和预算。 |

Game24新确认集目标20–30独立题，不包含旧七题pilot；不是“20题必然足够”。若预算/时间内不足，报告实际数量，不降门槛。原十题为开发集，七题为Stage-1 pilot，两者不并入新确认集主指标。

可以逐批执行主实验，无需等待所有筛题完成。但后续candidate order、采样预算和筛选规则不得受前批intervention结果影响；统一分析不得选择性保留有恢复的题。若根据新结果修改假设或干预，另立版本并重新界定确认集。

## 实验矩阵

| 优先级 | 实验 | 目标规模 | 新生成预算（不含筛题/smoke） |
|---|---|---|---:|
| 必须 | Game24，Qwen3-8B，R0/R2/whole-late/whole-path | 20–30题×2 paired seeds×4条件 | 160–240 |
| 必须 | 正确草稿full access vs whole-late | 预先固定10–15题×2 seeds×2条件 | 40–60 |
| 高 | 第二任务，8B，R0/R2/whole-late | 15–20题×2 seeds×3条件 | 90–120 |
| 高 | Game24，第二模型，R0/R2/whole-late | 预先固定10–15题×2 seeds×3条件 | 60–90 |

总计350–510次评测生成，另计baseline acquisition与correctness smoke。该矩阵是计划范围，不表示这些任务已经启动。正确草稿control需要在开始前冻结prompt：不得向模型错误宣称正确草稿为错误；若使用truthful或neutral信号，应明确其与失败草稿条件的差异，不能把差异直接归因为内容正误的纯交互。所选题不能依据intervention恢复大小挑选。

第二模型优先Qwen3-32B：权重和ordinary推理已有，selective干预需独立正确性smoke与实测成本；只能支持同家族跨规模，不声称跨模型家族泛化。第二任务优先核查现有MATH500数据、prompt、scorer与失败草稿产率；若不合适，讨论替代而非自动fallback。不铺开完整model×task交叉矩阵。

R3/R4已有时机对照，R0是无历史参照。优先正确草稿控制，不为数量追加ablation。R1时间允许时补充。正确草稿控制关注错误/正确历史下阻断效果是否不同，不预设阻断正确草稿一定有害；长度、信号与草稿来源差异必须报告。

## 数据与统计约束

- 同一完整candidate batch，两anchor各题各n16；不按8B outcomes决定是否采32B。
- Formal eligibility：跨模型合池，至少2条正常EOS、Thinking可解析、官方True；至少2条正常EOS、Thinking可解析、官方False且人工确认实质失败。
- 超长、未解析、未评分、纯格式失败不自动视为真实failed trace。不同统计维度避免重叠相加。
- 每题按固定随机规则从审计池抽一条失败正文；来源、文本hash、选择规则在干预前冻结。固定规则参见whole_trace_acquisition_plan_20260919.md。
- 四条件同一selective后端、相同采样配置；不用ordinary screening R0替代配对R0。
- 主指标accuracy、R0−R2、R3−R2；R4−R2与R4−R3作为次要时机诊断。报告paired transitions、按question聚类bootstrap、EOS/parse/scorer异常。error-formula reuse为secondary，不按其选择样本。
- 题目是独立统计单位，增加seed不等于增加独立题。小集、新任务不确定性如实报告，不以显著性决定何时停止或扩样。

## 资源与当前状态

七题56次selective评测实测9633秒（2.68小时）。按类似输出长度，8B Game24主实验160–240次约8–12 GPU小时；不能据此推算32B或MATH500。当前32B Batch02追加512次估14–18小时，共享GPU竞争/输出长度可能延长。第二任务采集成本未验证，是主要预算不确定性。

仅有一张可用GPU4时，模型生成实际串行；CPU数据审计、写作和准备可与GPU任务同时进行。优先级为主实验与关键控制，其次泛化验证。不承诺一周内全部目标必然完成；若资源冲突，在剩余预算下显式调整范围，不降低筛选门槛或偷偷改模型配置。

已运行：Batch02完整32题Qwen3-32B×16普通vLLM。现有脚本完成后自动汇总并恢复resident，停在pooled人工审计点。本文不改变已运行队列。Batch03名单已冻结但未启动；第二任务、32B selective评测、正确草稿control尚未启动。后续按本计划推进，关键未定设计先形成具体配置，遇到关键取舍与用户确认。

## 变更记录

| 日期 | 变化 | 原因与影响 |
|---|---|---|
| 2026-09-19 | v1：从先集齐30–50题改为时间限定的20–30题目标、分批主实验，加入正确草稿控制与第二任务/模型计划 | 截止日期约一周；减少筛题占用，保留写作核查时间。用户要求记录、GitHub同步并持续更新。 |

以后每次修改记录日期、原因、涉及题集/配置、是否已看结果、预算和运行状态。同步更新docs/RESEARCH_STATUS.md与MASTER_EXPERIMENT_LOG.md；不覆盖旧冻结manifest或原始结果。
