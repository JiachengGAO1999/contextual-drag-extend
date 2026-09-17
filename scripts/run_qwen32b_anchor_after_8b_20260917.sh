#!/usr/bin/env bash
set -euo pipefail
cd /data2/gaojc/projects/contextual-drag-extend
while [ ! -f ordinary_vllm_qwen8b_benchmark_20260917.exit ]; do sleep 15; done
if [ "$(cat ordinary_vllm_qwen8b_benchmark_20260917.exit)" != 0 ]; then
  echo '8B benchmark failed; 32B not launched.'; exit 1
fi
py=/data2/gaojc/envs/contextual-drag-vllm/bin/python
# The first wrapper restores our resident. Wait for it to be fully loaded;
# terminate only the exact own process and its own children.
"$py" - <<'PY'
import os,time,psutil,json
from pathlib import Path
assert json.loads(Path('outputs/ordinary-vllm-qwen8b-benchmark-20260917/summary.json').read_text())['generations']==32
expected=['/data2/gaojc/envs/contextual-drag-vllm/bin/python','-m','selective_context.phase0.vllm_resident']
for _ in range(120):
    matches=[p for p in psutil.process_iter(['cmdline','uids']) if p.info['uids'].real==os.getuid() and p.info['cmdline']==expected]
    if len(matches)==1 and 'SELECTIVE_VLLM_RESIDENT_READY' in Path('ordinary_vllm_qwen8b_benchmark_20260917.log').read_text(errors='replace'):
        parent=matches[0];children=parent.children(recursive=True)
        parent.terminate()
        for p in children:
            try:p.terminate()
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs([parent]+children,timeout=30)
        if alive:raise RuntimeError('Own resident did not exit; do not launch second model')
        break
    time.sleep(5)
else:raise RuntimeError('Expected ready resident missing; no fallback')
PY
export CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1 TMPDIR=/data2/gaojc/tmp
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1
unset SC_VLLM_DECODE_LAYOUT VLLM_ATTENTION_BACKEND
echo "QWEN32_BENCHMARK_START $(date -Is)"
set +e
"$py" -m selective_context.phase0.anchor_throughput \
  --model /data/zhaoyi/liujunyuan/models/Qwen3-32B --alias Qwen3_32B \
  --max-num-seqs 4 --max-num-batched-tokens 2048 --gpu-memory-utilization .95 \
  --output outputs/ordinary-vllm-qwen32b-benchmark-20260917
status=$?
echo "QWEN32_BENCHMARK_EXIT $status $(date -Is)"
printf '%s\n' "$status" > ordinary_vllm_qwen32b_benchmark_20260917.exit
export SC_VLLM_DECODE_LAYOUT=per_request
exec "$py" -m selective_context.phase0.vllm_resident
