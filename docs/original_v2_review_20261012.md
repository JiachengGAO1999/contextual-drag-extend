# 原论文版本核对（2026-10-12）

此前多处讨论链接到2026-02-04的v1。本次核实最新公开arXiv正文为
[v2，2026-03-02](https://arxiv.org/html/2602.04288v2)，不能将v1当作
论文全部已有内容。OpenReview PDF直接读取遇浏览器校验，本次不
宣称已逐页核实最终发表PDF与v2一致。

用户于2026-10-12确认无法取得原论文跨模型逐题的完整生成输出。
当前不再以获取这些轨迹为推进前提；以下解析器与转换的构造复核
不是原始结果的重新估计，不能据此宣称原结论失效。

与当前选题有关的新增内容：

- 附录C.3：移除要求复用正确部分的提示后，TED差异趋势仍保留。
  单纯删除“复用”措辞不是未探索的方法方向。
- 附录F.7：已比较标准最终答案奖励GRPO与定向SFT；前者改善有限。
  “普通结果奖励未教会重置”已属于原文讨论，不能当作新发现。

v2同样未提供我们所需的可区分计算机制；但这只说明需要更强证据，
不证明某个候选机制新颖或正确。已有的历史干扰、结构复用、二元
反馈不足、恢复与正确历史利用的权衡，继续仅作研究动机。

后续原论文相关创新判断以v2为基础；历史实验协议及当时引用保留。

## 公开verdict解析器的额外边界

本次读取本地原始 `analysis/ErrorSignalConditioning/analysis.py`，并通过
只读下载核对[上游函数](https://github.com/princeton-pli/Contextual-Drag/blob/main/analysis/ErrorSignalConditioning/analysis.py)
的AST内容一致。`parse_verification_output` 先匹配全文correct关键词、
再匹配incorrect关键词，最后才读overall_verdict标签；多个标签时，
去掉换行后的贪婪表达式也不保证取得最后一个标签。

三个构造反例均复现了与最后明确verdict不一致的结果：

| 输入情形 | 最后verdict | 原函数输出 |
|---|---|---|
| 先说“draft is correct”，随后指出超用数字并明确否定 | Incorrect | False |
| 条件句“If the draft is incorrect”，随后明确接受 | Correct | True |
| 先给Correct标签、再给Incorrect标签 | Incorrect | False |

这里True表示函数认为模型判旧草稿错误。逐例输入及核对记录位于
`outputs/generation-diagnostics-20261005/error_profile_preview/original_verdict_parser_preview.json`。
这是代码行为的受控复现，不是原始模型输出，没有测出论文实际误判
比例或修正后的效应；不据此宣称原论文结论失效，也不当作已完成的
机制贡献。当前查到的公开入口给出再生成流程，本地聚合结果及TED
缓存不足以重建完整诊断理由，仍未取得原跨模型完整轨迹。

因此，需要把此前“该分析测量最终正确整体verdict”的说法再收紧：
它按公开解析规则识别整体判定，但规则不保证对应最终判定，更没有
核验具体诊断的正确性。若未来取得原始轨迹，应分别报告最后明确
verdict、精确错误诊断和最终答案，不能仅更换关键词后宣称因果机制。
