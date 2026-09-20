# 现成失败轨迹替代来源：零生成初审

2026-09-19。没有新增生成，32B保持288/512暂停。原UFT审计见[报告](public_uft_audit_20260919.md)。本次用户追加要求寻找其他可复用来源，以下区分本地实测与数据卡声明。

## Game24：ToT官方GPT-4直接CoT（已下载、计数）

[固定版本原始日志](https://github.com/princeton-nlp/tree-of-thought-llm/blob/8050e67d0e3a0fddc424d7fa5801538722a4c4cc/logs/game24/gpt-4_0.7_naive_cot_sample_100_start900_end1000.json)。这不是搜索树，不需要拼接路径。

100题×100输出=10,000条，源评分403正确、9,597错误。只对源错误进行受限AST最终式复核：6,782条可确认数值或数字multiset错误，1,979条最终式暂不可判，836条没有Answer标记。后两类不自动纳入。

按官方CSV零基idx映射本地1362题，排除历史使用和Batch03预留后，剩 **91道新候选题、6,222条最终式错误记录**。尚未人工逐条审查步骤、完整性，未测target clean solvability，不能称正式合格题。没有逐条finish_reason，仍无法认证EOS。

UFT的720题来自前900题训练子集；这份ToT日志来自索引900–999，提供另一区段和GPT-4模型来源。但同样主要是短步骤CoT，不能等同于长Thinking草稿。Game24优先保留UFT并考虑这个补充，不必继续生成大量baseline等错误。

## 标准MATH500：rasbt/math_distill（优先第二任务）

[发布者数据卡](https://huggingface.co/datasets/rasbt/math_distill)。已下载`data/deepseek-r1-math500.json`并核实500条，包含problem、gtruth_answer、message_thinking、message_content。没有finish_reason字段。

数据卡报告DeepSeek-R1为456/500正确，Qwen3-235B-A22B为462/500正确，即分别44、38条源评测未判正确。**不能直接称44/38条实质错误**，需要统一scorer重评和人工核查；第二模型文件本轮未完成下载复核，两来源错误题并集未知，不能相加。

这是更适合现有MATH500兼容代码的长推理来源，可省去新草稿生成。还要排除格式误判、无最终答案和超出输入预算的轨迹；Qwen3-8B对其失败题未必clean-solvable。

## Qwen3-4B MATH-traces（已下载，有标签问题）

[数据卡](https://huggingface.co/datasets/jrosseruk/Qwen3-4B-MATH-traces)。本地实测10,000条、500题，每题20次；8,954 True / 1,046 False，False覆盖87题。False中具有结束Thinking标记、可提取答案及其后boxed答案的完整外观记录730条、58题；不是已审核通过数。

第一条False就是假阴性：出租车起步1.50美元、每英里0.25美元、5英里，参考`\$2.75`而模型`2.75`，模型推理和答案正确。不能直接使用False标签。

这些题来自按难度分层的MATH训练集，不是标准MATH500。与已下载rasbt MATH500做题面空白规范化精确匹配，重叠0题；未进行改写级重叠检查。无EOS/finish_reason。它适合作为重评分后的数学长推理备选。

## OpenR1-Math-220k（已核数据卡、字段，未全量统计）

[官方数据卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k)。`generations`保留多条DeepSeek-R1响应，配套`correctness_math_verify`、`is_reasoning_complete`和`finish_reasons`；预览确有True/False混合，结束原因部分为空。

应从generations数组逐条筛错误，不能只取训练用messages正确答案。需排除缺图或当前scorer不适用的题。不是MATH500，本轮未下载12.6GB全库、未计数错误池；作为大规模外部数学备选。

## Wrong-Reasoning Trace Bank（已核字段及baseline汇总）

[数据卡](https://huggingface.co/datasets/AZH04/wrong-reasoning-traces)。包含correct、truncated、n_tokens、trace_text、answer、gold、qid；任务为AIME24/25、maze、mini-sudoku，来源包括Qwen3-4B Thinking/Instruct及Gemma。

发布者明确只提供reasoning channel，未发布完整post-think最终回答；也未分发题面，需按qid恢复。False可能包括answer缺失，不能自动算实质错误。原研究也涉及错误推理注入，复用时须引用并了解筛选范围。可作AIME备选，接入成本高于现成MATH500。

## 推荐路线与证据边界

1. Track A双Qwen协议保持不变，已跑结果保留；不把公开数据塞进原协议。
2. Game24外部验证优先UFT/ToT直接CoT；先冻结单一来源和按题抽样规则，审核完整性及最终错误，分来源报告。
3. 第二任务优先零生成审计rasbt标准MATH500长推理；其次重评Qwen3-4B MATH-traces，后者必须标为MATH而非MATH500。
4. 外部数据节省草稿acquisition，但仍需正式target R0/R2/R3/R4。不能把外部模型的correct companion等同target clean-solvability。
5. 如需R0筛题，预先固定门槛和预算，并用不同seed正式评测R0，避免选择后复用高分基线。

本轮不自动启动生成，不更改formal protocol。UFT和ToT共同的关键决策仍是：是否接受“公开处理后、完整外观但无EOS证明”的短trajectory，作为独立external track。

本地原始文件、统计与SHA：`outputs/public-alternatives-audit-20260919/`；[summary.json](../../outputs/public-alternatives-audit-20260919/summary.json)。复核脚本：`scripts/audit_public_alternatives_20260919.py`。自动表达式检查不是人工完整性认证。
