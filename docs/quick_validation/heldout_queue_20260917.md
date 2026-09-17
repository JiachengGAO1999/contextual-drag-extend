# 新题首批：授权与接棒

用户授权：验收结束后开始；最多32次筛草稿 + 48次评测，不追加额度。

- 固定来源：ToT Game24，revision 8050e67d0e3a0fddc424d7fa5801538722a4c4cc。
- 按服务器历史 draft_candidates.jsonl/results.jsonl 排除题号和相同数字多重集；固定顺序种子20270917。
- 冻结8题：519、1080、69、377、45、1170、1144、197；每题4次，种子917000起。完整排除来源见 heldout_screen_plan_20260917.json。
- 筛草稿沿用 upstream R0 prompt；Thinking .6/.95/20，32768总上下文，不截断prompt。
- 只从 completed、parsable 且同时有正确/错误样本的题中，按固定题序审计，最多纳入6题。依采样顺序取第一份符合标准的真实 failed reasoning draft；格式错误、正文正确而最终解析失败不算推理错误。
- X 沿用完整目标错误候选公式及其副本的标注规则，不纳入独立 CALC 或评价文字。需核实算术/用数、引用位置、所有副本及固定path单元边界；模糊归属停下记录，不按干预结果回改。
- 评测每题2个新 paired seeds：927001、927002，四条件R0/R2/whole_path/X_path。最多48次，均使用同一vLLM后端；标注冻结前不生成干预结果。

自动执行边界：当前验收 exit=0、9条结果落盘 → vLLM resident → 32次筛选 → 写 review_candidates.json/completion.json → 常驻等待标注审计。agent不会因后台完成自动获得新的执行回合；因此不能声称无人值守完成尚不存在草稿的语义审阅。评测已获授权，但须后续agent审计、创建冻结manifest后调用常驻run_manifest；不再要求用户重复批准同一额度。

输出：outputs/game24-heldout-screen-20260917。队列状态：outputs/vllm-resident-startup.json。tmux：qwen3-vllm-resident。失败不重试、不切换后端，不自动扩题。筛到不足6题按实际数量评测；0题则报告无合格材料，1–2题仅作案例观察。
