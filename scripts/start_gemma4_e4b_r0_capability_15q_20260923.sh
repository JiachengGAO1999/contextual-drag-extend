#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
LOG=outputs/game24-gemma4-e4b-r0-capability-15q-20260923.log
PID=outputs/game24-gemma4-e4b-r0-capability-15q-20260923.pid
test ! -e "$LOG"
test ! -e "$PID"
nohup bash scripts/run_gemma4_e4b_r0_capability_15q_20260923.sh >"$LOG" 2>&1 < /dev/null &
pid=$!
echo "$pid" >"$PID"
echo "STARTED pid=$pid log=$LOG"
