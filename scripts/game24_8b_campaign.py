"""Separate single-Qwen8B campaign; reuse the completed pilot and preserve old accounting."""
import argparse
import datetime
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from batch03_resume_core_20260924 import atomic_write_json
from game24_100q_collect import check_gpu
from game24_8b_audit import audit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/game24_100q_8b'
RUN = ROOT/'outputs/game24-100q-8b-20261015/acquisition/a800'


def load(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def forecast(processed, gained, hours, remaining):
    if gained <= 0 or processed <= 0:
        return dict(point_yield=0, remaining_gpu_hours=None)
    return dict(point_yield=gained/processed,
                expected_additional_questions=math.ceil(remaining*processed/gained),
                remaining_gpu_hours=math.ceil(remaining*processed/gained)*hours/processed)


def completed_prefix(order, run, wave_questions):
    processed = 16
    for number, start in enumerate(range(16, len(order), wave_questions), 1):
        name = f'wave-{number:03d}'
        status = run/name/'status.json'
        if not status.exists() or load(status).get('state') != 'pilot_complete_pending_audit':
            break
        last = min(start+wave_questions, len(order))
        if load(run/(name+'.manifest.json'))['candidate_rows'] != order[start:last]:
            raise RuntimeError('Completed wave differs from frozen question order')
        processed = last
    return processed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    policy = load(OUT/'acquisition_campaign.json')
    profile = load(OUT/'execution_config_a800.json')
    pilot = load(OUT/'pilot_manifest.json')
    order = load(OUT/'fresh_question_order.json')['candidates']
    if policy['anchors'] != ['Qwen3_8B_Thinking'] or order[:16] != pilot['candidate_rows']:
        raise RuntimeError('Single-anchor protocol or frozen pilot/order mismatch')
    if len({tuple(sorted(r['numbers'])) for r in order}) != len(order):
        raise RuntimeError('Duplicate question multiset')
    summary = audit()
    processed = completed_prefix(order, RUN, policy['wave_questions'])
    eligible_prefix_ids = {str(r['id']) for r in order[:processed]}
    admitted_prefix = sum(q in eligible_prefix_ids for q in summary['admitted_ids'])
    estimate = forecast(processed, admitted_prefix, policy['reused_pilot_8b_gpu_hours'],
                        max(0, policy['target']-summary['admitted_independent_questions']))
    if not args.run:
        print(json.dumps(dict(state='validated_only', gpu_calls=0, summary=summary, forecast=estimate)))
        return
    if os.name != 'posix' or socket.gethostname() != profile['hostname']:
        raise RuntimeError('Collection must use the pinned Linux A800 host')
    RUN.mkdir(parents=True, exist_ok=True)
    lock = (RUN/'campaign.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    bindings = dict(policy=policy, profile=profile,
                    order_sha256=digest(OUT/'fresh_question_order.json'),
                    pilot_sha256=digest(OUT/'pilot_manifest.json'),
                    runner_sha256=digest(ROOT/policy['collector_script']),
                    controller_sha256=digest(Path(__file__)),
                    audit_sha256=digest(ROOT/'scripts/game24_8b_audit.py'))
    ledger = RUN/'campaign_ledger.json'
    entries = load(ledger) if ledger.exists() else []
    frozen = RUN/'campaign_config.json'
    if frozen.exists() and load(frozen) != bindings:
        prior = load(frozen)
        semantic_keys = ('policy', 'profile', 'order_sha256', 'pilot_sha256')
        if entries or any(prior[k] != bindings[k] for k in semantic_keys):
            raise RuntimeError('Frozen single-anchor campaign changed; resume refused')
        atomic_write_json(RUN/f'preflight_config_revision-{time.time_ns()}.json', prior)
    atomic_write_json(frozen, bindings)
    for e in entries:
        if e.get('finished_unix') is None:
            e.update(finished_unix=time.time(), state='unclosed_attempt_charged_conservatively')
    atomic_write_json(ledger, entries)
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    status = dict(protocol=policy['protocol'], anchor_models=policy['anchors'],
                  execution_host=socket.gethostname(), gpu_index=profile['gpu_index'], gpu_uuid=profile['gpu_uuid'],
                  target_eligible_questions=policy['target'], campaign_gpu_hours_cap=policy['maximum_campaign_gpu_hours'],
                  prior_campaign_job_gpu_hours=policy['prior_campaign_job_gpu_hours'],
                  automatic_interventions=False, active_pid=None)

    def spent():
        return sum((e.get('finished_unix') or time.time())-e['started_unix'] for e in entries)/3600

    def emit(**changes):
        status.update(changes, updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      new_8b_campaign_gpu_hours=spent(),
                      campaign_job_gpu_hours=policy['prior_campaign_job_gpu_hours']+spent())
        atomic_write_json(RUN/'status.json', status)
        atomic_write_json(OUT/'progress.json', status)

    def report(processed):
        current = audit()
        hours = policy['reused_pilot_8b_gpu_hours']+spent()
        prefix_ids = {str(r['id']) for r in order[:processed]}
        gained = sum(q in prefix_ids for q in current['admitted_ids'])
        prediction = forecast(processed, gained, hours,
                              max(0, policy['target']-current['admitted_independent_questions']))
        emit(eligible_questions=current['admitted_independent_questions'], admitted_ids=current['admitted_ids'],
             completed_8b_questions=processed, saved_8b_responses=current['acquisition_responses'],
             pending_response_reviews=current['pending_response_reviews'], remaining_cost_forecast=prediction,
             target_met=current['target_met'])
        text = '# Single Qwen3-8B acquisition live report\n\n'
        text += json.dumps(status, ensure_ascii=False, indent=2)+'\n\n'
        text += ('Strict eligibility uses one complete8-response Qwen3-8B cohort per independent question. '
                 'All prior dual-anchor costs remain in campaign accounting. No R2/R3 interventions run. '
                 'Cost extrapolation is a pilot point estimate, not a guarantee.\n')
        (OUT/'GAME24_100Q_ACQUISITION_LIVE.md').write_text(text, encoding='utf-8')
        return current, prediction

    try:
        emit(state='preflight', current_batch='reused_8b_pilot', current_batch_completed_generations=128)
        summary, estimate = report(processed)
        for number, start in enumerate(range(16, len(order), policy['wave_questions']), 1):
            if summary['target_met']:
                emit(state='target_frozen_complete', active_pid=None)
                report(processed)
                return
            if start < processed:
                continue
            if stop.is_set():
                raise RuntimeError('Stop requested')
            remaining = policy['maximum_campaign_gpu_hours']-policy['prior_campaign_job_gpu_hours']-spent()
            if estimate['remaining_gpu_hours'] is None or estimate['remaining_gpu_hours'] > remaining:
                emit(state='stopped_cost_gate', active_pid=None)
                report(processed)
                return
            free = shutil.disk_usage(RUN).free
            if free < policy['minimum_disk_free_gib']*1024**3:
                emit(state='awaiting_disk_space', disk_free_bytes=free,
                     minimum_disk_free_gib=policy['minimum_disk_free_gib'], active_pid=None,
                     error='Disk free below configured reserve; no GPU collection started and no files deleted')
                report(processed)
                return
            last = min(start+policy['wave_questions'], len(order))
            name = f'wave-{number:03d}'
            batchdir = RUN/name
            final_status = batchdir/'status.json'
            if not final_status.exists() or load(final_status).get('state') != 'pilot_complete_pending_audit':
                info = check_gpu(profile['gpu_index'])
                if info['uuid'] != profile['gpu_uuid']:
                    raise RuntimeError('GPU UUID differs from profile')
                manifest = dict(pilot, state='frozen_before_generation', phase='acquisition_wave',
                    candidate_count=last-start, candidate_rows=order[start:last], total_generations=(last-start)*8,
                    acquisition_batch='game24-100q-8b-a800-'+name+'-20261015',
                    max_gpu_hours=min(policy['maximum_wave_gpu_hours'], remaining))
                mp = RUN/(name+'.manifest.json')
                if mp.exists():
                    prior = load(mp)
                    if any(prior[k] != manifest[k] for k in ('candidate_rows', 'seed', 'anchor_models', 'acquisition_batch')):
                        raise RuntimeError('Frozen wave manifest changed')
                    manifest = prior
                else:
                    atomic_write_json(mp, manifest)
                e = dict(batch=name, started_unix=time.time(), finished_unix=None)
                entries.append(e)
                atomic_write_json(ledger, entries)
                cmd = [sys.executable, '-u', str(ROOT/policy['collector_script']), '--manifest', str(mp),
                       '--execution-config', str(OUT/'execution_config_a800.json'), '--output', str(batchdir),
                       '--gpu', str(profile['gpu_index']), '--run-pilot', '--remaining-campaign-hours', str(remaining)]
                env = dict(os.environ, PYTHONPATH=str(ROOT), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
                with (RUN/(name+'.console.log')).open('a') as log:
                    p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
                    emit(state='running_baseline_acquisition', current_batch=name, active_pid=p.pid,
                         current_candidate_ids=[r['id'] for r in order[start:last]])
                    try:
                        heartbeat = 0
                        while p.poll() is None:
                            if stop.is_set():
                                os.killpg(p.pid, signal.SIGTERM)
                                p.wait(timeout=60)
                                break
                            if time.monotonic()-heartbeat >= 15:
                                states = [dict(model=q.parent.name, **load(q)) for q in batchdir.glob('*/status.json')]
                                emit(models=states, current_batch_completed_generations=sum(
                                    s.get('completed_generations', 0) for s in states))
                                heartbeat = time.monotonic()
                            time.sleep(2)
                    finally:
                        if p.poll() is None:
                            os.killpg(p.pid, signal.SIGTERM)
                            try:
                                p.wait(timeout=60)
                            except subprocess.TimeoutExpired:
                                os.killpg(p.pid, signal.SIGKILL)
                                p.wait()
                        e.update(finished_unix=time.time(), returncode=p.returncode)
                        atomic_write_json(ledger, entries)
                if p.returncode or stop.is_set():
                    raise RuntimeError('8B batch stopped or failed; completed responses preserved')
            processed = last
            emit(state='cpu_audit', active_pid=None)
            summary, estimate = report(processed)
        raise RuntimeError('Frozen source order exhausted before target')
    except BaseException as exc:
        emit(state='stopped_at_checkpoint', error_type=type(exc).__name__, error=str(exc), active_pid=None)
        raise
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == '__main__':
    main()
