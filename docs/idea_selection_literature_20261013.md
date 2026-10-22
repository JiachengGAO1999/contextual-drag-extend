# Goal 3 文献边界表

检索日期：2026-10-13。服务于[选题投资 Memo](idea_selection_goal3_20261013.md)，不作完整系统综述。
以下只以论文原文、作者论文页面和正式会议页面支持结论；聚合站与博客只作发现线索。
“作者报告”不等于本项目独立复现。未生成 BibTeX，避免把未逐项核对的引用键加入论文库。

## 直接影响选择的来源

| 文献与可访问来源 | 核验深度／版本 | 选题中怎么使用 |
|---|---|---|
| Cheng et al., [Contextual Drag](https://arxiv.org/html/2602.04288v2) | arXiv 当前 v2，2026-03-02；正文及本地 v2 审查，另检索到 ICLR 2026 正式入口 | 已有结构复用、反馈／整体验证不足与 reset 动机，不能声称首次发现 |
| Kawada & Kellis, [Evidence Integration](https://arxiv.org/html/2609.04290v1) | 2026-09-03 v1，预印本；摘要、引言、§7.3 和讨论的相关片段 | 与“验证表征／候选采用分离”直接重合；不能把候选路由直接改名为程序机制 |
| Li et al., [LLMs Know the Constraint But Do Not Use It](https://arxiv.org/html/2608.12321v1) | v1 预印本；摘要和正文结构。页面 Submitted 日期与编号月份不一致，本文不用其具体投稿月份推断先后 | 编码／路由／donor 修复的概念已提出，降低泛化“知道但不用”的新颖性 |
| Lippl et al., [AlgoTrace](https://proceedings.mlr.press/v306/lippl26a.html) | ICML 2026 正式页面；下载官方 PDF，阅读方法、干预、跨任务结果、讨论及限制 | 最近邻等算法原语的提取、注入和迁移均已有；A 必须增加失败信息如何调节计算的机制解释 |
| Wang et al., [How Few-Shot Examples Add Up](https://proceedings.mlr.press/v306/wang26hp.html)；[正文 v2](https://arxiv.org/html/2605.16591v2) | ICML 2026 正式页面；正文引言、FV 定义及方法结构 | 示例级 FV、QK／V 分解已存在，方法复用不算科学贡献 |
| Zhang et al., [Correcting in Hindsight](https://proceedings.mlr.press/v306/zhang26ek.html) | ICML 2026 正式页面；下载官方 PDF，阅读动机、§3 编辑器、实验与限制 | KV 不可回写和事后编辑已有直接先例；B 需区分编码与读取而非再做编辑器 |
| Ye et al., [Prompt Injection as Role Confusion](https://proceedings.mlr.press/v306/ye26b.html) | ICML 2026 正式摘要，未对全文全部实验作审查 | 来源角色的内部表征和伪造 CoT 已有工作，不声称身份标记或角色 probe 首创 |
| Chen et al., [The Self-Correction Illusion: Role Relabeling Gates Explicit Error Flagging](https://arxiv.org/abs/2606.05976v2) | 2026-07-31 v2 摘要；预印本 | 相同错误文本换角色的纠正效应已有作者报告；explicit flagging 与最终路线使用仍须区分 |
| Yuan et al., [Hidden Error Awareness: The Signal Is Diagnostic, Not Causal](https://arxiv.org/abs/2605.09502) | 2026-05-10 v1 摘要；预印本，页面有 workshop 字样，不当作主会论文 | 解码错误信号不证明因果控制；干预失败的作者结论也不视为普遍不可能定理 |
| Samanta et al., [Structure Enables Effective Self-Localization of Errors](https://proceedings.mlr.press/v306/samanta26a.html) | ICML 2026 正式摘要；另结合项目既有公开代码／资产审查 | 语义 thought 分步、定位、回退已有实现，不把回退协议当新贡献 |
| Chao et al., [STALE](https://arxiv.org/abs/2605.06527) | 2026-05-07 v1 摘要；预印本 | 状态更新、隐式冲突和下游行为脱节已有研究，限制一般依赖撤销叙事 |
| Chia et al., [Contrastive Chain-of-Thought Prompting](https://arxiv.org/html/2311.09277) | v1 正文摘要及引言 | 负面推理示例可以有益已有研究，不能预设所有错误历史都应被删除 |
| H.-y. Wang, [Function-Vector Heads Are Two Populations](https://arxiv.org/html/2606.07560v5) | 2026-10-04 v5，最新摘要、引言、来源与角色变化片段；预印本 | 正负贡献抵消与组件角色随任务变化已有；不能靠 magnitude 排名再包装一个有害头集合 |

## 检索方法与范围

先重读本项目研究锚点、After Error Feedback 论文、来源控制与自然行为报告、Goal 1/2、
`new_plan_1010.md` 和仓库根目录 `feedback1012.md`。该反馈文件实际位于根目录，非 `docs/`。
围绕三个关键词组进行多种表述检索：

- failed / negative demonstrations、function vectors、algorithmic primitives、negative feedback、task inference；
- error awareness、self-correction、verification vs decision control、role confusion；
- late invalidation、KV editing、retraction、dependency invalidation、selective forgetting。

对 ICLR 2025/2026、ICML 2026、NeurIPS 2025 的官方入口作定向检索；
ICML 的 AlgoTrace、FV 分解、Hindsight Editing 构成最直接碰撞。
从其正文与引用追到既有 FV／copy-suppression 研究，结合项目此前 CoVe、定位与反馈研究记录。
最新预印本检索覆盖至 2026-10-13，未依赖此日期之后的结果。

这不是逐篇遍历三大会全部论文，也没有完成所有相关论文的全文或代码复核。
因此“尚未看到完全相同的反馈调节程序计算实验”只支持继续评估，不能写成 novelty 证明。
若准备把 A 升级成 GPU 协议，应优先核查其最强近邻的细节及后续工作，
而不是以更长泛化文献清单代替决定性设计。

## 本轮保存与成本

- 官方 AlgoTrace／HEdit PDF 的提取文本：`outputs/idea-selection-20261013/literature/`。
- 精确路径示例：`outputs/idea-selection-20261013/material_example.json`。
- 新增模型请求：0；新增 GPU 用时：0；未改确认集，未启动后台实验。

访问失败记录：官方 PDF 的 web 入口返回 octet-stream 不支持，改用本地 HTTP 读取公开 PDF 并通过 pypdf 提取；
某 OpenReview PDF 出现浏览器挑战，未据无法读取的全文作结论。
