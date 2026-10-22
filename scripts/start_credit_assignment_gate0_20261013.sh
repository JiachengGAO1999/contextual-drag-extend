#!/usr/bin/env bash
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/start_credit_assignment_gate0_20261013.py 2>&1 | tee outputs/credit-assignment-gate0-20261013/console.log
