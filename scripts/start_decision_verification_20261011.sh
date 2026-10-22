#!/usr/bin/env bash
set -o pipefail
cd /data2/gaojc/projects/contextual-drag-extend || exit 1
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/launch_generation_diagnostics_20261005.py --decision-verification 2>&1 | tee outputs/generation-diagnostics-20261005/decision_verification/runner.log
