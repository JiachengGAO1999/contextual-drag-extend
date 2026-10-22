# Pilot 下一步决策（2026-10-15）

**已由后续用户决定更新：暂时只用Qwen3-8B anchor。** 当前协议见[单anchor记录](../game24_100q_8b/README.md)，不再按下文建议补完51条32B响应。下文为用户改变anchor前的决策记录。

当前为建议和CPU分析记录，未改变采样配置、预算或启动GPU。目标仍为至少100道独立严格合格题，优先双Qwen anchor，先完成pilot成本检查再扩大。

## 已完成的保护工作

已把停止状态下的pilot原始回答、配置、日志与campaign账目备份至本地
`outputs/game24-100q-20261014/pilot_partial_backup_20261015/pilot_partial.tar.gz`。
共23个文件，压缩包2,053,372字节；每个文件均与远端SHA256核对，清单为同目录`source_manifest.json`。包含205条保存响应；备份未删除或修改远端文件。

## 同题比较结果

CPU复核使用冻结的`classify`规则，4次为每模型冻结sample index 0至3，8次为0至7。比较仅使用完成双anchor配额的同9道题，避免把缺失32B题混入分母。

| 策略 | 同9题合格数 | 合格题ID | 保存tokens |
|---|---:|---|---:|
| 8B，每题4次 | 1 | 584 | 237,931 |
| 8B，每题8次 | 2 | 584、1053 | 449,135 |
| 双anchor，每模型4次 | 1 | 584 | 516,264 |
| 双anchor，每模型8次 | 2 | 584、1053 | 982,254 |
| 32B，每题8次 | 0 | 无 | 533,119 |

8B完整16题的4次/8次结果也为1/2题，tokens分别445,136/862,373。8B全128条实测作业2,373秒（约0.66 GPU小时）。32B已保存77条的request时间合计26,026秒（32B并发1）；不能把8B并发8的request时间求和作为GPU小时。

目前32B在完整9题中的新增资格为0，但这是小规模、部分pilot的观察，不能外推为所有题均无增益。4→8在此样本翻倍了合格数，也近似翻倍tokens，尚未证明哪个策略的eligible/GPU-hour更高。

## 建议顺序

1. **保护数据、落实磁盘空间。** 本地校验备份已完成。A800共享/data目前只剩约4.6GB；本项目总量约700MB、cache约22MB，清理项目缓存不足以补到10GiB阈值。应落实有余量的持久目录或由有权限的使用者释放空间；不删除其他项目或权重，不把RAM临时盘当唯一数据存储。
2. **限定补完当前pilot。** 保持原16题、双anchor、每模型8次、参数和逐槽seed，只补剩余51条32B；不重复已保存响应。以已保存32B平均约5.6分钟/条外推约4.8小时，加加载和审计，累计pilot约13小时；长尾使估计不稳定。建议pilot累计保护上限修订为16小时，全项目240小时保持不变。修订必须保存原冻结配置、修订理由及前后hash，不直接覆盖campaign_config绕过当前恢复一致性校验。
3. **整批审计后再作采集策略决策。** 比较同16题的4/8前缀、8B单独与双anchor、32B新增合格题、无效/截断、实测总GPU时间及剩余成本。按同一套严格资格定义分析；8B-only仅作诊断策略，不能当作已完成双anchor协议的数据直接混计。
4. **成本门控。** 若预计剩余成本在240小时余额内，才进入下一批；若超出，优先评估32B并发吞吐的小规模对照或明确修订采集方案，保留独立记录。不降低资格门槛，不因已投入8小时而自动扩大。

## 配置修订草案（未应用）

```json
{
  "scope": "finish_existing_pilot_only",
  "pilot_gpu_hours_cap_before": 8,
  "pilot_gpu_hours_cap_proposed": 16,
  "maximum_campaign_gpu_hours": 240,
  "frozen_questions": 16,
  "samples_per_anchor": 8,
  "remaining_qwen3_32b_slots": 51,
  "minimum_disk_free_gib": 10,
  "reuse_completed_responses": true,
  "automatic_interventions": false
}
```

实验矩阵仅修订累计时间上限：原pilot上限8小时已结束；补完方案上限16小时，题序、模型、seed、采样与评分保持固定。4/8次、单/双anchor比较均为已有响应的CPU前缀分析，不额外生成。尚未实施配置修订支持，当前直接重复原启动命令不能完成续跑。

只读状态检查可直接执行：

```powershell
python -X utf8 scripts/game24_100q_status.py
```

分析输出须保留完整16题分母与partial响应，不依据干预结果挑题；正式100题及development/held-out split仍未冻结。
