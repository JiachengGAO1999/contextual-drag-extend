#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/gemma4-vllm019/bin/python
MODEL=/data2/gaojc/models/gemma-4-E4B-it
PAIR=outputs/game24-batch02-validation-20260920-prepared/585579aed1c5241bcec55697.pair.json
OUT=outputs/game24-gemma4-e4b-hf-selective-smoke-20260923

test -x "$PY"
test -f "$MODEL/model.safetensors"
test -f "$PAIR"
test ! -e "$OUT"
used=$(nvidia-smi --id=1 --query-gpu=memory.used --format=csv,noheader,nounits)
test "$used" -lt 1024

export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export PYTHONPATH="$PWD"

"$PY" scripts/smoke_selective_target_model_hf.py \
  --model "$MODEL" \
  --pair "$PAIR" \
  --output "$OUT" \
  --max-new-tokens 8 \
  --enable-thinking
