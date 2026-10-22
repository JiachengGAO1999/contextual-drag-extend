#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data/zhaoyi/liujunyuan/models/Meta-Llama-3.1-8B-Instruct
PREP=game24-target-generalization-15q-llama31-prepared-20260922
RUN=game24-llama31-8b-r0-capability-15q-hf-20260922

export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=per_request SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=1024
export PYTHONPATH="$PWD"

test -x "$PY"
test -f "$MODEL/config.json"
test -f "outputs/$PREP/manifest.json"
test ! -e "outputs/$RUN"

"$PY" - <<'PY'
import json
from collections import Counter
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "outputs/game24-target-generalization-15q-llama31-prepared-20260922/manifest.json").read_text())
assert len(manifest) == 120, len(manifest)
assert Counter(row["condition"] for row in manifest) == {"R0": 30, "R2": 30, "R3": 30, "R4": 30}
r0 = [row for row in manifest if row["condition"] == "R0"]
pairs = [json.loads((root / row["pair"]).read_text()) for row in r0]
assert len({str(row["id"]) for row in pairs}) == 15
assert Counter(row["stratum"] for row in pairs) == {"dual_anchor_initial7": 14, "dual_anchor_batch02": 16}
assert all(row["audit_status"] == "substantive_failed" for row in pairs)
assert all((root / row["bundle"]).is_file() for row in r0)
print("FROZEN_GATE_PASS requests=30 questions=15 seeds=2 condition=R0", flush=True)
PY

restore() {
    code=$?
    trap - EXIT
    echo "LLAMA_GATE_EXIT=$code RESTORING_GPU4_RESIDENT $(date -Is)"
    exec "$PY" -m selective_context.phase0.vllm_resident
}
trap restore EXIT

"$PY" - <<'PY'
import os
import subprocess
import time
import psutil

expected = [
    "/data2/gaojc/envs/contextual-drag-vllm/bin/python",
    "-m",
    "selective_context.phase0.vllm_resident",
]
matches = [
    process for process in psutil.process_iter(["cmdline", "uids"])
    if process.info["uids"].real == os.getuid() and process.info["cmdline"] == expected
]
assert len(matches) == 1, f"expected exactly one owned resident, found {len(matches)}"
parent = matches[0]
assert parent.environ().get("CUDA_VISIBLE_DEVICES") == "4"
children = parent.children(recursive=True)
assert all(child.username() == parent.username() for child in children)
parent.terminate()
for child in children:
    try:
        child.terminate()
    except psutil.NoSuchProcess:
        pass
_, alive = psutil.wait_procs([parent] + children, timeout=45)
assert not alive, [process.pid for process in alive]
for _ in range(45):
    used = int(subprocess.check_output([
        "nvidia-smi", "--id=4", "--query-gpu=memory.used", "--format=csv,noheader,nounits",
    ], text=True).strip())
    if used < 1024:
        break
    time.sleep(1)
assert used < 1024, f"GPU4 still uses {used} MiB; no unrelated process was touched"
print("OWN_RESIDENT_STOPPED_GPU4_FREE", flush=True)
PY

"$PY" scripts/run_target_r0_capability.py \
  --prepared "outputs/$PREP" \
  --output "outputs/$RUN" \
  --model "$MODEL" \
  --model-alias Llama_3.1_8B_Instruct \
  --task game24 \
  --expected-questions 15 \
  --seeds 927001 927002 \
  --batch-size 1 \
  --gpu-memory-utilization 0.65 \
  --max-new-tokens 32768 \
  --max-model-len 32768 \
  --backend hf
