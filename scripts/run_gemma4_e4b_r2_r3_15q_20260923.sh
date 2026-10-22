#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/gemma4-vllm019/bin/python
RESIDENT_PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data2/gaojc/models/gemma-4-E4B-it
PREP=game24-target-generalization-15q-gemma4-e4b-prepared-20260923
R0=game24-gemma4-e4b-r0-capability-15q-20260923
RUN=game24-gemma4-e4b-r2-r3-15q-20260923

export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1
export TMPDIR=/data2/gaojc/tmp PYTHONPATH="$PWD"
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=per_request SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=1024 CUDA_LAUNCH_BLOCKING=1

test -x "$PY"
test -f "$MODEL/model.safetensors"
test -f "outputs/$PREP/manifest.json"
test -f "outputs/$R0/gate_decision.json"
test -f "outputs/$R0/completion.json"
test ! -e "outputs/$RUN"

restore() {
    code=$?
    trap - EXIT
    echo "GEMMA4_R2_R3_EXIT=$code RESTORING_GPU4_RESIDENT $(date -Is)"
    exec "$RESIDENT_PY" -m selective_context.phase0.vllm_resident
}
trap restore EXIT

"$RESIDENT_PY" - <<'PY'
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

