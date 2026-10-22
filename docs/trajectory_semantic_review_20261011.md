# 已有轨迹的定向语义复核（2026-10-11）

GPU 等待期间，对既有自动提取中全部7条“Thinking出现合法式、最终
仍复用旧非法式”的历史条件记录，检查合法式上下文、旧式验证片段和
最终选择。没有新增模型调用，未改变已排队协议。

这些记录来自4道题、3种表示，不是7道独立题；又按已有失败结果选入，
只能用于解释案例，不能估计一般发生率或确认干预效应。全文保存在
`outputs/generation-diagnostics-20261005/identity_mvp/generations.jsonl`及
`identity_alias/generations.jsonl`；自动片段及字符位置见
`identity_trajectory_audit/audit.json`。

## 复核结果

7条记录的所查片段都支持：模型不仅提到合法式，还把它作为可行答案；
但同时错误认可旧式满足原约束，最后选择旧式。因此，这组案例不能
直接支持“正确识别旧式错误后仍无法撤销”。未在所查片段确认识错，
也不等于证明整段轨迹或内部状态从未识错。

| 题号／条件 | 原始文件及行 | 合法候选 | 旧式与可观察问题 |
|---|---|---|---|
| 285／IDENTITY_HISTORY | identity_mvp，第1行 | 1+4+6+13 | 旧式`((13-1)*6)/(4-1)`多用1；映射后D出现两次，却列出A,D,C,B并声称各用一次 |
| 285／NUMERIC_HISTORY | identity_mvp，第2行 | 1+4+6+13 | 认可简单加法合法，又称旧式也正确，最终因使用更多运算选旧式 |
| 719／NUMERIC_HISTORY | identity_mvp，第22行 | 8*(7-5)+8 | 正确认可合法式用了两个8；旧式`8*(7-(5-8/8))`有三个8，却也称各数恰用一次 |
| 50／NUMERIC_HISTORY | identity_mvp，第40行 | 12+12+9-9 | 旧式`12*((12-9)-9/9)`有三个9；逐项列数时把`9/9`当成一个9，称草稿正确 |
| 577／IDENTITY_HISTORY | identity_mvp，第52行 | 6*(13-9)*1 | 认可合法映射`A*(D-C)*B`；旧式`(D-A+B)*(C-A)`重复A，却称四字母各用一次并选回旧式 |
| 285／VALUE_HISTORY | identity_alias，第1行 | 1+4+6+13 | 认可简单和式，仍称旧式正确，并以可能期待更多运算为由沿用它 |
| 50／VALUE_HISTORY | identity_alias，第19行 | 12+12+9-9 | 旧式`C*((C-D)-D/D)`重复第三个D；最终说明错误地写成“两C、两D” |

几处决定性原文（均来自本项目模型输出）：

- 285 IDENTITY：`Let me check if all letters are used once: A, D, C, B. Yes, all four.`
- 50 NUMERIC：`The second 9 is in (9 / 9).`，随后`Yes, each number is used once.`
- 577 IDENTITY：`Let me check if that uses all letters once: D, A, B, C. Yes.`
- 285 NUMERIC：`But the problem might prefer the more complex one. So I'll go with the one that uses multiple operations as in the draft.`

577还正确拒绝过另一个候选中“1用了两次”的问题；这不能当成识别了
当前旧式中“A用了两次”。识别对象必须对应，不能由一般错误措辞推断。

## 对下一轮解释的约束

竞争解释应优先保留“旧候选的资源检查错误”，而不是默认搜索无解或
识错后撤销失败。有些记录还附带复杂度偏好／沿用草稿的选择理由，
但这是输出中的理由，不证明因果机制，也不据此再开一批小案例实验。

已排队30题两阶段实验无需改变，其结果按以下顺序解释：

1. 同候选下若旧式被判合法，先检验历史是否增加这种错误；无历史也
   同样出错时，不能称为历史特异的验收失败。
2. 两个合法性判断均正确却选旧式，才是可观察的判断／选择不一致。
   即使出现，也不直接等同于内部已经识错。
3. 同候选判断与选择正常、自然生成仍错时，候选可用性、搜索以及任务
   格式差异都保留，不能继续把结果强行解释为验收失灵。

这是一次缩小误读空间的证据更新，不是新的方法正结果或ICLR贡献。

## 同步核对的创新边界

以下为2026-10-11重新查阅的原始论文来源，不是全量文献综述：

- [Contextual Drag](https://arxiv.org/html/2602.04288v1)，第4节已经分别
  研究外部错误信号及事后自我识错，说明仅有错误信号不足以消除拖曳。
  因此，本项目不能把“被告知错误却仍受影响”作为新增发现。
- [How Well Can Reasoning Models Identify and Recover from Unhelpful Thoughts?](https://aclanthology.org/2025.findings-emnlp.370/)
  已比较有害思维的识别和被注入后的恢复能力。一般的识别／恢复落差
  也不是空白；我们需要更具体、可检验的失败环节及解释。
- [ThinkBrake](https://aclanthology.org/2026.findings-acl.1095/)
  已研究正确中间答案被后续推理覆盖，并提出基于概率边际的停止方法。
  因此，“想到正确答案但最终答错”本身及普通提前停止方案不够新。

据此，当前候选实验属于辨别工具。只有结果支持历史如何改变特定
约束判断／采用，并能产生跨题、自然生成中的新预测，才值得发展为
解释主线；实验整齐、候选高分、普通prompt增益都不能代替该贡献。
