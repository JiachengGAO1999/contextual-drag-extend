#!/usr/bin/env bash
# Only hand over after this named validation exits successfully.
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
while [ ! -f vllm_decode_validation_20260917.exit ]; do sleep 15; done
if [ "$(cat vllm_decode_validation_20260917.exit)" != 0 ]; then
  echo 'Validation failed; no vLLM resident launched.'
  exit 1
fi
py=/data2/gaojc/envs/contextual-drag-vllm/bin/python
"$py" - <<'PY'
import json
from pathlib import Path
p=Path('outputs/vllm-complete-decode-kernel-20260917')
assert json.loads((p/'summary.json').read_text())['n']==9
assert len((p/'results.jsonl').read_text().splitlines())==9
PY
# The validation wrapper restores our own HF resident; replace only that process.
for attempt in $(seq 1 30); do
  resident=$(pgrep -u "$(id -u)" -f '^/data2/gaojc/envs/contextual-drag-smoke/bin/python -i /data2/gaojc/projects/contextual-drag-extend/qwen3_resident.py$' || true)
  if [ -n "$resident" ]; then kill "$resident"; break; fi
  sleep 2
done
if [ -z "${resident:-}" ]; then echo 'Expected HF resident not found; inspect GPU before launch.'; exit 1; fi
while kill -0 "$resident" 2>/dev/null; do sleep 1; done
export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1 SC_VLLM_DECODE_LAYOUT=per_request
exec "$py" -m selective_context.phase0.vllm_resident
