# -*- coding: utf-8 -*-
"""Generate reviewable acquisition reports and freeze a bounded fresh pilot."""
import json
import math
import random
from pathlib import Path
from game24_100q_audit import OUT, SOURCE, dump, sha

def main():
    summary = json.loads((OUT/'audit_summary.json').read_text(encoding='utf-8'))
    stats = json.loads((OUT/'sampling_efficiency.json').read_text(encoding='utf-8'))
    questions = [json.loads(line) for line in (OUT/'game24_question_manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    fresh = [dict(id=q['tot_rank'], numbers=q['numbers']) for q in questions
             if not q['historical_development'] and not q['all_trajectory_ids']]
    fresh.sort(key=lambda q: int(q['id']))
    random.Random(20261014).shuffle(fresh)
    manifest = dict(version=1, state='frozen_before_generation', protocol='adapted_dual_anchor_fixed8',
        source_revision='8050e67d0e3a0fddc424d7fa5801538722a4c4cc', source_sha256=sha(SOURCE.read_bytes()),
        order_seed=20261014, seed=20261014, candidate_count=16, samples_per_problem=8,
        total_generations=256, max_pilot_gpu_hours=8,
        sampling_parameters=dict(temperature=.6, top_p=.95, top_k=20, context_length=32768),
        anchor_models=['Qwen3_8B_Thinking','Qwen3_32B'], target_model='Qwen3_8B_Thinking',
        exclusion='all prior baseline questions and local/server development materials by input multiset',
        eligibility='>=2 completed parseable mathematically correct and >=2 completed parseable substantive errors; no intervention results used',
        quota='exactly8 per anchor per question; interrupted unfinished slots resume; completed invalid outputs are not regenerated',
        expansion='none automatic; audit pilot and compare measured remaining cost with an explicit total resource budget',
        failure_conditions=['foreign GPU4 process','disk free <10 GiB','cumulative pilot GPU hours >=8',
                            'source/config mismatch','generation failure'],
        candidate_rows=fresh[:16])
    mp = OUT/'pilot_manifest.json'
    if not mp.exists():
        dump(mp, manifest)
        dump(OUT/'fresh_question_order.json', dict(order_seed=20261014, source_sha256=manifest['source_sha256'],
                                                candidates=fresh, frozen_before_new_generation=True))
    else:
        manifest = json.loads(mp.read_text(encoding='utf-8'))
    batch04 = next(x for x in stats['batches'] if 'batch04' in x['batch'])
    remaining = 100-summary['admitted_independent_questions']
    rate = batch04['eligible_all']/batch04['questions']
    raw_needed = math.ceil(remaining/rate)
    estimated_hours = raw_needed*batch04['measured_job_hours']/batch04['questions']
    costs = dict(remaining_eligible=remaining, observed_batch04_yield=rate,
        scenario_candidate_questions=raw_needed, scenario_generations=raw_needed*16,
        scenario_job_gpu_hours=estimated_hours,
        scenario_generated_tokens=round(raw_needed*batch04['tokens']/batch04['questions']),
        pilot_scenario_job_hours=16*batch04['measured_job_hours']/batch04['questions'],
        scope='scenario using Batch04 full-job cost including loads; not a calibrated forecast or approved budget',
        changed_32b_batching='max_num_seqs1 instead of historical16; speed effect unmeasured until pilot')
    dump(OUT/'cost_scenarios.json', costs)
    lines = ['| 数据批次 | 独立题数 | 完整保存响应 | 严格合格题（含历史题） | 生成 GPU h | 含加载 GPU h |',
             '|---|---:|---:|---:|---:|---:|']
    for b in stats['batches']:
        if b['generation_gpu_hours'] is None: continue
        lines.append(f"| {b['batch']} | {b['questions']} | {b['records']} | {b['eligible_all']} | {b['generation_gpu_hours']:.3f} | {b['measured_job_hours']:.3f} |")
    table='\n'.join(lines)
    prefixes=['| 批次 / 完整题数 | 每 anchor 4次 | 8次 | 12次 | 16次 |', '|---|---:|---:|---:|---:|']
    for batch in ['batch02_dual_anchor','game24-batch03-dual-anchor-20260924','game24-batch04-dual-anchor-screen-20260925']:
        rows=[r for r in stats['prefix_replay'] if r['batch']==batch]
        prefixes.append('| '+batch+' / '+str(rows[0]['complete_questions'])+' | '+' | '.join(str(r['eligible']) if r['complete_questions'] else '未采样' for r in rows)+' |')
    prefix_table='\n'.join(prefixes)
    (OUT/'DATA_ACQUISITION_AUDIT.md').write_text(f'''# Game24 数据采集审计（2026-10-14）

本轮为数据建设任务。已核实本地未提交状态、服务器最新 baseline、模型路径、磁盘与 GPU 进程；没有覆盖原 ICLR 数据、manifest 或结果。服务器快照为 `outputs/game24-100q-20261014/baseline_snapshot.zip`，443份文件逐一按服务器 SHA256 核验，保留完整原始文本和 token IDs。GitHub 远端不能代替该快照。

## 当前可用题数

原题源有1362个互不重复的数字多重集。逐条去重后 baseline 为 **{summary['baseline_records']} 条 / {summary['baseline_questions']} 题**；其中 {summary['reusable_records']} 条具有本研究 ordinary-vLLM 双 Qwen anchor 的采样参数与上下文配置。
原代码兼容合格 **{summary['protocol_compatible_questions']} 题**，严格实质错误合格 **{summary['strict_questions_all']} 题**（包含历史开发）；剔除历史开发/实验材料、要求至少完成同一批双 anchor prefix8 后，新池当前 **{summary['admitted_independent_questions']} 题：{', '.join(summary['admitted_ids'])}**。这是已核验快照下的成果，不是证明剩余宇宙最多只有2题。

合格题候选写在 `game24_eligible_candidates.jsonl`；`game24_eligible_100.jsonl` 当前为空且 split 为 `not_frozen_target_not_met`，不得称为已完成100题或已冻结验证集。全部正确/错误见证和原始文件行号可从 trajectory ID 回查。

开发材料隔离是保守的：包括已经使用的题和预先准备但未必执行的材料。对每题分别保存实际干预证据和历史材料证据；无本地干预证据不能等同于证明从未使用。服务器额外183个多重集的 manifest 盘点与本地记录合并；排除范围共 {summary['historical_material_questions']} 题。未按干预正确率、drag 或 recovery 大小选择题。

## 原论文与公开代码

核对[原论文v2 §2.1、附录A.2–A.3](https://arxiv.org/html/2602.04288v2)、[官方 initial_sampling.sh](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/initial_sampling.sh)与[聚合实现](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/aggregate_data.py)。论文要求同题跨anchor合池至少2对2错，允许 self/cross-model。公开脚本默认每模型16次，不等于已恢复作者全部运行配置。

| 项目 | 官方规则/实现 | 本次处理 |
|---|---|---|
| 题号 | 原论文缓存ID与ToT Rank不同 | canonical ID采用 `tot-rank:<Rank>`；跨源按排序数字多重集join，不能直接按同号join |
| Anchor | Qwen3-8B、Qwen3-32B、Nemotron-32B | 双Qwen适配；没有新下载Nemotron；不称exact reproduction |
| 采样 | Qwen .6/.95/top-k20，32768上下文；默认16 | 历史16及8全部保存；新pilot固定8；max generation为32768减prompt tokens |
| Prompt | qwen_math_prompt；原始problem字段未公开 | 现有R0模板+规范化Game24题文，实际chat prompt完整保存 |
| False / None | 聚合 `if correctness ... else ...` 把None也归入错误 | compatible重放 falsey；严格视图逐条数学复核，None本身不当实质错误 |
| 完成性 | stop + parsable_thinking | 保存原stop/eos映射、length、malformed、空final；截断不入门槛 |
| Thinking | 检查prompt+response的标签数，再取结束标签后的final | 原始thinking全文保留；未闭合thinking不得因存在式子补判合格 |
| 实质错误 | 原代码无人工审计硬门槛 | 最终选式用Fraction和AST核验用数/值；标量24和混合候选读完整final，不用未选择的正确备选救错式 |
| Source / target | self和cross均允许 | 每条记录标注 source model、target Qwen3-8B及self/cross |
| 后端 | 原文vLLM0.10.2 | 历史ordinary vLLM0.11；新异步默认worker，不加载selective backend；调度不同不保证逐token重现 |

官方聚合的False/None及格式误判差异意味着 compatible 37题不能直接替代 strict 32题。本次compatible-only五题为6、41、289、445、753，无strict-only题；不能把这5题的差异全部归因于None。严格结果允许明确认可且精确验证的正文正确式修复提取漏检，同时保留原官方标签；该适配改变了人群，已分别报告。只看到错误公式并不足以判定thinking全过程都错误，错误分类针对最终回答。

## 合法复用与缺失

- Batch02：8B与32B分属不同物理目录，按同题合并为一个logical batch；共1024条。原32B分块及8B全批参数兼容，但已用的开发题不进入新池。
- Batch03：保存864/1024条，8B512条、32B352条；22题双anchor完整、10题只有8B。缺失的160个32B配额不能视作已完成；满足2对2错但单anchor覆盖的5题122、200、764、1019、1171仍不是双anchor完整的新池成员。
- Batch04：服务器实际已完成512条；合并副本和chunk副本按生成身份去重。472原始True、35原始False、5原始None；9条截断。严格分类为472正确、30实质错误、1提取漏检正确、9截断。5题合格：50、353、643、1073、1119；50/353/1073已属于后续材料，当前只纳入643/1119。
- 早期HF或non-thinking：完整原文保留，但不能补ordinary-vLLM Thinking配额。原论文TED公式缓存缺原始轨迹/Thinking/prompt并经过后续输出过滤，不进入新独立数据池。
- 本轮新复核25条歧义final，全部绑定原记录SHA256。其余明确最终boxed公式由可靠程序检验；历史Batch03标量/混合最终式使用已冻结逐条决定，并重新检验。当前待审为 {summary['pending_responses']} 条，仍单列保守排除的歧义失败。

## 真实成本与前缀复盘

{table}

{prefix_table}

Batch03的8是22个双anchor完整题中的资格数，不是32题全部完整；另外5个partial合格只报告，不混入完整分母。早期2/6/7/7已被后续q122/q381最终选式复核纠正，当前重放2/7/8/8。
Batch02与Batch03在n8相对n16均漏1/8（12.5%）最终合格题；n12→16新增为0。独立题前缀token总量、每anchor单独资格、另一anchor加入的边际贡献在 `sampling_efficiency.json`。**prefix GPU-hours为null**：并发chunk wall time不能按记录重复相加或按token比例包装成实测前缀耗时。各prefix额外GPU耗时和 marginal eligible/GPU-hour没有足够日志可识别。

全批可测比较：Batch02 n16为8/19.170≈0.417 eligible/GPU-hour；Batch04 n8为5/10.683≈0.468。批次题目与调度不同，因此只能支持固定8作为成本审计pilot，不能证明8是最优。32B Batch04首chunk耗时约3.40h（含加载），存在明显长尾；新runner固定max_num_seqs1避免假定多序列长上下文能高效共存，改动效果必须由pilot实测。

## 复算

`python -X utf8 scripts/game24_100q_audit.py`

新增生成 {summary['new_generations_this_task']}；新增GPU hours {summary['new_gpu_hours_this_task']:.3f}。历史采样成本不算作本轮新GPU开销。计时为用户作业占用单卡的wall时间，不是整台共享服务器GPU能耗测量；未保存的Batch03在途tokens/时间不在完成chunk汇总中。
''', encoding='utf-8')
    ids=', '.join(q['id'] for q in manifest['candidate_rows'])
    (OUT/'GAME24_100Q_ACQUISITION_REPORT.md').write_text(f'''# Game24 100题采集报告（2026-10-14）

**状态：A100_GPU4_SHARED / A800_ALLOCATION_PENDING；当前独立合格2/100；本轮新增生成0。** 已完成服务器数据同步、统一资格审计、实质错误复核、成本重放和可续跑pilot实现，尚未采集新题。不得把准备完成称为100题验收通过。

## 固定pilot与工程实现

已冻结16道新题，每模型8条，双Qwen顺序执行，共256次，累计上限8 GPU-hours（含加载和恢复尝试），seed/order seed20261014。候选：{ids}。全部排除既有baseline和本地/服务器开发材料，完整余下固定题序保存在 `fresh_question_order.json`。当前尚有 {summary['fresh_questions_available']} 道无这些暴露记录的原题；不是题目宇宙耗尽。

采样 .6/.95/top-k20，Thinking开，context32768；每条seed=base_seed+sample_index，每请求n1以避免恢复时重标seed。8B最多8个并发请求，32B最多1个；模型在两个独立子进程顺序加载。先完成32B少量完整响应，实时记录其耗时/长度，之后仍受同一pilot上限约束。后端只用ordinary-vLLM，保留原selective服务供后续使用。

完成一条就fsync，15秒机器可读heartbeat；SIGINT/SIGTERM或预算停止只终止本作业请求，保存已完成响应与在途partial诊断。幂等恢复按model/question/index核对，配置/题源不一致拒绝续跑；完成的length/None不重复抽样。尾部半行先归档才修复，内部损坏拒绝自动处理；磁盘<10GiB停止且不删除数据。进程组超时只针对本次anchor；全程共用已有项目launcher锁。

只有GPU4全部compute进程都是本项目且resident经tmux确认idle时，才可释放该服务并运行，结束后恢复。发现其他用户进程即拒绝，连本项目resident也保持不动。不得换用其他卡或下载checkpoint。

## 当前阻塞

2026-10-14北京时间17:35检查：A100全部8卡有compute进程；GPU4同时有本项目EngineCore PID3451842和其他用户hezq PID2190663。其他用户进程使用约17–19GiB，该卡不能独占做32B完整采样。/data2空闲已从较早的114GB降至约60GB；真实可用空间必须在开跑时重检。

用户要求补查A800后，确认GPU0/2/4/6无compute进程，约79.3GiB显存可用；GPU1占有18GB显存但进程归属无法核实，不能当空卡；3/5/7有人使用。A800 `/data` 约13GB可用，根盘仅1.9GB。

A800现有 `/data/gaojc/shared/models/Qwen3-8B` 的5/5分片（16,381,516,776 bytes）、`/data/share/hjl/zhaoyi/models/Qwen3-32B` 的17/17分片（65,524,328,560 bytes）均可读且无缺片。现有env `vllm-budget-018` 实际vLLM0.10.2/torch2.8.0，`vllm-budget-clean`为0.19.1/torch2.10.0；不需搬运或下载权重。**A800存在硬件与模型可行路线；尚未占卡，需确定可用窗口与总GPU预算。** 原采集入口当前固定A100路径，迁移还需隔离部署依赖并冻结A800模型路径/后端版本，不能直接原命令启动A800。

A100 CPU运行验证已通过：vLLM0.11.0、5/5和17/17完整分片、两模型pilot最大prompt72tokens。没有初始化推理引擎、加载模型权重、forward或新生成。

## 成本情景（不是已批准预算）

Batch04实测5/32合格、512次、3,438,749 tokens、生成10.310h、含加载10.683h。按照该全批产率/成本，补齐剩余{remaining}题约需 **{raw_needed}候选题 / {raw_needed*16}生成 / {estimated_hours:.1f} GPU-hours**，约{costs['scenario_generated_tokens']:,}生成tokens；审核时间另计。按单卡持续占用约{estimated_hours/24:.1f}天，实际共享卡日历时长更长。该估计没有把已用的3道Batch04题算作新增。

16题pilot按同一历史成本约{costs['pilot_scenario_job_hours']:.2f}h，上限8h。32B改并发可能改善长尾，也可能降低吞吐，尚未测得。不能从Batch03 prefix8 token数反推出实测GPU-hours；不声称当前资源已经能在预算内完成100题。

pilot完成后：先审计256条，再用真实全批GPU-hours/eligible更新成本；若0题合格、不完整配额、错误标签不可靠或成本超出可用额度，停在检查点。下一批建议沿冻结题序32题、固定8次，不临时针对某题补到错误；需先明确整个100题项目可用的GPU时间额度。未启动1362×3×16或adaptive补样。

## 命令与进度入口

本地零GPU验证：`python -X utf8 scripts/game24_100q_collect.py`

服务器CPU/tokenizer验证：`/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/game24_100q_collect.py --validate-runtime`

独占GPU4可用后：`/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/game24_100q_collect.py --run-pilot`

断点恢复使用同一命令、manifest和output；进度在 `outputs/game24-100q-20261014/acquisition/pilot/<anchor>/status.json`，控制台日志为各anchor console.log；全pilot状态为其父目录status.json。默认命令只验证，绝不自动生成。

审计/资产：`game24_question_manifest.jsonl`覆盖1362题，`game24_trajectory_pool.jsonl`逐条索引完整原文、prompt及source path/line/hash；完整原始文本与token IDs位于独立snapshot，避免重复复制大文本。`game24_eligible_candidates.jsonl`保留两题及各2对2错见证；冻结100题文件和split当前明确未完成。

GO：已完成的数据审计与可执行pilot准备。**NO-GO：在共享GPU4上启动采样、未经总资源额度自动扩大到数百GPU-hours、冻结不满100题或进入机制探索。** 此为资源和数据阶段判断，不是否定Contextual Drag效应。
''', encoding='utf-8')
    (OUT/'INITIAL_EXPLORATION_REPORT.md').write_text('''# 初步探索状态（2026-10-14）

**NOT_STARTED：100题未完成、eligible dataset未冻结，development/held-out split未建立。** 本轮R0/R2/R3新生成数为0，因此无新准确率、恢复案例或bootstrap区间；旧论文87.0/39.1/78.3不能代替新数据复现。

待满足数据门槛后的预定分析：固定seed20261014划分20题development和至少80题held-out。development每题2paired seeds×R0/R2/R3，共120次；资源不足可先完成固定前10题的60次后审计。R2/R3必须复用同一failed draft、文本、位置、prefill和首token，R3从第2token起阻断draft直接KV读取；用实际元数据/首token校验该实现条件。

按全部development题统计R0−R2、R3−R2，恢复与损伤分别报告；每题先平均两个seed，5000次question-level bootstrap，保留finish reason、长度、截断率。不根据drag或R3恢复删题；held-out不参与调参。

RQ2优先在固定题目已有多草稿上做CPU描述；新增draft比较需事前冻结少量组合。RQ3来源/长度/最终错误类型/clean能力/基线错误频率先作探索性关联，不能当内部机制。当前2题不能支持稳定异质性；不运行X/CALC、局部mask或Gate0未通过的代理评分。
''', encoding='utf-8')
    (OUT/'NEXT_RESEARCH_DECISION.md').write_text(f'''# 下一步研究决策（2026-10-14）

**CONDITIONAL GO：只在GPU4具备独占条件时执行已冻结256-generation、≤8 GPU-hour pilot。**
**NO-GO：立即全量扩容、未经确定可用窗口占用A800、下载模型或提前开始机制探索。** 新数据效应尚无证据，关于继续机制研究的判断为HOLD，不能从缺少新数据推断R3无效。新资源检查发现A800的0/2/4/6空闲且双Qwen权重齐全，可在确定窗口后迁移单卡pilot，不需额外下载或同时使用多卡。

真实成果：3538条baseline审计、32道strict合格旧题，其中当前仅2道满足新池隔离与完整双anchor配额。新的256次采样尚未执行。可用题源未耗尽；主要阻塞是共享GPU4与尚未明确的长程资源额度。历史成本情景约{estimated_hours:.1f}GPU-hours补齐98道，不能默认为获准连续占卡约{estimated_hours/24:.1f}天。

最有决策价值的下一步问题：
1. 固定8次广覆盖在新题pilot的实际实质错误产率/完整性与GPU成本是否支持100题预算？若不支持，停止扩容并保留所有成果，不能降低2对2错或放入格式错误。
2. 数据冻结后，全体development是否同时显示drag和R3恢复？若不明显，报告损伤/恢复异质性与不确定性，再讨论后续投资，不能只选择恢复题。
3. 错误来源/用数错误/长度是否具有跨题稳定关联，并能提出区别竞争解释的新预测？仅有相关性或少数案例时，不投入大规模机制工程。

若pilot通过且总额度足够，沿冻结余下题序分批采集，每批报告实际成本和剩余预测；100题冻结前不消费新干预结果。若总预算不足，可报告已取得的合格题和估计，或另行讨论模型/材料适配；替代方案不在本轮自动执行。
''', encoding='utf-8')
    dump(OUT/'progress.json', dict(state='awaiting_a800_allocation_or_exclusive_a100_gpu4', phase='pilot_preflight',
        completed_baseline_audit=True, admitted_eligible_questions=summary['admitted_independent_questions'],
        goal_questions=100, new_generations=summary['new_generations_this_task'],
        new_gpu_hours=summary['new_gpu_hours_this_task'], pilot_planned_generations=256,
        freeze_complete=False, exploration_started=False, automatic_expansion=False))
    print(json.dumps(dict(pilot_ids=[r['id'] for r in manifest['candidate_rows']], cost_scenario=costs)))

if __name__=='__main__': main()
