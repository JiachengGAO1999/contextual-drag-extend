# 两题边际干预探针：冻结运行方案

用户批准GPU运行。1358/B3和719/B5，边界不变；每题C1_plus_U、C2_minus_U两个新条件，四组原paired seed bases2027/12027/22027/32027，总16次生成。属于开发集诊断，不是confirmatory evidence。

C1=P_X旧结果；C2=fixed_C2旧结果。复制两题R0/R2/R3/R4/C1/C2原始记录到references.jsonl，保持原condition_id与评分。请求、来源、实际sample_seed和单位记录在manifest及bundles。

预检证明C1→C1+U与C2−U→C2增删的是完全相同的unique (q,k)边，覆盖全部prefill加一个decode query；四seed输入相同。固定单位只增删目标unit，不合并起点。模型加载后检查四条件×36层prefill/decode阻断；leave-one-out须恢复目标U的正decode attention。

Thinking Qwen3-8B，HF eager BF16/float32 sampling，temperature0.6/top_p0.95/top_k20/context32768，生成预算为32768减完整prompt长度；官方scorer；parse失败/length按失败保留。模型路径只读/data2/huangrj/models/qwen3-8b；GPU4。

主要按同一方向报告：Acc(C1+U)−Acc(C1)，Acc(C2)−Acc(C2−U)，正值均表示阻断U有帮助。分别报告两题、每seed错→对/对→错和答案变化、parse/EOS。两题四seeds的小差异不能认定稳定交互，更不能直接标成有害/保护；没有结构控制，不能证明错误特异性。

不按结果换片段、扩seeds或自动追加。无明显方向允许结论不确定。边界与semantic unit定义沿用dependency_decisions_20260914，不通过输出回调标签。

tmux qwen3-marginal；日志marginal_20260914.log；输出outputs/game24-qwen3-marginal-path-20260914。预计1–2h，长Thinking可能延后。结束/失败记录exit并恢复常驻。代码selective_context/phase0/marginal_run.py。
