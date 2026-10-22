# 新数据上的 R0 / R2 / R3 复验（2026-10-17）

用户要求在数据准备完成后复跑旧方法、检验结论并预备扩展。本轮执行原任务书预定的development实验：**固定20题，每题2个配对seed，3个条件，共120次科学生成**。原102题资格与20/82划分保持冻结，82题保留集本轮不生成、不用于调参。

## 假设与实验矩阵

| 条件 | 输入及访问方式 | 预先指定的比较 |
|---|---|---|
| R0 | 无历史，独立解原题 | R0−R2：错误历史是否造成拖累 |
| R2 | 完整错误草稿、明确错误反馈，正常访问 | 配对参照 |
| R3 | 与R2相同文本、token、位置和完整prefill；从第2个生成token起阻断草稿KV直接访问 | R3−R2：晚期阻断能否恢复 |

旧23题Qwen3-8B结果为R0 40/46、R2 18/46、R3 36/46，仅作历史参照。新池来自单8B严格资格筛选、同模型草稿，因此检验的是该新分布上的可重复性，不能代表全部Game24或跨模型结论。合格不等于存在drag或干预恢复。

## 材料与统计冻结

- 纳入原development全部20题，每题从完整8响应cohort的全部实质错误中，按`random.Random('20261017:'+canonical_id)`固定一份草稿；候选按模型名、整数sample index排序。选择不读取干预结果；保存所选原始记录、行SHA256和草稿SHA256。
- 草稿使用旧论文相同的完整`final_response`正文，包括其中的解题步骤；原始Thinking及全文仍保存在源记录中。草稿与目标均为Qwen3-8B。
- 使用旧评估seed `927001/927002`，与资格采样分开。temperature0.6、top-p0.95、top-k20、BF16、Thinking开启、上下文32768、batch size8、prefix caching关闭。
- 前5批为40次R0，后10批为80次R2/R3；每个R2/R3配对同批执行。逐条fsync保存；每批检查提示词、输入token、草稿跨度与首个生成token一致，不一致则停止。
- 主准确率使用原官方Game24 grader的`correctness is True`，每条件分母40。另报None、finish reason、长度、缺失。缺失保留在全部请求分母，未完成时不作完整复验的推断结论。
- 主效应R0−R2、R3−R2：先在题内平均两个seed，再做5000次题目bootstrap（seed20261017），报告95%区间；恢复与损伤分别计数。20题是独立样本量，不能将seed当独立题。
- 效应消失、反转或区间宽时按原分母报告，不换题/草稿、不追加有利seed。即便复验成功，也仅支持持续直接访问的行为作用，不能推出模型已经识别错误、内部复制或状态清除。

## 环境、资源与检查

本轮使用**A100物理GPU4**及实际旧论文独立快照`/data2/gaojc/tmp/game24-batch03-validation-20260924`。A800采集环境是ordinary vLLM0.10.2，不能直接运行旧worker；A100根checkout待机引擎也加载较早代码，不能直接复用。

旧快照146项SHA256全部通过；旧64个请求重新编码的提示词token全部一致。vLLM0.11.0 / PyTorch2.8.0 / Transformers4.55.4。新请求输入96–1769 tokens，至少保留30999生成token空间。模型不下载、不搬运。只释放经进程树、GPU归属、交互空闲提示核验的本项目resident，复验退出后恢复原待机服务，不自动向其提交实验。

4个最多4-token工程请求排除出科学分母，检查普通/逐条落盘调用一致及R2/R3首token一致。CPU关键审计4项通过：输入/首token差异、缺失分母、题目bootstrap及重复记录拒绝。

旧64次生成实测20362.95秒，按请求数外推120次约10.61小时；这是历史估计，不包括新题长度差异、工程探针及编译。16小时后不再启动下一批，执行中的批次可完成；保留缺失，不自动重试或扩展。预计新增文件小于1GiB，不复制权重/检查点。该阶段单独记账，不把采集240小时保护上限视作新的实验额度。

## 扩展准备与退出条件

先在development上用CPU描述已有草稿长度、错误形式、基线正确率及新观察到的drag/恢复/损伤。这些关联不能直接解释为内部机制。

若基础效应出现，优先形成一个可推翻的扩展预测：**干预效应是否随历史中可用信息而改变，而不是所有历史都应阻断？** 预案是在事前固定的少量development题上比较两份错误草稿，并加入已有正确历史的FULL/LATE配对；检查是否存在内容依赖的恢复与损伤。长度与内容同时变化时，不能宣称只由真伪导致。具体矩阵、成本和退出条件在读取这些新条件结果前冻结；本启动器不执行该预案。

基础效应不稳定时，先保留零/负结果，检查测量与筛选分布差异。不自动启动局部mask、头搜索、旧短候选评分、增模型或扩seed。82题保留集用于随后冻结方案的独立确认，本轮开发集不能代替确认。

## 运行入口

运行目录`outputs/game24-replication-qwen3-8b-development-20261017/`包含：

- `plan.json`、`pairs.jsonl`、`selected_source_records.jsonl`：冻结配置与20份材料。
- `prepared/manifest.json`、`preflight.json`：120请求与旧协议一致性检查。
- `launch.json`、`launcher.jsonl`、`console.log`、`status.json`：执行记录。
- `results.jsonl`：逐条原始输出；完成后自动写`completion.json`和`analysis.json`。
- `plan_before_runtime_verification_20261017.json`：0次GPU调用时对运行后端判断的修订历史，题目、草稿、seed与统计未改变。

启动命令（A100；已启动不可重复）：

```bash
cd /data2/gaojc/projects/contextual-drag-extend
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/start_game24_replication_20261017.py
```

tmux为`game24-8b-dev-replication-1017`。本地查询最新远程状态：

```powershell
ssh sjtu-a100 'cat /data2/gaojc/projects/contextual-drag-extend/outputs/game24-replication-qwen3-8b-development-20261017/status.json'
```

CPU检查：`python -m unittest discover -s tests -p test_game24_replication_20261017.py -v`。
