"""Single-card, finite-budget acquisition through audited batches to100 questions."""
from __future__ import annotations
import argparse
import datetime
import fcntl
import hashlib
import json
import math
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from batch03_resume_core_20260924 import atomic_write_json
from game24_100q_collect import check_gpu

OUT=ROOT/'docs/game24_100q'
RUN=ROOT/'outputs/game24-100q-20261014/acquisition/a800'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def cost_forecast(processed, eligible_new, hours, remaining):
    if processed==0 or eligible_new==0:
        return dict(remaining_hours=None, point_yield=0, expected_candidates=None)
    rate=eligible_new/processed
    return dict(remaining_hours=math.ceil(remaining/rate)*hours/processed,
                point_yield=rate, expected_candidates=math.ceil(remaining/rate))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    policy=load(OUT/'acquisition_campaign.json')
    profile=load(OUT/'execution_config_a800.json')
    if socket.gethostname()!=profile['hostname']: raise RuntimeError('Wrong execution host')
    order=load(OUT/'fresh_question_order.json')['candidates']
    pilot=load(OUT/'pilot_manifest.json')
    if order[:16]!=pilot['candidate_rows']: raise RuntimeError('Frozen pilot/order mismatch')
    if len({tuple(r['numbers']) for r in order})!=len(order): raise RuntimeError('Duplicate independent question')
    if not args.run:
        print(json.dumps(dict(state='validated_only',target=100,questions_available=len(order),gpu_calls=0)))
        return
    RUN.mkdir(parents=True,exist_ok=True)
    frozen=dict(policy=policy,profile=profile,order_sha256=digest(OUT/'fresh_question_order.json'),
                pilot_sha256=digest(OUT/'pilot_manifest.json'),runner_sha256=digest(ROOT/'scripts/game24_100q_collect.py'))
    config=RUN/'campaign_config.json'
    if config.exists() and load(config)!=frozen: raise RuntimeError('Campaign config changed; resume refused')
    if not config.exists(): atomic_write_json(config,frozen)
    lock=(RUN/'campaign.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    ledger=RUN/'campaign_ledger.json'
    entries=load(ledger) if ledger.exists() else []
    # A prior interrupted, unclosed invocation is conservatively charged through
    # restart time. It cannot be silently omitted from the finite budget.
    for e in entries:
        if e.get('finished_unix') is None:
            e.update(finished_unix=time.time(),state='unclosed_attempt_charged_conservatively')
    atomic_write_json(ledger,entries)
    status=dict(state='preflight',target_eligible_questions=100,execution_host=socket.gethostname(),
                gpu_index=profile['gpu_index'],gpu_uuid=profile['gpu_uuid'],
                campaign_gpu_hours_cap=policy['maximum_campaign_gpu_hours'],automatic_interventions=False)
    guard=threading.Lock(); end=threading.Event(); stop=threading.Event()
    def emit(**changes):
        with guard:
            status.update(changes,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            atomic_write_json(RUN/'status.json',status)
            atomic_write_json(OUT/'progress.json',status)
    def heartbeat():
        while not end.wait(15):
            model_status=[]
            batch=status.get('current_batch')
            if batch:
                for p in (RUN/batch).glob('*/status.json'):
                    try:model_status.append(dict(model=p.parent.name,**load(p)))
                    except (ValueError,OSError):pass
            elapsed=sum((e.get('finished_unix') or time.time())-e['started_unix'] for e in entries)/3600
            emit(models=model_status,campaign_job_gpu_hours=elapsed)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    def on_stop(_sig,_frame): stop.set()
    signal.signal(signal.SIGTERM,on_stop);signal.signal(signal.SIGINT,on_stop)
    def run_child(cmd,log,entry=None):
        env=dict(os.environ,PYTHONPATH=str(ROOT),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                 TMPDIR=str(ROOT/'tmp'),XDG_CACHE_HOME=str(ROOT/'cache'),
                 VLLM_CACHE_ROOT=str(ROOT/'cache/vllm'),TRITON_CACHE_DIR=str(ROOT/'cache/triton'),
                 VLLM_WORKER_MULTIPROC_METHOD='spawn',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
        with log.open('a') as f:
            p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            emit(active_pid=p.pid)
            while p.poll() is None:
                if stop.is_set():
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid,signal.SIGKILL);p.wait()
                    break
                time.sleep(2)
        if entry is not None:
            entry.update(finished_unix=time.time(),returncode=p.returncode,
                         state='complete' if p.returncode==0 else 'failed_or_stopped')
            atomic_write_json(ledger,entries)
        if p.returncode or stop.is_set():raise RuntimeError(f'Child stopped or failed; see {log}')
    def audit():
        if (OUT/'game24_eligible_100.jsonl').exists() and (OUT/'game24_eligible_100.jsonl').stat().st_size:
            return load(OUT/'audit_summary.json')
        emit(state='cpu_audit',active_pid=None)
        run_child([sys.executable,'-u',str(ROOT/'scripts/game24_100q_audit.py')],RUN/'audit.console.log')
        return load(OUT/'audit_summary.json')
    def report(a,processed,forecast):
        efficiency=load(OUT/'sampling_efficiency.json')
        rows=[r for r in efficiency['batches'] if r['batch'].startswith('game24-100q-')]
        hours=sum((e.get('finished_unix') or time.time())-e['started_unix'] for e in entries)/3600
        emit(eligible_questions=a['admitted_independent_questions'],processed_fresh_questions=processed,
             new_generations=a['new_generations_this_task'],pending_response_reviews=a['pending_responses'],
             campaign_job_gpu_hours=hours,remaining_cost_forecast=forecast,target_met=a['target_met'])
        table=['| Batch | Questions | Records | Strict eligible | Tokens | Whole-job GPU hours |',
               '|---|---:|---:|---:|---:|---:|']
        for r in rows:
            table.append('| '+r['batch']+' | '+str(r['questions'])+' | '+str(r['records'])+' | '+str(r['eligible_all'])+' | '+str(r['tokens'])+' | '+str(r['measured_job_hours'])+' |')
        text='# Game24 100Q acquisition live report\n\n'
        text+='State: '+status['state']+'. Eligible independent questions: '+str(a['admitted_independent_questions'])+'/100.\n\n'
        text+='Actual new generations: '+str(a['new_generations_this_task'])+'; actual batch job hours including load: '+str(round(hours,3))+'. No interventions executed.\n\n'
        text+='\n'.join(table)+'\n\n'
        text+='Remaining cost is a point extrapolation from completed new batches, not a confidence bound: '+json.dumps(forecast)+'.\n\n'
        text+='Ambiguous/malformed/None/scalar-only errors are preserved for review and do not automatically count. Pending rows: '+str(a['pending_responses'])+'. Conservative omissions can change the selected population.\n\n'
        text+='New backend: ordinary vLLM0.10.2 on single A800 GPU4. Historical cohorts used0.11.0; full prompt, sampling, effective slot seed, checkpoint/config and raw completion preserved. No token-identical reproduction claim.\n\n'
        text+='On target achievement the audit freezes eligible rows and seed20261014 split20development/restheld-out before interventions; otherwise the100Q file remains empty.\n'
        (OUT/'GAME24_100Q_ACQUISITION_LIVE.md').write_text(text,encoding='utf-8')
    try:
        initial=audit(); legacy=policy['baseline_admitted_questions']
        if initial['target_met']:
            emit(state='target_frozen_complete');return
        check_gpu(profile['gpu_index'])
        batches=[('pilot',0,16)]+[(f'wave-{i:03d}',start,min(start+32,len(order)))
                                     for i,start in enumerate(range(16,len(order),32),1)]
        processed=0;summary=initial
        for name,start,last in batches:
            if stop.is_set():raise RuntimeError('Stop requested')
            batchdir=RUN/name
            finished=batchdir/'status.json'
            already=finished.exists() and load(finished).get('state')=='pilot_complete_pending_audit'
            spent=sum(e['finished_unix']-e['started_unix'] for e in entries if e.get('finished_unix'))/3600
            remaining=policy['maximum_campaign_gpu_hours']-spent
            if remaining<=0:raise RuntimeError('Campaign finite GPU-hour cap reached')
            if not already:
                manifest=dict(pilot,candidate_rows=order[start:last],candidate_count=last-start,
                    total_generations=(last-start)*16,phase='pilot' if name=='pilot' else 'acquisition_wave',
                    acquisition_batch='game24-100q-a800-'+name+'-20261014',
                    max_gpu_hours=min(8 if name=='pilot' else policy['maximum_wave_gpu_hours'],remaining))
                # Keep pre-existing pilot sampling manifest byte-for-byte; a separate
                # executed batch manifest carries hardware/campaign bounds.
                mp=RUN/(name+'.manifest.json')
                if mp.exists():
                    prior=load(mp)
                    for k in ('candidate_rows','seed','samples_per_problem','acquisition_batch'):
                        if prior[k]!=manifest[k]:raise RuntimeError('Frozen batch changed')
                    manifest=prior
                else:atomic_write_json(mp,manifest)
                e=dict(batch=name,started_unix=time.time(),finished_unix=None)
                entries.append(e);atomic_write_json(ledger,entries)
                emit(state='running_baseline_acquisition',current_batch=name,current_candidate_ids=[r['id'] for r in order[start:last]])
                cmd=[sys.executable,'-u',str(ROOT/'scripts/game24_100q_collect.py'),
                     '--manifest',str(mp),'--execution-config',str(OUT/'execution_config_a800.json'),
                     '--output',str(batchdir),'--run-pilot','--gpu','4',
                     '--remaining-campaign-hours',str(remaining)]
                run_child(cmd,RUN/(name+'.console.log'),e)
            processed=last
            summary=audit()
            hours=sum(e['finished_unix']-e['started_unix'] for e in entries if e.get('finished_unix'))/3600
            gained=summary['admitted_independent_questions']-legacy
            prediction=cost_forecast(processed,gained,hours,max(0,100-summary['admitted_independent_questions']))
            report(summary,processed,prediction)
            if summary['target_met']:
                emit(state='target_frozen_complete',freeze_complete=True,active_pid=None)
                report(summary,processed,prediction);return
            if name=='pilot' and gained<=0:
                raise RuntimeError('Completed pilot found no new strict eligible questions; no automatic expansion')
            if prediction['remaining_hours'] is None or prediction['remaining_hours']>policy['maximum_campaign_gpu_hours']-hours:
                raise RuntimeError('Remaining acquisition cost projection exceeds finite remaining budget; stop at audited checkpoint')
            emit(state='batch_audit_passed_continue')
        raise RuntimeError('Fresh source universe exhausted before100eligible questions')
    except BaseException as exc:
        emit(state='stopped_at_checkpoint',error_type=type(exc).__name__,error=str(exc),active_pid=None)
        # Preserve clear live report even on resource/estimate stop.
        if 'summary' in locals():
            report(summary,locals().get('processed',0),locals().get('prediction',{}))
        raise
    finally:
        end.set();thread.join(timeout=20)
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

if __name__=='__main__':main()
