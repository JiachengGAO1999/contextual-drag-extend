#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data/zhaoyi/liujunyuan/models/Qwen3-32B
PAIR=outputs/game24-batch02-validation-20260920-prepared/585579aed1c5241bcec55697.pair.json
OUT=outputs/selective-target-smoke-qwen3-32b-20260922
CACHE=/tmp/gaojc-torchinductor-qwen32-smoke-20260922

test -x "$PY"
test -f "$MODEL/config.json"
test -f "$PAIR"
test ! -e "$OUT"

used=$(nvidia-smi --id=0 --query-gpu=memory.used --format=csv,noheader,nounits)
test "$used" -lt 1024
mkdir -p "$CACHE"

export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=per_request SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=128 CUDA_LAUNCH_BLOCKING=1
export TORCHINDUCTOR_CACHE_DIR="$CACHE" PYTHONPATH="$PWD"

"$PY" scripts/smoke_selective_target_model.py \
  --model "$MODEL" \
  --pair "$PAIR" \
  --output "$OUT" \
  --max-model-len 8192 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.94 \
  --max-new-tokens 16
