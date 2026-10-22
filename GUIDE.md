# Contextual Drag 扩展研究入口

2026-10-22机制探索条件评估已做CPU描述，新增模型请求0：实际选中草稿99/102为算值24但用数非法，完整合格池同类错误291/299；R0/R2/R3最终式中的该类错误为63/129/71（各204次）。主效应确认加强，但旧特异性、来源转移及短读出问题仍未解决。后续围绕数值计算与用数约束的关系区分竞争解释，不自动启动旧head/窗口或评分矩阵。[分析备忘及复算入口](docs/game24_100q_8b/MECHANISM_READINESS_20261022.md)。

**2026-10-22最新核实：全部102题复验完成，612/612条齐全。** 82题确认于北京时间今日06:37结束，实际63.35小时；R0/R2/R3为104/55/95（各164次），恢复+24.39个百分点，题目bootstrap95%区间[+13.41,+35.37]。全102题为131/68/119（各204次），恢复+25.00个百分点[+14.71,+35.29]。保留全部截断/None；599完成文件及423冻结绑定hash通过，原文CPU复算一致，全部204对不变量通过；未自动启动扩展。[完整结果和原始证据](docs/game24_100q_8b/FULL_REPLICATION_RESULTS_20261022.md)。以下为历史执行记录。

## 当前执行：补齐82题，覆盖全部102题（2026-10-19）

用户明确要求全题集复验。已冻结剩余82题×2 seeds×R0/R2/R3＝492次新生成，保留既有20题120次，合计102题612次。2026-10-19 15:18北京时间A800 GPU4已通过16个固定旧请求前4-token一致性检查及4个短请求，主实验首批运行，保存0/492；tmux `game24-8b-heldout82-1019`。120旧请求token化一致、3707软件文件hash及30项CPU检查通过。按上一轮实测外推新增约63.13 GPU小时，单独设置96小时保护上限。运行目录移至用户系统盘并保留项目符号链接；不搬运权重、不停止其他任务。方案、启动修复记录、真实路径与查询命令见[全题集复验](docs/game24_100q_8b/FULL_REPLICATION_PLAN_20261019.md)。以下为20题复验及采集历史。

**2026-10-19最新核实：开发集R0/R2/R3复验已完成120/120。** 北京时间10月18日02:16结束，实际15.40小时。R0/R2/R3为67.5%/32.5%/60.0%；恢复+27.5个百分点，题目bootstrap95%区间[+10.0,+47.5]，15个配对恢复、4个损伤。1条截断无法判分保留分母；82题held-out未生成，无自动扩展。117个文件SHA256通过，原始结果CPU复算一致，40对不变量通过。[完整复验结果](docs/game24_100q_8b/REPLICATION_RESULTS_20261019.md)。下方启动记录为历史。

## 当前执行：新数据上的R0/R2/R3复验（2026-10-17）

用户要求重跑旧方法并预备扩展。已冻结20题development×2 paired seeds×3条件，共120次科学生成；82题held-out保留。使用A100 GPU4与经146项hash核验的旧论文vLLM0.11快照，tmux `game24-8b-dev-replication-1017`。已通过64个旧请求token化一致性检查；运行包含4个短工程探针。结果尚未完成，不能将旧准确率当新结论。方案、成本、状态查询和扩展边界见[复验入口](docs/game24_100q_8b/REPLICATION_PLAN_20261017.md)。以下是数据采集历史。

## 当前任务：Game24 100题，单Qwen3-8B anchor（2026-10-15）

**数据准备已于2026-10-17 01:26:50北京时间完成：102道合格题，20 development / 82 held-out已冻结。** 完整筛选720题、5760条回答，GPU已释放；全程累计39.05 GPU小时（含此前双anchor阶段），新8B续采31.04小时。已同步254文件完整快照并逐文件核验SHA256；102题的816条资格响应重新复核通过，21项CPU检查通过。[完成报告与数据入口](docs/game24_100q_8b/GAME24_100Q_ACQUISITION_REPORT.md)。机制探索尚未运行，下方为采集历史。

**最新执行（2026-10-16 22:38北京时间）：用户授权清理四处pip HTTP缓存后，采集已恢复。** 数据盘释放18.23GiB（剩19.85GiB）、系统盘释放8.92GiB（剩9.07GiB）；保留wheels/环境/模型/研究数据。原配置和源文件hash检查通过，原GPU4/tmux从第20批缺失13条继续。复核已保存完整cohort后候选89/100，继续至目标。详见[清理记录](docs/game24_100q_8b/DISK_USAGE_AUDIT_20261016.md)。下方原启动和pilot数字为历史。

用户已明确要求暂时只用8B。新协议/数据目录为[docs/game24_100q_8b](docs/game24_100q_8b/README.md)，原双anchor资产保持独立。
每题固定8次，至少2正确+2完整实质错误；复用已完成16题/128条8B回答，正式候选2/100（584、1053）。旧643/1119依赖32B错误，不能计入。
后续每批32题×8，按pilot合格率和含失败的实测8B成本，剩余点估计约32.7 GPU小时；此前全作业8.0048小时仍计入总上限240小时。
**2026-10-15 09:57北京时间已启动持续采集**：A800 GPU4，tmux `game24-100q-8b-a800`；首批32题×8=256响应，完成后自动审计并继续至100道合格题或资源/成本停止条件。
10GiB原为保守工程门槛；按实测16题全部原始输出6.16MB、预计新增约302MB，将8B任务空间余量修订为2GiB，旧配置归档。当前约4.5GiB，运行中每15秒监测并逐条fsync。21项CPU检查通过。
默认状态命令：`python -X utf8 scripts/game24_100q_status.py`；旧任务查询加`--protocol dual`。
启动：A800项目根目录运行`bash scripts/start_game24_8b_a800.sh`，程序先检查磁盘/GPU和冻结配置。
达到100题后先冻结20/rest split并停止采集；不自动启动机制实验。

## 原双anchor任务记录（2026-10-14至15，已停止）

**最新状态（2026-10-15 09:35北京时间核实）：pilot已在02:42达到8小时上限后停止，GPU4已释放。**
已保存205/256条（8B 128/128，32B 77/128），剩余51条32B响应。
9道题完成双anchor配额，初步严格检查新增候选584、1053；整批尚未审计，正式冻结未发生。
累计作业8.005 GPU小时；当前/data仅余约4.6GB，低于10GiB启动阈值，尚未续跑。
205条响应及配置/账目已完成本地SHA256校验备份；
[下一步决策](docs/game24_100q/PILOT_NEXT_STEP_20261015.md)记录同9题4/8次与anchor边际比较、磁盘条件及补完pilot建议（预算修订尚未应用）。
此前采集使用A800 GPU4的tmux `game24-100q-a800`，独立目录
`/data/gaojc/projects/contextual-drag-extend-game24-100q`。
16题pilot→审计/成本门控→每批32题→至少100题后冻结；全采集有限保护上限240GPU小时。
vLLM0.10.2、官方grader依赖已验证；无模型下载/搬运，无新机制实验。
首次启动因PATH中缺ninja失败，30.01秒已计入预算；修复后18:42:46北京时间恢复。
目前已有真实完整生成落盘（首8条EOS/parseable，随后出现待严格复核的scorer False）；
pilot未完成双anchor配额，不能提前增加正式合格题计数。13项CPU测试通过。
实时刷新：`python -X utf8 scripts/game24_100q_status.py`；完成批次原文同步：
`python -X utf8 scripts/game24_100q_status.py --sync-data`。
详情见[执行记录](docs/game24_100q/A800_EXECUTION_20261014.md)，下述旧等待窗口状态已被本次授权覆盖。

本次用户明确授权数据审计、必要baseline采样与完成100题后的有限探索；以下旧阶段暂停记录只作历史。
已同步服务器baseline快照并审计3538条/206题：37题原代码兼容、32题strict合格，
剔除历史材料且要求完整双anchor配额后当前可纳入新池2题（643、1119）。
100题未达成、development/held-out未冻结，新增生成/GPU hours均0；不进入机制探索。
报告及全部manifest：[数据审计](docs/game24_100q/DATA_ACQUISITION_AUDIT.md)、
[采集报告](docs/game24_100q/GAME24_100Q_ACQUISITION_REPORT.md)、
[研究决策](docs/game24_100q/NEXT_RESEARCH_DECISION.md)。
复算：`python -X utf8 scripts/game24_100q_audit.py`；默认零GPU验证：
`python -X utf8 scripts/game24_100q_collect.py`；11项语义/溯源/恢复测试通过。
已冻结16道新题×双anchor×8次的pilot，256次、累计≤8 GPU-hours；不自动扩大。
A100 CPU运行验证通过，但GPU4有其他用户进程。用户要求补查A800：
2026-10-14 17:35北京时间，GPU0/2/4/6空闲，完整8B/32B权重和vLLM0.10.2环境可读。
尚未占用A800；需确定可用窗口与100题总GPU额度，迁移还需冻结该机器路径/后端。
全部新资产在`docs/game24_100q/`和`outputs/game24-100q-20261014/`，原ICLR数据未修改。

## 当前研究路线

2026-10-13当前用户任务：[Causal Specificity Evidence Audit Memo](docs/causal_specificity_evidence_audit_20261013.md)。
仅CPU复核24题72条FULL/CANDIDATE/CONTROL及主23题/UFT20的86对R2/R3。
确认9/17/16正确；前者是同文本value贡献减法，**不是文本删除或attention mask**。
CANDIDATE−CONTROL为4改善/3损害，+4.17pp [−16.67,+25.00]；CONTROL−FULL为8改善/1损害。
非草稿方向也有收益，但可携带草稿间接影响，不能识别一般扰动机制或证明等效。
建议**STOP据此候选投入新same-text实验**，尚未确立论文方向。
产物`outputs/causal-specificity-audit-20261013/`；CPU复算
`python -X utf8 scripts/audit_causal_specificity_20261013.py`。
新增模型请求/forward为0，旧结果未改。**完成后暂停等待共同评估。**
以下均为历史阶段记录，不覆盖本次任务和授权边界。

2026-10-13 最新用户任务：[Error-Feedback Credit Assignment：Gate 0 Memo](docs/credit_assignment_gate0_memo_20261013.md)。
暂定问题是同题修正中局部反馈是否沿历史记录者边界外溢；来源抑制仅为竞争假说。
已冻结并精确验证32道双分支算术/短程序题、三种反馈、共享/分离来源及标签交换规则；
192个预留模板只编译，实际仅执行shared/local一格的32对Clean/history，另8次正确历史校准。
72次短生成与48个B读出条件完整保存，HF Qwen3-8B BF16/eager含加载519.19秒。
**Gate 0未通过，HOLD不进入Gate 1**：Clean联合9/32、12/32截断，history联合2/32；
虽然配对净Y损伤7/32且B直接读出信号可测，能力与地板门槛失败，不能据此声称来源机制。
完整原始输入/输出、192次辅助forward的96个候选分数和后端快照在
`outputs/credit-assignment-gate0-20261013/`；CPU复核
`python scripts/audit_credit_assignment_gate0_20261013.py`，状态入口
`python scripts/gate0_credit_assignment_20261013.py --status`。
**完成后暂停等待研究讨论**；正式2×3、Gate 1、新机制干预及Selective vLLM实验均未启动。
HF runner已退出，原项目空闲resident已恢复（tmux `gate0-credit-1013`）；其他GPU任务未停止。
以下Phase 2B及旧路线均为此前阶段记录，不覆盖本次用户给定的竞争问题与授权边界。

2026-10-13最新用户任务：[Phase 2B：P2 Reproducibility and Confound Audit](docs/p2_review_phase2b_20261013.md)。
仅CPU复核702条既有输出、132个R3/R4完整配对及16个identity/alias同输入跨批配对。
决策**CONDITIONAL**：保留逐题异质性线索；现有数据不能判定效应超过匹配执行波动，
native跨批波动不能作为selective Flex噪声基线。R4还改变suffix prefill及首步预测，
两题池的长度、错误类型、来源、筛选和截断混杂。产物
`outputs/p2-audit-phase2b-20261013/`；复算
`python -X utf8 scripts/audit_p2_phase2b_20261013.py`。新增模型调用/GPU生成0。
**完成后暂停等待共同评估**；最小可靠性门控仅为建议，未编写或启动新实验。
用户已确认P1的DEPRIORITIZE，保留651见证，当前不继续投入P1实验。

2026-10-13此前阶段：[Phase 2A：P1精细复核](docs/p1_review_phase2a_20261013.md)。
仅CPU复核38条已定位支持/反例，20条主要支持轨迹涉及17个不同数字多重集。
决策**DEPRIORITIZE P1作为机制主线**：多数失败与普通误验相容；保留651这一
准确诊断旧式超用12、思考末指定合法式、最终又输出旧式并误验的明确行为见证。
它不等于已隔离的selection failure。完整原文、注释和token解码复核位于
`outputs/p1-review-phase2a-20261013/`。新增模型调用/GPU生成0。
**完成后暂停等待共同评估**；不启动P2重复、不开发attention/KV干预或下一阶段。

2026-10-13最新用户任务：[Anomaly-Driven Mechanism Discovery — Phase 1 Evidence Audit](docs/evidence_audit_phase1_20261013.md)。
本轮为独立证据审计，旧机制假说只作背景。已在CPU索引3,889条既有输出，
保留3个待共同评估的候选现象，保存完整配对、输入哈希和42份支持/反例复核包。
产物`outputs/evidence-audit-phase1-20261013/`；复算入口
`python -X utf8 scripts/evidence_audit_phase1_20261013.py`，没有新增模型调用/GPU生成。
**完成后暂停等待共同评估**；不自动启动机制干预、扩题或选择论文方向。
以下Goal 1/2/3及路线锚点为此前研究背景，不作为本轮现象分类或后续执行授权。

2026-10-13[Goal 3：Research Idea Selection Memo](docs/idea_selection_goal3_20261013.md)
已完成 CPU 资产审查和最新相关工作核对，新增模型请求/GPU用时为0。
主方向是**失败反馈如何调节可迁移的求解规则**；备选是编码与读取的失效绑定。
这是投资建议与待检验假说，没有 work 的机制 MVP，不自动启动实验。
文献核对发现 Evidence Integration、AlgoTrace、Hindsight Editing 等直接重合：
“知道错却仍用”、算法向量注入或“旧KV不能回写”本身均不足以成为新贡献。
先投资有退出条件的第一周决定性比较，只有新增机制预测获支持才继续3–6周；
若仅是已有方法的新应用则退出。见[文献边界](docs/idea_selection_literature_20261013.md)。
CPU例子在 `outputs/idea-selection-20261013/material_example.json`，未提交GPU排队，
Goal 1的96题和Goal 2的36题确认集保持未使用。

2026-10-13[Goal 2：具有行为效度的低成本探针](docs/validated_probe_goal2_20261013.md)
已按门控提前结束，**STOP当前代理开发**，见[效度报告](docs/validated_probe_goal2_results_20261013.md)。
复用20题80条自然轨迹，先盲态标注前2048 tokens，再比较同轨迹最终AST复用。
按题等权balanced accuracy为83.3%[71.9%,93.1%]，但precision为60.0%，
未过80%门槛；完整双条件配对只有12题，未过14题门槛。7条早期认可的假阳性
最终全部给出合法新答案，因此不能把“认可旧式”当作“最终采用旧路线”。
新增forward/GPU用时为0。模板/成本新生成、36题独立确认和内部干预均未启动；
96道Goal 1确认题不动。产物`outputs/validated-probe-20261013/`，状态见
`run_state.json`，复算`python -X utf8 scripts/analyse_validated_probe_20261013.py`。
后续接受有限真实生成作为行为终点，早期立场只作辅助；不再自动调窗口、候选
或评分模板，也不自动启动Late Invalidation。两轮停止均未检验该机制假说。

2026-10-12用户设立[Goal 1：Late Invalidation机制可行性](docs/late_invalidation_goal1_20261012.md)，
这是此前已按STOP结束的阶段：单Qwen3-8B、单A100、短评分，依次通过测量效度、PRE/POST
独立确认、必要的局部状态移植、GO/PIVOT/STOP。30旧题只作校准；新128题固定
32发现/96确认，并排除source-binding的64题。Gate 0最多一次预定测量修正；
没有诊断性差异不开发/运行Gate 2，不自动扩展source-binding或其他机制方向。
冻结材料与结果位于`outputs/late-invalidation-20261012/`。
状态：`python scripts/run_late_invalidation_20261012.py --status`。

**Goal 1阶段决策：STOP当前短评分协议。**
[结果与证据边界](docs/late_invalidation_goal1_results_20261012.md)：Gate 0及唯一
一次预定读出修正共744次forward、47.25秒（含加载）均已完成。历史损失为正，
但两题组的CLEAN正确候选偏好均低于60%门槛，因此测量未被验证；96道确认
题评分为0，PRE/POST及KV移植未启动。Late Invalidation假说仍未受检验，
不能把本轮停止理解成总体机制被否定。原始输入与分数已下载，结束时已恢复
GPU4本项目空闲常驻（tmux `late-invalidation-1012`），无实验自动继续。

2026-10-12已准备[来源绑定有限否证批次](docs/source_binding_probe_20261012.md)：
取得独立公开教师首错标注1,002条、612题，固定种子选64独立题，准备
三条件192次短批改及两个参考符号对照4次。用户已授权后续按每批合理耗时安排，
不再以原24小时上限作为启动门槛；历史用时记录保留。本批预计30–60分钟，
采用GPU4单A100与原生vLLM；运行阶段以输出目录的`run_state.json`为准。
强来源核对提示是既有基线，不作为方法创新。

结束快照（非实时状态）：196/196批改已完成，含加载742.25秒。没有扩展
source-binding分支；随后串行运行Goal 1。远端`sjtu-a100` / `rtx-node131`，
当前状态以远端`run_state.json`为准；原`source-binding-1012`会话已退出。

启动：`bash scripts/start_feedback_source_binding_probe_20261012.sh`。
进度：`python scripts/run_feedback_source_binding_probe_20261012.py --status`。
结果：`outputs/generation-diagnostics-20261005/public_verification_preview/source_binding_probe/`。
查看远端：`ssh sjtu-a100`，进入`/data2/gaojc/projects/contextual-drag-extend`后执行进度入口；
实时日志：`tmux attach -t source-binding-1012`（Ctrl-B再D退出查看，任务继续运行）。

2026-10-12后续CPU审查：公开AIME的参考解仅覆盖12题、114历史轮次。
已保存四题五条“把参考解内容归给待批改回答”的具体反馈，含一个首轮例子，
故不能全部解释为旧反馈惯性。候选转向批评者的来源绑定错误；错误批评、
步骤对齐与参考解压制已有工作，不称已确认创新。准备了只改参考解辅助符号
的两个示例，尚未运行模型对照或证明下游损伤。详见
[公开轨迹审查后续](docs/public_feedback_friction_review_20261012.md#后续-cpu-进展参考解内容被归给待批改回答)。
共享24小时预算未增加，没有新增GPU请求。

2026-10-12新增[公开修订轨迹审查](docs/public_feedback_friction_review_20261012.md)：
取得另一篇Feedback Friction的Maverick公开快照，137题、1,338去重轮次，
仅本地CPU分析。AIME四题六条记录正文已得到正确所求数值却输出不同答案；
八边形题经穷举独立核实。推理与最终答案分离、错误反馈及评价偏置已有研究，
暂不称新机制或MVP，不启动小样本GPU矩阵；原论文完整轨迹不再作为前提。

2026-10-12新增[代数等价与资源合法性审核](docs/algebra_resource_preview_20261012.md)：
48题材料池中44道旧式数值为24，仅6道有严格形式恒等的合法四牌式；
全部为重复数值题。旧推理确有将10/10算作一个10等错误清点，但尚
无代数正规化机制证据，不启动小样本GPU实验或重启身份表示调参。

2026-10-12新增[反馈方向的文献取舍](docs/feedback_novelty_triage_20261012.md)：
反馈过度泛化、采样规则影响推断、语言反馈信息量均有相邻工作。
不把SQL作用域反例直接升级为新主线，不启动小矩阵；仅保留
报告规则与历史处理收益交互的待评估问题，尚无模型证据或新颖性结论。
随后CPU精确核对发现四角色材料没有预想的单次最优修复收益反转，
首错记录直接改标抽查还会引入选择偏差；该材料不进入GPU实验。

**2026-10-12最新结束结果：**[反馈方向解码报告](docs/feedback_decoding_results_20261012.md)。
共享24小时上限已触发，保存73/80请求，7份预算缺失不补跑；原始输出
与评分已下载。BAD真实反馈11题7→4正确，0恢复、3损伤，固定幅度MVP
未获支持；即使缺失取最好值，冻结12题的真实反馈收益也无法转正。
runner与launcher均已退出，当前没有本项目模型实验；GPU4仍被其他
用户任务占用，常驻恢复推迟。当前没有确认的新机制或稳定方法MVP。
下面的启动状态和剩余预算均为历史快照，不能作为继续运行的授权。

2026-10-12新增CPU候选：[失败反馈的信息充分性](docs/feedback_evidence_sufficiency_20261012.md)。
首错停止与独立抽查可返回同一句错误，却允许不同的事实推断；已在
四角色环境穷举核对信息等价摘要与有损摘要。只有三个逻辑类别，
不是模型结果或执行题单。记录了Feedback That Backfires、CORE及
前缀保留工作的重合；不将抽象失败消息或冲突缓存本身当新方法。
未创建新GPU请求，原共享24小时预算不变。

真实SQLite内存执行随后否定了通用的“报错前文字均已验证”推断；
局部名称不可见也不代表全局不存在。这些是检查器行为，尚非模型
机制证据。详见同页更新，停止把文字前缀认证推进为通用方法。
新增SQLite脚本与结果目前仅在本地。用户已确认无法取得原论文跨
模型逐题完整输出，后续不依赖获取这些轨迹；解析器构造反例不能
用于估计原论文实际结果错误率。

2026-10-12 CPU进展：[错误类型材料预览](docs/error_profile_feasibility_20261012.md)
在原30题中仅5题满足严格匹配，20式精确审核通过；没有新增模型请求。
它不是执行题单或新机制证据，不据此启动小样本GPU矩阵。
同页有局部构造的可延伸性审核：76个资源合法子树中18个仍可补成24、
58个不可；不等于模型行为机制，也不作为另一次GPU启动理由。
[原论文v2核对](docs/original_v2_review_20261012.md)补充复用指令消融及
GRPO已有结果的边界，后续创新判断不再仅参考v1。
同页记录公开verdict解析器的三个构造反例：它不保证读取最后明确
判定。已核对上游一致，尚未量化原论文实际受影响比例，不当作机制贡献。
[公开定位资料](docs/public_localization_data_review_20261012.md)检查找到
Thought-ICS的完整初始链缓存入口；已预览40题，缺少定位后结果。
其回退与历史保留已有实现，不能换名当作新方法；未提交复现实验。

2026-10-12：[反馈方向解码MVP](docs/feedback_decoding_20261012.md)已完成CPU
准备与两项tiny-Qwen3数值检查，80请求冻结：原顺序前12题的错误历史，
其中8题另有正确历史；真实/反向反馈×普通/放大解码，8192-token上限。
不将已有ID/CFG公式称为创新，检验反馈方向能否控制自然推理及历史
利用。复用共享24小时预算；实际启动状态查
`scripts/run_feedback_decoding_20261012.py --status`及远端进程。
启动时已核实launcher PID887884、runner PID887928及首批解码推进；现均退出。
tmux `game24-feedback-decoding-20261012`，结果目录`feedback_decoding/`。
下文“没有新批次”为此方案之前的历史状态。

最新：[附加计算对象切换完整结果](docs/subject_gated_verification_results_20261011.md)
576/576完成并同步。首要历史×对象交互0pp，95%区间[−20.83,+20.83]，
两个预设题组方向相反；停止该机制分支，不追加小矩阵。共享预算累计
20.16/24 GPU小时，余3.84小时；本项目常驻已恢复，没有新GPU批次。

[自然识错语义复核](docs/recognition_semantics_review_20261011.md)截至10月12日
已确认20条具体违规正例：15正常结束均答对，5截断；至少4条先出现合法式
再出现所标识错片段。正例筛选不能估计总体恢复率或识错的因果效应，
但要求重新检验“准确诊断后仍撤销失败”的前提。当前没有创新机制
或稳定方法MVP。CPU重算：`python scripts/audit_failure_recognition_20261011.py`。
审阅23条旧式复用输出的关键词窗口，并完整阅读五条无窗口轨迹，合计
21条、15题明确错报旧式次数；只有1条共享子构造边界案例，不据此
启动局部新实验。进一步读取六模型
TED缓存发现转换可能改变公式，已完成[CPU复核](docs/ted_conversion_review_20261012.md)。
停止从转换后缓存反推原始失败类型或具体诊断；这项测量发现不代替
创新机制或方法MVP。预算未增加，仍未提交新GPU批次。
下面的启动状态及预算数为历史记录，以本段和原始运行记录为准。

2026-10-11 [目标×资源反事实完整结果](docs/constraint_coupling_results_20261011.md)：
480/480完成并同步，首要历史×目标交互−2.08pp，区间跨零，两组反向。
停止目标耦合命题，不启动目标值反平衡。辅助次数单独检查：有历史
漏检13/48→1/48，无历史3/48→0/48；该收益与CoVe重合，不称创新机制。
共享预算累计19.76/24 GPU小时。下一项候选应区分同对象附加计算与
一般任务负担，而非再比较单问和多问；尚未据本段自动启动新实验。

[创新判断与停止清单](docs/novelty_decision_20261011.md)汇总已停止命题、
与CoVe/WhatCounts等工作的重合，以及当前辅助收益不能自动成为MVP的原因。

2026-10-11 [任务目的对照完整结果](docs/decision_verification_results_20261011.md)：
384/384完成、原始输出同步；整体判断的历史×采用交互−2.08个百分点，
题目bootstrap区间[−22.92,+18.75]，两组方向不一致，分项检查无稳定收益。
停止“采用要求额外扭曲检查”命题，不宣称新机制。累计19.52/24 GPU小时。
已准备并完成文献边界核对的下一项是
[独立约束交叉影响](docs/constraint_coupling_20261011.md)：同一公式只改
数值目标，读取次数判断，48题×10条件=480请求，最多估计3.20 GPU小时。
本批已提交GPU4、已核实runner PID170725与模型加载，tmux
`game24-constraint-coupling-20261011`；停止的仅为本项目已确认空闲常驻。
状态入口`scripts/run_constraint_coupling_20261011.py --status`，结果目录
`outputs/generation-diagnostics-20261005/constraint_coupling/`。

2026-10-11 [检查规则迁移结果](docs/check_rule_transfer_results_20261011.md)：
360/360均完成且全部分项判断正确，六条件各60/60，无截断。该协议不
支持约束类别迁移，停止这条合成矩阵；全对不等于总体无效。下一项
[固定原候选的任务目的对照](docs/decision_conditioned_verification_20261011.md)
已在CPU准备，全部48既有自然失败题×8条件=384请求，未新增筛题。
比较只审查/审查并选择及整体/分项检查，首要指标预先固定。尚无创新
机制或MVP结论。共享预算完成该批时为19.16/24 GPU小时，余4.84小时。
新384请求批次已启动GPU4、已核实进程及模型加载，tmux
`game24-decision-verification-20261011`；状态入口
`scripts/run_decision_verification_20261011.py --status`，结果目录
`outputs/generation-diagnostics-20261005/decision_verification/`。

2026-10-11 用户指出上一轮固定候选结果仍主要是 Contextual Drag 现象延伸，
接受该判断：尚未发现创新机制或方法 MVP，继续探索原论文未解释的内容。
新检验见[检查规则迁移](docs/check_rule_transfer_20261011.md)：区分具体解绑定、
整体判断宽松和约束类别特异迁移。30题×2 seeds×6条件，共360次验证生成；
CPU反事实材料已审核，复用共享24 GPU小时预算，不自动扩展。当前状态请查
`scripts/run_check_rule_transfer_20261011.py --status`，结果目录
`outputs/generation-diagnostics-20261005/check_rule_transfer/`。

2026-10-11 [30题候选验收实验已完成](docs/failure_adoption_results_20261011.md)：
480/480输出及评分已同步。自然解题有历史COUNT25/60、身份28/60，复核
组均12/30，未建立稳定身份方法收益。相同合法/非法候选下，有历史
选对率COUNT48/60→29/60、身份49/60→25/60，预设两组方向一致；候选
任务无截断。所有有历史错选都同时错误认可旧式，未观察到正确判错
却选旧式。保留“验收与采用受历史影响”这条初步机制方向，不宣称
神经机制或方法MVP。GPU用时累计18.94/24小时，余5.06小时，常驻恢复，
未自动开新批次。下一步候选设计见报告，不继续调字母命名或搜heads。

2026-10-11 用户授权继续探索到初步正面信号，已准备并提交
[自然失败历史与候选采用实验](docs/failure_adoption_20261011.md)。复用30道
尚未做身份表示比较的同模型Thinking自然失败题，15发现/15复核；先
240次自然解题，再240次同候选检查与选择，预计全上限3.20 GPU小时。
tmux `game24-qwen3-8b-failure-adoption-20261011`；提交时GPU4有他人训练，
现有启动器等待可用，不停止他人任务，等待不计共享预算。
结果目录`outputs/generation-diagnostics-20261005/candidate_adoption/`。
上述为启动时快照，当前结果见首段完成报告；不把提供合法候选后的高分当创新。

等待期间完成[旧轨迹定向语义复核](docs/trajectory_semantic_review_20261011.md)：
7条记录（4题）的合法候选已被认可，但旧式也被错误地判为满足使用
次数；不能把这些案例直接当成“正确识错后仍无法撤销”的证据。

2026-10-11 新题验证已完成，见[完整结果](docs/identity_prospective_results_20261011.md)：
64初稿+508后续生成，本轮约78.47 GPU分钟。全体历史交互+0.79个百分点，
95%区间[-5.56,+7.14]，未建立独立身份超过强次数提醒的稳定优势。
初稿61正确、2错误、1缺失历史；正确历史组两种表示均120/122，失败
历史组COUNT0/4、IDENTITY2/4，收益集中于一道题，不能作为一般恢复率。
累计17.74/24 GPU小时，余6.26小时；常驻已恢复，未提交新实验。
全部原始结果已下载。下面保留本轮启动信息作为复查入口。

2026-10-11 用户确认继续，已执行
[新题验证与失败阶段诊断](docs/identity_next_design_20261011.md)：固定64新题
各写一次初稿、保留全部状态，再比较强次数提示与独立身份的有/无历史
表现。已合并排除225个已记录组合；29题含重复值。最多576请求，预计
3.3–4.3 GPU小时的启动前估算，实际78.47分钟；原24小时共享预算不变。
远端sjtu-a100、GPU4，tmux `game24-qwen3-8b-count-vs-identity-20261011`；
入口`scripts/run_identity_prospective_20261011.py --status`，结果
`outputs/generation-diagnostics-20261005/identity_prospective/`。
旧144轨迹的CPU事件提取也已保存，支持进一步区分合法候选出现与最终
选择失败；具体识错语义不由关键词自动判断。不自动开下一轮机制实验。

2026-10-11 夜间用户授权自主推进到可用idea MVP；最新安排见
[夜间命题检验与方法MVP](docs/overnight_mvp_20261011.md)。先完成正常
Thinking的64次CLEAN及64次CORRECT_ROOT，再评估资源身份绑定原型。
后者冻结为原24题×有/无历史×数字/独立卡片表示＝96次真实生成；
原共享24 GPU小时预算不变，实际是否启动与结果以远端状态为准。
一般依赖撤销已有直接先例；卡片表示有无历史的交互才用于检验
历史特异性，不把普通算题提升或表示变化当作神经机制结论。

自然Thinking依赖修订已完成：CLEAN64/64及CORRECT_ROOT64/64均六步
全正确、无截断；32基础参数组的这项协议不支持预期的后继旧值保留。
576项短数字偏好不再作该材料上撤销失败证据，停止这一诊断线。
96次vLLM资源身份MVP已完成并下载：无历史数字/身份均19/24；有历史
为11/24与14/24。历史交互+12.5个百分点，95%区间[-20.8,+45.8]，
只算弱探索信号。唯一的48次值别名对照也已完成：CLEAN16/24、
HISTORY9/24；独立身份相对别名的历史交互区间仍跨零。重复值16题中
有历史独立身份12/16、别名6/16，是候选线索，非独立确认。
相同提示跨批重跑也出现答案波动；不把单seed净差视为确定因果恢复。
本夜所有实验已结束，GPU4本项目常驻已恢复，未排新实验；共享累计
16.43/24 GPU小时、余7.57小时。先研究新材料上的可区分预测，不继续
在这24题调提示或搜头。结果已同步本地。
完整评估见[夜间结果与路线判断](docs/overnight_results_20261011.md)。

2026-10-11 最新：用户要求用例子解释并尽可能推进，当前执行
[明确纠正错误源后的依赖更新短检验](docs/dependency_revision_experiment_20261011.md)。
32组、两个依赖版本、三个条件，576个短评分；复用原预算与GPU4启动器。
这是一次有限否证，不运行旧384单元矩阵，不以材料或跑分本身当创新。
已于2026-10-11完成576/576评分，用时约2.60GPU分钟，结果已下载；
本项目常驻已恢复。数字读出的CLEAN基线较弱，不据此宣称机制。
同一次自然Thinking测量已落实为先运行CLEAN基线，详见上述当前实验。

首先阅读 [2026-10-10 用户确认的研究路线锚点](docs/research_anchor_20261010.md)。
工作命题是“错误识别与路线撤销的计算分离”；它是待检验假设。
后续工作以具有创新价值的解释和新预测为主线，避免围绕小 case
不断增加消融，或仅通过收缩 claim 累积一篇论文。
允许从探索结果中发现创新命题，并继续检验；不把命题写成既有事实。

2026-10-11 的[下一步战略判断](docs/next_direction_20261011.md)优先于
旧待启动批次：先评估撤销对象与依赖选择性这一候选方向的增量价值，
不默认补 R3 或启动已上传矩阵；来源分区实验的原授权保持不变。

## 文档与代码

- `docs/dependency_natural_experiment_20261011.md`：当前自然测量阶段的例子、
  设计和查看命令；`scripts/run_dependency_natural_20261011.py`为入口。

- `docs/dependency_revision_experiment_20261011.md`：当前短评分假设、例子、
  冻结比较、分析和查看命令；`scripts/run_dependency_revision_20261011.py`为入口。

- `docs/dependency_revocation_review_20261011.md`：最新命题审查、相关工作
  重合、同值异源的依赖材料和停止条件；CPU准备完成，新GPU方案尚未冻结。
- `scripts/prepare_dependency_revocation_20261011.py`：上述材料的CPU生成与审查入口。

- `docs/route_revocation_next_20261010.md`：已准备但经定位复核暂不启动的历史方案；
  晚屏蔽与受限状态重建对照；保留32题及384评分单元，不默认继续运行。
- `docs/route_revocation_execution_20261010.md`：本地已实现内容、CPU检查、
  自然轨迹审阅覆盖和启动前交接；已获授权完成服务器部署及CPU检查，新GPU批次未启动。
- `docs/route_revocation_positioning_20261010.md`：相邻工作方法及创新性边界。
- `docs/research_discussion_20261006.md`：实验历史、研究判断与阶段更新；
  文件日期不代表最新更新日期，历史状态需与最新记录区分。
- `docs/source_partition_results_20261011.md`：来源分区已完成46/46评分、
  23/23几何；主要比较未显示预期的生成前缀来源优势，最终结果已下载。
- `docs/mechanism_next_20261009.md`：来源分区历史方案与查看进度命令。
- `docs/cross_question_behavior_20261009.md`：24 题三条件自然生成及解释。
- `docs/new_plan_1010.md`：用户提出的战略诊断原文；研究共识见路线锚点。
- `selective_context/`：模型后端及干预实现。
- `scripts/`：实验准备、运行、排队和分析入口。
- `outputs/generation-diagnostics-20261005/`：冻结配置、原始结果和预算；
  `source_partition/` 为已完成的来源分区批次。
- `texts/`：论文材料。

## 执行边界

现阶段模型实验使用单 A100、Qwen3-8B Thinking BF16，不新增训练；
沿用本轮共享 24 GPU 小时预算。远端运行记录可能比本地快照更新，
汇报当前进度需实时查询；历史计划不自动授权扩题、扩模型或新一轮生成。
