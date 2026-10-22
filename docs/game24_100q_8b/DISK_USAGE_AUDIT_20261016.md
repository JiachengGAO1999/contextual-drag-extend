# A800：gaojc账号磁盘清理盘点（2026-10-16）

**后续执行结果（2026-10-16 22:37北京时间）：** 用户明确要求直接清理、不另行归档下载缓存后，已仅删除下述四处pip目录内的`http-v2`内容，共3147个缓存文件。实际删除分配块约18.23GiB（数据盘）和8.92GiB（系统盘）；清理后可用空间分别为约19.85GiB与9.07GiB。`wheels`（4.3MiB）、selfcheck、环境、模型、研究数据及备份保留。记录见[pip_http_cleanup_20261016.json](pip_http_cleanup_20261016.json)。原缓存未备份，未来安装时按需重新下载。

22:38北京时间通过原冻结配置、源文件hash、运行时和官方评分器检查后，在原tmux `game24-100q-8b-a800`恢复第20批剩余13条。重新审计停机前已完整保存的cohort，当前合格数为89/100；GPU模型已加载并继续生成，未重采已保存回答。以下为清理前盘点快照。

本轮仅只读检查，没有删除、移动文件，也没有重启采集。范围为A800上的`gaojc`账号（UID1018），重点检查`/data/gaojc`和`/home/gaojc`；未盘点A100或其他用户的数据。

## 当前空间及总体占用

- `/data`总容量约36TiB，当前剩余约1.6GiB；Game24采集因低于2GiB余量而停止。
- 系统盘`/`总容量197GiB，当前仅剩约194MiB。清理`/home/gaojc`会释放系统盘，清理`/data/gaojc`会释放数据盘，两者分别计算。
- `/data/gaojc`整个目录树按`du -x`去重后约283GiB；`/home/gaojc`自身约15GiB，不跟随指向数据盘的VS Code软链接。
- 当前Game24项目目录约979MiB。主要长期占用是模型、Python环境、归档和多份包下载缓存。
- 各子目录之间存在大量硬链接，单独执行`du`后把结果相加会重复计数。本报告的优先清理项另按设备/inode、分配块数及链接计数核算实际可回收量。

## 优先清理：四处pip下载缓存

| 路径 | 所在磁盘 | 实际可回收GiB |
|---|---|---:|
| `/data/gaojc/pip-cache` | `/data` | 8.111 |
| `/data/gaojc/cache/pip` | `/data` | 5.222 |
| `/data/gaojc/tmp/pip-cache` | `/data` | 4.903 |
| `/home/gaojc/.cache/pip` | `/` | 8.922 |
| **数据盘三处合计** | **`/data`** | **18.236** |

这些目录的文件全部属于UID1018，未发现软链接或文件硬链接；主要内容是pip的`http-v2`、`wheels`和`selfcheck`。当前账号未运行安装进程或实验进程，仅有VS Code服务及检查用SSH进程。

清理这些下载缓存会使以后安装相关包时重新获取文件，不会卸载已经安装到环境中的包。仅第一处就可释放约8.1GiB，已足以解除本次采集的磁盘阻塞。建议优先清理三处数据盘pip缓存，同时清理系统盘pip缓存。

## 次优先项

| 项目 | 位置/规模 | 判断 |
|---|---|---|
| vLLM编译缓存 | `/data/gaojc/cache/vllm`约0.904GiB；`/data/gaojc/vllm-cache`约0.050GiB；`/home/gaojc/.cache/vllm`约961MiB | 可再生成，之后可能重新编译；当前不需要依靠这部分解决空间问题。 |
| Mamba下载包及索引 | `/data/gaojc/mamba/pkgs`中的55个下载包约0.201GiB，索引约0.835GiB | 可先用包管理器清理下载和索引缓存。整个包缓存的独占块约4.714GiB；更大范围清理前需核查环境软链接，不建议直接删除整个pkgs目录。 |
| 恢复测试目录 | `/data/gaojc/archive/sjtu-a800-functional-backup-20260827-restore-test`、`-v2`、`-v3`，每个约6.8GiB | 展开的项目恢复副本，三个约20GiB。可在核对归档和保留策略后清理。已有约602MiB压缩备份目录，存在BUILD_COMPLETE、RESTORE_TEST_PASSED，历史报告status为passed；本轮未重新做归档全量校验或证明三份内容完全相同。 |
| 其他历史归档 | `/data/gaojc/archive/cot-xround-codex-cleanup-20260602`约7.7GiB | 包含`server-junk-predelete.tar`及清单；应先核对是否仍需保留，或校验迁移到本地，再决定删除。 |
| 旧VS Code版本 | `/data/gaojc/.vscode-server`约3.8GiB，其中cli约3.2GiB | 可按版本进一步整理；当前VS Code服务正在使用该目录，不能整目录删除。 |

## 不应按目录表面大小直接清理的部分

- `/data/gaojc/.cache/uv`独立查看约7.521GiB，但29,857个文件有硬链接；单删该缓存实际仅约0.009GiB（约9MiB）可释放。它与环境共享文件，不能把7.5GiB当作可回收空间承诺。
- Mamba的环境目录单独查看约59GiB；`vllm-budget-018/bin/python`实际解析到`vllm-gptoss/bin/python3.11`，当前Game24 `.venv`又继承该基础环境。不能把它们看成无关旧环境。
- `/data/gaojc/shared/models`约145GiB，其中当前Qwen3-8B约16GiB。还有Gemma、Qwen其他尺寸、gpt-oss和Nemotron权重；是否仍使用需要按项目决定，优先清理缓存即可解决此次问题。
- Hugging Face相关目录：`/data/gaojc/.cache/huggingface`约6.9GiB、`/data/gaojc/cache/hf`约2.2GiB、`/home/gaojc/.cache/huggingface`约3.2GiB。可能含唯一模型/数据副本，不能仅因目录名带cache就整体删除。
- 当前Game24原始回答、资格见证、配置、种子、账目及实验日志继续保留。

## 建议顺序

1. 清理三处数据盘pip下载缓存，预计释放18.24GiB；清理系统盘pip下载缓存，预计释放8.92GiB。两盘均有足够收益，无需先动模型或研究数据。
2. 重新核对空间和GPU4是否空闲，然后按原配置从第20批剩余13条继续采集；本轮盘点未执行这一步。
3. 如需长期整理，再核对恢复测试副本、旧归档及环境使用情况，逐项决定去留。

以上为检查时快照，其他用户或后续任务可能改变共享磁盘剩余量。
