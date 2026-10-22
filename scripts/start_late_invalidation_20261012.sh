#!/usr/bin/env bash
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/run_late_invalidation_20261012.py --launch 2>&1 | tee outputs/late-invalidation-20261012/console.log
