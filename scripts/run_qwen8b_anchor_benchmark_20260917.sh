#!/usr/bin/env bash
set -uo pipefail
cd /data2/gaojc/projects/contextual-drag-extend || exit 1
export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
unset SC_VLLM_DECODE_LAYOUT VLLM_ATTENTION_BACKEND
py=/data2/gaojc/envs/contextual-drag-vllm/bin/python
echo "ANCHOR_BENCHMARK_START $(date -Is)"
"$py" -m selective_context.phase0.anchor_throughput \
  --model /data2/huangrj/models/qwen3-8b --alias Qwen3_8B \
  --output outputs/ordinary-vllm-qwen8b-benchmark-20260917
status=$?
echo "ANCHOR_BENCHMARK_EXIT $status $(date -Is)"
printf '%s\n' "$status" > ordinary_vllm_qwen8b_benchmark_20260917.exit
# Restore the authorized selective engine; paused startup queue does not generate.
export SC_VLLM_DECODE_LAYOUT=per_request
exec "$py" -m selective_context.phase0.vllm_resident
