# Gate 0 Memo：Controlled Task and Measurement Feasibility

日期：2026-10-13。暂定主线：**Error-Feedback Credit Assignment in LLM Reasoning**。

研究问题是同题修正时，局部错误反馈对历史计算的影响是否跨越计算有效性与依赖边界、沿记录者来源边界外溢。来源抑制、依赖选择性修正、一般不信任、答案复制和计算不足均保留为竞争解释。本 Gate 不选择其中任何一种作为既定机制。

本轮仅冻结材料并验证测量；完成后暂停。没有运行完整来源 × 反馈矩阵，没有正式机制实验、训练、新机制干预或 Selective vLLM 实验。

**结论：Gate 0 未通过，建议暂不进入 Gate 1。材料控制与 B 辅助读出可行，但当前短生成协议的 Clean 联合正确仅 9/32，12/32 截断；错误历史条件的 Y 正确仅 2/32，存在地板问题。** 这是否定当前测量协议的推进资格，不是否定或支持来源外溢假说。

## 1. 具体任务与精确真值

32 道新生成题均为无循环、无分支条件、无除法的整数计算。A/B 各自仅依赖本分支之前的寄存器；Y = 3A − 2B，确实依赖两者，任何非零 A 错误均不会在 Y 中抵消。

冻结题 G0-001：

```text
A0 = 79        B0 = 45
A1 = A0 * 7    B1 = B0 * 3
A2 = A1 + 31   B2 = B1 + 37
A3 = A2 - 41   B3 = B2 - 14
A = A3        B = B3
Y = 3*A - 2*B
```

程序化真值：`{"A":543,"B":158,"Y":1313}`。

提供的共享来源错误历史为：

```text
Recorder R, branch A:
A0 = 79
A1: 79 * 7 = 546       # 唯一局部算术错误；正文不含此注释
A2: 546 + 31 = 577
A3: 577 - 41 = 536
A = 536
Recorder R, branch B:
B0 = 45
B1: 45 * 3 = 135
B2: 135 + 37 = 172
B3: 172 - 14 = 158
B = 158
Combined record: Y = 1292
```

错误历史自身的 A2/A3/Y 都与错误 A1 一致，属于错误传播，不另计独立局部错误。正确 A、正确 B、旧 A、旧 Y 和所有步骤均可精确验证。分离来源只将 B 的 `Recorder R` 改为 `Recorder S`。短程序题用 `A = A * 7` 等直线赋值表达同类依赖，历史仍显式列出每步结果。

这里的“历史”是提供给模型的同题 worksheet，**不是模型先前自然生成的自有推理**。后续即使通过本 Gate，也不能直接外推到自有历史或复杂开放式推理。

## 2. 冻结数据协议

主清单：`outputs/credit-assignment-gate0-20261013/manifest.json`；种子 `20261013`。题库与门槛在模型调用前固定。

| 因素 | 取值与数量 |
|---|---|
| 任务表达 | arithmetic 16 / program 16 |
| 难度 | small：每支 3 步、起点 21–89，16 题；medium：每支 5 步、起点 103–287，16 题 |
| A 的唯一注入错误 | 第一运算 / 最后运算，各 16 题；精确结果加 ±7 |
| 历史及 specification 的分支顺序 | AB / BA，各 16 题 |
| 数值副本 | 每个结构格 2 道独立数值实例，共 32 道；不是同题重复 seed |
| 来源名称方向 | R/S 全局交换，16 / 16；此方向固定于实例，不作为独立样本 |

A 的错误注入后，程序重新传播 A 和 Y；B 保持精确正确。32 个 specification 不重复。没有根据模型表现删除、补充、替换或重排题目。

材料审核的边界：错误符号为 −7 共 15 题、+7 共 17 题，并非精确反平衡。早期错误传播至最终 A 的幅度为 7–126，末步错误为 7；因此不能将早/晚组差异单独归因于错误位置。本轮只要求同题来源/反馈反事实严格匹配，未估计错误位置的因果效应。上述不均衡全部保留，不事后替换。

预留的反馈正文逐字冻结为：

| 条件 | 反馈正文 |
|---|---|
| 整体错误 | `The previous result is incorrect.` |
| 局部 A 错误 | `Branch A contains an error. Recompute A.` |
| A 错误 + B 独立确认 | `Branch A contains an error. Recompute A. Independent verification confirms that branch B is correct.` |

来源条件：共享为 R/R，分离为 R/S；固定标签交换将二者分别变为 S/S、S/R。交换作用于所有 recorder 标签，不交换 A/B 计算角色、不移动内容、不改变反馈。录入者名称不携带“可靠/不可靠”描述，system 明确说明名称不等于正确性。

反馈放在全部历史之后；同题六条件以最长反馈长度为目标，在 user `im_end` 前插入固定数量的单个 newline token。**保存的 token IDs 是权威输入**，不再将解码字符串重新 tokenize。否则连续换行可能被合并而破坏匹配。六条件的总 token 数、A/B 计算位置、错误位置、assistant 读出位置均匹配；来源差异仅为一个 token。填充只匹配位置，不能把三种反馈的语义差异解释成独立的“长度效应”。

Clean 没有历史或反馈，正确历史校准没有错误反馈；二者不声称与错误历史等长。错误历史相对 Clean 的差异仍可能包含通用长度/上下文负担；本 Gate 只检查是否存在可研究的行为退化，不能隔离来源外溢。

## 3. 有限执行与评分

仅运行共享来源 + 局部 A 反馈这一格：32 次 Clean + 32 次错误历史修正。另在预选 8 题上运行 8 次正确历史校准，共 **72 次短生成**，每次最多 384 tokens、greedy、`enable_thinking=False`。允许可见简短计算，不强制第一 token 输出答案，不使用候选选项。

预选诊断题为 G0-001/007/011/013/019/021/025/031，每个“表达 × 难度 × 错误位置”格一题，AB/BA 平衡。它们在任何模型输出前固定。8 次正确历史校准仅为辅助：其反馈不同，不能把差异归因于历史正确性这一个变量。

主要终点是最后严格 JSON 对象中的 A、B、Y 整数真值，分别及联合评分。重复键、缺键、多字段、字符串/浮点数、非终端对象均不修复；截断即使包含一个早期正确对象也计失败。原文、token IDs、停止原因、解析结果、旧 A/Y 采用和耗时都保存。B 正确不证明读取过历史 B，因为 specification 仍可用于重算。

统计单位是**题目**。报告全部 32 题和所有失败、缺失、截断；配对 Clean − history，5000 次题目 bootstrap 仅描述本小题池的不确定性。8 个诊断题先平均位置交换，再跨题统计。模板、读出、token、位置视图均不增加样本量。

## 4. B 直接贡献的可执行测量路径

辅助读出不替代自由推理准确率。预选 8 题，每题两个位置视图 × 三种访问条件：完整访问、decode-only 阻断历史 B 计算块、decode-only 阻断等长无关块，共 48 个读出条件、96 个数值候选评分。每个候选重新创建缓存，避免 HF 可变 cache 被前一候选污染；每个候选一次 prefill 加一次 suffix forward，共 **192 次辅助 forward**。

无关块由与 B 计算块数量相同的 `.` token 组成，只用于 forward 诊断，不出现在 72 次自由生成中。两个视图交换 B 与无关块的槽位，使两者经历相同的两组绝对 key 位置。每一视图的三个 mask 使用完全相同的文本、token IDs、position IDs、key 数及 query 时点；B/无关 mask 的 key 数相同。来源标签保留在 mask 外。该控制匹配访问边数及位置，不匹配计算语义；句点块也是人工仪器，不能据其结果直接声称自然生成存在来源效应。

冻结辅助量：完整数值 `B_true` 与 `B_true+1` 的**序列 log likelihood 差**，以 nats 计；须验证位数及 token 数相同。不是首位正确率，不是自由生成准确率，也不把两候选 softmax 概率当求解能力。

正确执行顺序：

1. 普通完整 prefill 得到 pristine KV；保存末 token logits。此刻所有 decode-only 条件都尚未生效。
2. 强制追加不含金标准 B 的固定 bridge：`\nThe value of B is `。不评分 bridge 自身。bridge 的所有 query 在 prefill **之后**计算，并从第一个 bridge query 起应用相应 mask。
3. 用 bridge 最后一个 token 的 logits 评分 B 的第一 token；继续 teacher-force 候选剩余前缀，评分所有数值 token。显式使用绝对 `position_ids` 和 `cache_position`，mask 覆盖 past + current keys。
4. 每题、每位置视图记录 `M_full − M_blockB`、`M_full − M_blockN`；校正信号为两者之差，即 `M_blockN − M_blockB`，再平均两个视图。

同时核对同一视图下三个 mask 条件的**原始 prefill 首 token logits 完全一致**。既有 HF backend 的 `late_block` 是先普通 prefill 后阻断生成 query，因此不能将完整 prefill 的末 logits 当成“已阻断 B”的首输出评分。代码明确处理了这个 off-by-one 问题。

重要解释边界：普通 prefill 已允许 Y、反馈和末端 prompt KV 编码 B 信息。此读出只估计**这些状态固定时，bridge 对 B 历史 keys 的增量直接访问贡献**；不保证消除全部 B 信息，零差异也不证明未利用 B。完整输入中还有 specification、旧 Y 和 B 的可重算关系。

若以后确需测量“历史 B 整体不可用”，可复用现有 `SelectiveHFBackend.generate`，构造同 IDs 的 `SelectiveContextRequest(access_mode=AccessMode.PATH_BLOCK, mask_token_spans=(B_span, ...))`：从 B 块结束起，重算其后全部 prefill 和 decode；匹配无关块位置、长度、起效时点并交换槽位。此时最终 prefill logits 可改变，属于不同 estimand。**本 Gate 没有执行这条路径，亦未把它当成新机制干预或 Gate 1 授权。**

实现对照：[HF cache 官方说明](https://huggingface.co/docs/transformers/v4.53.3/en/cache_explanation)；[Qwen3 官方推理设置](https://github.com/QwenLM/Qwen3/blob/main/docs/source/getting_started/quickstart.md)。实际行为同时以保存的远端后端快照、模型版本及数值检查为准。

## 5. 模型调用前的失败条件

这些是操作性 feasibility 阈值，非机制检验的显著性标准：

- 32 题精确真值、唯一局部错误或六条件来源/位置匹配失败：停止。
- Clean 联合正确少于 24/32，或 Clean/history 任一条件非截断少于 30/32：当前短生成协议不可用。
- Clean − history 的净 Y 损伤少于 3/32：没有足够的行为动态范围；包括两者几乎全对的天花板。
- history Y 正确少于 8/32：地板过低，暂不进入来源归因。
- 8 题 B 校正读出均值低于 0.1 nats，或正向不足 6/8：当前直接访问读出信号不足；不自动调 bridge/mask/题库。
- prefill 数值不变性失败、候选 token 数不等、缺失或未完成：测量未验证。

只有全部通过才有资格**讨论** Gate 1；通过也不自动运行。任一失败均保留全部结果，当前协议暂停，不通过降低阈值、筛有利题或追加矩阵挽救。

## 6. 实际结果与建议

实际使用既有远端 HF 精确后端、Qwen3-8B、BF16、eager attention、单 A100 GPU4；PyTorch 2.8.0+cu128、Transformers 4.55.4。72/72 生成、48/48 辅助读出完成，无请求缺失或重跑，无题目排除。自由生成合计 10,310 tokens（含停止 token）；HF 阶段含模型加载共 519.19 秒，即 8.65 分钟，不含常驻恢复。

| 条件 | A 正确 | B 正确 | Y 正确 | 联合正确 | 截断 | 格式无效 |
|---|---:|---:|---:|---:|---:|---:|
| Clean，32 题 | 9/32 | 9/32 | 9/32 | 9/32 | 12/32 | 15/32 |
| 错误历史 + 局部 A 反馈，32 题 | 2/32 | 30/32 | 2/32 | 2/32 | 0/32 | 2/32 |
| 正确历史辅助校准，固定 8 题 | 7/8 | 7/8 | 7/8 | 7/8 | 0/8 | 1/8 |

“格式无效”与“截断”重叠，不能相加作为失败总数。全部失败均进入计划分母。

全题池 Clean − history 的 Y/联合正确率差为 **+21.875 个百分点**，题目 bootstrap 95% 描述区间 [6.25, 40.625]；8 题由正确变错、1 题由错变正确、23 题同为正确或同为错误。28/32 历史条件输出精确旧 A 和旧 Y。这里确有**在当前协议下的最终答案退化与旧值沿用**，但能力门槛和地板门槛失败，不能称“模型本来能解却被来源抑制拖偏”。该差异也未剔除长度、响应风格、格式和截断的影响。

B 在历史条件反而从 9/32 提高到 30/32：22 题恢复、1 题损伤。这个条件中正确 B 通常得到保留。没有共享/分离来源配对，亦没有另外两种反馈的行为结果，因此**不能估计来源边界外溢或反馈 × 来源交互**；它们既没有被确认，也没有被否定。

所有预设分层均报告，不只取表现有利的短程序题：

| 分层 | Clean 联合正确 | history 联合正确 | Clean 截断 |
|---|---:|---:|---:|
| arithmetic | 0/16 | 1/16 | 8/16 |
| program | 9/16 | 1/16 | 4/16 |
| small | 8/16 | 2/16 | 0/16 |
| medium | 1/16 | 0/16 | 12/16 |
| early | 5/16 | 2/16 | 6/16 |
| late | 4/16 | 0/16 | 6/16 |
| AB | 5/16 | 0/16 | 7/16 |
| BA | 4/16 | 2/16 | 5/16 |

算术/程序使用不同数值实例；这些是描述分层，不是同题纯格式因果对照。`small × program` 的 Clean 为 8/8，也不能据此事后挑出这一组进入正式实验。medium 12/16 的截断说明当前输出预算/表达组合不适合此档；本轮没有延长预算补跑。`enable_thinking=False`、可选而非强制的可见计算、任务表达及严格输出要求都可能影响结果，尚未区分其原因，也不将低表现概括为模型缺乏算术能力。

G0-001 的原始终端输出可核查这一限制：Clean 为 `{"A":217,"B":178,"Y":395}`，本来就错；错误历史条件输出 `{"A":536,"B":158,"Y":1292}`，精确复制旧值；正确历史校准经可见计算输出正确的 `{"A":543,"B":158,"Y":1313}`。不能只引用中间那条构建“已能求解却撤销失败”的叙事。

**B 辅助仪器通过本 Gate 的可测性门槛**：校正序列 log likelihood margin 平均 18.117 nats，8/8 题正向、16/16 位置视图正向；题目 bootstrap 描述区间 [17.078, 19.211]。未校正的 B 阻断损失平均 18.109 nats，无关块阻断损失 −0.0078 nats，校正信号主要来自 B 阻断而非无关块收益。被 mask 的 B/无关块每视图分别为完全相同的 60、62 或 113 个 keys。全部候选长度匹配；同一 prompt 的三个访问条件原始 prefill 首 token logits 指纹相同，重复最大绝对差为 0。这支持“固定 bridge 数值读出对 B keys 的直接访问敏感”，**不等于自由推理 B 利用率、对 B 的总体因果贡献或来源抑制机制**。

输入审核全部通过：Clean 163–231 tokens；错误历史 339–517；正确历史辅助 331–503。六条件每题总长度相同，A/B 历史 token 序列及绝对跨度完全一致，实际执行的 history 输入与冻结 shared/local 格完全相同。R/S 分别是单 token 49/50；所有来源配对只差一个标签 token。

| 冻结判据 | 结果 |
|---|---|
| 精确任务、来源/历史/读出位置匹配 | 通过 |
| 72 生成 + 48 读出完整 | 通过 |
| Clean 联合正确至少 24/32 | **未过：9/32** |
| Clean 非截断至少 30/32 | **未过：20/32** |
| history 非截断至少 30/32 | 通过：32/32 |
| 配对净 Y 损伤至少 3/32 | 通过：7/32，但不能替代能力验证 |
| history Y 正确至少 8/32 | **未过：2/32** |
| B 校正信号至少 0.1 nats、至少 6/8 题正向 | 通过 |
| decode-only prefill 首 logits 不变 | 通过 |

**建议：HOLD，不进入 Gate 1。** 保留可复用的精确任务生成器、来源模板、严格评分和正确 mask 测量路径；当前行为协议不足以解释局部反馈的 credit assignment。研究讨论应先决定是否值得设计一个让 Clean 有充分计算、同时避免历史条件地板的新 Gate 0 协议，并使用重新冻结的新题验证；不在这 32 题上挑难度、调 bridge 或扩大 token 预算以追回通过。现有任务还显式携带旧 Y，答案锚定是必须保留的解释。

已停止 HF runner；恢复后的原项目 resident 处于 `SELECTIVE_VLLM_RESIDENT_READY` 与空闲 `>>>` 提示符，未提交实验。其他 GPU4 进程未终止。此处仅记录结束核验快照；正式 2×3、Gate 1、PATH_BLOCK 测量和新机制干预请求均为 **0**。

## 7. 复核与交付

```powershell
python scripts/gate0_credit_assignment_20261013.py --prepare
python scripts/gate0_credit_assignment_20261013.py --analyse
python scripts/audit_credit_assignment_gate0_20261013.py
python scripts/gate0_credit_assignment_20261013.py --status
python -m pytest tests/test_gate0_credit_assignment.py -q
```

模型启动入口为服务器上的 `bash scripts/start_credit_assignment_gate0_20261013.sh`，不是继续实验的默认动作。它只释放经进程归属及 tmux 空闲提示符核实的本项目 resident；其他 GPU4 进程保留。HF 结束后恢复原 resident，不向它提交任务。

结果目录 `outputs/credit-assignment-gate0-20261013/` 包含冻结清单、CPU 真值验证、192 个只编译模板、72 份精确生成输入与原始输出、48 个辅助读出条件、逐候选完整 token 分数、模型环境和实际后端快照。未执行条件不是零效果。

此前 Late Invalidation 短评分结果只作为测量教训，本 Gate 不复用它的题池或效应。无新增文献新颖性结论；用户已给定本轮竞争问题，本 Memo 仅决定材料与测量是否足以开展下一轮讨论。
