#!/usr/bin/env bash
set -Eeuo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
mkdir -p outputs/generation-diagnostics-20261005
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/launch_generation_diagnostics_20261005.py 2>&1 | tee -a outputs/generation-diagnostics-20261005/launch.log
