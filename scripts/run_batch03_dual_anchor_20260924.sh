#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT=/data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
OUTPUT="$PROJECT/outputs/game24-batch03-dual-anchor-20260924"
LOG="$PROJECT/outputs/batch03-dual-anchor-20260924.log"

cd "$PROJECT"
mkdir -p outputs
test ! -e "$OUTPUT"
test ! -e "$LOG"
test -f scripts/baseline_manifest_batch03_20260919.json
test -f scripts/baseline_screen_vllm_20260917.py
test -f /data2/gaojc/data/game24-tot-8050e67/24.csv
test -f /data2/huangrj/models/qwen3-8b/config.json
test -f /data/zhaoyi/liujunyuan/models/Qwen3-32B/config.json

export CUDA_VISIBLE_DEVICES=4
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
export BATCH03_PYTHON="$PY"
unset SC_VLLM_DECODE_LAYOUT VLLM_ATTENTION_BACKEND

exec "$PY" -u scripts/batch03_dual_anchor_20260924.py > "$LOG" 2>&1
