#!/usr/bin/env bash
set -euo pipefail

ENV_DIR=/data2/gaojc/envs/gemma4-vllm019
PYTHON_BASE=/data2/gaojc/uv-python/cpython-3.11-linux-x86_64-gnu/bin/python3.11
MODEL_DIR=/data2/gaojc/models/gemma-4-E4B-it
OUTPUT_ROOT=/data2/gaojc/tmp/math-external-16q-20260920/outputs
COMPLETION="$OUTPUT_ROOT/gemma4-vllm019-env-completion.txt"

test -x "$PYTHON_BASE"
test -f "$MODEL_DIR/model.safetensors"
mkdir -p "$OUTPUT_ROOT"

if [[ -e "$ENV_DIR" ]]; then
  if [[ -f "$COMPLETION" ]]; then
    echo "ERROR completed environment already exists: $ENV_DIR" >&2
    exit 2
  fi
  /snap/bin/uv venv --clear --python "$PYTHON_BASE" "$ENV_DIR"
else
  /snap/bin/uv venv --python "$PYTHON_BASE" "$ENV_DIR"
fi
UV_HTTP_TIMEOUT=600 UV_HTTP_RETRIES=10 /snap/bin/uv pip install --python "$ENV_DIR/bin/python" \
  'vllm==0.19.1' \
  'transformers==5.9.0'

"$ENV_DIR/bin/python" - <<'PY' >"$COMPLETION"
import sys
import torch
import transformers
import vllm
from transformers import AutoConfig

model = "/data2/gaojc/models/gemma-4-E4B-it"
config = AutoConfig.from_pretrained(model, local_files_only=True, trust_remote_code=True)
assert vllm.__version__ == "0.19.1"
assert transformers.__version__ == "5.9.0"
assert config.model_type == "gemma4"
print("STATUS complete")
print("python", sys.version.replace("\n", " "))
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("transformers", transformers.__version__)
print("vllm", vllm.__version__)
print("config", type(config).__name__, config.model_type, config.architectures)
PY

cat "$COMPLETION"
