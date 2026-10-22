# 覆盖全部102题的复验（2026-10-19）

**已于2026-10-22 06:37:14北京时间完成。** 82题492次全部保存，合并此前20题共102题612次；完成状态`complete_all102_no_further_expansion`。完整结果与复核见[确认报告](FULL_REPLICATION_RESULTS_20261022.md)。以下是冻结方案与启动历史。

**2026-10-19 15:18北京时间：RUNNING。** A800 GPU4已通过16个固定旧请求的前4-token一致性检查及4个回调/配对短请求，开始492次科学生成首批；当时保存0/492。tmux `game24-8b-heldout82-1019`，后续以远程`status.json`为准。硬件短探针为16/16一致，仍不等于完整随机轨迹逐位一致。

用户明确要求在扩展后的全部题集上跑一遍。数据池实际为102道合格独立题；20题development已经完成120次R0/R2/R3。本阶段补齐原冻结的82题held-out，每题2个paired seeds、3条件，共492次新生成；完成后合计102题、612次生成。20题原结果直接保留，不覆盖、不重复计数。

## 协议与分析

R0为无历史独立求解；R2为错误草稿加明确错误反馈、正常访问；R3保持同一文本、token、位置、完整prefill及首个生成token，从第二个生成token起阻断错误草稿KV直接访问。草稿仍取完整`final_response`正文。

沿用`random.Random('20261017:'+canonical_id)`在同题完整8次响应的全部实质错误中选一份，按模型名/整数sample index排序。此选择规则重新应用于原20题，与其实际使用的20份草稿逐一一致；82题的选择在新干预结果出现前固定。None、截断和格式错误不提升为错误草稿资格。

两个seed为927001/927002，temperature0.6、top-p0.95、top-k20，Qwen3-8B Thinking、BF16、上下文32768、最大生成32768、batch size8、关闭prefix caching。R0共164次，R2/R3共328次，后者配对相邻，首次执行的每个配对同批。逐条fsync保存输出，检查全部164对R2/R3的文本、输入token、草稿跨度与首个生成token。失败与截断保留分母，不因恢复效果更换题目或草稿。

完成后分开报告：

1. **82题独立确认结果为主**：R0/R2/R3准确率、R0−R2和R3−R2、恢复与损伤、None、finish reason和长度。
2. **20题development结果为既有参照**，不冒充新的独立确认。
3. **102题全部结果为汇总描述**，每条件分母204。报告20/82及A100/A800分层；合并不改变development已被查看的事实。

每题先平均两个seed，以题目为重采样单位做5000次percentile bootstrap，seed20261017。完整题集未生成齐前不输出完整复验的推断结论；缺失保留全部请求分母并明确标注。无自动扩展条件、模型、seed、mask或新题。

## 执行环境

核查时A100 GPU4有其他用户任务，A800 GPU4空闲。因此本阶段使用一张A800物理GPU4，UUID `GPU-9d164491-5abf-96eb-3d3f-e08e77deb8f7`。不停止其他任务。

从A100复制已有vLLM0.11.0 / Transformers4.55.4 / xgrammar0.1.25及旧论文146项hash绑定的后端快照，在本项目目录形成独立导入overlay；共享安装环境保持原样。其余关键版本为Torch2.8.0、tokenizers0.21.4、xformers0.0.32.post1。显式使用PyTorch原生采样器，与上一轮的fallback一致。

压缩运行包533,808,307 bytes，SHA256 `6bebd016fb13d104baa128bdb41da701d6739add3cead99adcfba1f0c4aa8ca2`，3707项文件逐项校验。模型权重沿用A800已有文件，通过符号链接引用，不下载或跨服务器搬运；配置、generation config和tokenizer采用A100原元数据，避免A800原目录扩大的位置配置造成差异。权重索引必须相同，记录全部分片大小；没有宣称重新逐字节校验全部权重。

准备时对已完成development的全部120个请求重新编码，要求输入token完全一致。GPU启动后先固定重放8个旧R0、8个旧R2/R3请求的前4个token，与实际A100记录比较；再做4个held-out短请求检查回调落盘与首token一致。这20个短工程请求不计入492次科学分母。短探针一致不代表完整跨硬件随机轨迹逐位相同，因此仍保留平台分层解释。检查不通过则不进入held-out完整生成。

## 成本与停止边界

上一轮120次实测15.3965小时，按数量外推492次约63.13 GPU小时；A800平台、题目和轨迹长度差异尚未实测。这是估计，不是完成保证；若10月19日下午启动，点估计约10月22日上午完成，首批后应更新。

本阶段另设96小时累计运行保护上限（含尝试时间），达到后不再启动下一批，在执行批次可完成。运行文件与日志预计小于1GiB，另有约1.5GiB展开的软件overlay及约0.5GiB归档、编译缓存。启动及批间检查磁盘至少2GiB；不足则保留已完成结果停止。GPU启动前必须无compute进程。

支持显式断点续跑，核验原材料/代码/manifest绑定，只补缺失的题目-seed-条件；已完成回答不重抽。完整R2/R3配对仍须通过不变量检查。没有自动重试或追加条件。

## 文件与命令

本地及A800项目下逻辑运行目录：`outputs/game24-replication-qwen3-8b-heldout82-20261019/`。A800物理目录为`/home/gaojc/.local/share/contextual-drag/game24-replication-qwen3-8b-heldout82-20261019/`，项目内同名目录通过符号链接访问。共享/data空间降至约2.9GiB后，仅将本次新建运行目录复制到系统盘，4195个常规文件逐字节hash核验一致，保留全部权重链接，复查冻结preflight全部hash后移除/data上本次重复副本；没有删除旧研究或改动共享模型/环境。迁移后系统盘约6.4GiB、/data约4.75GiB。记录见`storage_migration.json`。

`plan.json`、`pairs.jsonl`、`selected_source_records.jsonl`为冻结材料；`runtime_profile.json`和`runtime_staging.json`为运行包校验；`prepared/manifest.json`和`preflight.json`为492请求及协议检查；`status.json`、`budget.json`、`console.log`及`resume_console.log`为运行状态；`results.jsonl`为原始输出。结束后写`completion.json`及包含heldout82/development20/pooled102三个范围的`analysis.json`。

首次启动因ZMQ临时socket路径超过107字节失败，改用`/home/gaojc/.cache/cd82-1019`短路径。第二次因spawn子进程重新导入旧helper后将最小checkout排到参考后端前面，找不到worker而失败；现于模块导入时为父/子进程恢复overlay与参考后端优先级。两次均在0条科学输出时发生，累计17.70秒纳入账目。旧启动器、runner和preflight均归档，修订记录分别为`short_tmp_fix_revision_20261019.json`与`worker_path_fix_revision_20261019.json`；题目/草稿/seed/采样/掩码未变。追加spawn路径回归检查通过。

启动（A800，已启动时不可重复）：

```bash
cd /data/gaojc/projects/contextual-drag-extend-game24-100q
.venv/bin/python -u scripts/start_game24_heldout82_a800_20261019.py
```

查询：

```powershell
ssh sjtu-a800 'cat /data/gaojc/projects/contextual-drag-extend-game24-100q/outputs/game24-replication-qwen3-8b-heldout82-20261019/status.json'
```

启动前及修复后CPU检查共30项通过，包含82题分母/缺失、跨split或重复结果拒绝、题目bootstrap、原20题草稿选择完全复现及spawn子进程导入优先级。120个development请求重新token化全部一致，新请求输入96–1897tokens。原开发集结果见[结果报告](REPLICATION_RESULTS_20261019.md)。
