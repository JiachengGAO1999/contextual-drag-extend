"""Bounded128-request external math validation; exit after completion."""
import json
import os
import subprocess
import time
from pathlib import Path
from selective_context.prompting import load_request_bundle, assert_same_text_contract
from selective_context.vllm_mask import key_block_onsets, request_metadata, NEVER

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / 'outputs/math-external-16q-20260920-prepared'
OUT = ROOT / 'outputs/math-external-16q-20260920'

def main():
    assert os.environ['CUDA_VISIBLE_DEVICES'] == '0'
    assert not OUT.exists(), 'No overwrite or automatic retry'
    checks = []
    manifest = json.loads((PREP / 'manifest.json').read_text())
    assert len(manifest) == 128
    for name in sorted({x['bundle'] for x in manifest}):
        enc, reqs = load_request_bundle(ROOT / name)
        assert_same_text_contract(reqs)
        n = len(enc.input_ids)
        assert 32768 - n >= 8192, 'Insufficient completion room; never truncate draft'
        for req in reqs:
            lo, hi = req.draft_token_span
            onset = {'R0': NEVER, 'R2': NEVER, 'R3': n, 'R4': hi}[req.condition_id]
            assert key_block_onsets(request_metadata(req)) == [onset if lo <= k < hi else NEVER for k in range(n)]
        checks.append(dict(bundle=name, input_tokens=n, remaining=32768-n, spillover=enc.boundary_spillover))
    (PREP / 'preflight.json').write_text(json.dumps(dict(passed=True, requests=128, checks=checks), indent=2))
    used = int(subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.used','--format=csv,noheader,nounits'], text=True).strip())
    assert used < 1000, 'GPU0 occupied; do not touch other processes'
    print('PREFLIGHT_PASSED128; loading Qwen3-8B on GPU0', flush=True)
    from selective_context.phase0.vllm_run import main as run
    run(['--manifest',str(PREP/'manifest.json'),'--output',str(OUT),'--batch-size','8','--task','math500'])
    print('COMPLETE128; no further generation; releasing GPU0', flush=True)

if __name__ == '__main__':
    main()
