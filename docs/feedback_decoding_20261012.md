# 反馈方向能否控制历史利用：自然生成 MVP

**结束更新：**共享24 GPU小时上限触发停止，保存73/80请求，模型进程
已退出；7缺失不补跑。固定幅度MVP未获支持，完整结果和有限题单
缺失边界见[结束报告](feedback_decoding_results_20261012.md)。以下为冻结
设计和历史启动记录，不是继续运行的授权。

## 为什么值得检验

原 Contextual Drag 已证明错误历史有害、二元反馈不足、识错后可能仍受
影响。继续重复这些现象不是新贡献。本轮检验一个更具体的解释：反馈
在条件分布中可能已有正确方向，但不足以克服草稿内容诱导。若保留
全部草稿、只增强对反馈方向敏感的预测成分就能恢复，后续研究可以
从一般历史屏蔽转向反馈如何调节历史利用；这仍不是神经机制的证明。

例如旧式 `8/((5-1)/(13-1))` 数值为24，却多用了一次1。模型两路
读取完全相同的旧草稿，只有提示中的 `INCORRECT` / `CORRECT` 不同。
两路始终接收同一条已生成推理前缀，但 KV 计算独立。

对当前条件的下一 token logits z 与反事实条件 z'，使用
`z_guided = z + (z - z')`，幅度固定1，不调参。不加额外可信度筛选、
plausibility mask或外部逐 token verifier。TRUE表示反馈符合草稿最终
答案的精确评分；FALSE故意反转评分，作为因果方向控制。

## 创新边界与相邻研究

- [Instructive Decoding](https://arxiv.org/abs/2311.00233) 已有原指令与噪声／
  反向指令分布的对比。本轮**不将公式或双 KV 实现称为新算法**。
- [Execution-Guided CFG](https://arxiv.org/html/2506.10948v1) 已放大代码执行
  反馈。本轮不用逐步执行、beam search或运行轨迹；二元反馈可控性本身
  才是待检验问题，普通收益不能被包装成首次反馈指导解码。
- [Draft De-anchoring Decoding](https://analemma.ai/papers/6bed6fc1-48fc-4175-98ce-c7eb56f963ea)
  公开摘要报告有／无草稿分布插值的负结果。此来源为 Analemma 平台，
  当前只核实公开摘要，未获取全文，不能把其归因当已确证机制。本轮
  两路均保留同一草稿，隔离的是反馈方向，避免将内容缺失作为对照。
- [同模型 Game24 公开研究](https://devonbrackbill.com/blog/contextual-drag/)
  已分析数字复用、虚假自检及训练纠正后的搜索瓶颈。该博客是作者的
  实验报告，不等于独立验证；但相关观点不能再声称首次提出。

潜在增量是：能否证明二元反馈的方向具有可利用的、双向的行为控制
作用，并在保留正确历史利用时帮助错误历史纠错。这需要实际结果和
后续独立材料，不保证单个 Game24 MVP 足以成为 ICLR 贡献。

## 冻结材料与实验

- Qwen3-8B Thinking，BF16，HF SDPA，单张 GPU4 A100。全部条件同后端。
- 沿用 candidate_adoption 已冻结打乱顺序的**前12题**，不按干预效果选题。
- BAD使用原自然失败草稿。GOOD取既有 COUNT_CLEAN 正确 continuation
  的最终草稿，按历史 seed 顺序取第一条；8题可用，4题缺失保留，不补生成。
  二元真值来自最终表达式，未证明草稿中每个推理句均正确。
- 每份历史：FULL_TRUE、FULL_FALSE、GUIDED_TRUE、GUIDED_FALSE，共80请求。
- 单 paired seed `20261022`；temperature=.6、top_p=.95、top_k=20；
  **8192新token**；保留Thinking，不提供正确解给BAD条件。
- 每批4请求，各两路独立KV。FULL也执行两路并取幅度0，保持实现布局
  一致，其额外计算包含预算。结束即保存每请求原始输出、评分和来源。
- 沿用共享24 GPU小时总预算，当前剩余以远端budget.json为准。按每秒
  50个选出token、加载300秒估计，上限3.72小时；实际达到总预算立即停，
  报告未完成请求，不自动重试。这里不是吞吐保证。

## 结果如何改变决策

首要读取BAD的 GUIDED_TRUE−FULL_TRUE 正确率；同时独立报告GOOD同一
差值、恢复与损伤、截断、旧式复用及每题方向。题目是统计单位。

反馈方向控制量：每类历史分别计算
`(GUIDED_TRUE−FULL_TRUE)−(GUIDED_FALSE−FULL_FALSE)`。
TRUE有益、FALSE更差才符合反馈方向被增强的预测；两者都改善更符合
一般解码变化，不能解释为反馈利用改善。若BAD无收益，停止固定幅度
MVP，不扫系数；若GOOD受损，不能宣称打破利用率权衡。

GOOD来自既有clean成功，且覆盖仅8题，存在选取偏差；不得把两类
不同覆盖的准确率合成总收益。一次探索性比较或GOOD损失不显著都
不证明普遍机制／无损。在BAD改善且方向控制一致时，才值得下一轮
独立材料与等计算基线。当前不预先承诺扩大题量、跨任务或训练。

本轮没有额外HF CLEAN条件；历史vLLM CLEAN成绩只能作背景，不能
当同后端因果对照。因此GOOD准确率保持仅证明在这些正确草稿输入上
未观察到明显损伤，不能独立证明模型实际利用了草稿，更不能宣布
已打破鲁棒性与利用率权衡。完整结论还需要后续独立的利用检验。

## 操作入口

准备与查看：`python scripts/run_feedback_decoding_20261012.py --prepare` / `--status`。
CPU分析：`python scripts/analyse_feedback_decoding_20261012.py`。生成
`paired_analysis.json`（逐题恢复/损伤与来源式匹配）、
`outcome_change_cases.json`（所有结果变化案例及原始行号）、`analysis.md`。
CPU分析另存 `completion_audit.json`（未完成请求及原始输出／评分覆盖）和
`missing_outcome_bounds.json`（冻结题单上未完成二元结果取最好／最坏值的
精确效应边界）。边界不是置信区间，不能用于总体推断；已有length结束
仍按实际失败计分，未完成请求不直接算错，缺失GOOD历史仍不补题。
这些是事后缺失性分析，不改变首要指标或停止规则。生成token长度统计
同样只作事后描述，不将长度变化解释为失败原因或GPU耗时。
运行中只作部分结果快照；整批结束前不据完成子集决定方法是否有效。
启动：`bash scripts/start_feedback_decoding_20261012.sh`。
远端 tmux：`game24-feedback-decoding-20261012`。
原始结果：`outputs/generation-diagnostics-20261005/feedback_decoding/`。
共享预算：`outputs/generation-diagnostics-20261005/budget.json`。
GPU空闲时恢复本项目常驻；其他用户任务不动。具体是否已启动以进程
及运行日志为准，本设计文件不是启动证明。

启动记录：2026-10-12 已提交并核实launcher PID887884、runner PID887928；
GPU4只有本项目空闲常驻（父PID233484、engine233557）时正常退出并
释放，随后模型加载完成，首批解码步数已由0推进至1280。状态running，
80请求；这条是启动时快照，实时以run_state及进程为准。
运行中run_state的active字段列出当前整批成员，其中可能含已经逐请求
保存的成员；实际完成数以completed和behaviour.jsonl为准。
