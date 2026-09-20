# MATH500 兼容准备（2026-09-19）

状态：代码与CPU集成检查完成；真实GPU生成未启动，尚不能称MATH500实验已验收。当前32B Game24任务不变。服务器隔离目录/data2/gaojc/tmp/math500-cpu-check-20260919，未覆盖运行中的项目。

## 实现

- selective_context/tasks.py：显式game24/math500任务路由、官方scorer、独立解题prompt。Game24默认与原prompt逐字一致；MATH500末句要求boxed最终数学答案，不要求四数字。
- real_smoke.evaluate与vllm_run接受task，记录到结果/config；旧manifest/pair默认Game24，跨任务不匹配报错。math500 pair必须显式task及字符串answer。
- resident.run_manifest支持task；已运行resident未热更新，不能直接调用新参数。新版本应在当前任务结束后的计划切换点部署。
- baseline_screen_vllm_20260917.py支持--task math500，读取CPU导出的JSONL，核对题目和reference哈希；保留upstream baseline外层prompt、Thinking采样和现有EOS策略。--validate-input-only只校验源数据/manifest/scorer，不加载模型。
- scripts/prepare_math500.py读取本地HF数据、按unique_id排序后固定shuffle、导出全部题序与指定prefix manifest。需显式给count/samples，不暗设科研预算；不按题型、难度或输出结果筛题。
- scripts/prepare_task_interventions.py从已审核固定pairs准备R0/R2/R3/R4相同输入请求。要求audit_status=substantive_failed；用户数据ID含斜杠，文件名使用ID哈希。拒绝覆盖、重复题/seed和上下文超限。synthetic fixture禁止送入scientific runner。

模型、后端、mask实现、采样参数均未优化或改动。math500评分必须使用官方math_verify，不允许Game24 fallback。

## 验证证据

- 本地：31 passed、4 skipped（本地Python缺math_verify）。
- 服务器隔离CPU：37 passed（任务路由、官方数学等价/错误/缺失答案、Game24 prompt回归、Thinking解析、token边界、vLLM onset元数据）。GPU通过CUDA_VISIBLE_DEVICES空值禁用。
- 真实MATH500：500题500唯一ID，引用本地revision ff5b20257d8185524591543f8ff5993951537bb8。
- CPU导出2题×n2演示manifest，输入校验通过；这是工程准备，不是正式题集或已批准生成预算。
- 真实Qwen tokenizer：一份显式synthetic fixture×2seed生成8个请求；R2–R4输入合同通过，121-token prompt，spillover仅换行。没有模型生成；fixture不能用作真实失败草稿。

## 可运行入口（在最终确定预算和部署后执行）

```bash
# CPU：固定题序和采样预算。2x2仅为工程例子，不代表formal protocol。
python scripts/prepare_math500.py --dataset data/math500/math500.ds \
  --output outputs/math500-prepared --count 2 --samples 2

# CPU：数据与官方scorer预检，不加载模型、不生成。
python scripts/baseline_screen_vllm_20260917.py --task math500 \
  --model /data2/huangrj/models/qwen3-8b \
  --input outputs/math500-prepared/source.jsonl \
  --manifest outputs/math500-prepared/manifest.json \
  --source-revision ff5b20257d8185524591543f8ff5993951537bb8 \
  --output outputs/math500-baseline --validate-input-only

# GPU：相同命令去掉--validate-input-only才会生成，需等计划切换点。
# CPU：审核完成后，pairs需id/problem/answer/traj1/task=math500/audit_status。
python scripts/prepare_task_interventions.py --task math500 \
  --pairs outputs/math500-audited-pairs.jsonl \
  --tokenizer /data2/huangrj/models/qwen3-8b \
  --output outputs/math500-bundles --seeds 927001 927002

# GPU：四条件示例。若仅R0/R2/R3，应在运行前冻结对应manifest，不能看结果后删除R4。
python -m selective_context.phase0.vllm_run --task math500 \
  --manifest outputs/math500-bundles/manifest.json \
  --output outputs/math500-evaluation --batch-size 8
```

## 后续推进与待冻结项

1. 当前GPU任务结束后先4次完整Thinking工程baseline（2题×2），检查真实输出、评分与时长。工程题如生成过，应从后续确认集排除。不以4次判断任务失败率或科学Go/No-Go。
2. 据实测成本确定MATH500 baseline批次和anchor protocol；若选择单8B不能混称Game24双anchor同一筛选协议。尚未默认扩到512次或自动排队。
3. baseline通过后审阅真实失败、冻结draft，再预检真实prompt下R2–R4边界并评测。数据读取和scorer CPU通过不能替代GPU干预验收。
4. 正确草稿控制的信号设计另行冻结；本轮未用INCORRECT去描述正确草稿，也未新增控制实验。
