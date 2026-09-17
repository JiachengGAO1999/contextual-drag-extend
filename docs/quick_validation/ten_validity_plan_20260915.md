# 十题：错误有效性评价的访问干预

用户批准从两题“否定后重新认可”扩展为候选/构造与有效性评价的比较，希望下一轮覆盖更多独立题。十份旧固定草稿全部保留，覆盖6题未明确否定的资源违规、1题不完整候选修补、3题否定与重新认可交错。新筛到的1261作为后续材料，不在本轮临时扩入；本轮没有重新按恢复效果选题。

## 当前RQ

错误草稿中的候选/构造信息，与对其有效性的评价信息，分别如何影响下一次解题？明确否定是可有可无的子类型，不再作为所有题的纳入门槛。本轮仅检验针对固定目标候选的错误认可/合理化表述的访问效应，不宣称已经识别统一内部机制。

## 冻结矩阵

|条件|操作|结果来源|
|---|---|---|
|R2|完整草稿访问|十题×4seeds，复用|
|L_E_v1|late_block遮固定F1的独立错误认可/合理化正文及认可标题|40条：12复用、28新增|
|R0/R3/R4|无草稿/整段late/整段path|已有参照，不解释为单因子控制|

完整候选公式、构造和明确否定保留。部分认可单元混有正确算术，不能理解为精确删除所有错误或纯语义操作。71公式内incorrect保留；513仅针对旧F1家族，其他候选的认可保留。旧M_V在513有两段跨候选归属问题，详见[统一审计](ten_validity_audit_20260915.md)。

577、719、1226各4条旧M_V逐请求精确复用；只在manifest将分析条件映射为L_E_v1，原始condition_id仍为M_V。旧1358结果保留为历史、不混入新条件。其余1189、804、123、71、513、1084、1358各新增4次。不是40个独立题目，不能把复制的参考记录计为新生成。

## 配置、检查与估计

原四组seed bases2027/12027/22027/32027，实际seed沿用每题bundle。Qwen3-8B Thinking；HF eager BF16/float32采样；temperature0.6/top_p0.95/top_k20/context32768；原independent-solve prompt、官方scorer不改。late首token仍来自完整prefill logits，每条与paired R2核对。

40请求通过token映射、边界spillover检查、完整公式token保留及输入/种子验证；12条旧M_V通过schema规范化后的完整请求相等检查。旧FULL记录省略空mask字段，规范化后与空列表语义一致，没有放宽实际mask一致性。

现有多区间/mask/采样测试19项通过。7个新题mask的真实模型所有层decode attention检查通过：目标为0，保留草稿attention为正。该检查验证逻辑阻断，不证明全部语义通路移除。预检位于`outputs/game24-qwen3-ten-validity-late-20260915-preflight.json`；真实检查在运行目录decode_sanity.json。

2026-09-15 09:56:06 CST启动，当前已进入第1/28条生成。预计2–4小时，约11:56–13:56 CST完成；长输出可能延迟。无额外API费用，使用原GPU4；输出保存文本、token与请求，不保存模型副本。代码新增`selective_context/phase0/ten_validity_run.py`，attention核心不改。

tmux `qwen3-ten-validity`；日志项目根目录`ten_validity_20260915.log`；退出码`ten_validity_20260915.exit`。输出`outputs/game24-qwen3-ten-validity-late-20260915`。启动脚本结束/失败后恢复自有GPU4常驻；无自动追加条件或seeds。

## 分析预案

主指标L_E_v1−R2准确率差及同方向wrong→correct/correct→wrong；逐题/逐seed报告，失败与截断按原scorer保留。10,000次paired整题bootstrap，保留每题四seeds，统计seed2027；仅探索性区间。单列旧四题与其余六题，避免把复用或旧开发选择当独立验证。

辅助检查完整Thinking和final中目标候选的提及、认可、最终采用，标量24或歧义改写不能判为确定采用。首轮允许零或负效应；不在看到结果后扩充E片段。没有匹配几何控制，不能以E−R2单独证明评价语义的因果特异性；late还保留prefill间接影响。后续是否加path、否定条件或新题，依据本轮分析另定，不在当前自动铺开。
