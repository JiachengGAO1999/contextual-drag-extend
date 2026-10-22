#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/gemma4-vllm019/bin/python
MODEL=/data2/gaojc/models/gemma-4-E4B-it
PREP=game24-target-generalization-15q-gemma4-e4b-prepared-20260923
R0=game24-gemma4-e4b-r0-capability-15q-20260923
RUN=game24-gemma4-e4b-r2-r3-15q-20260923

export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1
export TMPDIR=/data2/gaojc/tmp PYTHONPATH="$PWD"

test -x "$PY"
test -f "$MODEL/model.safetensors"
test -f "outputs/$PREP/manifest.json"
test -f "outputs/$R0/gate_decision.json"
test -f "outputs/$R0/completion.json"
test ! -e "outputs/$RUN"

# Gemma used about 16 GiB in the completed R0 run.  Permit co-scheduling only
# while at least 48 GiB remains free on this 80 GiB card.
used=$(nvidia-smi --id=4 --query-gpu=memory.used --format=csv,noheader,nounits)
test "$used" -lt 32768
echo "SHARED_GPU4_PREFLIGHT used_mib=$used required_headroom_mib=49152"
nvidia-smi --id=4 --query-compute-apps=pid,used_memory --format=csv,noheader,nounits

"$PY" scripts/run_target_r2_r3.py \
  --prepared "outputs/$PREP" \
  --r0-gate "outputs/$R0" \
  --output "outputs/$RUN" \
  --model "$MODEL" \
  --model-alias Gemma_4_E4B_it_Thinking \
  --task game24 \
  --expected-questions 15 \
  --seeds 927001 927002 \
  --batch-size 1 \
  --max-new-tokens 32768 \
  --max-model-len 32768 \
  --backend hf \
  --enable-thinking

