#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT=/data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data2/huangrj/models/qwen3-8b
INPUT=/data2/gaojc/data/game24-tot-8050e67/24.csv
MANIFEST="$PROJECT/scripts/baseline_screen_manifest_20260917.json"
OUTPUT="$PROJECT/outputs/game24-baseline-screen-vllm-20260917-retry1"
LOG="$PROJECT/outputs/baseline-screen-launch-20260917.log"
EXIT_MARKER="$PROJECT/outputs/baseline-screen-vllm-20260917.exit"

mkdir -p "$PROJECT/outputs"
if [[ -e "$OUTPUT" ]]; then
  echo "REFUSE_EXISTING_OUTPUT $OUTPUT" >&2
  exit 2
fi
[[ -f "$INPUT" ]] || { echo "MISSING_INPUT $INPUT" >&2; exit 3; }
[[ -d "$MODEL" ]] || { echo "MISSING_MODEL $MODEL" >&2; exit 4; }
[[ -f "$MANIFEST" ]] || { echo "MISSING_MANIFEST $MANIFEST" >&2; exit 5; }
rm -f "$EXIT_MARKER"

export CUDA_VISIBLE_DEVICES=4
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
unset SC_VLLM_DECODE_LAYOUT
unset VLLM_ATTENTION_BACKEND

resident_pid="$(pgrep -u "$(id -u)" -f '^/data2/gaojc/envs/contextual-drag-vllm/bin/python -m selective_context.phase0.vllm_resident$' | head -n 1 || true)"
if [[ -z "$resident_pid" ]]; then
  echo "REFUSE_UNKNOWN_GPU4_OWNER no exact project selective resident found" >&2
  exit 6
fi
echo "STOP_SELECTIVE_RESIDENT pid=$resident_pid" | tee -a "$LOG"
kill "$resident_pid"
for _ in $(seq 1 120); do
  if ! kill -0 "$resident_pid" 2>/dev/null; then break; fi
  sleep 1
done
if kill -0 "$resident_pid" 2>/dev/null; then
  echo "RESIDENT_DID_NOT_EXIT pid=$resident_pid" >&2
  exit 7
fi

status=0
set +e
"$PY" "$PROJECT/scripts/baseline_screen_vllm_20260917.py" \
  --model "$MODEL" --input "$INPUT" --manifest "$MANIFEST" \
  --source-revision 8050e67d0e3a0fddc424d7fa5801538722a4c4cc \
  --output "$OUTPUT" 2>&1 | tee -a "$LOG"
status=${PIPESTATUS[0]}
set -e
date -u +%Y-%m-%dT%H:%M:%SZ > "$EXIT_MARKER"
printf 'exit_code=%s\n' "$status" >> "$EXIT_MARKER"

echo "BASELINE_SCREEN_EXIT status=$status" | tee -a "$LOG"
if [[ "$status" -ne 0 ]]; then
  echo "RESTORE_SELECTIVE_RESIDENT_AFTER_FAILURE" | tee -a "$LOG"
  export SC_VLLM_DECODE_LAYOUT=per_request
  exec "$PY" -m selective_context.phase0.vllm_resident >> "$LOG" 2>&1
fi

echo "RESTORE_SELECTIVE_RESIDENT" | tee -a "$LOG"
export SC_VLLM_DECODE_LAYOUT=per_request
exec "$PY" -m selective_context.phase0.vllm_resident >> "$LOG" 2>&1
