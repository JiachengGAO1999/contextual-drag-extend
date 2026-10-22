"""Bounded ordinary-vLLM pilot. Default action is CPU-only validation.

Run anchors in separate processes, journal each completed response with fsync,
and refuse any GPU with an existing compute owner. Never downloads checkpoints.
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import hashlib
import json
import os
import shutil
import signal
import shlex
import subprocess
import sys
import time
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from batch03_resume_core_20260924 import atomic_write_json, append_jsonl_once, load_completed

MODELS = {'Qwen3_8B_Thinking': '/data2/huangrj/models/qwen3-8b',
          'Qwen3_32B': '/data/zhaoyi/liujunyuan/models/Qwen3-32B'}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def minimum_disk_free_bytes(profile=None):
    gib = (profile or {}).get('minimum_disk_free_gib', 10)
    if not isinstance(gib, (int, float)) or not 2 <= gib <= 1024:
        raise ValueError('Disk reserve must be a finite value of at least2GiB')
    return int(gib*1024**3)


def read_journal(path):
    """Archive and repair only a torn trailing line; fail on interior corruption."""
    if not path.exists(): return
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    for i, line in enumerate(lines):
        try: json.loads(line)
        except (ValueError, UnicodeError):
            if i != len(lines)-1:
                raise RuntimeError('Interior journal corruption; refusing automatic repair')
            backup = path.with_name(path.name + '.torn-' + str(time.time_ns()))
            shutil.copy2(path, backup)
            with path.open('wb') as f:
                f.write(b''.join(lines[:i])); f.flush(); os.fsync(f.fileno())

def check_gpu(gpu):
    info = subprocess.check_output(['nvidia-smi', f'--id={gpu}', '--query-gpu=uuid,memory.free',
                                     '--format=csv,noheader,nounits'], text=True).strip().split(',')
    uuid, free = info[0].strip(), int(info[1])
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
                                     '--format=csv,noheader,nounits'], text=True)
    pids = [int(s.split(',')[1]) for s in apps.splitlines() if s.split(',')[0].strip() == uuid]
    if pids:
        raise RuntimeError(f'GPU{gpu} has compute processes {pids}; no process stopped')
    if free < 76000:
        raise RuntimeError(f'GPU{gpu} free memory {free} MiB below 76000')
    return dict(gpu=gpu, uuid=uuid, memory_free_mib=free)

def selected_anchors(manifest):
    anchors = tuple(manifest.get('anchor_models', ('Qwen3_8B_Thinking', 'Qwen3_32B')))
    if anchors not in (('Qwen3_8B_Thinking',), ('Qwen3_8B_Thinking', 'Qwen3_32B')):
        raise ValueError('Only explicit Qwen8B-only or original dual-anchor acquisition is supported')
    return anchors


def validate(manifest, source):
    if digest(source) != manifest['source_sha256']:
        raise ValueError('Source hash mismatch')
    count = manifest['candidate_count']
    if manifest['samples_per_problem'] != 8 or not 1 <= count <= 32:
        raise ValueError('Only frozen prefix8 batches of at most32 questions are permitted')
    if count != 16 and manifest.get('phase') != 'acquisition_wave':
        raise ValueError('Non-pilot batch must declare acquisition_wave')
    with source.open(encoding='utf-8-sig') as f:
        mapping = {str(r['Rank']): sorted(map(int, r['Puzzles'].split())) for r in csv.DictReader(f)}
    keys = set()
    for r in manifest['candidate_rows']:
        key = tuple(sorted(r['numbers']))
        if mapping[str(r['id'])] != list(key) or key in keys:
            raise ValueError('Question identity or multiset duplication')
        keys.add(key)
    if len(keys) != count or manifest['total_generations'] != count*8*len(selected_anchors(manifest)):
        raise ValueError('Pilot budget mismatch')

def runtime_validate(manifest):
    import importlib.metadata
    from transformers import AutoTokenizer
    from selective_context.prompting import render_chat_prompt, render_official_prompt
    from baseline_screen_vllm_20260917 import problem_text
    from vllm import AsyncEngineArgs, AsyncLLMEngine
    checks = []
    for alias, model in MODELS.items():
        index_path = Path(model)/'model.safetensors.index.json'
        weight_index = json.loads(index_path.read_text())
        shards = sorted(set(weight_index['weight_map'].values()))
        if not shards or any(not (Path(model)/name).is_file() or (Path(model)/name).stat().st_size == 0 for name in shards):
            raise RuntimeError('Missing checkpoint weight shard: '+model)
        tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
        tokens = []
        for row in manifest['candidate_rows']:
            prompt = render_chat_prompt(tokenizer, render_official_prompt(ROOT, 'R0', problem_text(row['numbers'])), enable_thinking=True)
            tokens.append(len(tokenizer.encode(prompt, add_special_tokens=False)))
        if max(tokens) >= 32768: raise ValueError('Invalid generation budget')
        checks.append(dict(model=alias, checkpoint=model, max_prompt_tokens=max(tokens),
                           checkpoint_config_sha256=digest(Path(model)/'config.json'),
                           checkpoint_index_sha256=digest(index_path), shards=len(shards),
                           checkpoint_bytes=sum((Path(model)/name).stat().st_size for name in shards)))
    return dict(vllm_version=importlib.metadata.version('vllm'), models=checks,
                gpu_generations=0, model_forward_calls=0, engine_initialized=False)

async def anchor(args, manifest, output, hours):
    from baseline_screen_vllm_20260917 import problem_text, official_score, parse_final
    cfg = dict(manifest_sha256=digest(args.manifest), source_sha256=digest(args.source),
               model_alias=args.anchor, model=MODELS[args.anchor], seed=manifest['seed'],
               sampling=dict(temperature=.6, top_p=.95, top_k=20, max_tokens=32768),
               context_length=32768, max_num_seqs=8 if args.anchor == 'Qwen3_8B_Thinking' else 1,
               backend='ordinary_vllm_v1_async_default_worker', attention_backend='FLASH_ATTN',
               gpu_memory_utilization=.85 if args.anchor == 'Qwen3_8B_Thinking' else .95,
               batching='independent n=1 requests; same per-slot seeds across resume',
               acquisition_batch=manifest.get('acquisition_batch','game24-100q-pilot-20261014'), enable_thinking=True)
    planned = manifest['candidate_count']*8
    if args.execution_config:
        cfg.update(execution_config_sha256=digest(args.execution_config),
                   execution_profile=args.profile, gpu_uuid=args.profile['gpu_uuid'],
                   execution_host=socket.gethostname())
        cfg['hf_overrides']=args.profile.get('hf_overrides',{})
    import importlib.metadata
    cfg.update(vllm_version=importlib.metadata.version('vllm'),
               checkpoint_config_sha256=digest(Path(cfg['model'])/'config.json'), max_num_batched_tokens=8192,
               enable_prefix_caching=False, enable_chunked_prefill=True, enforce_eager=True)
    if args.profile and cfg['vllm_version']!=args.profile['expected_vllm_version']:
        raise RuntimeError('vLLM version differs from frozen execution profile')
    output.mkdir(parents=True, exist_ok=True)
    configpath = output / 'config.json'
    if configpath.exists():
        if json.loads(configpath.read_text()) != cfg:
            raise RuntimeError('Frozen configuration mismatch; resume refused')
    else: atomic_write_json(configpath, cfg)
    journal = output / 'draft_candidates.jsonl'
    read_journal(journal)
    completed, canonical = load_completed([journal]) if journal.exists() else (set(), {})
    missing = [(r,i) for r in manifest['candidate_rows'] for i in range(8)
               if (args.anchor, str(r['id']), i) not in completed]
    if not missing:
        atomic_write_json(output/'status.json', dict(state='complete', completed_generations=planned, new_generations=0))
        return dict(state='complete', new_generations=0)
    disk_floor = minimum_disk_free_bytes(args.profile)
    if shutil.disk_usage(output).free < disk_floor:
        raise RuntimeError(f'Disk free below configured reserve {disk_floor} bytes; no data deleted')
    check_gpu(args.gpu)
    if args.execution_config and check_gpu(args.gpu)['uuid'] != args.profile['gpu_uuid']:
        raise RuntimeError('GPU UUID differs from frozen execution profile')
    os.environ.update(CUDA_VISIBLE_DEVICES=str(args.gpu), VLLM_ATTENTION_BACKEND='FLASH_ATTN',
                      VLLM_USE_V1='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams
    from selective_context.prompting import render_chat_prompt, render_official_prompt
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    started = time.monotonic()
    atomic_write_json(output / 'status.json', dict(state='loading', elapsed_seconds=0))
    engine = AsyncLLMEngine.from_engine_args(AsyncEngineArgs(
        model=cfg['model'], tokenizer=cfg['model'], dtype='bfloat16', max_model_len=32768,
        max_num_seqs=cfg['max_num_seqs'], max_num_batched_tokens=8192,
        gpu_memory_utilization=cfg['gpu_memory_utilization'], enable_prefix_caching=False,
        enable_chunked_prefill=True, enforce_eager=True, generation_config='vllm',
        seed=manifest['seed'],hf_overrides=cfg.get('hf_overrides',{})))
    loaded = time.monotonic()
    tokenizer = await engine.get_tokenizer()
    prompts = {}
    for row in manifest['candidate_rows']:
        problem = problem_text(row['numbers'])
        prompt = render_chat_prompt(tokenizer, render_official_prompt(ROOT, 'R0', problem), enable_thinking=True)
        ids = tokenizer.encode(prompt, add_special_tokens=False)
        if len(ids) >= 32768: raise ValueError('No generation budget')
        prompts[str(row['id'])] = dict(problem=problem, prompt=prompt, prompt_token_ids=ids)
    atomic_write_json(output / 'requests.json', prompts)
    semaphore = asyncio.Semaphore(cfg['max_num_seqs'])
    active, new, errors = {}, [], []
    async def generate(row, i):
        async with semaphore:
            if stop.is_set(): return
            req = prompts[str(row['id'])]
            identity = f"{args.anchor}/{row['id']}/{i}"
            seed = manifest['seed']+i
            active[identity] = 0
            request_started = time.monotonic()
            try:
                params = SamplingParams(n=1, temperature=.6, top_p=.95, top_k=20,
                                        max_tokens=32768-len(req['prompt_token_ids']), seed=seed,
                                        skip_special_tokens=False)
                async for update in engine.generate({'prompt_token_ids': req['prompt_token_ids']}, params, request_id=identity):
                    g = update.outputs[0]
                    active[identity] = len(g.token_ids)
                    if g.finish_reason not in (None, 'abort'):
                        raw = g.text
                        try:
                            final, status = parse_final(raw, req['prompt'], tokenizer.eos_token)
                        except Exception as exc:
                            final, status = raw, 'parse_error'
                            errors.append(dict(identity=identity, error=str(exc)))
                        metadata = dict(backend=cfg['backend'], condition_id='R0', access_mode='full',
                                        sample_seed=seed, base_seed=manifest['seed'],
                                        resume_seed_policy='base_seed_plus_frozen_sample_index',
                                        prompt_tokens=len(req['prompt_token_ids']), generated_tokens=len(g.token_ids))
                        r = dict(id=str(row['id']), task='game24', answer=row['numbers'], problem=req['problem'],
                                 draft_key=f"{row['id']}/{i}", init_response_prompt=req['prompt'],
                                 final_response=final, thinking_status=status, tokens=len(g.token_ids),
                                 generation_seconds=time.monotonic()-request_started,
                                 generated_token_ids=list(g.token_ids),
                                 init_response_generations=[dict(response_id=i, generated_response=raw,
                                     finish_reason='eos' if g.finish_reason == 'stop' else g.finish_reason,
                                     vllm_finish_reason=g.finish_reason, stop_reason=g.stop_reason,
                                     selective_context_metadata=metadata)],
                                 init_response_generations_metadata=dict(model_config_alias=args.anchor,
                                     num_responses=1, enable_thinking=True, intervention=metadata))
                        try: r = official_score(r)
                        except Exception as exc:
                            r['init_response_generations'][0]['correctness'] = None
                            r['postprocess_error'] = str(exc)
                        if append_jsonl_once(journal, r, completed, canonical): new.append(r)
                        print(json.dumps(dict(event='persisted', model=args.anchor, id=row['id'],
                                               sample_index=i, completed=len(completed))), flush=True)
                        break
                    if stop.is_set():
                        await engine.abort(identity)
                        with (output/'aborted_responses.jsonl').open('a', encoding='utf-8') as f:
                            f.write(json.dumps(dict(id=str(row['id']), sample_index=i, seed=seed,
                                partial_text=g.text, generated_token_ids=list(g.token_ids),
                                finish_reason='abort', excluded_from_eligibility=True))+'\n')
                            f.flush(); os.fsync(f.fileno())
                        break
            finally: active.pop(identity, None)
    async def heartbeat():
        while True:
            elapsed = time.monotonic()-started
            if elapsed >= hours*3600: stop.set()
            disk_free = shutil.disk_usage(output).free
            if disk_free < disk_floor:
                if not stop.is_set(): errors.append(dict(error='disk_free_below_configured_reserve', reserve_bytes=disk_floor))
                stop.set()
            atomic_write_json(output/'status.json', dict(state='stopping_at_budget' if stop.is_set() else 'running',
                completed_generations=len(completed), planned_generations=planned, elapsed_seconds=elapsed,
                generated_tokens_persisted=sum(r['tokens'] for r in new), active_tokens=active,
                updated_unix=time.time(), maximum_this_attempt_hours=hours,
                disk_free_bytes=disk_free, minimum_disk_free_bytes=disk_floor))
            await asyncio.sleep(15)
    task = asyncio.create_task(heartbeat())
    try: await asyncio.gather(*(generate(r,i) for r,i in missing))
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
    elapsed = time.monotonic()-started
    summary = dict(state='complete' if len(completed)==planned else 'interrupted',
        new_generations=len(new), completed_generations=len(completed), total_seconds=elapsed,
        load_seconds=loaded-started, generation_seconds=time.monotonic()-loaded,
        tokens=sum(r['tokens'] for r in new), errors=errors)
    atomic_write_json(output / ('attempt-'+str(time.time_ns())+'.json'), summary)
    atomic_write_json(output/'status.json', summary)
    attempts = [json.loads(p.read_text()) for p in output.glob('attempt-*.json')]
    all_rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()] if journal.exists() else []
    atomic_write_json(output/'summary.json', dict(generations=len(all_rows), samples_per_question=8,
        total_seconds=sum(s['total_seconds'] for s in attempts),
        generation_seconds=sum(s['generation_seconds'] for s in attempts),
        tokens=sum(r['tokens'] for r in all_rows),
        interrupted_attempts=sum(s['state']!='complete' for s in attempts)))
    print(json.dumps(summary), flush=True)
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=ROOT/'docs/game24_100q/pilot_manifest.json')
    ap.add_argument('--source', type=Path, default=ROOT/'outputs/protocol-parity-audit-20260917/24.csv')
    ap.add_argument('--output', type=Path, default=ROOT/'outputs/game24-100q-20261014/acquisition/pilot')
    ap.add_argument('--gpu', type=int, default=4)
    ap.add_argument('--run-pilot', action='store_true')
    ap.add_argument('--validate-runtime', action='store_true')
    ap.add_argument('--inspect-gpu', action='store_true')
    ap.add_argument('--anchor', choices=MODELS)
    ap.add_argument('--attempt-hours', type=float)
    ap.add_argument('--execution-config', type=Path)
    ap.add_argument('--remaining-campaign-hours', type=float)
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    anchors = selected_anchors(manifest)
    args.profile = None
    if args.execution_config:
        args.profile = json.loads(args.execution_config.read_text(encoding='utf-8'))
        if set(args.profile['models']) != set(anchors): raise ValueError('Anchor model set differs from manifest')
        MODELS.clear()
        MODELS.update(args.profile['models'])
        if args.gpu != args.profile['gpu_index']: raise ValueError('GPU index changed')
        if (args.run_pilot or args.validate_runtime) and socket.gethostname() != args.profile['hostname']:
            raise RuntimeError('Execution host differs from frozen profile')
    else:
        selected = {name: MODELS[name] for name in anchors}
        MODELS.clear()
        MODELS.update(selected)
    if args.anchor and args.anchor not in anchors:
        raise ValueError('Requested worker anchor is outside the frozen manifest')
    validate(manifest, args.source)
    if args.validate_runtime:
        runtime=runtime_validate(manifest)
        if args.profile and runtime['vllm_version']!=args.profile['expected_vllm_version']:
            raise RuntimeError('vLLM version differs from frozen execution profile')
        from baseline_screen_vllm_20260917 import official_score
        tests=[(r'\boxed{6*(6-2)*1}',True),(r'\boxed{6*(6/2)+1}',False),('no boxed answer',None)]
        for text, expected in tests:
            r=dict(answer=[1,2,6,6],init_response_generations=[dict(generated_response=text)])
            result=official_score(r)['init_response_generations'][0]['correctness']
            if result is not expected: raise RuntimeError('Official scorer preflight failed')
        runtime['official_scorer_true_false_none_checked']=True
        print(json.dumps(runtime), flush=True)
    if args.inspect_gpu:
        print(json.dumps(check_gpu(args.gpu)), flush=True)
    if args.anchor and not args.run_pilot: ap.error('--anchor requires --run-pilot')
    if not args.run_pilot:
        print(json.dumps(dict(state='validated_only', questions=manifest['candidate_count'], planned_generations=manifest['total_generations'],
                              gpu_calls=0, manifest_sha256=digest(args.manifest))))
        return
    if os.name != 'posix': raise RuntimeError('GPU collection requires the audited Linux server')
    if args.gpu != 4: raise RuntimeError('This pilot is authorized only on GPU4')
    for model in MODELS.values():
        if not (Path(model)/'config.json').exists(): raise FileNotFoundError(model)
    max_hours = manifest.get('max_gpu_hours', manifest.get('max_pilot_gpu_hours', 8))
    args.output.mkdir(parents=True, exist_ok=True)
    if args.anchor:
        if args.attempt_hours is None or not 0 < args.attempt_hours <= max_hours:
            raise ValueError('Invalid remaining attempt budget')
        asyncio.run(anchor(args, manifest, args.output/args.anchor, args.attempt_hours))
        return
    import fcntl
    def parent_stop(_signum, _frame):
        raise KeyboardInterrupt('Parent received a stop signal')
    signal.signal(signal.SIGTERM, parent_stop)
    # Same project launcher lock used by earlier GPU diagnostics.
    lock_path = ROOT/'outputs/generation-diagnostics-20261005/launcher.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spent = 0.0
        for status in args.output.glob('*/attempt-*.json'):
            spent += json.loads(status.read_text())['total_seconds']/3600
        # A crashed attempt is conservatively charged from its last heartbeat.
        for status in args.output.glob('*/status.json'):
            s = json.loads(status.read_text())
            if s.get('state') in ('running', 'loading', 'stopping_at_budget'):
                spent += s.get('elapsed_seconds', max_hours*3600)/3600
        if not args.execution_config or args.profile.get('manage_project_resident'):
            from launch_generation_diagnostics_20261005 import resident, stop_resident, gpu_apps, EXPECTED
        else:
            # A800 migration never touches any existing service.
            resident = lambda: None
            gpu_apps = lambda: set()
        restore = False
        invocation_started=time.monotonic()
        try:
            owner = resident()
            if gpu_apps():
                if owner is None:
                    raise RuntimeError('GPU4 occupied; no process stopped')
                family = {owner.pid} | {p.pid for p in owner.children(recursive=True)}
                if not gpu_apps().issubset(family):
                    raise RuntimeError('GPU4 has foreign compute processes; no resident or other process stopped')
                # Restore even if a verified release partly succeeds before error.
                restore = True
                if not stop_resident(args.output):
                    raise RuntimeError('Project resident not verified idle; no experiment launched')
            check_gpu(args.gpu)
            if args.execution_config and check_gpu(args.gpu)['uuid'] != args.profile['gpu_uuid']:
                raise RuntimeError('GPU UUID differs from frozen execution profile')
            for name in MODELS:
                remaining = max_hours-spent
                if args.remaining_campaign_hours is not None:
                    remaining=min(remaining,args.remaining_campaign_hours-(time.monotonic()-invocation_started)/3600)
                if remaining <= 0: raise RuntimeError('Batch cumulative GPU-hour budget exhausted')
                started = time.monotonic()
                command = [sys.executable, '-u', str(Path(__file__).resolve()), '--manifest', str(args.manifest),
                           '--source', str(args.source), '--output', str(args.output), '--run-pilot',
                           '--anchor', name, '--gpu', str(args.gpu), '--attempt-hours', str(remaining)]
                if args.execution_config: command += ['--execution-config',str(args.execution_config)]
                env = dict(os.environ, PYTHONPATH=str(ROOT), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
                with (args.output/(name+'.console.log')).open('a') as log:
                    proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                    try: returncode = proc.wait(timeout=remaining*3600+120)
                    except BaseException:
                        # New process group contains only this anchor and its engine.
                        if proc.poll() is None:
                            os.killpg(proc.pid, signal.SIGTERM)
                            try: proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                        raise
                spent += (time.monotonic()-started)/3600
                if returncode: raise RuntimeError(f'Anchor {name} failed; see console log')
                state = json.loads((args.output/name/'status.json').read_text())['state']
                if state != 'complete':
                    raise RuntimeError('Pilot interrupted; journal preserved; no expansion')
            atomic_write_json(args.output/'status.json', dict(state='pilot_complete_pending_audit',
                              gpu_hours_this_invocation=spent, automatic_expansion=False))
        except BaseException as exc:
            atomic_write_json(args.output/'status.json', dict(state='stopped_before_completion',
                              error_type=type(exc).__name__, error=str(exc), automatic_expansion=False))
            raise
        finally:
            if restore and resident() is None:
                if gpu_apps():
                    atomic_write_json(args.output/'resident_restore_status.json', dict(
                        state='restore_deferred_foreign_gpu_processes', pids=sorted(gpu_apps())))
                else:
                    env = dict(os.environ, CUDA_VISIBLE_DEVICES='4', SC_GPU='4',
                               SC_VLLM_DECODE_LAYOUT='per_request', VLLM_WORKER_MULTIPROC_METHOD='spawn',
                               PYTHONPATH=str(ROOT))
                    restore_command = 'cd '+shlex.quote(str(ROOT))+' && '+shlex.join(EXPECTED)
                    subprocess.run(['tmux','new-session','-d','-s','game24-100q-resident-restore',restore_command],
                                   env=env, check=True)

if __name__ == '__main__': main()
