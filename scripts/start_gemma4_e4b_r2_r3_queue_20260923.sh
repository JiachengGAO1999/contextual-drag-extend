#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
LOG=outputs/game24-gemma4-e4b-r2-r3-queue-20260923.log
PID=outputs/game24-gemma4-e4b-r2-r3-queue-20260923.pid
test ! -e "$LOG"
test ! -e "$PID"
nohup bash scripts/queue_gemma4_e4b_r2_r3_after_gate_20260923.sh >"$LOG" 2>&1 < /dev/null &
pid=$!
echo "$pid" >"$PID"
echo "QUEUED pid=$pid log=$LOG"
