#!/usr/bin/env bash
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
OUT=outputs/generation-diagnostics-20261005
# The first semantic screen is already running. Wait without reserving the GPU.
while "$PY" -c 'import json,sys; sys.exit(0 if json.load(open("outputs/generation-diagnostics-20261005/budget.json")).get("active") else 1)'; do
    sleep 5
done
# budget.close() precedes launcher cleanup by a few moments; wait for its lock.
"$PY" -c 'import fcntl; f=open("outputs/generation-diagnostics-20261005/launcher.lock","a"); fcntl.flock(f,fcntl.LOCK_EX); fcntl.flock(f,fcntl.LOCK_UN)'
if [ -f "$OUT/semantic_failure.json" ]; then
    echo 'Previous semantic stage failed; continuation not launched.'
    exit 1
fi
if ! "$PY" -c 'import json,sys; s=json.load(open("outputs/generation-diagnostics-20261005/semantic_summary.json")); sys.exit(0 if s.get("status")=="semantic_signal_requires_localization" else 1)'; then
    echo 'Semantic screen did not pass; continuation stopped without loading a model.'
    exit 0
fi
"$PY" -u scripts/launch_generation_diagnostics_20261005.py --semantic --localize 2>&1 | tee "$OUT/semantic_launch.log"
