# 公开数学失败轨迹四条件验证（2026-09-20）

用户授权：原20题×2seeds×4条件；允许补充非MATH500的MATH题并分层报告；随后明确排除图形题，按实际纯文本合格数运行。

冻结16题：MATH500/Qwen3-1.7B来源8题（136、138、184、246、294、295、401、491）；MATH训练集/Qwen3-4B来源8题（1101、2383、3000、3289、5293、5300、6774、6835）。编号为公开来源索引，非统一官方ID。每题一份完整公开输出，包含Thinking及final，不截断；paired seeds=930001,930002，R0/R2/R3/R4共128次。未做target R0筛选，未读取intervention outcome选样。

主问题：同题失败轨迹是否造成drag，以及whole late/path访问阻断是否恢复。先报告各层R0−R2，再解释R3−R2及R4−R2。数据来源与benchmark同时变化，不能用两层差异独立识别模型来源效应。合计16题仅作辅助汇总。报告paired transitions、question-cluster bootstrap、EOS/parse/长度终止。

数据审计：cipt全部500题精确映射标准MATH500；82条源False中，35条不完整、30条等价/提取伪错误、6条图形依赖、2条任务歧义、1条缺图、8条纯文本实质错误。MATH训练数据没有源EOS元数据，仅确认文本完整外观；不能声称源EOS已验证。拒绝把多boxed漏提、单位或选项字母差异作为失败草稿。5293、5300、6774参考答案已独立CPU枚举验证。

冻结时3289误填trace10（正确答案），assert阻止写出；更正为已审阅trace11（8pi错误，正确24pi），随后冻结成功。MATH评分新增balanced-last-box-v1，支持任意嵌套及转义集合括号；保留last-box政策，多答案单独box的输出需后续标记复核。Game24评分不变。本地8pass/4依赖skip，服务器12pass。128请求的same-text与mask onset检查通过，完整prompt均保留至少8192tokens生成空间。此为元数据检查，未声称新增真实attention权重探针通过。

运行：Qwen3-8B Thinking，selective vLLM0.11/Flex，temperature0.6/top_p0.95/top_k20/context32768/batch8，prefix cache关闭，per_request布局。R3首token仍来自完整prefill logits。相对UFT参考运行仅任务、数据、scorer、GPU/隔离目录改变，mask与sampling不变。

服务器隔离目录：`/data2/gaojc/tmp/math-external-16q-20260920`；tmux：`math-external-16q-20260920`；GPU0。GPU4既定32B不受影响。首次导入缺data_generation，未生成即退出，补齐依赖重启。启动器完成128次后退出释放GPU0，不自动扩题。预计数小时，可靠ETA需首批实测。

进度：`ssh sjtu-a100 "tail -n 15 /data2/gaojc/tmp/math-external-16q-20260920/outputs/run.log"`。结果在同目录`outputs/math-external-16q-20260920/results.jsonl`，按8条一批保存。完成标志`completion.json`。

本地冻结数据：`outputs/math-external-16q-20260920-source/pairs.jsonl`及`protocol.json`、`preflight.json`。启动实现：`scripts/run_math_external_20260920.py`及同名sh。部署为本地工作区快照而非与主服务器Git版本一致的checkout。
