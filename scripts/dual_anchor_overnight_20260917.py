"""Bounded, checkpointed two-anchor acquisition; never launches interventions."""
import collections
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/game24-dual-anchor-20q-20260917'
MODELS = [
    ('Qwen3_8B_Thinking', '/data2/huangrj/models/qwen3-8b', 16, 8192, .85),
    ('Qwen3_32B', '/data/zhaoyi/liujunyuan/models/Qwen3-32B', 4, 2048, .95),
]


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def pool_summary():
    counts = collections.defaultdict(collections.Counter)
    completed = collections.defaultdict(collections.Counter)
    total = 0
    for path in sorted(OUT.glob('batch-*/draft_candidates.jsonl')):
        alias = json.loads((path.parent / 'config.json').read_text())['model_alias']
        for line in path.read_text().splitlines():
            r = json.loads(line)
            g = r['init_response_generations'][0]
            q = r['id']
            total += 1
            completed[q][alias] += 1
            good = g['finish_reason'] == 'eos' and r['thinking_status'] == 'parsable_thinking'
            key = 'correct' if good and g.get('correctness') is True else 'incorrect' if good and g.get('correctness') is False else 'excluded'
            counts[q][key] += 1
    eligible = [q for q, c in counts.items() if c['correct'] >= 2 and c['incorrect'] >= 2
                and all(completed[q][m[0]] == 16 for m in MODELS)]
    save(OUT / 'pool_summary.json', dict(generations=total, counts=dict(counts),
         samples_by_anchor=dict(completed), strict_scorer_eligible_ids=eligible,
         eligible_count=len(eligible), manual_substantive_failure_audit_pending=True,
         note='False may include formatting failures. No drafts selected, no interventions. Old n4 run excluded.'))


def main():
    manifest = json.loads((ROOT / 'scripts/dual_anchor_overnight_manifest_20260917.json').read_text())
    assert len(manifest['candidate_rows']) == 20 and manifest['samples_per_problem'] == 16
    OUT.mkdir(exist_ok=False)
    save(OUT / 'manifest.json', manifest)
    started = time.monotonic()
    status = dict(state='running', started_unix=time.time(), maximum_generations=640,
                  budget_hours=12, completed_batches=0, interventions=False)
    save(OUT / 'status.json', status)
    try:
        # Pair both anchors within each two-question chunk. This leaves complete
        # paired question prefixes if runtime reaches the budget boundary.
        for start in range(0, 20, 2):
            if time.monotonic() - started > 11 * 3600:
                status['state'] = 'stopped_at_budget_boundary'
                break
            chunk = dict(manifest, candidate_rows=manifest['candidate_rows'][start:start+2],
                         candidate_count=2, total_generations=32)
            chunk_path = OUT / f'questions-{start:02d}.json'
            save(chunk_path, chunk)
            for alias, model, seqs, tokens, memory in MODELS:
                name = f'batch-{start:02d}-{alias}'
                status.update(current_batch=name, elapsed_seconds=time.monotonic()-started)
                save(OUT / 'status.json', status)
                command = [sys.executable, str(ROOT / 'scripts/baseline_screen_vllm_20260917.py'),
                    '--model', model, '--model-alias', alias,
                    '--input', '/data2/gaojc/data/game24-tot-8050e67/24.csv',
                    '--source-revision', '8050e67d0e3a0fddc424d7fa5801538722a4c4cc',
                    '--manifest', str(chunk_path), '--output', str(OUT / name),
                    '--max-num-seqs', str(seqs), '--max-num-batched-tokens', str(tokens),
                    '--gpu-memory-utilization', str(memory)]
                remaining = 12 * 3600 - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError('12-hour runtime budget reached')
                print('BATCH_START', name, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), flush=True)
                with (OUT / (name + '.log')).open('w') as log:
                    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        code = process.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        import signal
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                        raise TimeoutError('12-hour budget reached; active batch incomplete and excluded')
                if code:
                    raise RuntimeError(f'{name} exited {code}; no retry or fallback')
                summary = json.loads((OUT / name / 'summary.json').read_text())
                assert summary['generations'] == 32
                status['completed_batches'] += 1
                pool_summary()
                print('BATCH_COMPLETE', name, summary['generation_seconds'], flush=True)
        else:
            status['state'] = 'complete'
    except Exception as exc:
        status.update(state='stopped_error_or_timeout', error=repr(exc))
        raise
    finally:
        status['elapsed_seconds'] = time.monotonic() - started
        save(OUT / 'status.json', status)
        pool_summary()


if __name__ == '__main__':
    main()
