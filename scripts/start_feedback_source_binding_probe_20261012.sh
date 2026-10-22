#!/usr/bin/env bash
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
OUT=outputs/generation-diagnostics-20261005/public_verification_preview/source_binding_probe
/data2/gaojc/envs/contextual-drag-vllm/bin/python -u scripts/run_feedback_source_binding_probe_20261012.py --launch 2>&1 | tee "$OUT/console.log"
