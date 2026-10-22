#!/usr/bin/env bash
set -euo pipefail
cd /data/gaojc/projects/contextual-drag-extend-game24-100q
mkdir -p tmp cache/vllm cache/triton cache/flashinfer
export PATH="/data/gaojc/projects/contextual-drag-extend-game24-100q/.venv/bin:/data/gaojc/mamba/envs/vllm-gptoss/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONPATH="/data/gaojc/projects/contextual-drag-extend-game24-100q"
export TMPDIR="/data/gaojc/projects/contextual-drag-extend-game24-100q/tmp"
export XDG_CACHE_HOME="/data/gaojc/projects/contextual-drag-extend-game24-100q/cache"
export VLLM_CACHE_ROOT="/data/gaojc/projects/contextual-drag-extend-game24-100q/cache/vllm"
export TRITON_CACHE_DIR="/data/gaojc/projects/contextual-drag-extend-game24-100q/cache/triton"
export FLASHINFER_WORKSPACE_BASE="/data/gaojc/projects/contextual-drag-extend-game24-100q/cache/flashinfer"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_WORKER_MULTIPROC_METHOD=spawn
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export MAX_JOBS=4
exec .venv/bin/python -u scripts/game24_100q_campaign.py --run
