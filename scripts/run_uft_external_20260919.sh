#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1 SC_VLLM_DECODE_LAYOUT=per_request
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
test ! -e outputs/game24-uft-external-20q-20260919
test -f /data2/huangrj/models/qwen3-8b/config.json
"$PY" - <<'PY'
import subprocess,psutil
p=psutil.Process(930390)
assert abs(p.create_time()-1789783061.78)<.1
assert p.status()==psutil.STATUS_STOPPED, 'Original32B task must remain stopped'
used=int(subprocess.check_output(['nvidia-smi','--id=4','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
assert used<1000, 'GPU4 occupied; stop without touching other processes'
PY
"$PY" scripts/prepare_uft_external_20260919.py --tokenize
exec "$PY" scripts/run_uft_external_20260919.py
