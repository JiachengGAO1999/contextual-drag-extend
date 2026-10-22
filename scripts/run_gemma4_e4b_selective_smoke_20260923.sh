#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/gemma4-vllm019/bin/python
MODEL=/data2/gaojc/models/gemma-4-E4B-it
PAIR=outputs/game24-batch02-validation-20260920-prepared/585579aed1c5241bcec55697.pair.json
OUT=outputs/game24-gemma4-e4b-selective-smoke-20260923
CACHE=/data2/gaojc/tmp/torchinductor-gemma4-e4b-smoke-20260923
MASK_MARKER=outputs/game24-gemma4-e4b-selective-smoke-20260923.mask-active
ENV_COMPLETION=outputs/gemma4-vllm019-env-completion.txt
DOWNLOAD_COMPLETION=outputs/gemma-modelscope-download-20260923-completion.txt

test -x "$PY"
test -f "$MODEL/config.json"
test -f "$MODEL/model.safetensors"
test -f "$PAIR"
test -f "$ENV_COMPLETION"
test -f "$DOWNLOAD_COMPLETION"
test ! -e "$OUT"
test ! -e "$MASK_MARKER"
grep -q '^STATUS complete$' "$ENV_COMPLETION"
grep -q '^STATUS complete$' "$DOWNLOAD_COMPLETION"

used=$(nvidia-smi --id=1 --query-gpu=memory.used --format=csv,noheader,nounits)
test "$used" -lt 1024
mkdir -p "$CACHE"

export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=packed SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=128 CUDA_LAUNCH_BLOCKING=1
export SC_SELECTIVE_MASK_MARKER="$PWD/$MASK_MARKER"
export TORCHINDUCTOR_CACHE_DIR="$CACHE" PYTHONPATH="$PWD"

"$PY" scripts/smoke_selective_target_model.py \
  --model "$MODEL" \
  --pair "$PAIR" \
  --output "$OUT" \
  --max-model-len 8192 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.90 \
  --max-new-tokens 16 \
  --worker-cls selective_context.vllm_worker_019.SelectiveWorker019 \
  --enable-thinking

test -f "$MASK_MARKER"

"$PY" - <<'PY'
import json
from pathlib import Path
out = Path('outputs/game24-gemma4-e4b-selective-smoke-20260923')
status = json.loads((out / 'status.json').read_text())
rows = json.loads((out / 'results.json').read_text())
assert status['engineering_smoke'] == 'passed'
assert status['r2_r3_first_token_equal'] is True
assert [row['condition'] for row in rows] == ['R2', 'R3', 'R4']
assert all(row['tokens'] for row in rows)
assert rows[0]['metadata']['backend'] == 'vllm_selective_flex_0.19.1'
print('GEMMA4_SELECTIVE_SMOKE_AUDIT_PASSED')
PY
