#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=per_request SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=1024 CUDA_LAUNCH_BLOCKING=1
export PYTHONPATH=/data2/gaojc/projects/contextual-drag-extend
"$PY" - <<'PY'
import json, subprocess
from pathlib import Path
uuid='GPU-bb740995-3c17-c363-1553-ef7ac3907eca'
card=subprocess.check_output(['nvidia-smi','-i','4','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip().split(',')
assert card[0].strip()==uuid and int(card[1])<1024 and int(card[2])<=5, card
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
assert uuid not in apps, 'GPU4 became occupied; no process touched'
p=Path('outputs/vllm-resident-startup.json')
assert not p.exists() or json.loads(p.read_text()).get('status')!='authorized_pending', 'Pending startup job must not run'
print('GPU4_IDLE_CONFIRMED_RESIDENT_ONLY',flush=True)
PY
exec "$PY" -m selective_context.phase0.vllm_resident
