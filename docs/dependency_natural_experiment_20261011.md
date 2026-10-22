# 当前实验：同一次Thinking中，根值与依赖结果是否一起更新

> 完成更新（2026-10-11夜间）：CLEAN与CORRECT_ROOT各64/64，均六步全正确，
> 无截断、无“根正确而依赖项保留旧值”的共同模式。统计单位为32个基础组。
> 停止这条材料上的机制定位；前批短数字偏好不再作为自然撤销失败证据。
> 这不是对所有推理撤销问题的否定。后续有限方法探索见
> [夜间记录](overnight_mvp_20261011.md)，原始结果在`dependency_natural/`。
> 下文保留阶段设计与提交记录，“当前只运行CLEAN”已是历史状态。

## 假设与例子

待检验：模型已经在自己的回答中写出正确的错误源值，后续却仍使用
依赖该错误的旧结果。这里要求发生在**同一次真实生成**，不能把
不同固定前缀上的数字概率当作已观察到这一现象。

例子：A=23−9，旧草稿错写12，正确为14；B=6+6，正确为12。
旧草稿据此把(A+3)×2和(B+3)×2都写成30。明确纠正A后，前者应
改成34，后者应保留30。交换两条分支的依赖，修正对象也应交换。

## 为什么增加自然测量

前一短评分批次已完成576项：明确给根正确值后，根读出64/64偏好
正确，但依赖终点仅3/64偏好修正值。无旧草稿的CLEAN依赖终点也
仅30/64偏好正确，说明直接逼出数字的测量基线不稳定；三个读出
还是分开的分支。该结果提示旧值偏好，不能确认内部撤销机制。

本批允许模型正常Thinking，最后一次性提交全部六步JSON。这样
根、依赖项和独立项来自同一次实际回答，精确算术可逐项核验。

## 当前只运行CLEAN阶段

固定沿用原32组参数与两个依赖版本，共64次生成；不按上轮效果挑题。
只给方程，不给错误草稿、不插入正确推理前缀。Qwen3-8B BF16，
单A100 GPU4，greedy、Thinking开启，每次最多2048个新tokens。

若自然基线也不能可靠完成这类计算，停止把这些材料作为机制证据。
若基线可用，再评估同一题、同一生成方式下CORRECT_ROOT比较，
最多另64次；**不自动启动该阶段**，不新增题、seed、heads或窗口。
这是同题的测量桥接，不是独立外部验证集，也不是新的创新结论。

保存原始响应后才评分。只解析`</think>`后的六步JSON；未闭合
Thinking、截断、缺字段或解析失败均另列，保留在64请求分母。
报告全部六步正确、根正确、依赖正确、独立保持和旧值复用；
按32个基础参数组汇总，不把64版本当作64个独立样本。

## 执行与资源

2026-10-11 01:15:56北京时间已提交tmux：
`qwen3-8b-dependency-natural-clean-20261011`。
主入口：`scripts/run_dependency_natural_20261011.py`。
启动后首批进度：10/64，已完成10次均六步正确、无截断；按首批速度
预计剩余约18分钟。该快照仅用于监控，不据此前10次下总体结论。
复用原GPU4启动器和共享24小时预算；本次启动前累计14.92小时，
剩余9.08小时。CLEAN阶段最多131072新tokens；按30–60tokens/s估算
生成部分约0.61–1.21小时，实际ETA根据首批记录更新，加载也计预算。

原始结果与进度：`outputs/generation-diagnostics-20261005/dependency_natural/`
下的`generations.jsonl`、`behaviour.jsonl`、`run_state.json`、`summary.json`、
`current_request.json`和`runner.log`。原始响应先保存，不因解析失败重生成。

```bash
ssh sjtu-a100
cd /data2/gaojc/projects/contextual-drag-extend
/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/run_dependency_natural_20261011.py --status
tmux attach -t qwen3-8b-dependency-natural-clean-20261011
```

正常启动命令已执行，不要重复提交：

```bash
/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/launch_generation_diagnostics_20261005.py --dependency-natural
```

后续CORRECT_ROOT仅在另行决定后用同一入口显式选择phase，不由本
阶段结束自动触发。新评分解析测试2通过，连同原语义和分析测试6通过。
# 夜间状态更新（2026-10-11）

用户已授权休息期间继续自主推进。CLEAN完成64/64、全部六步正确、
无截断；CORRECT_ROOT已于约01:36北京时间提交，同一HF后端。
因此下文“当前只运行CLEAN、不自动开始纠错”是此前阶段的冻结记录，
已由新的夜间授权与明确阶段判断推进。最新后续安排见
[夜间MVP协议](overnight_mvp_20261011.md)。

