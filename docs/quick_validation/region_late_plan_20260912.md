# 局部late blocking验证：冻结标注与运行计划

用户已授权标注、必要代码修改及启动。四题1226/719/577/1358，四组原paired seeds（base2027/12027/22027/32027），四个新增条件，共64次。原R2与整段R3复用。只做late，暂不做path/descendants。

| 题号 | L_A末尾答案 tokens | L_E首次未纠正的构造错误 tokens | E标注理由 |
|---|---:|---:|---|
| 1226 | 20 | 13 | “Then, 6÷2=3”再次使用前一步8−6已用过的6 |
| 719 | 27 | 12 | 7−(5−8/8)在已保留外层8后，使用两个8构造子问题 |
| 577 | 20 | 27 | 第二因子(9−6)及其展开复用第一因子的6 |
| 1358 | 20 | 58 | 首次提出以加减7补齐漏数，包含提议句和完整等式；此前三数候选被明确否决，不算已接受的错误步骤 |

L_A仅遮最后boxed答案，正文中相同错误式仍可见。L_E仅遮上表完整步骤，不遮其后所有重复表达。负结果不能据此排除相应语义内容的作用。

L_CA/L_CE分别取草稿第一段正确说明的末尾等token长度窗口，与A/E精确匹配遮挡量。原始题目与独立解题任务后缀不受影响。控制区可能包含草稿内重述的数字/约束及通用解题说明，因此是非错误内容的遮挡量对照，不是位置、语义或有用信息的完美匹配；两种控制窗口可能嵌套，不能把它们当独立重复。精确文本、token/字符边界、spillover见[标注JSON](../../outputs/game24-region-late-20260912-annotations.json)。

所有输入逐token复用原R2 bundle，sample_seed也直接复用，固定Thinking temperature=.6/top_p=.95/top_k20/context32768，HF eager BF16、float32 sampling、官方scorer。全prefill保持不变、首token必须逐条等于原R2，否则停止。仅改变后续生成query无法访问的key区间。目标边界只容许格式spillover；原prompt未编辑。

新增代码selective_context/phase0/region_late.py；现有后端本已支持单span，不改核心attention实现。记录中draft_token_span字段表示实际干预区间；完整draft字符边界与原R2源bundle保留，另存region_annotation避免把局部区间误解为整个草稿。没有实现多span或细粒度path。

预检：64条唯一固定任务、16个区域，token与seed一致、目标/对照长度一致、所有区间落在draft内；6项mask回归测试通过。加载真实模型后，在四题×四区域分别检查一个decode query的36层attention，目标keys应全为0，检查失败不进入正式生成。此检查不是每个生成token的全程追踪。

优先报告accuracy，L_A−L_CA、L_E−L_CE与各条件相对R2/整段R3的paired转变。按题bootstrap仅作探索参考（nquestion=4，且按既有表现选题）。保留所有截断/不可评分，不能因为Thinking里有正确式就手工改分。辅助审阅错误式再采用、重复用数识别、Thinking/Final反转与长度。

单GPU4预计约4–6小时，长输出会增加耗时；无自动扩题或后续path。运行tmux qwen3-region-late，日志服务器region_late_20260912.log，输出outputs/game24-region-late-20260912/seed-*/results.jsonl。成功结束自动恢复常驻模型。
