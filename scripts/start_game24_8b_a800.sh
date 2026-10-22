#!/usr/bin/env bash
set -euo pipefail
cd /data/gaojc/projects/contextual-drag-extend-game24-100q
mkdir -p tmp cache/vllm cache/triton cache/flashinfer
export PATH="$PWD/.venv/bin:/data/gaojc/mamba/envs/vllm-gptoss/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONPATH="$PWD" TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/cache"
export VLLM_CACHE_ROOT="$PWD/cache/vllm" TRITON_CACHE_DIR="$PWD/cache/triton"
export FLASHINFER_WORKSPACE_BASE="$PWD/cache/flashinfer"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_WORKER_MULTIPROC_METHOD=spawn
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=4
exec .venv/bin/python -u scripts/game24_8b_campaign.py --run
