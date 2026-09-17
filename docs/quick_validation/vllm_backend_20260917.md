# Selective vLLM后端：实现与验收记录

## 环境与范围

- 独立环境：`/data2/gaojc/envs/contextual-drag-vllm`，vLLM0.11.0、Torch2.8.0、Transformers4.55.4；完整锁定见`requirements/vllm-development-lock-20260917.txt`。
- 模型只读`/data2/huangrj/models/qwen3-8b`，无权重复制；GPU4 A10080GB。
- 支持full、late_block、固定单元/legacy多区间path_block；同一批请求可以有不同模式、mask、prompt长度和seed。
- eager V1 + FlexAttention，BF16，prefix caching关闭，不量化、不投机解码。V1实际启用chunked prefill，mask使用逻辑绝对位置，不能用chunk局部位置代替。
- 使用独立worker类，不修改安装包源码，不修改HF后端。

## 实现

`vllm_mask.py`把每个prompt key的阻断起点编码为表：late起点为prompt长度；path起点为该基本单元末端，重叠时取最早起点；full不阻断。生成key不被选中。

`vllm_worker.py`在GPUModelRunner的实际批次中按request id取SamplingParams.extra_args，处理请求重排。FlexAttention的分页物理位置先转换成逻辑q/k位置，再施加上述边界。元数据缺失、版本不符或不支持的microbatch映射直接报错。

A100实际遇到默认64x64 tile共享内存超限，已固定32x32 tile；这是kernel tiling调整，不改变mask定义。首版限制单GPU、1–8并发。CUDA graph未启用。

## 已完成检查

- 26项mask/fixed-path/新表示测试通过。
- CPU模拟分页地址乱序和请求重排，2112条边与HF参考一致，覆盖full/late/path、prefill和decode。
- 真实Qwen3三题full/late/path的256token greedy跑通；三题full与late首token一致。
- 三题path对选中token做替换后，64token greedy输出完全一致。
- HF/vLLM前256token：3/9完全一致，6处首次分叉已作同前缀概率审计；5处HF top候选并列，1处HF分差0.25。top20 logprob最大差约0.24–0.62，不能声称数值或逐token等价。
- 首轮短输出吞吐：1/2/4/8并发约45.45/84.09/134.56/180.10 tokens/s。包含当次prefill和生成、排除引擎加载；不能直接外推长Thinking或完整实验耗时。

初版 packed 长输出测试因吞吐下降而主动中止，没有完整结果，不能当作通过。优化版将纯 decode 的 query 按请求拆成独立 batch，KV 使用零 stride 视图，不复制缓存；prefill 仍走原 packed 路径。小型 GPU 检查相对 dense 参考最大误差 0.0009765625，修改被屏蔽 KV 后输出差为 0。

优化版首次真实验收触发 Torch Dynamo 默认 8 个编译变体上限。2026-09-17 12:37 CST 将有限上限设为 64 后重启，真实三题 path mutation 已重新通过；完整 Thinking、数值审计和吞吐仍待本轮产物确认。优化版使用 `SC_VLLM_DECODE_LAYOUT=per_request`；默认 packed 尚未切换。复现检查脚本位于 `tests/manual/vllm_paged_mapping.py` 与 `tests/manual/vllm_decode_layout_gpu.py`。

12:40 CST 更新：优化版短输出验收全部通过，数值审计仍为 3/9 greedy 前缀完全一致，分叉位置与 packed 相同；真实 mutation 3/3 通过。短输出 1/2/4/8 并发为 42.57/76.98/150.96/232.62 tokens/s（每档同样 2048 个输出 token）。本地已同步 `outputs/vllm-acceptance-per-request-20260917/`。完整 9 条 Thinking 已接棒，仍待完成；不以短输出速度预测完整实验加速比。

停止条件显式使用 `ignore_eos=True, stop_token_ids=[tokenizer.eos_token_id]`，避免引擎额外加入模型配置中的 151643；独立检查确认最终 stop 列表仅为 151645，与当前 HF oracle 一致。

## 实际运行入口

通用入口：`python -m selective_context.phase0.vllm_run --manifest <manifest.json> --output <new-output> --batch-size 8`。
manifest为JSON数组，每项包含仓库相对路径`bundle`、`pair`及该bundle中的`condition`。bundle保存原始token和请求，不重新构造prompt。输出兼容原官方scorer，保留Thinking、final、token、请求及后端元数据。temperature=.6/top_p=.95/top_k=20/context32768，生成预算为32768减prompt长度。

服务器运行前使用`CUDA_VISIBLE_DEVICES=4 VLLM_WORKER_MULTIPROC_METHOD=spawn`，并先确认GPU4原任务结束。使用独立环境python。不要同时启动另一个占满GPU4的后端。

完整smoke入口：`python -m selective_context.phase0.vllm_complete_smoke --output <new-output>`，需工程门槛结果存在。

## 科研使用边界

2026-09-17 用户明确收敛开发范围：优先交付能运行实验的第一版，不继续追求性能最优。当前 decode-kernel 验收完成 full/late/path 基本正确性、完整输出与官方评分后即可交付；不再追加性能迭代或反复 benchmark。当前运行：tmux `qwen3-vllm-decode`，日志 `vllm_decode_validation_20260917.log`。此前 per-request 完整输出测试已主动中止（未形成完整结果），所有中止记录保留。若本次失败，优先修复阻塞使用的问题或明确交付已通过的实现及其限制，不自动扩大优化范围。

HF保留为结构/正确性参考。新实验的比较条件必须统一在vLLM下运行，不能把新vLLM干预输出与旧HF基线当作同后端paired结果。相同seed跨后端不保证相同随机流；相同后端的并发形状也可能影响BF16舍入。保留backend、批次配置和版本信息。

本轮是工程验收，不以9条正确率作科学Go/No-Go。首版没有证明跨后端accuracy等价；后续科学结果应单列后端。
