# Game24 数据采集审计（2026-10-14）

本轮为数据建设任务。已核实本地未提交状态、服务器最新 baseline、模型路径、磁盘与 GPU 进程；没有覆盖原 ICLR 数据、manifest 或结果。服务器快照为 `outputs/game24-100q-20261014/baseline_snapshot.zip`，443份文件逐一按服务器 SHA256 核验，保留完整原始文本和 token IDs。GitHub 远端不能代替该快照。

## 当前可用题数

原题源有1362个互不重复的数字多重集。逐条去重后 baseline 为 **3538 条 / 206 题**；其中 3136 条具有本研究 ordinary-vLLM 双 Qwen anchor 的采样参数与上下文配置。
原代码兼容合格 **37 题**，严格实质错误合格 **32 题**（包含历史开发）；剔除历史开发/实验材料、要求至少完成同一批双 anchor prefix8 后，新池当前 **2 题：643, 1119**。这是已核验快照下的成果，不是证明剩余宇宙最多只有2题。

合格题候选写在 `game24_eligible_candidates.jsonl`；`game24_eligible_100.jsonl` 当前为空且 split 为 `not_frozen_target_not_met`，不得称为已完成100题或已冻结验证集。全部正确/错误见证和原始文件行号可从 trajectory ID 回查。

开发材料隔离是保守的：包括已经使用的题和预先准备但未必执行的材料。对每题分别保存实际干预证据和历史材料证据；无本地干预证据不能等同于证明从未使用。服务器额外183个多重集的 manifest 盘点与本地记录合并；排除范围共 207 题。未按干预正确率、drag 或 recovery 大小选择题。

## 原论文与公开代码

核对[原论文v2 §2.1、附录A.2–A.3](https://arxiv.org/html/2602.04288v2)、[官方 initial_sampling.sh](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/initial_sampling.sh)与[聚合实现](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/aggregate_data.py)。论文要求同题跨anchor合池至少2对2错，允许 self/cross-model。公开脚本默认每模型16次，不等于已恢复作者全部运行配置。

| 项目 | 官方规则/实现 | 本次处理 |
|---|---|---|
| 题号 | 原论文缓存ID与ToT Rank不同 | canonical ID采用 `tot-rank:<Rank>`；跨源按排序数字多重集join，不能直接按同号join |
| Anchor | Qwen3-8B、Qwen3-32B、Nemotron-32B | 双Qwen适配；没有新下载Nemotron；不称exact reproduction |
| 采样 | Qwen .6/.95/top-k20，32768上下文；默认16 | 历史16及8全部保存；新pilot固定8；max generation为32768减prompt tokens |
| Prompt | qwen_math_prompt；原始problem字段未公开 | 现有R0模板+规范化Game24题文，实际chat prompt完整保存 |
| False / None | 聚合 `if correctness ... else ...` 把None也归入错误 | compatible重放 falsey；严格视图逐条数学复核，None本身不当实质错误 |
| 完成性 | stop + parsable_thinking | 保存原stop/eos映射、length、malformed、空final；截断不入门槛 |
| Thinking | 检查prompt+response的标签数，再取结束标签后的final | 原始thinking全文保留；未闭合thinking不得因存在式子补判合格 |
| 实质错误 | 原代码无人工审计硬门槛 | 最终选式用Fraction和AST核验用数/值；标量24和混合候选读完整final，不用未选择的正确备选救错式 |
| Source / target | self和cross均允许 | 每条记录标注 source model、target Qwen3-8B及self/cross |
| 后端 | 原文vLLM0.10.2 | 历史ordinary vLLM0.11；新异步默认worker，不加载selective backend；调度不同不保证逐token重现 |

官方聚合的False/None及格式误判差异意味着 compatible 37题不能直接替代 strict 32题。本次compatible-only五题为6、41、289、445、753，无strict-only题；不能把这5题的差异全部归因于None。严格结果允许明确认可且精确验证的正文正确式修复提取漏检，同时保留原官方标签；该适配改变了人群，已分别报告。只看到错误公式并不足以判定thinking全过程都错误，错误分类针对最终回答。

## 合法复用与缺失

- Batch02：8B与32B分属不同物理目录，按同题合并为一个logical batch；共1024条。原32B分块及8B全批参数兼容，但已用的开发题不进入新池。
- Batch03：保存864/1024条，8B512条、32B352条；22题双anchor完整、10题只有8B。缺失的160个32B配额不能视作已完成；满足2对2错但单anchor覆盖的5题122、200、764、1019、1171仍不是双anchor完整的新池成员。
- Batch04：服务器实际已完成512条；合并副本和chunk副本按生成身份去重。472原始True、35原始False、5原始None；9条截断。严格分类为472正确、30实质错误、1提取漏检正确、9截断。5题合格：50、353、643、1073、1119；50/353/1073已属于后续材料，当前只纳入643/1119。
- 早期HF或non-thinking：完整原文保留，但不能补ordinary-vLLM Thinking配额。原论文TED公式缓存缺原始轨迹/Thinking/prompt并经过后续输出过滤，不进入新独立数据池。
- 本轮新复核25条歧义final，全部绑定原记录SHA256。其余明确最终boxed公式由可靠程序检验；历史Batch03标量/混合最终式使用已冻结逐条决定，并重新检验。当前待审为 0 条，仍单列保守排除的歧义失败。

## 真实成本与前缀复盘

| 数据批次 | 独立题数 | 完整保存响应 | 严格合格题（含历史题） | 生成 GPU h | 含加载 GPU h |
|---|---:|---:|---:|---:|---:|
| batch02_dual_anchor | 32 | 1024 | 8 | 18.776 | 19.170 |
| game24-baseline-screen-vllm-20260917-retry1 | 24 | 96 | 0 | 0.372 | 0.403 |
| game24-batch03-dual-anchor-20260924 | 32 | 864 | 13 | 12.689 | 13.004 |
| game24-batch04-dual-anchor-screen-20260925 | 32 | 512 | 5 | 10.310 | 10.683 |
| game24-dual-anchor-20q-20260917 | 20 | 640 | 6 | 8.703 | 9.003 |

| 批次 / 完整题数 | 每 anchor 4次 | 8次 | 12次 | 16次 |
|---|---:|---:|---:|---:|
| batch02_dual_anchor / 32 | 7 | 7 | 8 | 8 |
| game24-batch03-dual-anchor-20260924 / 22 | 2 | 7 | 8 | 8 |
| game24-batch04-dual-anchor-screen-20260925 / 32 | 2 | 5 | 未采样 | 未采样 |

Batch03的8是22个双anchor完整题中的资格数，不是32题全部完整；另外5个partial合格只报告，不混入完整分母。早期2/6/7/7已被后续q122/q381最终选式复核纠正，当前重放2/7/8/8。
Batch02与Batch03在n8相对n16均漏1/8（12.5%）最终合格题；n12→16新增为0。独立题前缀token总量、每anchor单独资格、另一anchor加入的边际贡献在 `sampling_efficiency.json`。**prefix GPU-hours为null**：并发chunk wall time不能按记录重复相加或按token比例包装成实测前缀耗时。各prefix额外GPU耗时和 marginal eligible/GPU-hour没有足够日志可识别。

全批可测比较：Batch02 n16为8/19.170≈0.417 eligible/GPU-hour；Batch04 n8为5/10.683≈0.468。批次题目与调度不同，因此只能支持固定8作为成本审计pilot，不能证明8是最优。32B Batch04首chunk耗时约3.40h（含加载），存在明显长尾；新runner固定max_num_seqs1避免假定多序列长上下文能高效共存，改动效果必须由pilot实测。

## 复算

`python -X utf8 scripts/game24_100q_audit.py`

新增生成 0；新增GPU hours 0.000。历史采样成本不算作本轮新GPU开销。计时为用户作业占用单卡的wall时间，不是整台共享服务器GPU能耗测量；未保存的Batch03在途tokens/时间不在完成chunk汇总中。
