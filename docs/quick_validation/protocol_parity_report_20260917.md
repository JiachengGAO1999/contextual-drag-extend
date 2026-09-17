# Contextual Drag Game24 Protocol Parity Report

日期：2026-09-17。范围：论文、固定官方源码、发布数据线索、本地/服务器历史baseline及模型文件。**零次新生成；不加载新模型；停在生成前决策点。**

## 结论

**partially aligned but materially different。** 当前任务家族、Qwen3 Thinking数值采样参数、上游scorer、Thinking剥离及先筛选后干预原则基本对齐；题目纳入、anchor来源、采样深度、错误标签解释、prompt和后端不同。不能称exact reproduction。

原方案不是无意误读：用户曾为quick validation明确接受单模型少量采样替代三anchor重建。现在进入正式研究，应把这一适配协议与论文协议分开，不能直接沿用quick筛选产率规划正式样本。

“仅1170/1261可用主要由protocol mismatch造成”**尚无法判定**。单模型每题4次减少观察机会，来源限制减少失败来源；但1对1错比原2对2错数量门槛低，不能整体称严格子集。最新32次仅1条完整False；只有补入同题其他anchor的baseline，才能测量多anchor增量，而不是预先承诺恢复协议会解决产率问题。

## 证据与版本

- [论文v2 §2.1、§A.1–A.3](https://arxiv.org/html/2602.04288v2)：原Game24总1362题、eligible653题；三anchor、至少2正确/2错误，允许self/cross-model草稿；去掉`<think>`部分。
- 官方远端HEAD核查为 `8614634d3625e7d965aa30df9f99a640f4533dac`。本地`data_generation/`、`utils/general_inference/`、`utils/verifiable_evaluation/`、`prompt_templates/`相对该提交无diff。
- [初始采样脚本](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/initial_sampling.sh)：默认16 samples/model/question、seed42；默认template=qwen_math_prompt，环境变量可覆盖。只能确认公开默认配置，不能声称拿到了作者所有实际launch记录。
- [聚合实现](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/aggregate_data.py)：model filter后统一按id分组；`num_trajs=T+F`，正确与错误池各至少num_trajs；`T=0,F=2`仍要求2对2错。
- [Game24启动参数](https://github.com/princeton-pli/Contextual-Drag/blob/8614634d3625e7d965aa30df9f99a640f4533dac/data_generation/2f_datagen/datagen.sh#L26)：Nemotron_32B/Qwen3_32B/Qwen3_8B，开启完成和Thinking解析过滤。
- 当前实现：`selective_context/phase0/thinking_pilot.py`、`heldout_drafts.py`；本次离线盘点：`scripts/protocol_parity_audit_20260917.py`。

## 逐项对照

|Item|原文/公开代码|当前实现|Match?|Action needed|
|---|---|---|---|---|
|Game24 source|论文1362题，筛后653；发布tree缺Game24原始dataset和构建代码|ToT commit8050e67…的24.csv，1362题|题目宇宙有强支持，字节版本未证实|保留来源与SHA；不得称原始dataset已恢复|
|预先难度筛选|公开协议用anchor成功/失败定义难度；未查到另一个显式预筛|固定随机题序，mixed-success|原则相近、操作不同|不加入主观“像是能恢复”的预筛|
|去重/题号|聚合按id，无数字multiset去重；原始预处理未知|以ToT Rank命名并按数字multiset去重|不完全|统一数字multiset为跨源join键|
|Anchor models|Nemotron32B、Qwen3-32B、Qwen3-8B|只有Qwen3-8B|否|完整或明确批准的anchor适配方案|
|Samples/model/problem|初始脚本默认16；缓存可见每模型最多16条保留baseline|4条|否|正式重建固定16，缺额记录，不自适应补到答错|
|Pool across models|先按model白名单过滤，再按题合并|单模型|否|同题三anchor合池|
|Correct threshold|至少2|至少1|否|固定2，不要求每个anchor各2|
|Incorrect threshold|论文至少2错误；现存代码按falsey归错误|至少1且`is False`|否|分别报告False/None，不混淆论文意图与代码行为|
|Completion filter|`finish_reason=='stop'`|`finish_reason=='eos'`|概念相近、停止token不同|记录EOS/stop token及length，显式归一化|
|Thinking parsing|必须`parsable_thinking`|相同，并要求非空final|部分|空final处理列为差异|
|Final parser artifacts|现存聚合未排除None；scorer异常/无box可返回None|None不作为failed draft|否|设置代码兼容与严格False两份审计视图，运行前选定primary|
|人工substantive错误|代码无这项硬过滤|排除纯格式/部分誊写错误，人工确认推理错误|否|若保留，单列机制子集，不能冒称原population|
|Draft model restriction|任一anchor，允许cross-model|self-generated|否|记录source/target/self-cross，不限定self|
|Draft内容|`init_response_final`，去掉Thinking；聚合还截前32768字符|上游Thinking剥离；完整final，无相同字符截断|部分|记录是否发生截断，不能混成token限额|
|1F/2F|先采2条失败、同题均有2对；flatten生成两个1F行|每题取第一条合格失败|否|恢复2F配对及两个1F变体，或声明固定抽1条的适配|
|Sampling config|Qwen .6/.95/20/32768；Nemotron .6/.95/未设top_k/65536|Qwen数值相同|Qwen部分是|按模型配置，不强制Nemotron也32768|
|Backend/RNG|论文vLLM0.10.2，seed42，n=16|历史HF；现vLLM0.11.0 custom；每请求独立seed|否|全部新比较统一后端，记录不同随机流|
|Prompt|初始qwen_math_prompt+原problem字段；1F要求审阅|初始相同wrapper但problem自己规范化；R2重写为independent-solve|部分|原problem字段缺失；新prompt作为已声明研究适配|
|Question selection timing|clean-slate→冻结→干预|新题遵循；旧十题为开发集|原则是|旧题排除新验证；不得据R2/late/path效果筛题|

## Anchor模型与参数

|Alias|Checkpoint|Thinking|Temperature|top_p|top_k|Context / nominal max_tokens|
|---|---|---|---:|---:|---:|---:|
|Qwen3_8B|Qwen/Qwen3-8B|True|0.6|0.95|20|32768|
|Qwen3_32B|Qwen/Qwen3-32B|True|0.6|0.95|20|32768|
|Nemotron_32B|nvidia/OpenReasoning-Nemotron-32B|默认True|0.6|0.95|未显式设置|65536|

依据：`eval_models_params.json`与`src/model_config.py`。未设top_k由vLLM默认值解释，不能写成20。官方代码给SamplingParams传nominal max_tokens，引擎受总上下文限制；我们显式用context−prompt作为生成预算。官方还会对过长prompt按max_tokens−150做字符解码后的token截断；当前实现拒绝超长prompt、不静默截断。当前tokenizer EOS-only策略与上游默认停止策略也不完全相同。

## 公开代码缺口：不能把README当作无缝可运行协议

1. `2f_datagen/datagen.sh`调用不存在的`aggregate_data_minimal.py`；现存`aggregate_data.py`实现与论文2对2错相符，但无法证明缺失文件历史上完全同实现。
2. README说1F从2F flatten；现存Python循环确实产生两个1F行，保留相同question id，分别用traj1、traj2。然而shell实际glob仅`*_T2_F0.ds`，Python输出路径只替换`T2`。直接对F2输入使用现脚本可能输出到原路径；**不可原样执行**。
3. `downloading_datasets.py`只有名称字典，没有下载逻辑；仓库没有Game24源数据、三anchor完整baseline或653题manifest。
4. `aggregate_data.py`复制若干非Game24通用元数据列，直接对我们精简row运行还需显式schema adapter。
5. 1F评测脚本n=8，2F脚本n=16。两个1F变体×8可形成每题16条，但缺实际launch/output，不能把每个阶段都无差别写作16。

离线直接提取执行现存函数的两项测试已通过：False/None归类与2对2错阈值；2F→两条1F的题号/草稿保持。连同既有新题排除/冻结检查共4项通过；104题唯一性、预算算式和generate=false另行检查通过。上游文件未修改，未运行会覆盖数据的脚本。

## 已公开数据能恢复什么

截至本次检查：官方GitHub releases API为空；HF dataset search `contextual-drag`为空，额外关键词搜索未找到作者公开的完整Game24草稿。此为限定检索结论，不声称全网不存在。

官方`analysis/TED/cache/direct/`六份缓存覆盖630–631题，合并631。三个anchor缓存保留了normalized最终公式、correctness、finish_reason，以及后续anchored-response分析。它们**不是完整草稿池**：无原始文本、Thinking解析状态、完整prompt和trajectory来源ID；生成相同公式的独立样本不能按公式内容去重。

本次按同题不同draft组中重复的init_response列表只计一次，三anchor合并后596题保留了至少2条stop/True及2条stop/False。缺Thinking状态，不能确认这些条目全部通过原聚合过滤。缓存构建还会按anchored结果的完成/公式可解析性丢弃题目，故不能把缓存成员资格作为“只依据baseline”的新题筛选条件。

**题号重要发现：**从正确公式的四个数字恢复631个multiset，全部无冲突匹配ToT题源；631/631同时匹配“数字组合字典序排序后的零基索引”。与ToT Rank直接相同仅2个。因此只能用multiset关联，不能将原论文id1170和我们Rank1170默认当同一题。该结果支持共享题目宇宙，但不能恢复缺失22题的eligible身份、原problem文本或精确653名单。

缓存可用来核查来源、形成背景难度证据及检查协议一致性；不能拼接公式伪造原失败草稿，也不能未经声明地替代独立验证样本。

## 历史baseline复用盘点

|分层|去重样本|正确 / False / None|题数|复用范围|
|---|---:|---|---:|---|
|早期non-thinking smoke|70|39 / 19 / 12|70|工程/来源记录；不能补Thinking anchor配额|
|Qwen3-8B HF Thinking|299|262 / 26 / 11|75|已声明HF来源的适配baseline，不能当vLLM同协议重跑|
|新Qwen3-8B vLLM Thinking|32|30 / 1 / 1|8|同后端适配池中最接近可复用的部分；seed/n设置仍不同|

共401条、86个数字multiset。旧audit把non-thinking与Thinking汇总的总体331/401正确率不能用作Thinking采样产率。它的人工错误标签按题号赋值，不能直接视作逐条错误证据；本次不扩大其人工标签用途。

完成+Thinking可解析+明确False的历史池中，16题至少1对1错；只有开发题1084达到2对2错，排除开发题后为0。1170/1261均只有一条明确完整失败，不能直接成为2F/2对2错合格题。现有两份草稿可保存为适配方案材料，不由此降低新协议阈值。

## 资源可行性

|Anchor|当前证据|生成前状态|
|---|---|---|
|Qwen3-8B|用户已授权只读`/data2/huangrj/models/qwen3-8b`；vLLM常驻GPU4|可运行，当前不生成|
|Qwen3-32B|发现`/data/zhaoyi/liujunyuan/models/Qwen3-32B`，17/17分片，65,524,328,560字节|只做文件核查；使用授权和GPU实际加载均未确认|
|Nemotron-32B|对/data2、/data限定depth≤4可读目录未找到|未落实，不下载、不自动替换|

自己的Nemotron-7B/Qwen3-14B等目录没有safetensors权重，不能当可用模型。/data2约33.2GB空闲，小于一个约65GB的32B BF16检查点；不能假定可直接下载。GPU4上的8B与32B不能假定同时容纳，正式运行需明确顺序切换或另获GPU资源。官方脚本32B使用4卡，不能由此断言单A10080GB绝对不可行，但目前未验证支持原长上下文预算。

## 推荐方案与预算：准备但不执行

**优先A：同三个anchor重建一个固定新题子集的pool。** 不必为全1362题重新生成，也不宣称复现精确653。先补齐模型授权/资源；固定16 samples/model/question、3模型合池；按code-faithful和strict-False两视图报告，选定primary后冻结；记录self/cross source。若对实际错误作人工筛选，另列机制子集，不替换原协议主集。

候选顺序已准备：从1362题排除历史86个multiset，余1276，seed20270918固定抽取前104题。选择不读TED恢复结果或任何新旧intervention outcome。为避免根据结果补样偏差，所有纳入问题需完成相同anchor配额；阶段边界固定，不给难题临时追加直到产生错误。

|累计候选题|baseline生成(3×16)|若eligible率沿用论文653/1362，仅作情景估算|
|---:|---:|---:|
|32|1536|约15题|
|64|3072|约31题|
|104|4992|约50题|

653/1362不是当前产率保证。若eligible率为25%，30/50题期望需120/200 candidates，即5760/9600次baseline；若50%，需60/100，即2880/4800次。完整1362×3×16为65376次，没有必要自动展开。32题阶段若不足目标，先报告，不自动解锁64/104阶段。

四条件×2paired seeds：30/40/50题分别240/320/400次评测。若保留两个1F草稿变体，则干预评测翻倍，须在预算中明确；建议机制首批从已抽取两条失败中用固定随机规则选一条，标为adapted single-draft protocol，不按恢复或人工美观挑选。

最新8B batch4筛选32次耗时约2.04h。只按这个速度，1536次相同工作负载约98h；32B速度和65536上下文不可按8B估计，这不是三anchor工期预测。预算必须用各anchor短工程测量后更新，不能承诺几小时拿齐50题。

**B：若Nemotron资源无法落实，双原anchor适配（8B+32B）是可讨论的最小模型集合偏离。** 固定同题16+16、pooled2/2、允许cross-model；32题1024次baseline。必须称adapted protocol、不能声称保留原eligible population，产率未知。当前尚未批准，也未执行。

**C：单8B增加到16次**可用当前资源，但仍保留单模型选择偏差，不是优先协议复现方案。公开缓存作为candidate预筛也会引入额外选择条件；不将这两者自动替代A/B。

## 生成前必须决定的事项

1. 能否落实Nemotron-32B及Qwen3-32B使用/算力；否则是否接受B的模型集合偏离。
2. 原数据prompt无法恢复、现vLLM0.11.0与上游0.10.2不同：接受明示的适配，还是提供原始数据后再做。
3. primary错误池是现存code-faithful falsey还是strict-False；建议保留原代码兼容视图，同时将真正错误作为单列机制子集，避免悄悄改变分布。
4. 批准首阶段baseline额度后才生成；旧32+48额度不自动转成三anchor上千次预算。

机器方案`protocol_prepared_generation_plan_20260917.json`已置`generate:false`并列出blockers；没有自启动launcher。旧队列标记`paused_protocol_audit`，GPU4常驻保持，不启动1170/1261或其他intervention。

## 交付索引

- 本报告：协议、逐项parity、预算与待决策项。
- `protocol_inventory_20260917.json`：缓存与历史baseline审计摘要。
- `protocol_ted_question_mapping_20260917.json`：631题multiset推断映射及限制。
- `protocol_prepared_generation_plan_20260917.json`：104道固定候选顺序、分阶段额度、阻塞条件，禁止生成。
- `scripts/protocol_parity_audit_20260917.py`：可复跑的只读审计；原始CSV及API快照在`outputs/protocol-parity-audit-20260917/`。
- `tests/selective_context/test_protocol_audit.py`：现存聚合与flatten语义检查。
