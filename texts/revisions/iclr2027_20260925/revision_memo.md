# ICLR 2027 论文修订说明（2026-09-25）

依据 `texts/iclr2027_astra_revision_instructions.md` 修改当前稿。标题保持 **After Error Feedback: Continued Access to Failed Reasoning Sustains Contextual Drag**。本轮不生成模型回答，不加入仍在运行的实验，也不改变既有评分。15 道 Game24 题在论文中统一报告，不按 independent/pilot 划分证据等级；采样规则及题目 41 的早期纳入规则例外仍透明披露。

## 交付

- 完整修改稿及编译 PDF：`texts/iclr-2027-style-files/iclr2027/contextual_drag_continued_access.{tex,pdf}`。
- 摘要逐字快照：本目录 `abstract_before.txt`、`abstract_after.txt`；后者同步到 `texts/abstract.txt`。
- 新 Figure 2：论文目录 `figure2_access_effects.{pdf,png,csv}` 及 `_provenance.json`；生成脚本 `scripts/plot_iclr2027_access_effects_20260925.py`。
- 附录生成诊断表：论文目录 `generation_diagnostics.tex`。
- 静态证据审计：本目录 `revision_audit.json`；脚本 `scripts/audit_iclr2027_revision_20260925.py`。

## 摘要前后与理由 [WRITING ONLY]

完整前后文本见上述两个快照；实际只有两处改动：

1. 原第一句之后新增：“Does this influence depend only on having processed the trace, or also on continued access during generation?” 显式提出全文识别问题，不扩大结论。
2. “We isolate the role of continued direct access” 改为 “We isolate continued direct access”，避免紧邻新增问题造成冗余。

其余摘要文本、数字、任务范围及结论保持不变。这是保守文字修订；已注册摘要的正式提交状态并未被本地修改自动更新。

## 论证及章节组织 [STRUCTURE]

引言从生成、反馈、保留历史、再次推理的流程切入，区分两条可共存的信息路径：初始处理影响其他可访问状态，以及后续生成继续直接读取草稿。既有 Contextual Drag 工作建立现象，本文识别的是后一个问题。贡献改为概念区分、同文本识别设计、实验发现三个层次。

正文顺序保留 Introduction、Related Work、Problem Setup、Method、Experimental Design、Results、Discussion、Limitations、Conclusion。Results 改按科学问题组织：

1. 明确错误反馈后，失败历史仍造成性能损失。
2. 阻断持续访问恢复大部分观测损失，这是主结果。
3. 其他目标模型和实现具有同方向结果。
4. 正确历史对照说明阻断并非普遍有益。
5. MATH 提供更长推理场景下的方向性证据。
6. 更早阻断没有一致的额外收益，作为次要时序检验。

保留三种访问掩码公式；将 R2/R3 定为主要比较，R4 放在次要位置。强调配对条件具有相同文本、token、位置、草稿区间、反馈与采样设置。澄清完整 prefill 产生第一个 token，第一次被阻断的查询用于预测第二个生成 token；Gemma 的干预与其原生局部注意力限制取交集。

## Figure 1 与 Figure 2 [STRUCTURE]

Figure 1 保留已有图形设计，修改图注说明上述时序，不重画实验机制。

Figure 2 是六行效应图：五个失败历史 R3−R2 效应，以及一个正确历史阻断效应；以颜色和点形区分，含零线及既有 95% 题目聚类 bootstrap 区间。它直接读取已保存统计结果，不重采样或重评分。图中标明 Game24 主结果为 15 题、正确历史对照为 8 题；图注明确不能直接拿这两行当匹配交互。

图注核心信息：阻断持续访问在失败历史上呈正向效应，在正确历史上呈负向效应；区间按题目聚类；正确历史对应的正式交互分析在相同八题上进行。Gemma 区间触及零，正文不宣称其具有确定的统计显著性。

## 表格与附录 [STRUCTURE]

主文 Game24、MATH 表聚焦 R0/R2/R3 正确数与 R3−R2 效应及区间。R4、EOS/length/unresolved 移至附录诊断表，正文保留 MATH 的终止问题说明。附录继续给出完整 Game24 逐题表，并将八题最终表达式复用分析作为描述性行为检查。

附录诊断表覆盖 460 条既有输出。未解析回答计为不正确；终止原因单独报告，不能把所有 length stop 自动等同于未解析。全部 18 条 length stop 中 16 条未解析、2 条已解析但错误；MATH 单独有 14 条 length stop、13 条未解析。

## 主要数字与结论审计 [WRITING ONLY]

1. **主效应与恢复范围。** Qwen3-8B 为 25/30 → 10/30 → 24/30；配对效应 +46.7 pp，95% CI [26.7, 66.7]。16 条改善、2 条恶化、8 条均正确、4 条均错误。写作采用“most of the observed loss”，不声称完全恢复或与 R0 等价。
2. **正确历史的特异性。** 相同八题正确历史为 16/16 → 13/16，效应 −18.75 pp [−37.5, −6.25]；匹配八题的失败历史效应为 +37.5 pp，交互 +56.25 pp [37.5, 75]。没有将十五题效应代入交互。草稿内容、长度和反馈标签同时不同，因此不把对照解释为只改变真伪的单因素实验。
3. **跨模型及后端。** Qwen3-32B 效应 +26.7 pp [3.3, 50.0]；Gemma +16.7 pp [0.0, 30.0]。解释为同方向证据；架构、模型与实现共同变化，不主张模型规模规律、后端因果效应或位级等价。
4. **跨任务及终止。** 两组 MATH 效应分别 +75.0 pp [50.0, 93.75]、+50.0 pp [18.75, 81.25]。每组仅八题，来源与草稿模型混杂，且截断分布不均，因此定位为方向性扩展，不宣称普遍跨任务可靠性。
5. **机制与外推。** 识别的是完整初始暴露后，持续直接访问对所测表现的贡献。其他 token/state 中的信息仍可能存在；不声称遗忘、信息擦除、切断所有路径、内部复制机制或部署优越性。选择性样本限制外推，但不抵消同提示词条件下的访问对照。

Discussion、Limitations 和 Conclusion 均按这五类边界收紧。结论简短重申 exposure/access 的区分、失败与正确历史的不同方向，以及其他信息路径仍然开放。

## 后续实验建议：尚未执行

- [EXPERIMENT NEEDED] 优先扩展到 30–50 道不同题目，使用一致且记录完整的选择规则；增加题目覆盖比继续堆同题 seed 更直接解决当前外推限制。
- [EXPERIMENT NEEDED] 在扩展题目上增加匹配的正确历史控制，保留内容、长度及反馈标签差异的披露。
- [EXPERIMENT NEEDED] 三个目标模型优先完成 R0/R2/R3；无需为扩展全部补 R4 才能检验主要结论。
- [EXPERIMENT NEEDED] 检查 MATH 的生成预算与终止不平衡，预先固定处理规则后再开展补实验，避免只补有利条件。
- [OPTIONAL] 增加通用区间阻断或长度匹配控制，以进一步区分草稿内容作用与更一般的注意力限制效应。
- [OPTIONAL] 扩展 R4 或其他时序条件，研究更早阻断的异质性；当前证据不足以宣称它优于 R3。

## 验证范围

审计脚本核对证据清单中的 460 条原始输出哈希、摘要数字序列、标题、未完成结果标记及图表来源哈希。LaTeX 重新编译并检查页面。以上验证证明本次改写与现有材料一致，不替代新的实验，也不宣称已完成投稿前的引用、匿名公开制品和正式会议规则检查。
