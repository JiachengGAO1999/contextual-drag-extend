#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT=/data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
LOG="$PROJECT/outputs/batch04-dual-anchor-screen-20260925.launch.log"

cd "$PROJECT"
mkdir -p outputs
exec > >(tee -a "$LOG") 2>&1

test -x "$PY"
test -f scripts/baseline_manifest_batch04_20260925.json
test -f scripts/batch04_dual_anchor_screen_20260925.py
test -f scripts/baseline_screen_vllm_20260917.py
test -f /data2/gaojc/data/game24-tot-8050e67/24.csv
test -f /data2/huangrj/models/qwen3-8b/config.json
test -f /data/zhaoyi/liujunyuan/models/Qwen3-32B/config.json
test ! -e outputs/game24-batch04-dual-anchor-screen-20260925

export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
export BATCH04_PYTHON="$PY"
unset SC_VLLM_DECODE_LAYOUT VLLM_ATTENTION_BACKEND

if [[ -f outputs/vllm-resident-startup.json ]]; then
  "$PY" - <<'PY'
import json
from pathlib import Path
p=Path('outputs/vllm-resident-startup.json')
j=json.loads(p.read_text())
assert not (j.get('status')=='authorized_pending' and j.get('kind')=='heldout_screen'), 'Pending heldout screen must be handled first'
PY
fi

restore_resident() {
    code=$?
    trap - EXIT
    resident="$(pgrep -u "$(id -u)" -f '^/data2/gaojc/envs/contextual-drag-vllm/bin/python -m selective_context.phase0.vllm_resident$' | head -n 1 || true)"
    if [[ -z "$resident" ]]; then
        used="$(nvidia-smi --id=4 --query-gpu=memory.used --format=csv,noheader,nounits | tr -d '[:space:]')"
        if [[ "$used" -lt 8192 ]]; then
            echo "BATCH04_EXIT=$code RESTORING_SELECTIVE_VLLM_RESIDENT $(date -Is)"
            export SC_VLLM_DECODE_LAYOUT=per_request
            exec "$PY" -m selective_context.phase0.vllm_resident
        fi
        echo "BATCH04_EXIT=$code RESTORE_REFUSED_GPU4_USED_MIB=$used; no other process will be touched"
    fi
    exit "$code"
}
trap restore_resident EXIT

"$PY" - <<'PY'
import os, subprocess, time, psutil
expected=["/data2/gaojc/envs/contextual-drag-vllm/bin/python","-m","selective_context.phase0.vllm_resident"]
matches=[p for p in psutil.process_iter(["cmdline","uids"]) if p.info["uids"].real==os.getuid() and p.info["cmdline"]==expected]
assert len(matches)==1, f"Expected exactly one owned resident, found {len(matches)}"
parent=matches[0]
assert parent.environ().get("CUDA_VISIBLE_DEVICES")=="4", "Resident is not bound to physical GPU4"
family=[parent]+parent.children(recursive=True)
family_ids={p.pid for p in family}
apps=subprocess.check_output(["nvidia-smi","--id=4","--query-compute-apps=pid","--format=csv,noheader"],text=True)
app_ids={int(x.strip()) for x in apps.splitlines() if x.strip()}
assert app_ids and app_ids <= family_ids, f"GPU4 has unrelated compute processes: {sorted(app_ids-family_ids)}"
print(f"STOP_OWN_RESIDENT pid={parent.pid} gpu4_compute_pids={sorted(app_ids)}",flush=True)
parent.terminate()
for p in family[1:]:
    try: p.terminate()
    except psutil.NoSuchProcess: pass
_,alive=psutil.wait_procs(family,timeout=45)
assert not alive, f"Owned resident did not exit: {[p.pid for p in alive]}"
used=None
for _ in range(90):
    used=int(subprocess.check_output(["nvidia-smi","--id=4","--query-gpu=memory.used","--format=csv,noheader,nounits"],text=True).strip())
    if used<1024: break
    time.sleep(1)
assert used<1024, f"GPU4 did not release owned resident memory: {used} MiB"
print(f"OWN_RESIDENT_STOPPED_GPU4_FREE used_mib={used}",flush=True)
PY

"$PY" -u scripts/batch04_dual_anchor_screen_20260925.py
