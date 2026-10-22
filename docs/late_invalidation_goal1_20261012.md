# Goal 1：Late Invalidation机制可行性

目标：建立低成本、可复用的内部机制协议，判断提前和事后错误标记产生的状态
差异是否因果地影响历史干扰，以及是否值得发展为ICLR机制工作。不是以证明
假说为目标。单Qwen3-8B、BF16、单A100 80GB，10–14天阶段周期。

## 冻结材料与测量

- 校准：已有candidate-adoption实验的全部30个独立Game24问题，沿用经审核
  的自然错误草稿、合法式和非法式。不是新的确认集，不继续细分错误种类。
- 新材料：Stepwise Verification and Remediation公开教师首错标注库。
  按题目文本去重取首条，排除当前source-binding的64题；只要求末行数值答案
  明确、正确与错误答案不同、首错索引与文本一致。不按模型表现选题。
  可用548题，种子20261012打乱取前128题：32发现、96确认。
  原学生回答由既有模型生成；跨题独立不等于跨数据集或跨模型泛化。
- 候选：Game24为原合法/非法表达式，新题为参考解和学生解的最终数值。
  只评分选项标签1/2，每题两种选项顺序取平均；不把顺序或措辞当独立样本。
  教师首错理由只保存在材料中，不注入提示。正确历史参考解另存供Gate 2。
- 主读出：Thinking模板，强制一条不包含题目答案的短中性思考前缀，随后评分
  两个单token选项。`p_correct`为两选项内部归一化概率；同时记录两个选项在
  完整词表中的概率质量、log-prob及margin。它不是自然生成准确率，也不等于
  检出了抽象错误策略。Gate 0检验这种读出是否具有所需效度。
- 全部统计按题目配对，5000次bootstrap、种子20261012。缺失、失败与覆盖率
  单列；不换题、不把未完成项算错，也不按效果剔除问题。

来源：[公开数据](https://github.com/eth-lre/verify-then-generate/blob/main/dataset/dataset.json)。
冻结文件：`outputs/late-invalidation-20261012/manifest.json`。

## Gate 0：短评分必须测到历史干扰

30校准题和32发现题，各比较CLEAN、NEUTRAL、POST，两种选项顺序，共372次
forward。首要量为每题`p_correct(CLEAN)-p_correct(POST)`，POST明确标记草稿错误。

两个题组分别要求：完整配对覆盖至少90%；CLEAN平均正确候选偏好≥0.60；
所评分选项的平均词表概率质量≥0.10；平均历史损失≥0.05且95%区间下界>0。
NEUTRAL为辅助，不能替代POST让主gate通过。

失败时只允许一次预定测量修正：相同题目、任务和候选，在Thinking结束后的
固定JSON `choice`字段评分1/2，代替思考内的读出。重新做372次Gate 0；若仍
失败，停止本评分协议，不打开确认集。此时结论是测量未被验证，不是假说被否定。
程序缺陷的修复不是改题或换指标；任何修改必须记录，确认集不参与修正选择。

## Gate 1：告知时机、措辞与位置对照

固定两个短标签槽，分别位于草稿之前和之后。标签明确指向Draft A，不依赖
following/preceding的指代变化。每种措辞使用错误、中性及另一种中性标签：

| 措辞 | 错误标签 | 中性标签 | 安慰剂标签 |
|---|---|---|---|
| note | Draft A note: incorrect. | Draft A note: included. | Draft A note: provided. |
| sentence | Draft A is wrong. | Draft A is shown. | Draft A is supplied. |

| 条件 | 前槽 | 后槽 | 用途 |
|---|---|---|---|
| CLEAN | 无草稿 | 无草稿 | 校准与辅助基线 |
| NEUTRAL | 中性 | 中性 | 未标错历史 |
| PRE | 错误 | 中性 | 提前标错 |
| POST | 中性 | 错误 | 事后标错 |
| PLACEBO_PRE | 安慰剂 | 中性 | 普通标签位置效应 |
| PLACEBO_POST | 中性 | 安慰剂 | 普通标签位置效应 |

用真实tokenizer预先检查：同题、同措辞、同选项顺序下，所有历史条件的草稿
token、绝对位置和读出位置严格一致；不新增哈希。若不一致，在模型加载前
修复标签或分段实现并记录，不能带着位置混淆解释KV机制。CLEAN移除历史，
其位置不匹配，因此只用于校准与辅助，不能用于定位PRE/POST编码差异。

首要量：`(PRE−POST)−(PLACEBO_PRE−PLACEBO_POST)`，先在题内平均两种
选项顺序和两种措辞。辅助报告原PRE−POST及各措辞方向，不追逐次要显著性。
安慰剂只能排除所测试的中性措辞位置差异，不能穷尽全部顺序/语义混淆。

发现集：至少29/32完整，首要均值≥0.03，两种措辞均为正，才打开确认集。
确认集：至少87/96完整，首要均值≥0.05、95%区间下界>0，两种措辞均为正。
阈值表示3/5个百分点的候选条件偏好差，是可行性门槛，不是准确率恢复阈值。
若未过，记录无支持或证据不足，停止此版本，不换题/措辞/seed寻找显著性。

完整Gate 1为128×22次评分，校准180次；复用Gate 0，不重复已完成请求。
一次读出协议最多2996次forward；若启用一次Gate 0修正，总上限3368次。
确认集题单在任何新评分之前冻结；仅确认结果通过才能设计并启动Gate 2。

## Gate 2：有差异才定位内部对象

不预先搜索heads或开发大规模patch框架。优先在发现集比较四个连续层组，
选择最多一个局部层组，选择指标必须优先区分PRE donor与中性donor，随后
冻结位置、替换强度和全部对照；确认集不能用于选择位置。

必须包含POST接受PRE草稿KV、中性donor替换、K-only、V-only、反向替换，
以及正确历史的对应对照。先做一次少量同状态替换检查。目标草稿位置对齐，
基线和patch均采用相同分段计算；替换后重算原recipient的草稿后文本，避免
把不一致的旧后缀缓存当成自然反事实。K/V拆分本身可能产生非自然组合，
因此它是干预证据，不是自动读取到了天然独立的计算模块。

完整Gate 2配置、确认范围和定量判据，在Gate 1通过之后、任何移植结果
产生之前另行冻结。正确历史若存在天花板，不能据无损伤宣称保留有用信息。
仅patch有变化不能证明write-once造成撤销失败；需要来源特异性、方向预测
和相应行为读出一致。若只是一般扰动/拒绝倾向变化，则PIVOT或STOP。

## Gate 3：研究决策与创新边界

- GO：独立确认的时机差异，加上有来源特异性、方向预测的因果干预，且能
  给出超过提示顺序或一般上下文干扰的解释。GO是继续发展论文，不是ICLR保证。
- PIVOT：现象可复现，但状态干预只支持一般读取或扰动，或与既有机制重合。
  先评估新的解释对象，不自动启动错误向量或另一个机制矩阵。
- STOP：评分两次未验证，或确认集不支持时机差异，或必要对照否定候选。
  输出有限协议的边界，不将无显著差异称为总体等效。

旧R3/R4在Game24为36/46与35/46，没有一致更早阻断收益。本协议改变草稿
编码时的信息，而非仅改变读取权限；仍须解释旧结果，不能绕过已有负证据。
False induction heads、function vectors、算法向量和来源角色混淆均已有研究：
[Overthinking the Truth](https://arxiv.org/abs/2307.09476)、
[Function Vectors](https://arxiv.org/abs/2310.15213)、
[AlgoTrace](https://proceedings.mlr.press/v306/lippl26a.html)、
[Role Confusion](https://proceedings.mlr.press/v306/ye26b.html)。
架构的KV不回写是已知属性；未来query仍可使旧内容在功能上失效。

## 运行、用时与交付

Gate 0预估15–45分钟；Gate 1额外30–120分钟，Gate 2若值得开展估计1–3小时。
含加载、等待另计；按首批真实吞吐更新，不恢复旧24小时总预算门槛。
不调用外部模型API，不保存全attention或全模型激活；预计文本/分数文件<100MB。
现有196次source-binding批次完成后串行运行，不扩展该分支。

阶段安排：第1–2天完成材料、Gate 0；第3–5天Gate 1；第6–9天有条件Gate 2；
第10–14天形成证据边界与GO/PIVOT/STOP。GPU排队可能延长日历时间。

```bash
python -X utf8 scripts/run_late_invalidation_20261012.py --prepare
# 在远端tmux中，自动等前批和GPU4：
bash scripts/start_late_invalidation_20261012.sh
python scripts/run_late_invalidation_20261012.py --status
python scripts/run_late_invalidation_20261012.py --analyse
```

逐请求写`scores.jsonl`，`run_state.json`记录阶段与用时，`gate0_r*.json`及
`gate1_*.json`记录判据，`analysis.json`保留统计。不自动重启失败进程；
显式续跑只跳过完整保存的请求。Gate 2尚未实施，不能把Gate 0/1跑完当作目标完成。
