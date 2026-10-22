#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR=/data2/gaojc/models/gemma-4-E4B-it
TARGET="$MODEL_DIR/model.safetensors"
BACKUP="$MODEL_DIR/model.safetensors.scp-partial-20260923"
OUTPUT_ROOT=/data2/gaojc/tmp/math-external-16q-20260920/outputs
LOG="$OUTPUT_ROOT/gemma-modelscope-download-20260923.log"
COMPLETION="$OUTPUT_ROOT/gemma-modelscope-download-20260923-completion.txt"
SESSION=gemma-modelscope-download-20260923
REMOTE_SCRIPT=/data2/gaojc/tmp/math-external-16q-20260920/scripts/download_gemma_e4b_modelscope_20260923.sh
URL=https://modelscope.cn/models/google/gemma-4-E4B-it/resolve/master/model.safetensors
EXPECTED_SIZE=15992595884
EXPECTED_SHA256=cfbd3d2f1cd71bd471c37fe2bf8546d5028d41e5736f64e1ca6c6b8893125503

if [[ "${1:-}" == "--worker" ]]; then
  exec >"$LOG" 2>&1
  echo "START_UTC $(date -u +%FT%TZ)"
  aria2c \
    --continue=true \
    --max-connection-per-server=8 \
    --split=8 \
    --min-split-size=8M \
    --file-allocation=none \
    --auto-file-renaming=false \
    --summary-interval=30 \
    --dir="$MODEL_DIR" \
    --out=model.safetensors \
    "$URL"
  actual_size=$(stat -c %s "$TARGET")
  actual_sha256=$(sha256sum "$TARGET" | awk '{print $1}')
  [[ "$actual_size" == "$EXPECTED_SIZE" ]]
  [[ "$actual_sha256" == "$EXPECTED_SHA256" ]]
  {
    echo "STATUS complete"
    echo "END_UTC $(date -u +%FT%TZ)"
    echo "SIZE $actual_size"
    echo "SHA256 $actual_sha256"
  } >"$COMPLETION"
  exit 0
fi

resolved_target=$(readlink -f "$TARGET")
[[ "$resolved_target" == "$TARGET" ]]
mkdir -p "$MODEL_DIR" "$OUTPUT_ROOT"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "ERROR session already exists: $SESSION" >&2
  exit 2
fi

if [[ -f "$TARGET" ]]; then
  if [[ -e "$BACKUP" ]]; then
    echo "ERROR backup already exists: $BACKUP" >&2
    exit 3
  fi
  mv "$TARGET" "$BACKUP"
fi

rm -f "$COMPLETION"
tmux new-session -d -s "$SESSION" "bash '$REMOTE_SCRIPT' --worker"
echo "STARTED $SESSION"
[[ -f "$BACKUP" ]] && stat -c 'BACKUP %s %y' "$BACKUP" || true
