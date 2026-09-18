# 七题新样本恢复验证：2026-09-18

用户批准七题各一条真实failed draft、两paired seeds、四条件，共56次生成。没有继续筛题或细化mask。

题目44,914,1112,41,1057,413,509。Primary为七题；同时报告排除41的六题严格子集。41满足官方2C2F但只有一条实质失败，明确保留标记。

从两anchor已审计实质失败池中抽取：按model alias、整数sample index排序，以Python Random('20270918:'+qid).choice固定抽取。该抽样实现本轮在干预前冻结，不声称此前已明确该字符串算法。来源：8B 44/4、41/8、1057/2、413/11、509/12；32B 914/14、1112/1。草稿为最终回答正文，保留原boxed格式，不暴露私有Thinking、不修改错误文本。

评测模型Qwen3-8B，现有selective vLLM0.11常驻，batch_size8。条件R0/R2/R3 whole late_block/R4 whole path_block。seeds927001/927002沿用prepared plan；temperature.6/top_p.95/top_k20/context32768，Thinking开启。使用thinking_pilot.independent_prompt原有独立解题模板；不是upstream critique模板。R0也重新生成，不拿ordinary-vLLM筛题结果替代。

R2–R4同文本、token、position与hash；整段草稿token span阻断。R3首次阻断query为prompt_length，因此首token仍来自完整prefill logits；R4阻断query从draft_end开始，草稿内部传播保留。56请求validate、same-text和boundary检查通过，14组R2–R4逐key核对实际metadata onset表通过。沿用既有vLLM真实模型验收，不宣称本轮新跑了GPU attention实测。

准备物料：outputs/game24-dual-anchor-validation-20260918-prepared/，包含selection.json、pairs.jsonl、pairs/、bundles/、manifest.json、preflight.json，已同步本地。

运行输出：outputs/game24-dual-anchor-validation-20260918/，每8次落盘results.jsonl，最后completion.json。复用tmux dual-anchor-overnight-20260917 resident，通过run_manifest启动；运行日志继续写outputs/dual-anchor-overnight-20260917.log。结束回到resident交互提示符，不再自动生成。

结果主看accuracy、R0−R2、R3−R2、R4−R3、wrong→correct/correct→wrong和按题cluster bootstrap；再看completion/parse、错误公式复用和missing-draft异常。只有7个独立题目，两seeds不是14道独立题，CI需保留小样本限制。未含R1，不能将R0−R2直接称无error-signal contextual drag。
