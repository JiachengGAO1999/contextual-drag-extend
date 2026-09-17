# 配对补充path：生成前冻结方案

用户明确授权在当前late实验之外追加path并一起比较。新增48次，六题1189/123/577/719/1084/1226，seed bases42027/52027/62027/72027，条件P_X_fixed与P_XCALC_fixed。与late同输入、seed、key集合、模型与采样设置；唯一时机差异是prefill已施加path。

固定单元：X沿用旧X区间；XC使用这些X区间及旧CALC区间作为独立units，各自[lo,hi)从q>=hi阻断。key union可以合并，但units不合并，保证旧X阻断边全部保留。区间内仍允许读取，不声称所有形式的内部传播都消失。path首token来自干预后的prefill，不要求与late或另一path条件相同。

48请求预检：输入和seed配对、覆盖扩大不重开旧边、decode遮挡与late一致。13项fixed-path/mask测试通过。开始生成之前12个真实mask做prefill阻断、decode阻断、保留访问，以及修改被遮token后末位logits不变检查；任一失败则退出并恢复常驻，不自动fallback。

主比较：path-XC减path-X；path-X减late-X；path-XC减late-XC；以及覆盖差值的时机交互。报告accuracy、paired transitions、逐题、question-cluster CI、parse/EOS和长度。相同新seed四格96记录联合分析，旧seed分开。六题均开发集，不作确认性机制或语义独立性结论。

资源：GPU4，接在late成功结束之后，预计额外2–3小时。queue_xcalc_path.sh在tmux qwen3-xcalc-path-queue等待late exit0，确认自己的resident出现后停止该resident并开始path；late失败或找不到指定resident则停止。path结束后自动生成outputs/game24-xcalc-timing-comparison-20260916/summary.json与REPORT.md，再恢复resident；不追加其他实验。

输出：outputs/game24-qwen3-x-vs-xcalc-path-fresh-seeds-20260916。
日志：xcalc_path_replication_20260916.log；完成：xcalc_path_replication_20260916.exit。
