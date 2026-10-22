# Game24：Qwen3-8B单anchor采集

**2026-10-22：全102题复验已完成，612/612条齐全。** 82题确认R0/R2/R3为63.4%/33.5%/57.9%，恢复+24.39个百分点[+13.41,+35.37]；全102题为64.2%/33.3%/58.3%。截断与None保留分母，全部204对一致性检查通过，未自动扩展。[完整确认结果及证据](FULL_REPLICATION_RESULTS_20261022.md)。以下为启动与采集历史。

**2026-10-19 15:18北京时间：全102题复验补跑中。** 补齐82题×2 seeds×R0/R2/R3＝492次新生成，保留20题120次，最终612次。A800 GPU4的16个固定旧请求前4-token及4个短请求检查通过，主实验首批运行，当前保存0/492。分别报告heldout82确认与pooled102汇总。[方案与状态查询](FULL_REPLICATION_PLAN_20261019.md)。

**2026-10-19核实：开发集复验已完成120/120。** R0/R2/R3为27/13/24（各40次）；恢复+27.5个百分点，题目bootstrap95%区间[+10.0,+47.5]。82题held-out未使用，未自动扩展。[完整结果与核验](REPLICATION_RESULTS_20261019.md)。以下为启动及采集历史。

**后续复验已启动（2026-10-17）：** 用户要求复跑旧方法并预备扩展，当前在A100 GPU4执行固定20题development×2 seeds×R0/R2/R3，共120次科学生成。4个短工程请求已通过，主实验首批运行中；82题held-out未使用。详见[复验方案与状态查询](REPLICATION_PLAN_20261017.md)。以下为数据采集完成时的历史记录。

**数据准备已完成：2026-10-17 01:26:50北京时间，102道合格独立题已冻结。** 共筛选720题，保存5760条8B回答，development20题、held-out82题；GPU4已释放。完整结果和本地数据位置见[完成报告](GAME24_100Q_ACQUISITION_REPORT.md)。机制探索尚未启动。原先22:38从磁盘中断中恢复的任务已正常达到目标；下方为协议与采集历史。

本任务最初于2026-10-15 09:57北京时间启动；达到至少100道严格合格独立题后冻结并停止。

2026-10-15用户明确提出暂时只使用8B anchor，以加快100题数据准备。此目录为独立的单anchor协议和资产；原双anchor目录`docs/game24_100q`及其原始32B回答保留为历史，不混作单anchor资格见证。

## 当前资格和资源

- 仅Qwen3-8B Thinking，ordinary-vLLM，单张A800 GPU4；每题固定8次，最多8并发，temperature0.6/top-p0.95/top-k20，上下文32768、bf16，逐槽seed20261014+i。
- 每题同一完整8响应cohort内至少2条正确和2条完整实质性错误；None、歧义、格式错误、截断不自动算实质错误，已完成无效回答不补抽。
- 复用原pilot的全部128条8B响应：16题、2题合格（584、1053），8B成功作业0.659小时、含首次失败为0.668小时。重新核验的历史8B prefix8记录1024条，没有额外未暴露的合格题。
- 旧双anchor合格643、1119的错误来自32B，不计入本单anchor池。pilot起点为2/100；最新进度以上方记录和progress.json为准。100题文件在达到目标前保持为空，development/held-out未冻结。
- 保留原先预冻结的1034题顺序，前16题已由复用pilot完成；后续每批32题×8=256响应，独立审计后再继续。不能只给已有错误的题补样。
- 全项目240小时保护上限保留；此前双anchor失败/停止作业8.0048小时继续计入，不能因改协议清零。每个新8B批次上限8小时。
- 以2/16合格率和含失败的0.668小时8B pilot外推，剩余98题约需784道新题、32.7 GPU小时。该数是小pilot的点估计，非完成保证；每批更新成本，超出剩余额度或冻结宇宙耗尽时停止。
- 新8B数据池只支持该anchor下的结论；如后续需要跨模型验证，应另行明确验证集和协议，不能把当前结果说成原三anchor复现。

## 启动和观察

```powershell
python -X utf8 scripts/game24_100q_status.py
python -X utf8 scripts/game24_100q_status.py --protocol dual
```

默认状态命令选择新8B协议；`--protocol dual`仅查询旧停止作业。

资源满足后在A800执行：

```bash
cd /data/gaojc/projects/contextual-drag-extend-game24-100q
bash scripts/start_game24_8b_a800.sh
```

启动及运行时要求/data可用空间至少2GiB、GPU4启动前无其他compute进程、UUID/版本/配置匹配。原10GiB是保守工程默认值，非模型运行需求；16题全部8B原始数据实测6,164,152字节，按pilot点估计784道新增候选约302MB，覆盖所有剩余1018题约392MB，该次修订时约4.5GiB可用。运行中每15秒检查空间，低于2GiB停止，每条完成回答fsync保存。该估计不保证共享盘不会被其他作业填满。

门槛10→2GiB的旧配置与原preflight绑定已归档，修订见`resource_guard_revision_20261015.json`；采样、资格和240小时总预算未改变。此前awaiting_disk_space属于修订前状态。持续任务日志在`outputs/game24-100q-8b-20261015/acquisition/a800/campaign.console.log`，每批和模型分别保留日志。

达到至少100题后，按固定seed20261014冻结20题development、其余held-out，并停止数据采集。此campaign不自动开始R2/R3或机制探索。

## 验证位置

`acquisition_campaign.json`记录用户协议修订、旧账目及原始文件hash；`audit_summary.json`记录资格计数；`game24_eligible_candidates.jsonl`保存8B独立见证；`game24_trajectory_pool.jsonl`保留原文路径/行号/hash。运行时报告和进度分别为`GAME24_100Q_ACQUISITION_LIVE.md`与`progress.json`。

CPU验证：`python -m unittest discover -s tests -p 'test_game24*.py'`（本次21项通过，包括断点恢复分母和磁盘阈值合法性检查）。
