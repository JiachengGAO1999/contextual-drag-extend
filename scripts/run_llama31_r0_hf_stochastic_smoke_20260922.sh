#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data/zhaoyi/liujunyuan/models/Meta-Llama-3.1-8B-Instruct
PREP=outputs/game24-target-generalization-15q-llama31-prepared-20260922
OUT=outputs/game24-llama31-r0-hf-temp06-2048-smoke-20260922.json

export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export CUDA_LAUNCH_BLOCKING=1 PYTHONPATH="$PWD"
test -x "$PY"
test -f "$MODEL/config.json"
test -f "$PREP/manifest.json"
test ! -e "$OUT"

restore() {
    code=$?
    trap - EXIT
    echo "HF_STOCHASTIC_SMOKE_EXIT=$code RESTORING_GPU4_RESIDENT $(date -Is)"
    exec "$PY" -m selective_context.phase0.vllm_resident
}
trap restore EXIT

"$PY" - <<'PY'
import os, subprocess, time, psutil
expected = ["/data2/gaojc/envs/contextual-drag-vllm/bin/python", "-m", "selective_context.phase0.vllm_resident"]
matches = [p for p in psutil.process_iter(["cmdline", "uids"])
           if p.info["uids"].real == os.getuid() and p.info["cmdline"] == expected]
assert len(matches) == 1, len(matches)
parent = matches[0]
assert parent.environ().get("CUDA_VISIBLE_DEVICES") == "4"
procs = [parent] + parent.children(recursive=True)
parent.terminate()
for child in procs[1:]:
    try: child.terminate()
    except psutil.NoSuchProcess: pass
_, alive = psutil.wait_procs(procs, timeout=45)
assert not alive, [p.pid for p in alive]
for _ in range(45):
    used = int(subprocess.check_output(["nvidia-smi", "--id=4", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True).strip())
    if used < 1024: break
    time.sleep(1)
assert used < 1024, used
print("OWN_RESIDENT_STOPPED_GPU4_FREE", flush=True)
PY

"$PY" scripts/smoke_llama_r0_ordinary_vllm.py --model "$MODEL" --prepared "$PREP" \
  --backend hf --temperature 0.6 --max-new-tokens 2048 --output "$OUT"
