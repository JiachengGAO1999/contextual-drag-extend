**2026-09-19 active execution plan:** [ICLR 2027 submission sprint](quick_validation/iclr2027_submission_sprint_20260919.md). User adopted this as the working plan. Time-box Game24 acquisition through September 21; target 20–30 new strict questions, batchwise main evaluation, correct-draft control, then bounded second-task/model validation. Freeze primary results September 24. This supersedes the older requirement to acquire 30–50 questions before any evaluation; scientific eligibility is unchanged. Current Batch02 32B queue remains unchanged; other planned runs are not yet launched. Changes must be logged in the sprint plan.

**2026-09-19 current direction:** Whole-trace failed-context access control. Seven-question pilot is Stage-1 evidence, excluded from confirmatory primary sample. Formal target: 30 independent audited dual-anchor questions initially (maximum 50); strict >=2 completed parsable correct + >=2 substantive False. Batch02 full 32-question Qwen3-32B x16 (512) launched; no outcome-dependent selection, no intervention or next-batch auto-launch. 8B manual audit: 452 correct / 35 substantive / 7 format-only / 17 length / 1 completed unscored; 8 preliminary eligible questions. See [frozen plan](quick_validation/whole_trace_acquisition_plan_20260919.md). All status entries below are historical.

# 当前研究入口

**2026-09-18 Gate A：**七题×两paired seeds×R0/R2/whole-late/whole-path已完成56/56，全部EOS且可解析。R0/R2=12/14 vs 4/14；R3 whole-late=12/14；R4 whole-path=10/14。R3相对R2为+57.1pp，R4相对R3为−14.3pp；因此Go baseline acquisition，但不声称path优于late，也不新增局部mask。当前已冻结下一批32道未使用题×每题16条R0，共512次普通vLLM Qwen3-8B；排除全部development/intervention题和此前24题screen。队列脚本见`scripts/queue_baseline_acquisition_a100_20260918_batch02.sh`，结束后只做baseline eligibility audit，不自动跑intervention。

详见[Gate A decision](quick_validation/gate_a_decision_20260918.md)。

**2026-09-17 18:14：普通vLLM吞吐benchmark已启动。** 用户批准小规模测速并确认Qwen3-32B只读授权。GPU4先跑Qwen3-8B开发题2×16=32条，成功后自动接Qwen3-32B同32条；结束恢复selective常驻。Nemotron32B资源未落实，不下载、不替代。正式64题acquisition仍未授权启动。见[当前运行方案](quick_validation/ordinary_anchor_benchmark_20260917.md)。下方“禁止新生成”指此前审计阶段，已被这项限定benchmark授权更新。

**2026-09-17 协议审计完成，禁止新生成：**当前协议结论为partially aligned but materially different。三anchor合池2对2错已由论文与现存代码支持；公开脚本默认每模型每题16条；官方Game24数据/完整草稿未找到，TED缓存不能替代。现存聚合把None归错误池，1F脚本存在路径/glob缺口。已准备104道候选及阶段32/64/104的三anchor预算1536/3072/4992次，全部`generate:false`。32B模型资源和使用授权未落实，旧筛选队列已暂停。见[完整协议审计与生成前决策](quick_validation/protocol_parity_report_20260917.md)。

**2026-09-17 16:20 核查：**vLLM完整验收exit0，9/9 EOS、官方答案解析8/9，长输出约37.4 tokens/s；GPU4已vLLM常驻。新题32次筛选结束：30正确、1完整错误（1170/0，重复使用12）、1超长循环；仅1道mixed-success题，干预评测0条。已停在审计点。见[结果与方向判断](quick_validation/heldout_screen_results_20260917.md)。

**2026-09-17 baseline-only corpus audit：**补核服务器 `/data2/gaojc/projects/contextual-drag-extend` 后，将本地未同步的两份历史 R0 草稿池纳入审计；去重后共401条 baseline 样本、86道题。严格排除当前十题开发/标注集（1189、1358、804、123、577、719、1084、71、513、1226）及旧 prompt/mask/reuse 案例（170、159、1093），不使用任何 R2/R3/R4/late/path/X/CALC/X+CALC outcome。当前仅1170、1261满足“未复用、borderline、正确 companion + 人工确认 substantive failed trace”，远未达到下一轮12–15道独立题目标；不启动 intervention。完整 provenance 与机器可读结果见 [`baseline_corpus_audit.md`](../outputs/baseline-corpus-audit-20260917/baseline_corpus_audit.md)。

**2026-09-17 新题批次已授权并排队：**当前 vLLM 验收成功后自动开始8道独立新题×4次筛草稿，最多32次；随后等待 X 标注审计，评测额度最多6题×2 seeds×4条件=48次。不是自动跳过审阅的全流程。见[冻结方案与自动执行边界](quick_validation/heldout_queue_20260917.md)。

当前汇总入口：[2026-09-17 阶段报告与下一阶段建议](quick_validation/progress_report_20260917.md)。本次 GitHub 同步包含实现、标注、报告和汇总统计，不含 bulk outputs 或模型权重。

**2026-09-17：**HF 新 seeds 的 late/path 两批共 96 条已完成。X / X+CALC：late 为 15/24、12/24；path 为 16/24、16/24，尚不能认定 CALC 的稳定功能方向。当前按用户授权开发独立 vLLM 后端：full/late/path 短生成已跑通，优化版完整验收正在 GPU4 运行；尚未批准作为正式科研后端。见 [vLLM 验收记录](quick_validation/vllm_backend_20260917.md)。以下排队状态均为历史。

**2026-09-16补充：**用户授权额外48条配对path，已预检并安排在late成功结束后接棒；两批共96条新seed生成，自动产出四格汇总。path真实模型预检将在接棒后执行，当前不能称已通过。见[path方案](quick_validation/x_calc_path_plan_20260916.md)。

**2026-09-16 19:29 CST运行：**用户授权一轮最多48次，已启动六题×4新seeds的固定X vs X+CALC复查；仅seed变化。预计2–3小时，结束恢复GPU4常驻，不自动扩展。见[冻结方案](quick_validation/x_calc_replication_plan_20260916.md)及[96条输出候选出现审计](quick_validation/candidate_presence_audit_20260916.md)。下方状态为历史。

**2026-09-16最新：**X+CALC已完成24/24；同六题R2/X/CALC/X+CALC=10/18/8/14正确。相对X，3恢复/7损伤，-16.7pp，题目聚类CI[-41.7,8.3]。不足以认定CALC具有保护作用或确定交互方向。见[四格分析](quick_validation/x_calc_results_20260916.md)。结果已同步；未启动下一轮。下方运行状态为历史记录。

**2026-09-16最新分析：**六题CALC完成：8/24（33.3%）vs R2 10/24（41.7%），6恢复/8损伤。相同六题既有X为18/24。没有新实验运行。见[完整结果与行为分析](quick_validation/calculation_role_results_20260916.md)。下方启动记录为历史状态。

**2026-09-16 12:01最新运行：**形态筛查v2与draft_key审计完成；六份固定用数违规草稿，统一遮挡局部数值计算，新增24次L_CALC_v1 late生成，基线复用。见[修正说明](quick_validation/morphology_revision_20260916.md)、[运行与分析方案](quick_validation/calculation_role_plan_20260916.md)。不作形态间因果比较。下方“没有新实验运行”为此前状态。

**2026-09-16最新结果：**十题E干预完成，17/40（42.5%），R2为18/40（45%）；7恢复/8损伤，无净恢复。没有新实验运行。见[结果与方向评估](quick_validation/ten_validity_results_20260916.md)。以下启动记录为历史状态。

**2026-09-15最新决定与运行：**RQ扩展为“候选/构造与有效性评价分别如何影响下一次解题”，明确否定后重新认可保留为子类型，不再限制题集。十题×4seeds的L_E_v1与R2比较已完成：新增28条、复用12条；初步全体R2/L_E_v1为45.0%/42.5%，新增七题子集均为46.4%。见[当前运行方案](quick_validation/ten_validity_plan_20260915.md)、[十题结果](quick_validation/ten_validity_results_20260915.md)、[十题统一审计](quick_validation/ten_validity_audit_20260915.md)。下方9月14日两题入口为历史阶段。

更新：2026-09-14。**当前方向：受到否定的候选，在反复求值、修补和重新认可之后，如何影响下一次解题。** 用户已选择优先研究同一候选被明确否定后再次认可；1358为清晰案例，71为复杂案例。见[已确认入口与下一步](quick_validation/reendorsement_entry_20260914.md)。

先读[当前RQ定义](quick_validation/rq_revision_20260914.md)，再看[材料筛查与事件样例](quick_validation/rejection_materials_20260914.md)。旧研究方案保留原样作为历史设计，不能将其中待验证的贡献措辞当作当前结论。

## 已有证据

|阶段|规模与结论|报告|
|---|---|---|
|五条件基线|10题×4seeds；R0/R1/R2/R3/R4正确率70/37.5/45/72.5/77.5%|[五条件](quick_validation/five_condition_baseline_20260912.md)|
|单区间late|4题；答案/首次错误位置遮挡没有稳定恢复|[单区间](quick_validation/region_late_results_20260912.md)|
|多区间late|4题；M_X优于R2，认证扩展不单调|[多区间](quick_validation/multi_late_results_20260913.md)|
|十题局部late/path|M_X60%、P_X62.5%；均低于整段|[十题局部](quick_validation/ten_question_mx_late_path_results_20260913.md)|
|C2覆盖诊断|5题，C1/C2均60%，3恢复/3损伤|[C2](quick_validation/fixed_c2_results_20260914.md)|
|两题边际探针|719阻断U两背景均净损伤一次；1358一损伤、另一背景全失败|[边际](quick_validation/marginal_results_20260914.md)|

所有题均已进入开发/探索用途；不是新RQ的独立验证集。早期smoke、旧prompt和不同题集不合并到上表。详情见[完整历史讨论稿](quick_validation/discussion_brief_20260913.md)及根目录MASTER_EXPERIMENT_LOG.md。

## 资料层级

1. **固定输入**：`quick_validation/multi_region_annotations_20260912.json`保存十份草稿、draft_key及旧表达式证据；它不是新事件标签。
2. **旧区域与请求**：`fixed_coverage_annotations_v1_20260913.json`、`fixed_coverage_preflight_20260913.json`及各运行bundles。保留原版本，不按新RQ修改。
3. **后续生成输出**：仓库`outputs/`各运行下的`seed-*/results.jsonl`；完整Thinking和final均保留。汇总应识别复用来源，不能将重复复制记录计为新生成。
4. **语义审查历史**：[增量片段审计](quick_validation/incremental_unit_audit_20260914.md)、[依赖归属决策](quick_validation/dependency_decisions_20260914.md)。其中primary候选是旧组件问题的范围，不能直接继承成新RQ的primary题集。
5. **新事件材料**：[筛查结果](quick_validation/rejection_materials_20260914.md)及其JSON；用于挑选可定义的问题，不自动生成mask。

## 实现入口

- `selective_context/schema.py`：请求、mask区间与固定基本片段。
- `selective_context/masks.py`：late、legacy per-span path、fixed-unit path。
- `selective_context/hf_backend.py`：完整prefill、缓存decode与固定采样。
- `selective_context/multi_region.py`：字符证据到token映射；不把非相邻区间取大外包络。
- `selective_context/phase0/`：各历史运行器，不能混用其条件定义。

上一批筛选：32次限额采样于2026-09-15 00:37:47 CST结束；30正确、1完整错误、1截断，按当时狭义RQ合格草稿0。见[筛选结果](quick_validation/reendorsement_screen_results_20260915.md)。随后用户批准扩大RQ并使用十题：当前运行L_E_v1，见本页顶部。两题事件标注仍作为子类型资料保留。本页不是实时监控。
