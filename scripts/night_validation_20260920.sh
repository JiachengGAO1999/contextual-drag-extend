#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/tmp/math-external-16q-20260920
export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1 SC_VLLM_DECODE_LAYOUT=per_request
export SC_FLEX_NO_CUDAGRAPHS=1 SC_FLEX_COMPILE_LIMIT=1024 CUDA_LAUNCH_BLOCKING=1
export PYTHONPATH="$PWD"
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
restore() {
    code=$?
    trap - EXIT
    echo "QUEUE_EXIT=$code $(date -Is); restoring GPU4 resident"
    unset SC_MATH_RESUME SC_MATH_RUN SC_PREP SC_TASK SC_TOTAL
    exec "$PY" -m selective_context.phase0.vllm_resident
}
trap restore EXIT
echo "APPROVED_LIMIT=176 ACTUAL_PENDING=168 $(date -Is)"
export SC_MATH_RESUME=1 SC_MATH_RUN=math-external-16q-20260920-retry3
"$PY" scripts/retry_math_external_20260920.py > outputs/math-external-16q-20260920-retry3/night-resume.log 2>&1
echo "MATH_COMPLETE $(date -Is)"
unset SC_MATH_RESUME
export SC_TASK=game24 SC_TOTAL=64 SC_PREP=game24-batch02-validation-20260920-prepared
export SC_MATH_RUN=game24-batch02-validation-20260920
"$PY" scripts/retry_math_external_20260920.py > outputs/game24-batch02-validation-20260920-night.log 2>&1
echo "GAME24_COMPLETE $(date -Is)"
