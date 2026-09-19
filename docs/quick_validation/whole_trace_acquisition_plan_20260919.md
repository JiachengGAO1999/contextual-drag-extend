> Schedule superseded on 2026-09-19 by [the submission sprint](iclr2027_submission_sprint_20260919.md): time-boxed 20–30 new-question target and batchwise intervention, rather than waiting for 30–50. Existing Batch02 protocol and raw artifacts remain unchanged.

# Whole-trace acquisition：2026-09-19 冻结计划

用户批准 trajectory-level failed-trace access control 主线，优先独立样本 acquisition、人工 eligibility audit 和双anchor合池。暂停局部mask、新任务、新评测模型、Nemotron下载和kernel优化；correctness blocker例外。

## 研究边界

Primary H1：R0 > R2，操作性定义为适配prompt下带error signal的residual drag。R0/R2提示语不同，不能只据此排除所有提示语因素。
Primary H2：R3 whole late_block > R2。相同输入、token与position下访问干预的总效果，不等于已经证明唯一的错误传播机制。late首token仍由full prefill logits生成。
R4 whole path_block作为时机诊断，不预设优于R3，也不解释成一般的越早越好。路径阻断保留草稿内部传播；不删除KV或文本。
模型实际接收的failed trace是最终回答正文，不包含源模型私有Thinking，论文必须准确说明暴露范围。

七题pilot原始记录复核R0/R2/R3/R4=12/4/12/10（各14），作为Stage-1 evidence保留，不合并进新假设的confirmatory primary denominator。新确认集目标先30道，上限50，不含旧开发/七题pilot。在完整batch边界审计后达到30即可停止acquisition，不根据干预效果继续补题，也不保证给定候选预算一定达标。

## Formal eligibility 在本轮预先明确

两Qwen anchor，各题各模型固定n16，跨模型合池。至少2个正常EOS、Thinking可解析、官方True，以及至少2个正常EOS、Thinking可解析、官方False且经人工核实的实质失败。None、超长、纯格式不进入failed pool。错误无解声明可属实质失败，必须有合法解/正确companion支持。官方False+None口径不作为primary。

这比早期七题pilot的官方2C2F+至少一实质草稿严格：41不满足新的strict formal rule。差异显式记录，不能追溯改写旧pilot。

按题固定随机抽一条实质失败；原规则Random('20270918:'+qid).choice，pool按model alias和整数sample index排序。当前只建立pool，不执行抽取或intervention。达到目标且完成审计后，冻结全体draft与prompt、seeds，再统一R0/R2/R3/R4评测。

## Batch02：32B补齐

8B既有32题×16=512已完成；本轮对同一完整32题再生成32B×16=512。名单严格沿用scripts/baseline_screen_manifest_20260918_batch02.json，不按8B成败缩小名单。与prepared candidate order及multiset唯一性检查一致；原prepared pool排除了历史86组数字。

32B只读授权路径/data/zhaoyi/liujunyuan/models/Qwen3-32B。普通vLLM0.11 FLASH_ATTN、BF16、Thinking、temperature.6/top_p.95/top_k20/context32768、seed42；并发4/batched2048/memory.95，沿用已跑通benchmark，不缩上下文、不量化。

每两题一个32输出chunk，共16chunks，每块完成落盘；错误停止不fallback。最终自动汇总pooled_scorer_summary.json与manual_review_queue.json，仅人工完成后冻结正式eligible。停止在pooled审核点，不自动intervention或Batch03。

预计14–18小时（长度/共享GPU竞争可延长），最大新增512；不是沿用前夜12h cap。仅停止自己的已空闲resident，未动其他用户进程。启动前其他进程合计约2.6GB，小于3.5GB检查阈值，仍为既定.95配置留有容量；如vLLM资源预检失败停止，不调整科学配置。

tmux：batch02-qwen32b-20260919。日志：outputs/batch02-qwen32b-20260919.log。输出：outputs/game24-batch02-qwen32b-20260919/。status.json显示已完成数；每chunk日志记录生成进展。结束恢复selective resident。

## 8B人工审计纠正

互斥分类总512：452正确、35实质失败（32用数违规、1最终值错误、2错误无解声明）、7纯格式、17超长、1正常完成但unscored。原47官方False包括5条超长，不能全部作failed trace；13官方null与17超长有交集。

754/14的boxed24正文最后重复使用3，须从格式候选改为实质失败。1342/11合法用数却算得22并在最终宣称24；754/3、754/6明确返回27并错误宣称24无解。所有scalar候选均人工查最终正文，再用Fraction与数字multiset复算。脚本scripts/audit_batch02_manual_20260919.py保存可复核证据。

8B-only符合strict条件8题：230,339,717,754,956,1214,1305,1342。只是baseline预合格，不称最终formal sample。7旧pilot+8候选可以说15道进入不同阶段，不能说15道confirmatory样本。

后续Batch03继续冻结顺序中未使用32题，8B+32B各16，不按前批失败类型调整选题。预计达到30题的候选成本仅用产率作情景预算，25%来自single-anchor pre-audit，不是双anchor真实产率。
