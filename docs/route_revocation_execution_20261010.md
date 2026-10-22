# 路线撤销受控检验：启动前交接

**2026-10-11：研究定位复核后，本批不作为默认启动任务。** 下文运行命令
保留为历史交接；新的推进顺序见
[依赖撤销命题审查](dependency_revocation_review_20261011.md)。

状态：本地 CPU 材料与代码准备完成；自然轨迹全文审阅仍为部分覆盖。
**新 GPU 批次未启动、未排队**。
2026-10-11 用户明确同意上传；现已部署至 `sjtu-a100` 的
`/data2/gaojc/projects/contextual-drag-extend`。远端32题材料审查通过，
CPU测试3通过、1跳过，未调用新GPU模型。具体记录见
`route_revocation/deployment.json`；本次只同步文件，不启动或排队新GPU实验。

## 已落地

- 冻结文件：`outputs/generation-diagnostics-20261005/route_revocation/manifest.json`。
  32 个独立数字组合、每题 A/B 两个历史、3 条件、2 类读出，384 个评分单元。
- 212 个本地历史来源文件对应 226 个排除组合；不声明预训练未见过新组合。
  题序种子 20261010，17 个 CPU 资格不适用项保留在 manifest。
- 错误 A/B 都精确等于 24，恰有四个整数叶子，但替换了一个给定数字的出现；
  合法候选精确使用原四数。没有把完整合法解藏在草稿中。
- A/B 的 D 外 token IDs 与位置相同；不添加 padding。固定前缀 138–145 tokens。
  `materials.md` 可逐题阅读，`material_audit.json` 保存全32题算术及分词检查。
- 独立入口 `scripts/run_route_revocation_20261010.py`；复用已有 R4 mask，
  不修改既有诊断后端的 prefill 保护。共同截止点是强制 critique 的最后一个 query。
- CPU 测试 3 passed、1 skipped；跳过项是 A100 上的实际模型分支／边界验收。
  未调用任何新 GPU 模型，不能把 CPU 通过报告为 GPU 已验收。
- 实现逐评分单元落盘、断点续跑、题目级配对 bootstrap 与缺失报告；复用
  原共享 24 GPU 小时预算及 GPU4 launcher 锁，不开新额度，不自动扩展或重试。

这里的“判决”测量**收到外部反馈并重放正确拒绝之后的判断保持**；“采用”
测量把旧错误式子作为解、相对合法候选的续写偏好。没有把同一拒绝指标改名。
候选概率仍不等于自由生成的真实采用或准确率。

## 自然轨迹审阅的实际覆盖

`natural_review.html` 收录全部24条 FULL 原文，`natural_review.json` 保存定位。
目前完整阅读2条：651、170；其余22条仅建立索引，其他48条控制轨迹未新增完整审阅。
不报告“24条已语义审查”，也不据检索片段统计首次事件或现象比例。

651 明确指出草稿用了三个12，Thinking 最后选中了合法 `12*3-12*1`，
但 Final 又提交旧错误 `(12*(3-1))+(12-12)`。这是研究动机的实际例子，
不是普遍性证据。170 正确修复括号，将19改为24，说明“使用相同数字和局部
计算”不能自动算错误路线再采用。两条均保存原文字符区间及解释。
完整24条事件序列审阅仍是 CPU 待办，不能用当前两条代替，也不能报告现象比例。
本批受控前缀不使用自然首次事件来选位置；因此完整重标不再作为受控批次的
启动门槛。只有未来要报告首次事件／总体频率时，才需要补全相应覆盖。

## 可用命令（本地 CPU）

```powershell
python scripts/run_route_revocation_20261010.py --status
python scripts/run_route_revocation_20261010.py --audit-materials --tokenizer outputs/generation-diagnostics-20261005/route_revocation/tokenizer
python scripts/run_route_revocation_20261010.py --analyse
```

`--analyse` 会报告缺失，不会载入模型。分词使用从既有服务器只读下载的公开
tokenizer；manifest 中模型路径仍是 `/data2/huangrj/models/qwen3-8b`。

## 恢复推进时的顺序

1. 保留当前自然证据及审阅覆盖；不按这些结果重选受控32题或 heads。
2. 已获用户明确授权并完成服务器部署与CPU检查。
   `handoff.zip` 不含模型、tokenizer、既有原始实验结果或登录信息。
3. 核对原来源分区任务与共享预算。它保持原授权的等待／运行状态，不能为
   本批抢占外部进程或绕过共享锁。源分区结果只作解释，不用于本批选组件。
4. 在单张 A100 上执行已编写的模型验收，再固定前两题计时；该用时计入原预算。
   若验收失败先修复，不进入384单元评分；规模不按效应修改，预算耗尽保留缺失。
   固定前两题另检查真实 Qwen3 的早阻断 A/B logits 不变性；失败则停止、
   保留失败记录，不把工程样本产生的部分分数解释为机制结果。

**以下命令会开始等待 GPU 并最终运行，本次未执行：**

```bash
cd /data2/gaojc/projects/contextual-drag-extend
/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/launch_generation_diagnostics_20261005.py --route-revocation
```

后续启动须置于 tmux；状态入口为同一 `--status`，逐项完成日志为
`route_revocation/scores.jsonl`，当前项为 `current_request.json`，阶段和失败
记录为 `run_state.json`，首次两题计时为 `engineering_timing.json`。

最后只报告主预测是否获支持、内容身份与判决的解释，以及缺失和边界；不自动
跑16次行为桥接，不声称本批单独足以支撑 ICLR。新颖性定位见
[方法比较](route_revocation_positioning_20261010.md)。
