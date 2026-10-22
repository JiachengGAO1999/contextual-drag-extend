# 下一轮机制辨别：直接草稿读取、下游传输与一般扰动

> 2026-10-11 已完成46/46评分、23/23几何；最终记录已下载。
> 见[结果与研究决策](source_partition_results_20261011.md)。下文保留历史方案。

> 研究价值与后续路线以 [2026-10-10 用户确认的路线锚点](research_anchor_20261010.md)
> 为准。本批是检验核心命题的诊断入口，不因完成来源消融自动形成
> 论文贡献或启动更多局部搜索；下文冻结实验参数保持原样。

本轮起点：24 题真实生成中 FULL/草稿移除/非草稿匹配控制答对
9/17/16；候选相对控制的准确率和复用差区间均跨零。剩余共享预算
约 9.86 GPU 小时。不能由这些结果直接宣称有害 heads 或等效无效。

## 需要区分的解释

1. 旧构造信息通过草稿 value 直接传输，移除它会改变相关判断。
2. 草稿影响也进入草稿之后的提示词、已生成推理及当前 query 的表示；
   原 NON_DRAFT_MATCHED 控制可能同时削弱这些受历史影响的内容。
3. 两种干预主要改变一般计算、判断强度或后续轨迹，并不特异影响
   旧错误内容。

解释 2 是由因果 attention 的位置依赖提出的待检验假设，不能用来
事后宣布原控制无效，也不说明任何非草稿向量已经携带了错误路线。
原 CONTROL 与其结果始终保留。

## A. 整理现有 72 条轨迹（CPU，无模型生成，与 B 并行）

保留全部轨迹，按明确语义记录旧构造的引用/检查、正确拒绝、错误
认可、实际用于构造，以及最终答案。判断必须指向具体表达式；对
新构造的判断、假设句、转述与指代不清不能算旧路线重新认可。
没有事件、未结束 thinking、无算式回答分别记录。不把文本自述
当作内部状态或因果机制的证明。

优先读取候选相对 CONTROL 的 4 个恢复、3 个损伤及 2 个无算式案例，
用于找竞争解释；完整统计仍覆盖 72 条，不能只报这些精选案例。
例如已查看的 651 中 FULL/CONTROL 都把三次 12 当作两次，候选明确
指出多用了 12 并给出合法解；1261 候选指出旧式非法但仍截断。二者
分别说明正确检查可能有用，以及正确检查并不足以完成求解，均仅作
探索案例。原论文已报告验证未必消除 drag，不能把这一文本现象本身
重新命名为 novelty。

已提供 CPU 队列入口：

```bash
python scripts/prepare_mechanism_audit_20261009.py
```

输出 `outputs/generation-diagnostics-20261005/mechanism_audit/` 的
`audit_queue.jsonl` 与 `status.json`。关键词只检索候选片段，不能
自动判断重新接受；完整原文仍以 raw_source/raw_line 为准。人工
语义标注另存 `reviews.json`，不因重建队列覆盖。目前只准备队列，
不宣称 72 条已完成语义审查。这项复盘不改变已审查的原 23 个探针，
不作为来源分区重放的启动门槛；新的语义对照仍需在复盘后另行设计。

## B. 低成本检验来源分区，保留原比较

继续使用原 23 道可评分题的冻结自然前缀和候选，不根据新结果找
新事件、heads 或窗口。这仍是已见题上的机制辨别，不是独立确认。

将 attention value 来源分为：

- P：草稿开始之前的 prompt tokens，其 value 受因果 mask 保护，不能
  读取后面的草稿。
- D：原草稿 span。
- F：草稿结束后的 prompt tokens，可能在 prefill 中读取草稿。
- G：generated tokens，包括当前 query 的 self value，可能同时携带
  草稿影响和有效的新计算。

P 的 attention weights 仍由当前 query 决定，不能称作“完全不受草稿
影响”的控制。边界依据原 request，不新增哈希或修改提示。

| 条件 | 移除的 value 来源 | 状态 |
|---|---|---|
| FULL | 无 | 原分数复用 |
| DRAFT | D | 原 CANDIDATE 分数复用 |
| NON_DRAFT | P+F+G 的等 norm 方向 | 原 CONTROL 分数复用 |
| PRE_DRAFT | P 的等 norm 方向 | 新短重放 |
| GENERATED | G 的等 norm 方向 | 新短重放 |

只改变移除方向；相同 144 heads、幅度、generated-query 起点、固定
token 前缀及候选评分。新方向在相同 per-head、o_proj 前单位匹配
D 的 norm，保持该次局部 weights，不重归一化。源向量接近零时
记录不可解释的匹配，不选择替代题或位置。

主要比较事前冻结为 GENERATED−PRE_DRAFT 的拒绝/认可 margin 差；
DRAFT−PRE_DRAFT 和原 DRAFT−NON_DRAFT 为辅助。按题报告均值、
区间和方向，同时保留原 15 次认可/8 次拒绝的描述性分组，避免将
两种状态下相反的效应都解释为纠错。单个正均值不证明路线语义已被
定位；来源和功能不同的控制仍有局限。

同一次 FULL 重放只在原判决附近记录 D/P/F/G 的贡献 norm、D 与
其他来源方向的 cosine，以及经过 W_o 的真实扰动 norm。只保存
目标 queries 的聚合信息，不保存全 attention 或全序列向量。
可附加目标下一 token 分布熵作为判断强度的辅助指标；熵变化或
向量相似性本身均不能证明内容传输。当前 prefixes 已包含旧构造，
G 的作用也可能只是维持一般推理，必须在后续语义对照中辨别。

新增 23×2=46 个候选评分请求，外加最多 23 次目标 FULL 仪器化
重放；旧 69 个条件分数不重新生成。按前轮 69 请求约 0.80 小时
估算，新增约 1–2 GPU 小时（含加载及采集开销），不是阶段硬配额。
沿用单 A100/GPU4、原共享 24 小时截止、tmux、逐请求保存和不自动
重试规则；无训练、无完整自然生成。

### 2026-10-09 执行状态

来源分区实现和可执行配置已完成，已在 `sjtu-a100` 提交 GPU4 等待队列。
提交时 GPU4 的 PID 75036 属于其他用户（UID 1019），本项目 UID 1024；
未停止该任务。等待期间共享预算仍为 inactive，累计 14.14 GPU 小时，
剩余约 9.86 小时。预计上卡后 1–2 GPU 小时，无法据此推算排队结束时间。

CPU 针对性测试：8 passed、6 skipped；6 个小模型 A100 测试将在上卡后
先执行，计入共享预算，失败即停止。FULL 目标重放同时记录与原分数的
差值，用于检查旧分数复用是否一致，不另开一批模型验收。

- 实验入口：`scripts/run_source_partition_20261009.py`。
- 干预实现：`selective_context/diagnostics.py`。
- tmux：`game24-qwen3-8b-source-partition-20261009`。
- 输出：`outputs/generation-diagnostics-20261005/source_partition/`。
- 冻结记录：`manifest.json`、`reference_scores.json`。
- 增量结果：`scores.jsonl`、`geometry.jsonl`，逐请求保存。
- 进度：`runner.log`、`current_request.json`、`summary.json`；结束生成 `report.md`。

在服务器项目目录查看进度：

```bash
tail -n 20 outputs/generation-diagnostics-20261005/source_partition/runner.log
/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/run_source_partition_20261009.py --status
```

冻结主要比较为 GENERATED−PRE_DRAFT，固定 144 heads、幅度 1、原前缀和
原语义候选；不追加生成，不按本轮结果重选题目或组件。原 72 条自然轨迹
的全量语义复盘尚未完成，不能把关键词队列或代表性案例当成全量结论。

## C. 解释结果后再决定语义对照

若 GENERATED 与 NON_DRAFT 的作用类似且不同于 PRE_DRAFT，可优先
研究草稿之后位置参与维持旧路线的解释；仍需区分其携带旧错误内容
和维持一般当前判断，不能仅凭来源差异断言错误信息传播。
若 PRE_DRAFT 也产生类似变化，则优先检查一般扰动/判断强度解释。
若方向高度相似或 W_o 后幅度差异大，缩小对来源特异性的解释范围，
不反复新增对照寻找正结果。任何不确定结论都不能解读为等效。

只有明确了竞争解释，才设计同一构造的正确算术与错误数字库存判断，
或合法新构造与旧错误构造的语义对照。候选必须在上下文中成立，
不能拿不自然续写的概率差当正确性。必要时在同一关键前缀后做有限
自由续写，连接局部判断与后续路线。题单、事件规则和规模需在新
干预结果之前固定；不得按这批事后标签设计门控再用同批题验证。

暂缓扩模型、MATH、混合历史、大量多 seed 生成及进一步 head/窗口
搜索。研究目标是解释反馈后旧构造信息如何被继续利用、何时帮助
正确拒绝、何时维持错误路线。当前没有证据保证这些方向能形成
ICLR 级结论，后续还需可重复的内容对照与独立预测验证。

文献：[Contextual Drag](https://arxiv.org/abs/2602.04288)；
[activation patching 的指标与方法](https://arxiv.org/abs/2309.16042)。
