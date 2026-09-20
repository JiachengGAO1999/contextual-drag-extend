# UFT外部Game24：20题配对验证

用户2026-09-19授权复核并开始生成。本轮采用已披露完整性限制的公开处理后轨迹；不更改Track A双anchor筛选协议。独立Track B，模型来源Qwen2.5-Math-7B CoT，target Qwen3-8B Thinking。

## 冻结样本

20题：510、724、507、176、792、856、476、322、414、121、752、235、147、827、721、529、330、412、366、495。

从已排除历史及预留题的625题中，按数值ID排序后用Python Random(20260919)打乱，取前20；每题在三步＋错误最终式候选中取 `SHA256('20260919:'+json(path))` 最小的文本。全过程未读干预结果、不按R0选题。冻结文件包含完整候选顺序和源CSV行号。

20份草稿已逐条读完：均有完整外观的三步及最终表达式，数值不为24或违反原数multiset；保留计算正确但结果非24的失败尝试，不将其误标为算术错误。部分步骤与最终式不一致，这是真实源输出，未修补。没有EOS证据，不能声明已验证非截断。全部源path逐行原样保留。

原文与审核：[draft_review.md](../../outputs/game24-uft-external-20q-20260919-prepared/draft_review.md)。机器记录：同目录pairs.jsonl、protocol.json、selected_raw.json、candidate_order.json。

## 条件与预算

20题 × seeds929001/929002 × R0/R2/R3/R4 = **160次生成**。不补R1，不自动重试或扩题。

沿用七题pilot服务器后端和独立求解prompt：selective vLLM0.11.0，Qwen3-8B只读权重`/data2/huangrj/models/qwen3-8b`，Thinking，temperature0.6、top_p0.95、top_k20、context32768，batch8，prefix caching关闭，per_request decode layout。R2/R3/R4共用完整文本、token及position；whole late/path逻辑attention blocking，不是物理KV删除。R3首token来自完整prefill logits，保持原边界。

本地Git16c60af、服务器基础Git7fc7245；仅新增本轮脚本和数据传至服务器，未部署本地尚未同步的MATH500/任务路由改动。参考运行即服务器原七题pilot，核心推理实现保持该版本；不声称两地Git一致。

## 假设及分析

- Primary H1：R0−R2，外部failed trace是否造成drag。
- Primary H2：R3−R2，阻断持续访问是否恢复。
- Secondary：R4−R2、R4−R3；不预设path优于late。
- 报告accuracy、reference→intervention错对转移、按题cluster的paired bootstrap CI、EOS/parse率、恢复比（分母接近0时不作强解释）。全部预选题保留，不用R0或干预得分事后删题。
- R0−R2小：说明这批短公开草稿没有形成足够drag，不否定长Thinking来源上的机制。
- R3−R2正：外部来源恢复证据，仍不能单独证明唯一传播机制。
- 若无恢复，先检查completion/parse和实现记录；不根据结果改选草稿。

## 运行与停点

tmux：`uft-external20-20260919`。启动脚本` scripts/run_uft_external_20260919.sh`，先确认原32B父进程仍STOP、GPU4空闲，再真实tokenizer预检和生成。原32B288/512维持暂停；不得同时恢复它。

日志：`outputs/game24-uft-external-20q-20260919.log`；状态：`outputs/game24-uft-external-20q-20260919-status.json`；逐批结果：`outputs/game24-uft-external-20q-20260919/results.jsonl`；完成标记：同目录completion.json。每8条保存一次。

参考七题56次9633秒，线性估计160次约7.65小时；预计7–9小时，输出长度可使实际偏离。约北京时间9月20日03:35–05:35完成（按9月19日20:35启动估计）。完成或失败后保留同一vLLM backend交互常驻，失败不自动重跑，没有下一批自动任务。

查看：`ssh sjtu-a100 'tail -n 20 /data2/gaojc/projects/contextual-drag-extend/outputs/game24-uft-external-20q-20260919.log'`。
