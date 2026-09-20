# 公开 Game24 failed-trace 数据审计（2026-09-19）

结论：`llm-reasoning-uft` 足以支持继续准备独立的 external failed-draft track，值得用来减少自生成草稿成本。但当前只是可用性审计，不能将自动候选数当作正式合格题数。没有启动新生成，没有读取 intervention outcome 选题，没有修改 dual-anchor eligibility。

## 数据来源与复现

- [官方仓库](https://github.com/twni2016/llm-reasoning-uft)，本次固定 commit `5d5b56c3a12b5f96100e4418e7913cb6ee8df302`。
- [官方 README 提供的数据下载](https://drive.google.com/file/d/1cu2xTI89uvK57LkrVeaYmiI4jDNRDZD_/view)。本地 `outputs/public-uft-audit-20260919/data.zip`，388,659,338 bytes，SHA256 `0da8c056e4d5c7c78f298c73fc783308a7447d28c043e216ad710ad42902c502`。
- 统计脚本：`scripts/audit_public_uft_20260919.py`；人工判定与CPU封装检查：`scripts/finalize_public_uft_audit_20260919.py`。
- 只读取CSV和源码；不执行下载仓库的生成代码或其 `eval` verifier。表达式复核使用受限AST和精确分数。
- 排除 `__MACOSX` 资源文件；真实 Game24 文件为54份 failed、54份 correct CSV。本报告统计 failed 文件。

## 规模与映射

| 来源 | failed行数 | 独立题 | 每题平均 | 每题中位数 |
|---|---:|---:|---:|---:|
| Qwen2.5-Math-1.5B CoT | 514,897 | 720 | 715.13 | 724 |
| Qwen2.5-Math-1.5B ToT/BFS | 140,024 | 720 | 194.48 | 187 |
| Qwen2.5-Math-1.5B RAP/MCTS | 245,635 | 720 | 341.16 | 343 |
| Qwen2.5-Math-7B CoT | 470,898 | 720 | 654.03 | 664 |
| Qwen2.5-Math-7B ToT/BFS | 94,686 | 720 | 131.51 | 128 |
| Qwen2.5-Math-7B RAP/MCTS | 167,953 | 720 | 233.27 | 236 |
| 合计（题目取并集） | **1,634,093** | **720** | **2,269.57** | **2,276** |

这些是发布数据行数，不是独立问题数，也不能直接视为互不重复的生成次数。7B CoT跨9个采样变体，按原始 `text` 字符串精确去重后361,394条。每题多条不会增加独立题目样本量。

720题全部通过原始数字multiset无歧义映射到本地1362题；逐行同时核对源case_id对应的数字，映射异常为0。不是完整1362题原始生成日志：发布包经过训练集筛选，来源为前900题中的720个训练题。不得声称它恢复了 Contextual Drag 原始653题。

## 字段、文本完整性与标签

字段为 `case_id / success / structured / text`。failed文件全部 `success=False`。`text` 是包含输入、步骤、最终答案的序列；`structured=True` 表示识别到Answer，不保证推理正确或原始生成正常结束。

[CoT序列化源码](https://github.com/twni2016/llm-reasoning-uft/blob/5d5b56c3a12b5f96100e4418e7913cb6ee8df302/reasoners/examples/game24/base_cot.py) 会保留至首个Answer行，并去掉Answer前缀；生成设有文本stop及256个max_new_tokens。CSV没有EOS、finish_reason或生成token数。可以保留全部已发布path，但不能恢复被处理前的完整原始输出，也不能严格证明非截断。

因此，若坚持“必须有可核验EOS”作为external纳入条件，本数据**尚无可认证合格题**。若接受“公开处理后的、具有完整步骤和最终答案的trajectory”，则存在大量候选；这一标准变更必须明确写入独立Track B协议，不能悄悄当作已满足原要求。

源verifier同时检查步骤、剩余数及最终式，并有字符串/格式约束；故 `success=False` 不等于“最终答案确实错”。当前wrapper明确告知 `INCORRECT final answer`，必须额外核查最终式，不应只沿用标签。

## 自动保守候选（仅7B CoT）

| 自动类别 | 行数 |
|---|---:|
| 输入＋恰好3步＋最终式，最终式数值或用数multiset确实错误 | 299,817 |
| 步骤数非标准，需额外审查 | 155,966 |
| 未识别Answer | 8,404 |
| 最终式合法，需复核步骤/标签 | 3,653 |
| 最终式无法解析 | 2,173 |
| 含小数，留待复核 | 885 |

自动检查没有验证所有中间步骤连贯性，也没有证明未截断。最终错误类别覆盖全部720题；这里只是候选目录，不能自动进入实验。

## 与项目既有题目的重叠

只读取baseline清单、数字映射和历史题目ID，不读取R2/R3/R4得分。

- 与旧10题development重叠5题。
- 与7题pilot重叠4题。
- 与全部已用/已screen题目并集重叠77题；历史排除清单自身共142题。前两项包含在77中，不能相加。
- 排除77题后剩643道新题。
- 再预留未生成的Batch03冻结清单，额外排除18道重叠，剩 **625道新候选题**，对应 **261,356条自动保守候选记录**。

625是容量上限，不是625道人工通过或target clean-solvable的题。当前审计支持“有较大余量准备30–50题external样本”，不能承诺最终合格数或drag强度。

## 固定随机20条人工审查

种子20260919，从7B CoT全部470,898行做reservoir抽样，先抽后审；按行抽样，不是按题均匀。完整原文和逐条理由见 [20条审阅文档](../../outputs/public-uft-audit-20260919/random20_review.md)，机器记录见 [random20_reviewed.json](../../outputs/public-uft-audit-20260919/random20_reviewed.json)。

| 人工判定 | 条数 | 处理建议 |
|---|---:|---|
| 最终答案实质错误，恰好3步且有最终式 | 12 | 可进入候选复核，结束原因仍未知 |
| 最终答案实质错误，但有额外步骤/非法状态 | 5 | 主池保守排除，留存原文 |
| 最终表达式合法，但步骤或等号右侧不一致 | 2 | 当前错误答案wrapper不宜使用 |
| 明显不完整，无最终答案 | 1 | 排除 |

17/20存在明确最终错误；其中12/20符合本次更保守的形状要求。没有发现纯格式错误。不能据20条推断全部数据质量，也不能把所有有Answer的19条认定为已验证EOS。

失败形态不局限于重复用数：包括计算本身错误、最终式算不出24、正确执行却停在非24结果、步骤与最终式不一致、重复使用数字。因此它提供更宽的刺激来源，同时也改变了难度、文风和长度分布；不能把这些差异解释成单独的模型来源效应。

## R2/R3接入验证

对抽查中12条保守候选，将已发布path逐行原样拼接作为draft；不修正错误、不补推理、不伪造boxed答案。现有independent prompt wrapper可定位整个draft。

CPU CharacterTokenizer检查12/12通过：R2/R3/R4共用完整prompt和token序列、hash及draft span；draft子串与原样拼接完全一致。示例见 [wrapper_audit_examples.json](../../outputs/public-uft-audit-20260919/wrapper_audit_examples.json)。这里只验证封装合同；**没有使用真实Qwen tokenizer，也没有做模型attention或生成检查**，不能替代启动前预检。产物标记 `generate:false`，不是实验运行清单。

## 建议与当前停点

Track A保持双Qwen原协议，已有结果和剩余baseline保留。Track B明确为外部模型产生的短步骤trajectory验证，不并入Track A主分析，不代表第二任务或target-model泛化。

建议在接受上述完整性证据边界之后，固定一个按题抽样的30–50题external候选清单，按统一规则复核，每题固定一条draft；规则和候选顺序都在intervention前冻结。现阶段不需要继续寻找ToT日志或其他备选数据源。

若用少量R0筛clean-solvability，筛选用的R0不能再当作主要R0对照，否则会引入选择后的高估/回归均值。应预先固定筛选预算和门槛、使用独立评测seeds；或者不按R0结果筛题，将clean-solvability作为预定义分层。公开failed trace节省的是草稿acquisition，不能消除目标模型评测费用，也不保证出现drag。

**本轮零新生成，停在协议选择前：**是否接受“有完整步骤与最终答案、但无EOS元数据”的公开短trajectory作为Track B。未启动external intervention，也未恢复32B或启动新baseline批次。

## 32B暂停与恢复

服务器Batch02现已实际保存 **288/512** 条（chunk-00至chunk-16，每组32），当前子进程结束，父进程PID930390为STOP状态；没有chunk-18启动。剩224条。

`status.json` 和早先 `pause.json` 仍可能显示256，这是父进程在回收最后子进程、更新计数之前被暂停所致；以9份已落盘结果为准。恢复时必须确认父PID创建时间仍为1789783061.78、命令相同、GPU可用，再对该父进程SIGCONT；它会回收已完成子进程、登记第288条后继续下一组。不要从头重启runner（其输出目录保护会拒绝重跑）。此恢复依赖原暂停进程仍存活；服务器重启后需另做按已有chunk恢复，当前未声称具备重启容错。
