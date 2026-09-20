# 2026-09-20 夜间验证与可用记录

## 已完成及部分结果

|实验|独立题数 / 配对数|R0|R2|whole late R3|whole path R4|解释|
|---|---:|---:|---:|---:|---:|---|
|双-anchor初始pilot|7 / 14|12/14|4/14|12/14|10/14|明显drag及recovery；strict subset排除41后为6题|
|公开UFT外部草稿|20 / 40|36/40|39/40|34/40|40/40|未出现drag，不应声称阻断恢复；R3有3次长度超限|
|MATH外部草稿，未完成|3 / 6|6/6|0/6|6/6|5/6|仅冻结顺序的前三题，不能外推16题；R4有1次长度超限|

分母均包含长度超限，不能只报告成功解析子集的准确率。原十题及局部mask实验保留为开发历史，不并入新确认集。UFT与MATH不是双-anchor同分布样本。

数学已保存24条的metadata中`enable_thinking=False`是默认字段遗漏，实际冻结prompt和输出均为Thinking；续跑修正字段，旧记录不覆盖。此前失败的retry1/retry2没有正式科学结果，不合并。

原始记录：
- `outputs/game24-dual-anchor-validation-20260918/`：56条。
- `outputs/game24-uft-external-20q-20260919/`：160条。
- `outputs/math-external-16q-20260920-retry3/results.jsonl`：启动前24条；服务器继续追加，本地副本需后续同步。

## GPU4 acquisition完成及审核

Batch02完整32题：Qwen3-8B和Qwen3-32B各题16次，共1024条。合池938 correct、60 official False、26 excluded。60条中53条实质性失败、7条格式错误。32B新增18条False全部为实质性失败。不能用官方False直接替代substantive审核。

严格2C/2F eligible共8题：1342、956、339、1214、754、1305、230、717。289仅格式错误被排除。新8题尚未观察干预结果。已有7题pilot+新增8题=15题进入该实验管线；排除pilot题41后的strict合计14题，不能把15题全称独立held-out确认集。

冻结资料：`outputs/game24-batch02-validation-20260920-source/audit.json`、`pairs.jsonl`。从substantive错误池按(model alias, sample index)排序，用`random.Random('20270918:'+qid).choice`选择每题一条，复用pilot的选择规则。Game24保留final_response正文而非完整Thinking，保持与七题pilot一致；MATH使用完整公开trajectory，因此二者的草稿构成存在差异。

64条prepared请求已同步本地，验证无重复，输入长度96–1501 tokens；每题每seed的R2/R3/R4引用同一编码bundle。

## 已批准并启动的队列

用户批准上限176次。本轮实际168次：
1. 原16道纯文本数学题（8 MATH500 + 8 MATH train），原128请求保留24条，续104条。
2. 新8题Game24 × seeds927001/927002 × R0/R2/R3/R4 =64条。

GPU4；tmux `night-validation-20260920`；2026-09-20 23:16北京时间启动。只替换我们自己的空闲resident，未使用其他用户GPU进程。没有新增baseline、题目、条件或科学重复请求。每个任务另有8条、每条4-token工程探针，不计科学样本。

23:21:54短接口一致性验收通过（STREAMING_SMOKE_PASS）；23:22:04已进入正式数学续跑，Running=8，瞬时aggregate generation约41.5 tokens/s。这不是整批平均吞吐，不据此承诺完成时间。

数学旧GPU0恢复尝试未成功运行；此次才在GPU4从24条断点恢复。有效token mask不改，保持静态形状编译和关闭mask cudagraph；有限Dynamo per-frame上限1024、累计至少2048，避免原64变体限制。每条完成立即fsync。失败停止后续队列，不自动重试；正常或失败退出均恢复GPU4 resident。

服务器运行根目录：`/data2/gaojc/tmp/math-external-16q-20260920`。
- 总日志 `outputs/night-validation-20260920.log`
- 数学日志 `outputs/math-external-16q-20260920-retry3/night-resume.log`
- Game24日志 `outputs/game24-batch02-validation-20260920-night.log`
- Game24结果 `outputs/game24-batch02-validation-20260920/results.jsonl`

原数学24条耗时约3.36小时，按此粗算104条约14.6小时；题长差异很大，不能承诺一夜全部结束。Game24另需数小时，明早优先验收已持久化部分。后续只分析冻结全批/预定义来源层，不按部分结果选择追加题。

## 下一步优先级

完成两批后，分别计算R0-R2、R3-R2、R4-R2及R4-R3、paired transitions、question-cluster bootstrap、EOS/parse率。MATH500和MATH train分别报告。新Game24是对旧pilot的独立样本检查，MATH检验跨任务/外部长草稿边界；UFT无drag结果保留为失败边界，不扩这一路生成。

在这两项完成前，不新增局部mask或性能优化。下一轮优先考虑正确草稿的同等阻断control及第二target模型，但需先核对本轮结论、预算和模型后端验收，不在本队列自动执行。
