#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/tmp/math-external-16q-20260920
export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1 SC_VLLM_DECODE_LAYOUT=per_request
export PYTHONPATH="$PWD"
exec /data2/gaojc/envs/contextual-drag-vllm/bin/python scripts/run_math_external_20260920.py
