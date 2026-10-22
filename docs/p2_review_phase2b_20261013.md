# P2 Phase 2B Memo — Reproducibility and Confound Audit

2026-10-13。**决策：CONDITIONAL。** 保留“逐题差异可能存在”的观察，但现有记录还不能证明 R3/R4 差异稳定、可预测，或超过匹配执行条件下的波动。只值得讨论一次有退出条件的可靠性门控，不足以进入机制干预或论文主线。此次仅 CPU 审查，新增模型请求、GPU 生成均为 0；完成后暂停。

## 1. 审查范围与判定口径

复用已定位资产，读取 **702 条**原始输出：主23题184条、UFT20题160条、HF Stage A三题六种子72条、HF Stage B七题四种子112条、两个早期 HF 批次30条，以及 identity/alias 144条。未重遍 Phase 1 的3,889条。四个科学批组分别保留 **46、40、18、28** 个完整 R3/R4 配对，不跨后端合并。

每个配对核对同题、同种子、相同 prompt/input-ID 哈希、draft span 和 token cap，保留原始评分、最终式、生成长度与 finish reason。成功率以原评分的 `correctness is True` 为准，截断/未提取成功仍留在分母；这不表示文本中绝无正确式。统计单位为题，种子不是独立题。见[完整索引](../outputs/p2-audit-phase2b-20261013/record_index.json)、[所有配对](../outputs/p2-audit-phase2b-20261013/paired_effects.json)及[原文件哈希](../outputs/p2-audit-phase2b-20261013/asset_manifest.json)。

## 2. 同输入重复：存在运行差异，但不能移植成 R3/R4 噪声基线

在上述范围中，严格匹配输入与已记录设置的跨批、同种子对照只有 **16对／8题**：四个数字互异时，identity 与 value-alias 的 CLEAN/HISTORY 提示实际上完全相同。其余早期同题同种子记录存在提示或草稿差异，不能算精确重跑。

| 项目 | identity / alias 实际记录 | 主23题 / UFT20 R3/R4 |
|---|---|---|
| 模型与精度 | 本地 Qwen3-8B，BF16 | 同模型路径，BF16 |
| 执行路径 | native vLLM0.11.0 / FLASH_ATTN | selective vLLM0.11.0 / FlexAttention，per_request decode |
| 采样 | temperature .6，top-p .95，top-k20 | 相同采样参数 |
| 种子 | engine 与每请求均20261011 | engine2027；主组请求927001/927002，UFT929001/929002 |
| 调度与缓存 | max_num_seqs8，动态补位；prefix cache开；chunked prefill开；batched tokens8192 | batch8；prefix cache关；chunked prefill开；batched tokens32768 |
| 输出预算 | 每请求8192 | 32768减各自完整prompt长度 |

**16/16 token序列不同**，共同前缀为6–2,610 tokens；**5/16最终正确性翻转**，其中4对涉及一端EOS、另一端length。两端均EOS的8对仍有1次翻转，但这是按运行结果条件化的描述。对这32条输出用同一精确算术/数字清点口径重新评分，32/32与保存的任务正确性一致；另保留符号格式合规字段，排除了当前评分口径变化制造这5次翻转的解释。[配对原始行号](../outputs/p2-audit-phase2b-20261013/same_input_cross_run.json)、[统一复评分](../outputs/p2-audit-phase2b-20261013/repeat_uniform_rescore.json)。

这不是“温度非零，所以同seed必然不同”的论证。同seed约束随机抽样初始化，但没有固定批伴随请求、每步调度、浮点运算和缓存状态；两批请求总数96/48、补位顺序和缓存热度不同。BF16/核函数数值差异、调度/缓存效应、随机流消耗差异都是竞争解释，记录不足以分配责任。native 的5/16 **不能**作为 selective Flex 的噪声率，亦未发现可直接证明这两批误配模型或采样参数的证据。

实际日志的首个engine配置匹配；均使用FlashAttention，并记录FlashInfer缺失后使用PyTorch top-p/top-k。日志后半出现seed2027、prefix cache关闭，是 `diagnostic_process_exited` **之后恢复空闲常驻**，不是实验中途换配置。精确边界：identity runner.log第182/183行，alias第111/112行；摘录见[运行日志证据](../outputs/p2-audit-phase2b-20261013/execution_log_evidence.json)。

版本证据有边界：HF配置保存torch2.8.0+cu128、transformers4.55.4与git HEAD，但同时标明工作区修改；native日志确认vLLM0.11.0，却缺少逐次权重/tokenizer内容哈希、实际执行源码哈希、完整依赖/driver/GPU标识及RNG/logits/调度快照。归档 `identity_handoff.zip` 与当前脚本有差异：run函数差异仅停止标记和dtype元数据，评分函数也有变化；归档不能当实际执行版本证明。[逐项代码比较](../outputs/p2-audit-phase2b-20261013/archive_code_comparison.json)。

另外确有历史配置风险：Batch02记录修复了physical-padding guard、禁止mask cudagraph capture并改为逐请求fsync；Batch03称复用该快照，最早7题/UFT则先于此修复。因此相同backend名称不能证明完全相同历史worker。另一个[Batch03 acquisition恢复审计](quick_validation/batch03_interrupted_audit_20260924.md)记录过缺失子样本从seed42重新编号的恢复bug；它涉及多输出筛题恢复，不能据此判定本轮保存的单请求R3/R4种子错配，本轮配对未见这种证据。

## 3. R3/R4改变的计算范围

令prompt长为n，整个草稿区间为D=[d,e)。本轮132个配对均使用whole draft，没有selected subspan或额外path units。

| query与状态 | R3 whole late_block | R4 whole path_block |
|---|---|---|
| prefill中q<e | 普通因果attention | 普通因果attention |
| suffix prefill，e≤q<n | 能读草稿KV | 不能直接读草稿KV |
| generated query，q≥n | 不能直接读草稿KV | 不能直接读草稿KV |
| suffix自身的状态与KV | 在完整草稿可见时形成 | 在草稿被阻断时形成，suffix表示及后续层KV可不同 |
| 其他历史KV | 保留prefix、suffix和已生成KV | 同样保留，但其数值可沿不同轨迹发展 |

两者都保留草稿token、位置、物理KV及草稿内部计算，没有物理删除或回写。decode直接边规则相同，不代表进入decode的缓存状态相同。特别是**第一个输出token由最后一个prompt query n−1预测**：R3仍使用完整prefill，R4可改变该分布；第一个generated query n预测的是第二个输出token。保存的首token相同不能证明logits相同。

因此，虽可用不同onset表描述边界，实际比较同时改变了suffix编码、首步预测及后续轨迹，不能简化为“同一个prefill状态下，把同一种decode mask提早开启”。也不能把R3剩余表现直接叫作suffix中的某种语义传播：prefix及生成历史仍可被读取，语义内容没有在此测量。

代码位置：[onset表](../selective_context/vllm_mask.py#L16)、[逻辑mask](../selective_context/masks.py#L10)、[物理/逻辑映射guard](../selective_context/safe_flex_mask.py#L2)、[worker映射](../selective_context/vllm_worker.py#L88)、[per_request decode](../selective_context/vllm_worker.py#L46)、[HF prefill与首步logits](../selective_context/hf_backend.py#L103)。当前代码的132份metadata边界断言与已有6个CPU mask测试通过；这验证静态契约，不追溯证明历史GPU激活正确。[逐配对mask范围](../outputs/p2-audit-phase2b-20261013/mask_contract.json)。

## 4. 效应与波动

“改善/损害”均指R4相对R3的正确性变化，未丢弃截断。

| 批组 | 题×种子＝配对数 | R3正确 | R4正确 | 改善 / 损害 | 净差pp | 两端EOS配对：改善/损害 |
|---|---:|---:|---:|---:|---:|---:|
| 主23题 | 23×2＝46 | 36/46 | 35/46 | 6 / 7 | −2.17 | 43对：4/6 |
| UFT20 | 20×2＝40 | 34/40 | 40/40 | 6 / 0 | +15.00 | 37对：3/0 |
| HF Stage A | 3×6＝18 | 10/18 | 11/18 | 2 / 1 | +5.56 | 18对：2/1 |
| HF Stage B | 7×4＝28 | 22/28 | 22/28 | 6 / 6 | 0.00 | 26对：5/5 |

主组R4−R3题级bootstrap95%区间为[−19.57,+13.04]pp，UFT为[+5,+27.5]pp（本轮固定5000重采样）。这些区间不包含历史执行不确定性、选题偏差或事后选择；三题HF的区间尤其不宜作总体证据。两端EOS是受处理影响的完成子集，只作敏感性描述。

不同种子的同条件正确性不一致：主组R3为**6/23题**、R4为**5/23题**，对照R3/R4的**13/46配对翻转**；规模接近，配对结构不同，不能做简单相减或正式噪声校正。UFT为R3 **4/20题**、R4 **0/20题**。HF多种子的所有种子对：Stage A为18/45、15/45；Stage B为12/42、16/42，同题种子对相互依赖。[完整同条件种子比较](../outputs/p2-audit-phase2b-20261013/within_condition_seed_variation.json)。

有方向线索，也有反例：主组1057两个种子均R3对/R4错（均EOS），但215和509各自出现相反方向翻转；UFT792两个种子均R3错/R4对（均EOS），412贡献另一次EOS改善；147、529、856的另三次改善均涉及R3截断。HF719四种子中三次改善、一次无差，577两次损害、两次无差，123出现一好一坏。全部种子结果和**精确原始行号**见[逐题表](../outputs/p2-audit-phase2b-20261013/per_question.json)，不能只摘同向见证。

回答“有多少超过同条件运行波动”：**目前无法确认任何一组已超过匹配执行条件的同seed重跑波动**，因为selective Flex没有这样的严格重复基线；这不等于差异全是噪声。跨种子同向的少量题仅支持保留待检验的异质性，尚无未参与选题的预测确认。

## 5. 题池混杂与可检验线索

| 属性 | 主23题 | UFT20 |
|---|---|---|
| 选题 | anchor有正确与实质失败；22题满足最终严格门槛，41为早期例外 | 625 fresh IDs随机20题，不按R0/干预结果筛选 |
| 草稿来源 | 16条Qwen3-8B Thinking、7条Qwen3-32B最终回答正文 | Qwen2.5-Math-7B公开处理后的三步/最终路径 |
| 草稿tokens：中位数[范围] | 406 [311,1380] | 77.5 [71,85] |
| 草稿字符：中位数[范围] | 1283 [1057,3171] | 108 [100,113] |
| 最终旧式错误 | 20仅数字清点、2仅算值、1仅scalar24 | 14仅算值、5算值与清点均错、1仅清点 |
| R0能力代理 | 40/46；17题2/2、6题1/2正确 | 36/40；18题2/2、2题0/2正确 |
| R2正确 | 18/46 | 39/40 |
| R3/R4 length | 2/46、1/46 | 3/40、0/40 |

“仅数字清点”表示式值为24、操作数多重集不合法；“仅算值”表示清点合法、式值不为24。scalar24未强行归入完整表达式错误。草稿长度完全不重叠，来源、错误类型、筛题规则也联动。UFT源CSV没有EOS/finish/token计数，不能证明处理前自然输出完整；主组Batch03来自中断32题中的22题完整前缀、8题合格，可能偏向较快完成题。主组与UFT请求种子也不同。跨题池均值不能单独归因于草稿长度或错误类型。[题池数据](../outputs/p2-audit-phase2b-20261013/pool_confounds.json)、[草稿来源](../outputs/p2-audit-phase2b-20261013/main_draft_sources.json)、[UFT冻结规则](../outputs/game24-uft-external-20q-20260919-prepared/protocol.json)、[Batch03中断边界](quick_validation/batch03_interrupted_audit_20260924.md)。

现有记录允许提出但不能确认条件交互：UFT里R0两次均错的792/412贡献3/4个配对改善，均EOS；其余18题的3/36个改善全涉及R3截断。主组R0仅1/2正确的6题反而净损害4/12，其余17题净改善3/34。R0只有两次抽样，且此分层为事后观察，不能称独立测得能力，更不能选取有利一侧作预测。错误类型也缺少共同支持：主组仅2道算值错题，UFT仅1道清点错题。

UFT−主组的R4/R3效应差为+17.17pp，独立题池描述性bootstrap95%区间[−1.52,+37.72]pp；不构成已确认题池交互，更不识别原因。[分层完整配对](../outputs/p2-audit-phase2b-20261013/descriptive_strata.json)、[跨池描述](../outputs/p2-audit-phase2b-20261013/cross_pool_description.json)。

## 6. 决策与最小下一步（仅建议，未编写或启动）

**CONDITIONAL的条件是先验证可重复性，再要求可预测性。** 当前至少有三类竞争解释：①普通采样与执行日程/数值波动；②题池选择、原题难度与截断机会；③R4额外改变suffix prefill与首步预测，产生真实但未细分的计算效应。现有数据不能排除前两类，也不能在第三类内部定位原因。

如果共同评估后继续，最小门控应在**原selective Flex路径**上冻结权重/tokenizer、代码、依赖与硬件标识、输入token、cap及batch/cache设置，用一个预先固定的小面板同时包含有利、不利和无差题。每个题/种子做R3的重复R3、R4的重复R4，再用独立种子测正常采样波动；同seed重跑与换seed是两个不同基线。至少两个独立种子、每个条件/种子至少两次执行是可估计门控的最低结构，不是足以确认微小效应的功效承诺。固定相同batch伴随与请求顺序，另作预定换序复核，记录逐步调度、首次分歧logits/随机状态、完整finish与原文；先排除分数/停止逻辑差异，再比较条件间效应与条件内波动。

若差异不能在该门控中稳定重现，应STOP P2；若只复现事后挑出的题，只能KEEP描述性个例，不能升级为机制方向。形成值得投入的现象还需要一个事前条件预测在未参与挑选的题上成立。若主张长度/错误类型交互，必须在同题上匹配或交叉这些因素并独立测量R0能力，不能靠两个现有题池均值。若主张suffix计算原因，R3/R4本身也不足以拆分suffix状态与首步分布；本轮不开发对应干预。

创新性边界：证明“mask导致输出不同”或重新讲述单个翻转没有足够价值。只有获得超出执行/采样波动、跨新题可预测、并能排除上述竞争解释的规律，才值得再讨论计算机制。当前未达到KEEP，也没有证据支持把所有差异都判为无现象而STOP。

## 7. 复核入口与结束状态

CPU复算：`python -X utf8 scripts/audit_p2_phase2b_20261013.py`。它只解析已有文件、精确算术、描述性重采样及metadata边界，不加载模型。产物目录为 `outputs/p2-audit-phase2b-20261013/`；`record_index.json` 的 `source` / `line` 是1起始物理行号，`raw_line_sha256` 为去掉行终止符后的UTF-8行哈希，`asset_manifest.json`保留整文件哈希。

当前代码契约检查使用已有 `tests/selective_context/test_masks.py`：6 passed；验证结果与本轮脚本/产物哈希见[verification.json](../outputs/p2-audit-phase2b-20261013/verification.json)。这些不是历史运行的确定性证明。P1维持用户确认的DEPRIORITIZE，651见证保留。**本阶段已完成并暂停，等待共同评估；未准备新GPU请求或自动继续实验。**
