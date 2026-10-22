# Game24 100题采集报告（2026-10-14）

**状态：A100_GPU4_SHARED / A800_ALLOCATION_PENDING；当前独立合格2/100；本轮新增生成0。** 已完成服务器数据同步、统一资格审计、实质错误复核、成本重放和可续跑pilot实现，尚未采集新题。不得把准备完成称为100题验收通过。

## 固定pilot与工程实现

已冻结16道新题，每模型8条，双Qwen顺序执行，共256次，累计上限8 GPU-hours（含加载和恢复尝试），seed/order seed20261014。候选：1036, 374, 584, 1191, 1053, 849, 309, 16, 295, 442, 1079, 1039, 1298, 839, 349, 1164。全部排除既有baseline和本地/服务器开发材料，完整余下固定题序保存在 `fresh_question_order.json`。当前尚有 1034 道无这些暴露记录的原题；不是题目宇宙耗尽。

采样 .6/.95/top-k20，Thinking开，context32768；每条seed=base_seed+sample_index，每请求n1以避免恢复时重标seed。8B最多8个并发请求，32B最多1个；模型在两个独立子进程顺序加载。先完成32B少量完整响应，实时记录其耗时/长度，之后仍受同一pilot上限约束。后端只用ordinary-vLLM，保留原selective服务供后续使用。

完成一条就fsync，15秒机器可读heartbeat；SIGINT/SIGTERM或预算停止只终止本作业请求，保存已完成响应与在途partial诊断。幂等恢复按model/question/index核对，配置/题源不一致拒绝续跑；完成的length/None不重复抽样。尾部半行先归档才修复，内部损坏拒绝自动处理；磁盘<10GiB停止且不删除数据。进程组超时只针对本次anchor；全程共用已有项目launcher锁。

只有GPU4全部compute进程都是本项目且resident经tmux确认idle时，才可释放该服务并运行，结束后恢复。发现其他用户进程即拒绝，连本项目resident也保持不动。不得换用其他卡或下载checkpoint。

## 当前阻塞

2026-10-14北京时间17:35检查：A100全部8卡有compute进程；GPU4同时有本项目EngineCore PID3451842和其他用户hezq PID2190663。其他用户进程使用约17–19GiB，该卡不能独占做32B完整采样。/data2空闲已从较早的114GB降至约60GB；真实可用空间必须在开跑时重检。

用户要求补查A800后，确认GPU0/2/4/6无compute进程，约79.3GiB显存可用；GPU1占有18GB显存但进程归属无法核实，不能当空卡；3/5/7有人使用。A800 `/data` 约13GB可用，根盘仅1.9GB。

A800现有 `/data/gaojc/shared/models/Qwen3-8B` 的5/5分片（16,381,516,776 bytes）、`/data/share/hjl/zhaoyi/models/Qwen3-32B` 的17/17分片（65,524,328,560 bytes）均可读且无缺片。现有env `vllm-budget-018` 实际vLLM0.10.2/torch2.8.0，`vllm-budget-clean`为0.19.1/torch2.10.0；不需搬运或下载权重。**A800存在硬件与模型可行路线；尚未占卡，需确定可用窗口与总GPU预算。** 原采集入口当前固定A100路径，迁移还需隔离部署依赖并冻结A800模型路径/后端版本，不能直接原命令启动A800。

A100 CPU运行验证已通过：vLLM0.11.0、5/5和17/17完整分片、两模型pilot最大prompt72tokens。没有初始化推理引擎、加载模型权重、forward或新生成。

## 成本情景（不是已批准预算）

Batch04实测5/32合格、512次、3,438,749 tokens、生成10.310h、含加载10.683h。按照该全批产率/成本，补齐剩余98题约需 **628候选题 / 10048生成 / 209.6 GPU-hours**，约67,485,449生成tokens；审核时间另计。按单卡持续占用约8.7天，实际共享卡日历时长更长。该估计没有把已用的3道Batch04题算作新增。

16题pilot按同一历史成本约5.34h，上限8h。32B改并发可能改善长尾，也可能降低吞吐，尚未测得。不能从Batch03 prefix8 token数反推出实测GPU-hours；不声称当前资源已经能在预算内完成100题。

pilot完成后：先审计256条，再用真实全批GPU-hours/eligible更新成本；若0题合格、不完整配额、错误标签不可靠或成本超出可用额度，停在检查点。下一批建议沿冻结题序32题、固定8次，不临时针对某题补到错误；需先明确整个100题项目可用的GPU时间额度。未启动1362×3×16或adaptive补样。

## 命令与进度入口

本地零GPU验证：`python -X utf8 scripts/game24_100q_collect.py`

服务器CPU/tokenizer验证：`/data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/game24_100q_collect.py --validate-runtime`

独占GPU4可用后：`/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/game24_100q_collect.py --run-pilot`

断点恢复使用同一命令、manifest和output；进度在 `outputs/game24-100q-20261014/acquisition/pilot/<anchor>/status.json`，控制台日志为各anchor console.log；全pilot状态为其父目录status.json。默认命令只验证，绝不自动生成。

审计/资产：`game24_question_manifest.jsonl`覆盖1362题，`game24_trajectory_pool.jsonl`逐条索引完整原文、prompt及source path/line/hash；完整原始文本与token IDs位于独立snapshot，避免重复复制大文本。`game24_eligible_candidates.jsonl`保留两题及各2对2错见证；冻结100题文件和split当前明确未完成。

GO：已完成的数据审计与可执行pilot准备。**NO-GO：在共享GPU4上启动采样、未经总资源额度自动扩大到数百GPU-hours、冻结不满100题或进入机制探索。** 此为资源和数据阶段判断，不是否定Contextual Drag效应。
