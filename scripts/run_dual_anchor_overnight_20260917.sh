#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
unset SC_VLLM_DECODE_LAYOUT VLLM_ATTENTION_BACKEND
test ! -e outputs/game24-dual-anchor-20q-20260917
test -f /data2/gaojc/data/game24-tot-8050e67/24.csv
test -f /data2/huangrj/models/qwen3-8b/config.json
test -f /data/zhaoyi/liujunyuan/models/Qwen3-32B/config.json
"$PY" - <<'PY'
import os, psutil, json, time, subprocess
from pathlib import Path
startup=Path('outputs/vllm-resident-startup.json')
if startup.exists():
    assert json.loads(startup.read_text()).get('status') != 'authorized_pending', 'Unexpected pending resident job'
expected=['/data2/gaojc/envs/contextual-drag-vllm/bin/python','-m','selective_context.phase0.vllm_resident']
matches=[p for p in psutil.process_iter(['cmdline','uids']) if p.info['uids'].real==os.getuid() and p.info['cmdline']==expected]
assert len(matches)<=1, 'Multiple residents; stop without fallback'
if matches:
    parent=matches[0]; children=parent.children(recursive=True)
    parent.terminate()
    for p in children:
        try: p.terminate()
        except psutil.NoSuchProcess: pass
    for _ in range(60):
        alive=[]
        for p in [parent]+children:
            try:
                if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE: alive.append(p)
            except psutil.NoSuchProcess: pass
        if not alive: break
        time.sleep(1)
    assert not alive, 'Own resident did not exit'
for _ in range(30):
    used=int(subprocess.check_output(['nvidia-smi','--id=4','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
    if used<1024: break
    time.sleep(1)
assert used<1024, 'GPU4 not free after resident stop; no other process is touched'
print('OWN_RESIDENT_STOPPED',flush=True)
PY
set +e
"$PY" scripts/dual_anchor_overnight_20260917.py
status=$?
set -e
printf '%s\n' "$status" > outputs/dual-anchor-overnight-20260917.exit
echo "ACQUISITION_EXIT=$status RESTORING_SELECTIVE_RESIDENT $(date -Is)"
export SC_VLLM_DECODE_LAYOUT=per_request
exec "$PY" -m selective_context.phase0.vllm_resident
