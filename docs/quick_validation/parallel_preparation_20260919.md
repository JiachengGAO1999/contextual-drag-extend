# GPU生成期间的CPU准备：2026-09-19

17:55北京时间只读状态：Batch02 32B已保存224/512（14/32题），chunk-14正在生成。开始约09:57，按已完成7块耗时约7.45小时，剩余预计9–11小时，长度和共享资源可能改变；不是实时承诺。

## 本次已实际完成

- 检查服务器MATH500本地数据：datasets.load_from_disk读取成功，500条、500个唯一unique_id；字段problem/solution/answer/subject/level/unique_id齐全。
- 本地dataset_info记录来源HuggingFaceH4/MATH-500 revision ff5b20257d8185524591543f8ff5993951537bb8。未联网下载，未运行模型。
- 服务器官方math scorer最小CPU检查：0.5与1/2等价为True，2与3为False。仅接口smoke，不是全面评分正确性验证。
- 发现现有vllm_run调用real_smoke.evaluate，后者硬编码Game24 scorer；thinking_pilot.independent_prompt末句硬编码使用四个数字。MATH500必须显式选择math_verify并替换任务专属末句，不能直接套现有Game24运行器。

## 无需GPU即可推进的工作

1. 同步已完成chunks，逐条审计官方False及scalar答案，保留证据；后续合池只做增量更新，不修改candidate order。
2. 完成第二任务的prompt/scorer显式路由和CPU测试，保留Game24原默认行为；冻结MATH500题序与采样预算，再做小规模GPU成本预检。
3. 正确草稿control：不能保留INCORRECT声明。先比较两种设计：neutral signal下正确/错误草稿的full/late四格（解释更干净但多生成），或独立truthful correct-context full/late（成本较低，但不能声称纯内容正误交互）。关键取舍需明确后冻结，不能悄悄更改primary。
4. 论文方法、数据筛选流程、pilot表、局限性与正式结果表骨架可现在撰写。不要填造未完成结果。
5. 对已完整合池的题准备不可变pairs/bundles、预算与分析脚本；正式GPU评测仍遵守当前串行队列与审计停点。

当前CPU检查不占GPU、不终止或改动32B任务；没有新增生成，没有自动选择第二任务样本或调整实验配置。本文件记录阶段准备，不表示上述待办均已实现。
