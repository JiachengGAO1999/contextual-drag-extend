#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT=/data2/gaojc/projects/contextual-drag-extend
PY=/data2/gaojc/envs/contextual-drag-vllm/bin/python
MODEL=/data2/huangrj/models/qwen3-8b
INPUT=/data2/gaojc/data/game24-tot-8050e67/24.csv
MANIFEST="$PROJECT/scripts/baseline_screen_manifest_20260918_batch02.json"
OUTPUT="$PROJECT/outputs/game24-baseline-screen-vllm-20260918-batch02"
LOG="$PROJECT/outputs/baseline-acquisition-a100-20260918-batch02.log"
EXIT_MARKER="$PROJECT/outputs/baseline-acquisition-a100-20260918-batch02.exit"
GPU=4
EXTERNAL_LARGE_MB=8192

mkdir -p "$PROJECT/outputs"
if [[ -e "$OUTPUT" ]]; then
  echo "REFUSE_EXISTING_OUTPUT $OUTPUT" >&2
  exit 2
fi
[[ -f "$INPUT" ]] || { echo "MISSING_INPUT $INPUT" >&2; exit 3; }
[[ -d "$MODEL" ]] || { echo "MISSING_MODEL $MODEL" >&2; exit 4; }
[[ -f "$MANIFEST" ]] || { echo "MISSING_MANIFEST $MANIFEST" >&2; exit 5; }

export CUDA_VISIBLE_DEVICES=$GPU
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export TMPDIR=/data2/gaojc/tmp
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
unset SC_VLLM_DECODE_LAYOUT
unset VLLM_ATTENTION_BACKEND

is_external_large_process_present() {
  while IFS=',' read -r pid memory; do
    pid="${pid//[[:space:]]/}"
    memory="${memory//[[:space:]]/}"
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    [[ "$memory" =~ ^[0-9]+$ ]] || continue
    [[ "$memory" -ge "$EXTERNAL_LARGE_MB" ]] || continue
    user="$(ps -o user= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)"
    if [[ -n "$user" && "$user" != "gaojc" ]]; then
      echo "EXTERNAL_LARGE_PROCESS pid=$pid user=$user memory_mb=$memory" >> "$LOG"
      return 0
    fi
  done < <(nvidia-smi --id=$GPU --query-compute-apps=pid,used_memory --format=csv,noheader,nounits 2>/dev/null || true)
  return 1
}

echo "QUEUE_STARTED $(date -Is) gpu=$GPU manifest=$MANIFEST" >> "$LOG"
while is_external_large_process_present; do
  echo "WAIT_EXTERNAL_GPU_OWNER $(date -Is)" >> "$LOG"
  sleep 30
done

resident_pid="$(pgrep -u "$(id -u)" -f '^/data2/gaojc/envs/contextual-drag-vllm/bin/python -m selective_context.phase0.vllm_resident$' | head -n 1 || true)"
if [[ -n "$resident_pid" ]]; then
  resident_children="$(pgrep -P "$resident_pid" || true)"
  echo "STOP_OWN_RESIDENT pid=$resident_pid $(date -Is)" | tee -a "$LOG"
  # The exact resident and its direct worker/resource-tracker children are
  # owned by this job; no unrelated PID is touched.
  kill "$resident_pid" $resident_children 2>/dev/null || true
  for _ in $(seq 1 120); do
    alive=0
    for pid in $resident_pid $resident_children; do
      if kill -0 "$pid" 2>/dev/null; then alive=1; break; fi
    done
    if [[ "$alive" -eq 0 ]]; then break; fi
    sleep 1
  done
  alive=0
  for pid in $resident_pid $resident_children; do
    if kill -0 "$pid" 2>/dev/null; then alive=1; break; fi
  done
  if [[ "$alive" -ne 0 ]]; then
    echo "RESIDENT_DID_NOT_EXIT pid=$resident_pid" | tee -a "$LOG"
    exit 6
  fi
fi

used=999999
for _ in $(seq 1 60); do
  used="$(nvidia-smi --id=$GPU --query-gpu=memory.used --format=csv,noheader,nounits | tr -d '[:space:]')"
  if [[ "$used" =~ ^[0-9]+$ ]] && [[ "$used" -le "$EXTERNAL_LARGE_MB" ]]; then break; fi
  sleep 1
done
if ! [[ "$used" =~ ^[0-9]+$ ]] || [[ "$used" -gt "$EXTERNAL_LARGE_MB" ]]; then
  echo "GPU_NOT_READY_AFTER_OWN_RESIDENT_STOP memory_mb=$used" | tee -a "$LOG"
  exit 7
fi

status=0
set +e
"$PY" "$PROJECT/scripts/baseline_screen_vllm_20260917.py" \
  --model "$MODEL" \
  --input "$INPUT" \
  --manifest "$MANIFEST" \
  --source-revision 8050e67d0e3a0fddc424d7fa5801538722a4c4cc \
  --output "$OUTPUT" \
  --max-num-seqs 16 \
  --max-num-batched-tokens 8192 \
  --gpu-memory-utilization 0.85 2>&1 | tee -a "$LOG"
status=${PIPESTATUS[0]}
set -e
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'exit_code=%s\n' "$status"
} > "$EXIT_MARKER"
echo "BASELINE_ACQUISITION_EXIT status=$status $(date -Is)" | tee -a "$LOG"

echo "RESTORE_SELECTIVE_RESIDENT $(date -Is)" | tee -a "$LOG"
export SC_VLLM_DECODE_LAYOUT=per_request
exec "$PY" -m selective_context.phase0.vllm_resident >> "$LOG" 2>&1
