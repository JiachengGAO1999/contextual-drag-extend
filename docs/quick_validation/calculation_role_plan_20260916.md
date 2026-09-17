# 六题局部计算证据的late干预

用户授权完成修正并启动生成。范围固定于1189、123、577、719、1084、1226：它们是十题中全部没有明确自我否定的用数约束违规案例，不按过去是否恢复选题。保留123的boxed24问题，保留577的R2高正确率和1226的低正确率，不做效果筛选。

## 可检验问题与定义

在完整错误候选和有效性声明仍可访问的情况下，阻断支撑该候选数值的局部计算算式，会改变下一次解题的正确率吗？

L_CALC_v1遮挡“目标候选相关、独立出现的显式数值求值等式”，无论它出现在构造还是Verification标题下。保留完整目标公式（包括公式行自带的求值）、有效性声明、remaining等资源状态声明；保留构造之前的通用目标因式分解。不声称遮掉全部计算信息或纯粹分离构造和核查。该定义以文本对象为准，不把有用/有害作为预设标签。

六题共27个完整display block或inline equation line，均经手工转录后的精确有理数求值检查。它们的数值计算正确，但组合可能重复使用资源。1358/804修补及71/513矛盾核查暂不并入同一角色实验。

|题号|固定draft_key|计算单元数|
|---|---|---:|
|1189|1189/3|4|
|123|123/1|3|
|577|577/0|4|
|719|719/2|3|
|1084|1084/0|6|
|1226|1226/1|7|

标注：`calculation_role_annotations_v1_20260916.json`；完整原文与高亮：[离线审阅页](../../outputs/calculation-role-review-20260916.html)。原ten_validity注释文件保持原样。生成器`.tmp-smoke/build_calculation_role.py`。

## 冻结矩阵与复用

L_CALC_v1：6题×4个原paired seeds=24次；R2以及R0/R3/R4全部复用。同题已有M_X和L_E只作为不同区域的描述性参照，不因片段长度/位置不同就把准确率差当成纯语义角色效应。

预检扫描旧multi-late、ten-question M_X/path、region-late、morphology-surgery、ten-validity结果；按去除condition_id后的完整schema请求比较，24个请求均无完全相同的历史条件。不会重复跑旧MASK_C。新references每题每seed写一次，避免旧surgery的重复参考问题。

固定Qwen3-8B Thinking、HF eager BF16、float32采样、temperature0.6/top_p0.95/top_k20/context32768、原prompt和官方scorer。仅变mask区域，保留late完整prefill和首token边界。生成预算32768减完整prompt长度。

## 启动检查与进度

24份请求token边界、无语义spillover、完整候选和E的token保留、原文与seed一致检查通过；19项已有mask/多区间/采样测试通过；形态修正另5项测试通过。真实模型加载后对6个mask进行所有层attention=0、保留草稿attention>0检查；每条生成首token与R2比较。源码HEAD7fc7245，新增运行器，不改attention核心。

2026-09-16 12:01:48 CST启动tmux `qwen3-calculation-role`。GPU4，仅替换自有resident4135183。输出`outputs/game24-qwen3-local-calculation-late-20260916`，项目根日志`calculation_role_20260916.log`，退出码`calculation_role_20260916.exit`，结束/失败恢复自有常驻。

启动后已确认`CALC_ROLE_ATTENTION_PASSED 6 unique masks;all layers`，第1/24条1189/base2027进入生成并超过512tokens。不是仅启动了tmux。

预计1.5–3小时（约13:32–15:02 CST），长Thinking可延迟。无自动追加seeds/条件、无新题采样。

## 分析预案与解释边界

主比较L_CALC_v1−R2；逐题正确率、全部24组paired wrong→correct/correct→wrong、parse/EOS、10,000次整题bootstrap（统计seed2027）探索区间。六题不是24独立问题。

正向效应与“局部数值支撑影响错误候选采用”相容，但需要控制才能归因为语义；负向效应与移除了有用求值信息相容，但不能直接称片段保护性；零效应仍不能排除prefill间接信息或完整公式中保留的求值。先统计accuracy，再审阅原候选复制、新候选同类用数违规、明确识错却输出错误、合法答案四种非互斥行为。不得看到新输出后调整区间。

没有几何匹配控制，也没有条件使局部算式独立于位置/预算改变。因此这是更明确的角色诊断，不是因果责任定位的最终证据。阶段结束后再决定是否需要控制或更大独立题集，不按效果自动扩展mask。
