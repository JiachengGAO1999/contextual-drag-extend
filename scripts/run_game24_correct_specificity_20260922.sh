#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
RUN=game24-correct-draft-specificity-qwen3-8b-20260922
PREP=game24-correct-specificity-prepared-20260921

export CUDA_VISIBLE_DEVICES=4 SC_GPU=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
export SC_VLLM_DECODE_LAYOUT=per_request SC_FLEX_NO_CUDAGRAPHS=1
export SC_FLEX_COMPILE_LIMIT=1024 CUDA_LAUNCH_BLOCKING=1
export PYTHONPATH="$PWD"

test -x "$PY"
test -f /data2/huangrj/models/qwen3-8b/config.json
test -f "outputs/$PREP/manifest.json"
test ! -e "outputs/$RUN"

"$PY" - <<'PY'
import json
from collections import Counter
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "outputs/game24-correct-specificity-prepared-20260921/manifest.json").read_text())
assert len(manifest) == 32, len(manifest)
assert Counter(row["condition"] for row in manifest) == {"C_FULL": 16, "C_LATE": 16}
assert len({row["bundle"] for row in manifest}) == 16
pairs = []
for row in manifest:
    bundle = root / row["bundle"]
    pair = root / row["pair"]
    assert bundle.is_file(), bundle
    assert pair.is_file(), pair
    pairs.append(json.loads(pair.read_text()))
assert len({str(row["id"]) for row in pairs}) == 8
assert {row["source_model"] for row in pairs} == {"Qwen3_8B_Thinking", "Qwen3_32B"}
assert all(row["correct_source_correctness"] is True for row in pairs)
assert all(row["correct_source_finish_reason"] == "eos" for row in pairs)
assert all(row["correct_source_thinking_status"] == "parsable_thinking" for row in pairs)
print("FROZEN_MANIFEST_PASS requests=32 questions=8 seeds=2 conditions=C_FULL,C_LATE", flush=True)
PY

restore() {
    code=$?
    trap - EXIT
    echo "SPECIFICITY_EXIT=$code RESTORING_GPU4_RESIDENT $(date -Is)"
    unset SC_MATH_RUN SC_PREP SC_TASK SC_TOTAL
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
        "nvidia-smi", "--id=4", "--query-gpu=memory.used",
        "--format=csv,noheader,nounits",
    ], text=True).strip())
    if used < 1024:
        break
    time.sleep(1)
assert used < 1024, f"GPU4 still uses {used} MiB; no unrelated process was touched"
print("OWN_RESIDENT_STOPPED_GPU4_FREE", flush=True)
PY

export SC_MATH_RUN="$RUN" SC_PREP="$PREP" SC_TASK=game24 SC_TOTAL=32
"$PY" scripts/retry_math_external_20260920.py
