# 双 Qwen anchor 夜间 acquisition：2026-09-17

用户明确批准双 anchor adaptation、固定前20题、每模型每题16次，最多640次新生成。不是原论文三anchor/653题的精确复现。不运行 intervention。

研究方向：先建立跨模型、baseline-only 的可用失败草稿池，再检验错误上下文下 whole late/path 是否恢复。暂停细粒度mask类别扩展。最终目标仍是增加独立题目；今晚不保证达到30–50题，最多20题候选。

## 冻结协议

- 原准备候选顺序前20题，未按本轮结果挑选：964,6,44,137,914,1293,655,753,1112,697,1126,949,165,41,1033,1057,125,413,152,509。
- Qwen3-8B / Qwen3-32B 只读原权重，不复制。Thinking，temperature=.6, top_p=.95, top_k=20, context=32768，n=16, seed=42。
- 普通vLLM0.11默认worker、FLASH_ATTN、BF16、eager、关闭prefix cache、开启chunked prefill；沿用已通过benchmark配置。8B并发16/batched8192/memory.85；32B并发4/batched2048/memory.95。
- 题目文字采用当前ToT转换器；外层复用upstream prompt。不是原始完整数据的精确恢复。
- 每两题为一批，依次8B32B；共20个模型批次，每批32条。每批结束保存原始输出、token、评分和summary。
- 原n4/seed42结果不加入primary pool，以免与新n16重复计数。新增640为完整新n16请求，不宣称与旧样本独立。
- eligibility：正常stop、Thinking解析成功、严格True>=2且False>=2，跨模型合池。只有两个anchor都完成各16次的题才列eligible。False仍可能是格式错误，需下一轮人工审核实质性失败；本夜不抽draft、不自动评测。
- 不要求达到某个eligible数量才停，不按干预效果补题。最多640生成；11小时后不开始新两题组，12小时终止正在运行的批次（不完整批次排除）。因此完成量可能小于640。

## 预算和监控

32B benchmark32条总3615秒，8B32条555秒，10组约11.6小时。实际长度不同，不能保证20题全完成。2026-09-17约23:46北京时间启动，预计次日09:45–11:45，最长约11:46结束生成，随后常驻加载。

服务器目录 `/data2/gaojc/projects/contextual-drag-extend`。
tmux `dual-anchor-overnight-20260917`。
总日志 `outputs/dual-anchor-overnight-20260917.log`。
输出 `outputs/game24-dual-anchor-20q-20260917/`。
`status.json`记录当前批次，`pool_summary.json`记录已保存样本与strict-scorer eligibility，`batch-*.log`记录vLLM运行。
脚本 `scripts/dual_anchor_overnight_20260917.py`、`scripts/run_dual_anchor_overnight_20260917.sh`、manifest同目录。
正常结束/生成失败/预算超时后恢复GPU4 selective resident。启动前确认没有待自动启动的旧resident任务。

## 预检与异常

本地AST检查、固定候选前缀/唯一性/两模型采样配置一致检查通过；远端py_compile与bash -n通过。GPU4唯一自己的resident；/data2剩余17GB，权重不复制。首启在停止resident后的psutil.wait_procs遇到pidfd EINVAL，尚未加载生成；改用限时存活状态轮询，实测GPU4为0MiB后重启。未产生重复生成。

## 前轮审计纠正

96条：82官方正确、8实质错误（含1057/1）、3纯格式错误、3超长。1057/1正文同样重复使用9，不应归纯格式。四次全部官方正确为16题，不是18。原analysis文件保留，以上为纠正说明。

补充启动记录：第二次启动发现Windows CRLF shell行尾，已转换LF；两次均未开始生成。最终队列在北京时间23:45:51进入running，第一批8B加载中。
