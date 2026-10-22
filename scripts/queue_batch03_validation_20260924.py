"""Wait for a genuinely idle A100 GPU, execute one preflighted run, then exit."""
import csv
import fcntl
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/data2/gaojc/envs/contextual-drag-vllm/bin/python'
RUN = 'game24-batch03-qwen3-8b-paired-validation-retry1-20260925'


def status(state, **details):
    payload = dict(state=state, updated_utc=datetime.now(timezone.utc).isoformat(), **details)
    temporary = ROOT / 'queue_status.json.tmp'
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    temporary.replace(ROOT / 'queue_status.json')
    print(json.dumps(payload), flush=True)


def inventory():
    def query(args):
        return list(csv.reader(subprocess.check_output(['nvidia-smi', *args, '--format=csv,noheader,nounits'], text=True).splitlines()))
    occupied = {row[0].strip() for row in query(['--query-compute-apps=gpu_uuid,pid']) if row}
    cards = query(['--query-gpu=index,uuid,memory.used,utilization.gpu'])
    return [dict(index=int(i), uuid=u.strip(), memory_mib=int(m), utilization=int(v),
                 idle=u.strip() not in occupied and int(m) < 1024 and int(v) <= 5)
            for i, u, m, v in cards]


def verify_frozen():
    report = json.loads((ROOT / 'preflight.json').read_text())
    assert report['passed'] and report['scientific_requests'] == 64
    for name, expected in report['hashes'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name


def main():
    lock = (ROOT / 'queue.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (ROOT / 'outputs' / RUN).exists(), 'Never silently restart an existing run'
    verify_frozen()
    deadline = time.time() + 12 * 3600
    stable = Counter()
    selected = None
    while time.time() < deadline:
        cards = inventory()
        for card in cards:
            stable[card['uuid']] = stable[card['uuid']] + 1 if card['idle'] else 0
        candidates = [card for card in cards if stable[card['uuid']] >= 3]
        if candidates:
            selected = sorted(candidates, key=lambda card: (card['index'] != 4, card['index']))[0]
            break
        status('waiting_for_idle_gpu', cards=cards, deadline_unix=deadline, completed=0, total=64)
        time.sleep(30)
    if selected is None:
        status('expired_without_launch', completed=0, total=64)
        return
    verify_frozen()
    assert any(c['uuid'] == selected['uuid'] and c['idle'] for c in inventory()), 'GPU became occupied before launch'
    env = os.environ.copy()
    # vLLM 0.11 resolves CUDA_VISIBLE_DEVICES through an integer physical index.
    # Keep the UUID in the launch record for an unambiguous device audit.
    env.update(CUDA_VISIBLE_DEVICES=str(selected['index']), SC_GPU=str(selected['index']), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONUNBUFFERED='1', TMPDIR='/data2/gaojc/tmp',
               VLLM_WORKER_MULTIPROC_METHOD='spawn', VLLM_NO_USAGE_STATS='1', SC_VLLM_DECODE_LAYOUT='per_request',
               SC_FLEX_NO_CUDAGRAPHS='1', SC_FLEX_COMPILE_LIMIT='1024', CUDA_LAUNCH_BLOCKING='1',
               PYTHONPATH=str(ROOT), SC_TASK='game24', SC_TOTAL='64', SC_PREP='game24-batch03-8q-prepared', SC_MATH_RUN=RUN)
    env.pop('SC_MATH_RESUME', None)
    status('launching', gpu=selected, total=64)
    (ROOT / 'launch_record.json').write_text(json.dumps(dict(gpu=selected, scientific_generations=64,
        engineering_probe_requests=8, engineering_max_new_tokens=4, launched_utc=datetime.now(timezone.utc).isoformat(),
        reference='Batch02 validated selective snapshot; vLLM0.11 unchanged code path',
        resource_policy='three consecutive idle samples; no process terminated; no automatic retry'), indent=2))
    with (ROOT / 'run.log').open('w') as log:
        process = subprocess.Popen([PYTHON, 'scripts/retry_math_external_20260920.py'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        status('running', gpu=selected, pid=process.pid, total=64)
        code = process.wait()
    completion = ROOT / 'outputs' / RUN / 'completion.json'
    if code != 0 or not completion.exists():
        status('failed_no_retry', gpu=selected, returncode=code)
        return
    result = json.loads(completion.read_text())
    assert result['completed'] == 64
    status('complete', gpu=selected, **result)


if __name__ == '__main__':
    from collections import Counter
    try:
        main()
    except Exception as exc:
        status('failed_no_retry', error=f'{type(exc).__name__}: {exc}')
        raise
