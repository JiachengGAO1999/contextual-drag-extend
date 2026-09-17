# 普通vLLM anchor吞吐预检（已授权并启动）

用户授权先做资源核查与小规模吞吐benchmark，并在本轮开始生成。随后明确授权只读使用 `/data/zhaoyi/liujunyuan/models/Qwen3-32B`。不启动64/104题baseline acquisition，不使用干预结果选题。

## 冻结工作负载

- 两道已使用的开发题577、1189，各16次clean-slate完整Thinking，共32次/anchor；这些benchmark题不进入新正式集。
- 原始初始采样wrapper、temperature0.6/top_p0.95；Qwen top_k20、context32768；n16、seed42。总上下文预算保持，输出不人为缩短。
- 普通vLLM0.11.0、默认worker、FLASH_ATTN、BF16、prefix cache关闭、chunked prefill开启、enforce_eager=True。没有import自定义mask worker；这是功能分离，不是继续优化科研kernel。
- 8B：16个并发序列、8192 batched tokens、0.85显存比例。
- 32B：单GPU4、4个并发序列、2048 batched tokens、0.95显存比例。每题仍采16条，只是调度并发不同。若单卡原上下文无法加载，则失败停止，不自动量化/缩上下文/换模型。
- stopping使用普通vLLM model/tokenizer默认；区别于custom后端显式EOS-only设置，配置已记录。因此测速不作为HF/custom后端科学准确率比较。

## 执行顺序和停点

8B普通后端32条 → 恢复本人的selective resident → 32B等待器核查前批exit0、32条结果与resident ready → 仅关闭本人的resident及子进程 → 32B普通后端32条 → 恢复8B selective resident。

第一批已在北京时间18:13:52进入生成，核查GPU4利用率95%、显存约68.9GB。两批合计最多64条；原批准的三anchor最多96条中的Nemotron部分尚未启动。

脚本：`scripts/run_qwen8b_anchor_benchmark_20260917.sh`、`scripts/run_qwen32b_anchor_after_8b_20260917.sh`。

日志：服务器repo根目录 `ordinary_vllm_qwen8b_benchmark_20260917.log` / `ordinary_vllm_qwen32b_benchmark_20260917.log`。

tmux：`qwen3-anchor-benchmark` / `qwen32-anchor-queue`。

输出：`outputs/ordinary-vllm-qwen8b-benchmark-20260917` / `outputs/ordinary-vllm-qwen32b-benchmark-20260917`，保存config、prompt/token请求、32条完整输出和summary。加载与生成计时分开，给出64题单anchor投影，不能把8B速度用于32B。

## Nemotron资源限制

官方模型卡确认研究用途及CC-BY-4.0：https://huggingface.co/nvidia/OpenReasoning-Nemotron-32B 。限定目录核查未发现现成32B权重；/data约38GB、/data2约31GB空闲；系统盘仅约66GB空闲，不将它自动用于接近占满的模型下载。未删除缓存/他人文件，未下载或改用7B。需要确认足够存储位置及原65536上下文运行资源后才能安排第三个benchmark。

## 结果解释

32次/anchor只用于粗略成本测量，包含完整长输出和尾部；不做并发参数搜索。两道开发题的长度不能保证代表新题。报告均值、完成率和最长输出，并给出投影不确定性；收到结果后再决定三anchor/双anchor方案和正式baseline预算。当前不自动进入大批次。
