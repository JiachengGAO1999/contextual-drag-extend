# C2固定片段path：20条覆盖诊断

用户明确决定先比较扩大覆盖后的变化，结构控制另行设计。此前控制预检失败不再阻止本次较弱诊断；没有将旧前缀控制包装成合格结构控制。

## 冻结矩阵

五题1226/719/577/513/1358 × seed bases2027/12027/22027/32027 × fixed_C2，共20条新生成。C1对应旧P_X，保留原记录；R0/R2/R3/R4一并复制到references.jsonl作为参照，不重新生成或重打分。每组实际sample_seed与原R2一致。

C2由固定C1区间加已审阅的重建步骤组成。使用path_block_units独立起点，不因区间并集合并而解除旧阻断。C1复用依据为实际mask相等，而不是仅token数相同。C3与C2重复，不运行；C4暂不运行。

模型、输入和scorer不变：真实Qwen3-8B Thinking，HF eager BF16，float32 sampling，temperature0.6/top_p0.95/top_k20/context32768。预算32768减完整prompt长度。所有失败/不可评分/截断保留在分母中。

## 分析范围

主比较C2−C1，同时报告C2−R2和相对整段R4的差距。报告每题正确数、paired wrong→correct/correct→wrong、accuracy、parse、EOS完成率；五题cluster bootstrap只作探索性参考。观察恢复与损伤，不按结果追加区间、seed或提前停机。无法用本次结果独立证明错误语义特异性、完整覆盖或内部传输责任。

即使准确率无变化，也检查是否有相抵的恢复/损伤；不能把四seeds的小差异当作稳定机制。没有预设必须提高或必须接近整段。

## 执行与监控

启动前20请求全部输入/哈希/seed/旧C1身份及配置验证通过。C2真实prefill检查沿用已通过的完全相同请求，模型加载后补查五题固定path的实际缓存decode attention。已有服务器回归58通过。

GPU4；权重只读。tmux `qwen3-fixed-c2`；日志 `fixed_c2_20260913.log`；输出 `outputs/game24-qwen3-fixed-c2-path-20260913`。运行器`selective_context/phase0/fixed_coverage_run.py`拒绝覆盖已存在输出目录。

预计1–2小时，2026-09-13约22:10启动则约23:10–次日00:10，长Thinking可能延后。结束或失败记录exit状态并恢复原Qwen3常驻，不自动重试或追加实验。
