#!/usr/bin/env bash
set -Eeuo pipefail

cd /data2/gaojc/tmp/math-external-16q-20260920
GATE=outputs/game24-gemma4-e4b-r0-capability-15q-20260923

while true; do
    if test -f "$GATE/gate_early_stop.json"; then
        echo "R0_GATE_FAILED; R2/R3 NOT STARTED"
        exit 0
    fi
    if test -f "$GATE/gate_decision.json" && test -f "$GATE/completion.json"; then
        break
    fi
    sleep 30
done

/data2/gaojc/envs/gemma4-vllm019/bin/python - <<'PY'
import json
from pathlib import Path
gate = Path("outputs/game24-gemma4-e4b-r0-capability-15q-20260923")
decision = json.loads((gate / "gate_decision.json").read_text())
completion = json.loads((gate / "completion.json").read_text())
assert decision["status"] == "passed", decision
assert decision["total"] == 30 and completion["completed"] == 30
print(f"R0_GATE_PASSED correct={decision['correct']}/30 normal_parseable={decision['normal_parseable']}/30", flush=True)
PY

# The R0 wrapper restores our resident server immediately after writing its
# completion files.  Give that process a short window to finish loading.
sleep 30
exec bash scripts/run_gemma4_e4b_r2_r3_15q_20260923.sh

