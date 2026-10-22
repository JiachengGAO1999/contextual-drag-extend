"""Complete the frozen82 confirmation and report it separately from pooled102.

The completed20-question runner and its outputs are immutable references.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/game24-replication-qwen3-8b-heldout82-20261019"
DEV = ROOT / "outputs/game24-replication-qwen3-8b-development-20261017"
DATA = ROOT / "docs/game24_100q_8b"
sys.path.insert(0, str(ROOT / "scripts"))
from game24_replication_20261017 import read, rows, sha, save, write_rows, bootstrap, verify_first_tokens

SEEDS = [927001, 927002]
CONDITIONS = ["R0", "R2", "R3"]


def activate_worker_paths():
    # spawn imports this module as __mp_main__, without calling runtime()/run().
    # Restore overlay precedence after the legacy helper prepends checkout ROOT.
    path = BASE/"runtime_profile.json"
    if path.exists():
        profile = read(path)
        if Path(profile["reference"]).is_dir():
            sys.path.insert(0,profile["reference"])
            sys.path.insert(0,profile["overlay"])


activate_worker_paths()


def status(state, **extra):
    result = dict(status=state, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
    save(BASE / "status.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def select_materials(qids, eligible, trajectories):
    pairs, sources, cache = [], [], {}
    for qid in qids:
        cohort = [trajectories[t] for t in eligible[qid]["trajectory_ids"]]
        if (len(cohort) != 8 or {r["sample_index"] for r in cohort} != set(range(8))
                or any(r["source_model"] != "Qwen3_8B_Thinking" for r in cohort)):
            raise RuntimeError("Incomplete/wrong-model cohort: " + qid)
        pool = sorted((r for r in cohort if r["classification"] == "substantive_error"),
                      key=lambda r: (r["source_model"], r["sample_index"]))
        if len(pool) < 2:
            raise RuntimeError("Missing error witnesses: " + qid)
        choice = random.Random("20261017:" + qid).choice(pool)
        source = ROOT / choice["source_path"]
        if source not in cache:
            cache[source] = source.read_text(encoding="utf-8").splitlines()
        raw_line = cache[source][choice["source_line"] - 1]
        import hashlib
        if hashlib.sha256(raw_line.encode()).hexdigest() != choice["raw_record_sha256"]:
            raise RuntimeError("Source provenance mismatch")
        raw = json.loads(raw_line)
        draft = raw["final_response"]
        if (not draft.strip() or raw["thinking_status"] != "parsable_thinking"
                or raw["init_response_generations"][0]["finish_reason"] not in ("eos", "stop")
                or sorted(raw["answer"]) != sorted(eligible[qid]["numbers"])):
            raise RuntimeError("Invalid source draft")
        pair = dict(id=qid, task="game24", problem=raw["problem"], answer=raw["answer"], traj1=draft,
            audit_status="substantive_failed", stratum="frozen_new_heldout", benchmark="Game24",
            source_model="Qwen3_8B_Thinking", target_model="Qwen3_8B_Thinking", self_or_cross="self",
            source_trajectory_id=choice["trajectory_id"], source_path=choice["source_path"],
            source_line=choice["source_line"], raw_record_sha256=choice["raw_record_sha256"],
            source_sample_index=choice["sample_index"], draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
            eligible_failed_pool_size=len(pool))
        pairs.append(pair)
        sources.append(dict(trajectory=choice, raw_record=raw))
    return pairs, sources


def freeze():
    if BASE.exists():
        raise RuntimeError("Refusing to overwrite confirmation freeze")
    split = read(DATA / "game24_split_manifest.json")
    eligible = {r["canonical_question_id"]: r for r in rows(DATA / "game24_eligible_100.jsonl")}
    development, held = split["development"], split["held_out"]
    if (split["state"] != "frozen" or len(development) != 20 or len(held) != 82
            or set(development) & set(held) or set(development + held) != set(eligible)):
        raise RuntimeError("Frozen split mismatch")
    previous = read(DEV / "plan.json")
    if (previous["questions"] != development or previous["seeds"] != SEEDS
            or previous["conditions"] != CONDITIONS or read(DEV / "completion.json")["completed"] != 120):
        raise RuntimeError("Development reference mismatch")
    trajectories = {r["trajectory_id"]: r for r in rows(DATA / "game24_trajectory_pool.jsonl")}
    # Check unchanged deterministic selection against already completed20.
    replay, _ = select_materials(development, eligible, trajectories)
    for a, b in zip(replay, rows(DEV / "pairs.jsonl")):
        for k in ("id", "traj1", "draft_sha256", "source_trajectory_id"):
            if a[k] != b[k]:
                raise RuntimeError("Selection policy drift")
    pairs, sources = select_materials(held, eligible, trajectories)
    BASE.mkdir(parents=True)
    write_rows(BASE / "pairs.jsonl", pairs)
    write_rows(BASE / "selected_source_records.jsonl", sources)
    reference_hours = read(DEV / "completion.json")["seconds"] / 3600
    bindings = [DATA/"game24_split_manifest.json", DATA/"game24_eligible_100.jsonl",
                DATA/"game24_trajectory_pool.jsonl", DEV/"results.jsonl", DEV/"plan.json",
                DEV/"pairs.jsonl", BASE/"pairs.jsonl", BASE/"selected_source_records.jsonl"]
    save(BASE / "plan.json", dict(protocol="unchanged_R0_R2_R3_frozen82_confirmation_v1",
        status="frozen_before_heldout_outcomes", created_utc=datetime.now(timezone.utc).isoformat(),
        authorization="2026-10-19 user explicitly requests running the entire expanded question set.",
        questions=held, development_questions=development, full_questions=development+held,
        scientific_requests=492, pooled_scientific_requests=612, seeds=SEEDS, conditions=CONDITIONS,
        sampling=previous["sampling"], backend=previous["backend"],
        draft_selection=previous["draft_selection"], draft_representation=previous["draft_representation"],
        predictions=previous["predictions"], primary_effects=previous["primary_effects"],
        statistics=previous["statistics"], scoring=previous["scoring"],
        resource_limit_hours=96, resource_limit_scope="Cumulative attempt time; stop new batches at96h, an active batch may finish. No extra conditions/seeds/models.",
        cost_reference_hours=reference_hours, estimated_additional_gpu_hours=reference_hours*492/120,
        report_scopes=["heldout82_primary_confirmation", "development20_reference", "pooled102_descriptive"],
        report_boundary="Pooling does not make development outcome-blind. Report hardware strata and all failures/None/truncations; no post-effect exclusions.",
        restart_policy="Resume only durable missing request keys under identical bindings; complete pending R2/R3 pairs without rerunning saved responses.",
        hashes={p.relative_to(ROOT).as_posix(): sha(p) for p in bindings}))
    status("frozen_cpu_only", completed=0, total=492)


def runtime():
    profile = read(BASE / "runtime_profile.json")
    reference = Path(profile["reference"])
    sys.path.insert(0, str(reference))
    sys.path.insert(0, str(Path(profile["overlay"])))
    return profile, reference


def prepare():
    profile, reference = runtime()
    from transformers import AutoTokenizer
    from selective_context.prompting import (encode_direct_prompt, encode_prompt, make_request,
        make_r2_r4_requests, persist_request_bundle, render_chat_prompt, load_request_bundle)
    from selective_context.schema import AccessMode
    from selective_context.tasks import independent_prompt
    from selective_context.vllm_mask import NEVER, key_block_onsets, request_metadata
    plan = read(BASE / "plan.json")
    target = BASE / "prepared"
    if target.exists():
        raise RuntimeError("Refusing prepared overwrite")
    for name in ("pairs.jsonl", "selected_source_records.jsonl"):
        if sha(BASE/name) != plan["hashes"][(BASE/name).relative_to(ROOT).as_posix()]:
            raise RuntimeError("Changed frozen source")
    for name, digest in read(reference/"preflight.json")["hashes"].items():
        if sha(reference/name) != digest:
            raise RuntimeError("Paper snapshot changed")
    for name, version in profile["expected_versions"].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError("Version mismatch: " + name)
    tok = AutoTokenizer.from_pretrained(profile["model"], local_files_only=True, use_fast=True)
    target.mkdir()
    clean, paired, lengths = [], [], []
    for row in rows(BASE/"pairs.jsonl"):
        key = row["id"].split(":")[-1]
        pair_path = target/(key+".pair.json")
        save(pair_path, row)
        for seed in SEEDS:
            direct = encode_direct_prompt(tok, render_chat_prompt(tok, independent_prompt(row["problem"], task="game24"), True))
            hist = encode_prompt(tok, render_chat_prompt(tok, independent_prompt(row["problem"], row["traj1"], "game24"), True))
            req0 = make_request(direct, "R0", AccessMode.FULL, seed)
            reqs = [r for r in make_r2_r4_requests(hist, seed) if r.condition_id in ("R2", "R3")]
            for name, enc, requests in [("r0", direct, [req0]), ("r2_r3", hist, reqs)]:
                n = len(enc.input_ids)
                if 32768-n < 8192:
                    raise RuntimeError("Insufficient generation room; do not truncate/reselect")
                lengths.append(n)
                path = target/f"{key}.{seed}.{name}.json"
                persist_request_bundle(path, enc, requests)
                for req in requests:
                    req.validate()
                    lo, hi = req.draft_token_span
                    want = [n if req.condition_id == "R3" and lo <= i < hi else NEVER for i in range(n)]
                    if key_block_onsets(request_metadata(req)) != want:
                        raise RuntimeError("Access-mask mismatch")
                    item = dict(task="game24", bundle=path.relative_to(ROOT).as_posix(),
                                pair=pair_path.relative_to(ROOT).as_posix(), condition=req.condition_id)
                    (clean if name == "r0" else paired).append(item)
    manifest = clean+paired
    if len(clean) != 164 or len(manifest) != 492:
        raise RuntimeError("Unexpected manifest count")
    save(target/"manifest.json", manifest)
    # Re-tokenize all completed development requests, rather than selecting favorable probes.
    old_manifest = read(DEV/"prepared/manifest.json")
    for item in old_manifest:
        enc, _ = load_request_bundle(ROOT/item["bundle"])
        row = read(ROOT/item["pair"])
        prompt = independent_prompt(row["problem"], None if item["condition"] == "R0" else row["traj1"], "game24")
        other = (encode_direct_prompt if item["condition"] == "R0" else encode_prompt)(tok, render_chat_prompt(tok, prompt, True))
        if other.input_ids != enc.input_ids:
            raise RuntimeError("Development tokenizer parity failed")
    # Fixed8 R0 and8 R2/R3 probes, compared with saved A100 first4 tokens.
    old_results = {}
    for row in rows(DEV/"results.jsonl"):
        meta = row["init_response_generations_metadata"]["intervention"]
        old_results[row["id"], meta["sample_seed"], meta["condition_id"]] = row
    bridges = []
    for item in old_manifest[:8]+old_manifest[40:48]:
        _, reqs = load_request_bundle(ROOT/item["bundle"])
        req = next(r for r in reqs if r.condition_id == item["condition"])
        row = read(ROOT/item["pair"])
        bridges.append(dict(item=item, expected_first4=old_results[row["id"],req.sample_seed,req.condition_id]["generated_token_ids"][:4]))
    save(BASE/"bridge_probes.json", bridges)
    files = [BASE/"plan.json", BASE/"pairs.jsonl", BASE/"selected_source_records.jsonl",
             BASE/"runtime_profile.json", BASE/"bridge_probes.json", Path(__file__),
             ROOT/"scripts/game24_replication_20261017.py",
             ROOT/"scripts/start_game24_heldout82_a800_20261019.py",
             ROOT/"scripts/stage_game24_heldout_runtime_20261019.py",
             BASE/"runtime/runtime_manifest.json", BASE/"runtime_staging.json",
             DEV/"results.jsonl"]+sorted(target.glob("*.json"))
    save(BASE/"preflight.json", dict(passed=True, scientific_requests=492, paired_units=164,
        development_tokenization_parity_requests=120, reference_files_verified=146,
        minimum_prompt_tokens=min(lengths), maximum_prompt_tokens=max(lengths),
        versions={name: importlib.metadata.version(name) for name in profile["expected_versions"]},
        reference_preflight_sha256=sha(reference/"preflight.json"),
        hashes={p.relative_to(ROOT).as_posix(): sha(p) for p in files}))
    status("prepared_cpu_only", completed=0, total=492)


def key(record):
    meta = record["init_response_generations_metadata"]["intervention"]
    return record["id"], meta["sample_seed"], meta["condition_id"]


def summarize(records, qids):
    expected = {(q,s,c) for q in qids for s in SEEDS for c in CONDITIONS}
    indexed = {}
    for row in records:
        k = key(row)
        if k in indexed or k not in expected:
            raise RuntimeError("Unexpected/duplicate result key")
        indexed[k] = row
    n = len(qids)
    result = dict(completed=len(records), expected=6*n, missing=len(expected-set(indexed)),
                  independent_questions=n, conditions={}, effects={}, inferential_status="incomplete")
    for c in CONDITIONS:
        rs = [r for r in records if key(r)[2] == c]
        correct = sum(r["init_response_generations"][0].get("correctness") is True for r in rs)
        result["conditions"][c] = dict(correct=correct, requested=2*n, saved=len(rs), missing=2*n-len(rs),
            accuracy_over_all_requested=correct/(2*n),
            unknown_score=sum(r["init_response_generations"][0].get("correctness") is None for r in rs),
            finish_reasons=dict(Counter(r["init_response_generations"][0]["finish_reason"] for r in rs)))
    if set(indexed) == expected:
        result["paired_invariant_checks"] = verify_first_tokens(records)
        score = lambda q,s,c: int(indexed[q,s,c]["init_response_generations"][0].get("correctness") is True)
        per = [dict(id=q, **{c: sum(score(q,s,c) for s in SEEDS)/2 for c in CONDITIONS}) for q in qids]
        for a,b in [("R0","R2"),("R3","R2")]:
            delta = [r[a]-r[b] for r in per]
            result["effects"][a+"-"+b] = dict(estimate=sum(delta)/n, question_bootstrap_95ci=bootstrap(delta),
                recovery=sum(score(q,s,a)>score(q,s,b) for q in qids for s in SEEDS),
                damage=sum(score(q,s,a)<score(q,s,b) for q in qids for s in SEEDS),
                per_question_differences=delta)
        result.update(inferential_status="complete_question_cluster_bootstrap", per_question=per)
    return result


def analyse():
    plan = read(BASE/"plan.json")
    if sha(DEV/"results.jsonl") != plan["hashes"][(DEV/"results.jsonl").relative_to(ROOT).as_posix()]:
        raise RuntimeError("Development reference changed")
    held = rows(BASE/"results.jsonl")
    development = rows(DEV/"results.jsonl")
    result = dict(heldout82=summarize(held,plan["questions"]),
                  development20=summarize(development,plan["development_questions"]),
                  pooled102=summarize(development+held,plan["full_questions"]),
                  boundary=plan["report_boundary"])
    save(BASE/"analysis.json", result)
    return result


def run(resume=False):
    profile, reference = runtime()
    from selective_context.prompting import load_request_bundle
    from selective_context.phase0.real_smoke import evaluate
    from selective_context.phase0.thinking_pilot import extract_final_draft
    from selective_context.vllm_backend import SelectiveVLLMBackend
    pre = read(BASE/"preflight.json")
    for name,digest in pre["hashes"].items():
        if sha(ROOT/name) != digest:
            raise RuntimeError("Frozen input changed: "+name)
    if not pre["passed"] or sha(reference/"preflight.json") != pre["reference_preflight_sha256"]:
        raise RuntimeError("Reference manifest changed")
    for name,digest in read(reference/"preflight.json")["hashes"].items():
        if sha(reference/name) != digest:
            raise RuntimeError("Reference code changed")
    for name,version in profile["expected_versions"].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError("Runtime version changed: "+name)
    if os.environ.get("SC_HELDOUT_LAUNCHER") != "1":
        raise RuntimeError("Use the GPU ownership/storage launcher")
    existing = rows(BASE/"results.jsonl")
    if not resume and ((BASE/"results.jsonl").exists() or (BASE/"launch.json").exists()):
        raise RuntimeError("Explicit resume required")
    plan = read(BASE/"plan.json")
    summarize(existing,plan["questions"])
    done = {key(r) for r in existing}
    jobs = []
    for item in read(BASE/"prepared/manifest.json"):
        enc,requests = load_request_bundle(ROOT/item["bundle"])
        req = next(r for r in requests if r.condition_id == item["condition"])
        row = read(ROOT/item["pair"])
        jobs.append((enc,req,row))
    pending = [j for j in jobs if (j[2]["id"],j[1].sample_seed,j[1].condition_id) not in done]
    started = time.monotonic()
    budget = read(BASE/"budget.json") if (BASE/"budget.json").exists() else dict(spent_seconds=0)
    spent = budget["spent_seconds"]
    attempt = int(budget.get("attempts",0))+1
    save(BASE/(f"resume_{attempt}.json" if resume else "launch.json"),dict(started_utc=datetime.now(timezone.utc).isoformat(),
        pid=os.getpid(),gpu=os.environ.get("CUDA_VISIBLE_DEVICES"),model=profile["model"],
        backend=plan["backend"],scientific_requests=492,preserved=len(done),attempt=attempt))
    def tick(state,**extra):
        seconds = spent+time.monotonic()-started
        save(BASE/"budget.json",dict(spent_seconds=seconds,attempts=attempt,limit_hours=96))
        status(state,completed=len(done),total=492,elapsed_seconds=seconds,**extra)
    try:
        tick("loading_model")
        backend = SelectiveVLLMBackend(profile["model"],max_num_seqs=8)
        if backend.backend_name != plan["backend"]:
            raise RuntimeError("Incorrect backend")
        bridges = read(BASE/"bridge_probes.json")
        bridge_results = []
        for start in range(0,16,8):
            requests = []
            for item in bridges[start:start+8]:
                _,reqs = load_request_bundle(ROOT/item["item"]["bundle"])
                requests.append(next(r for r in reqs if r.condition_id == item["item"]["condition"]))
            generated = backend.generate_batch(requests,max_new_tokens=4)
            for spec,g in zip(bridges[start:start+8],generated):
                bridge_results.append(dict(condition=spec["item"]["condition"],expected=spec["expected_first4"],
                                           actual=g.generated_token_ids,match=g.generated_token_ids==spec["expected_first4"]))
        save(BASE/f"hardware_bridge_attempt{attempt}.json",dict(requests=16,max_new_tokens=4,excluded_from_science=True,
            all_match=all(r["match"] for r in bridge_results),results=bridge_results,
            boundary="Short fixed probes do not establish bitwise equality of full A100/A800 trajectories."))
        if not all(r["match"] for r in bridge_results):
            raise RuntimeError("Hardware bridge differs from fixed A100 first4-token probes; no heldout generation")
        probes = [j[1] for j in jobs[164:166]]
        a = backend.generate_batch(probes,max_new_tokens=4)
        got = {}
        b = backend.generate_batch(probes,max_new_tokens=4,on_result=lambda i,g:got.setdefault(i,g.generated_token_ids))
        if (len(got)!=2 or [g.generated_token_ids for g in a]!=[g.generated_token_ids for g in b]
                or any(got[i]!=g.generated_token_ids for i,g in enumerate(b))
                or a[0].generated_token_ids[0]!=a[1].generated_token_ids[0]):
            raise RuntimeError("Callback/paired first-token smoke failed")
        save(BASE/f"engineering_smoke_attempt{attempt}.json",dict(passed=True,requests=20,max_new_tokens=4,excluded_from_science=True))
        all_records = list(existing)
        with (BASE/"results.jsonl").open("a",encoding="utf-8") as f:
            # Original order, even boundaries and paired R2/R3 requests preserved on a fresh run.
            for start in range(0,len(pending),8):
                if spent+time.monotonic()-started >= 96*3600:
                    tick("stopped_time_limit")
                    analyse()
                    return
                import shutil
                if shutil.disk_usage(BASE).free < 2*1024**3:
                    tick("stopped_disk_space")
                    analyse()
                    return
                batch = pending[start:start+8]
                tick("running",batch_start=start)
                def persist(index,generation):
                    enc,req,row = batch[index]
                    k = row["id"],req.sample_seed,req.condition_id
                    if k in done: raise RuntimeError("Duplicate completion")
                    r = evaluate(row,enc,req,generation,task="game24")
                    final,parsed = extract_final_draft(generation.text,enc.text,backend.tokenizer.eos_token)
                    r.update(final_response=final,thinking_status=parsed,stratum="frozen_new_heldout",
                        source_trajectory_id=row["source_trajectory_id"],replication_hardware="A800")
                    r["init_response_generations_metadata"].update(enable_thinking=True,model_config_alias="Qwen3_8B_Thinking")
                    f.write(json.dumps(r,ensure_ascii=False)+"\n");f.flush();os.fsync(f.fileno())
                    done.add(k);all_records.append(r)
                    tick("running",last_saved=dict(id=row["id"],seed=req.sample_seed,condition=req.condition_id))
                backend.generate_batch([j[1] for j in batch],max_new_tokens=32768,temperature=.6,top_p=.95,top_k=20,on_result=persist)
                # Check every pair completed so far, including one-sided pairs preserved from an interrupted attempt.
                paired = {}
                for row in all_records:
                    q,s,c = key(row)
                    if c in ("R2","R3"): paired.setdefault((q,s),{})[c]=row
                complete = [r for group in paired.values() if len(group)==2 for r in group.values()]
                verify_first_tokens(complete)
        result = analyse()
        if len(done)!=492 or result["heldout82"].get("paired_invariant_checks")!=164:
            raise RuntimeError("Incomplete factorial")
        save(BASE/"completion.json",dict(completed=492,paired_checks=164,seconds=spent+time.monotonic()-started,pooled_completed=612))
        tick("complete_all102_no_further_expansion")
    except BaseException as exc:
        tick("failed_no_automatic_retry",error=f"{type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode",choices=["freeze","prepare","run","analyse","status"])
    ap.add_argument("--resume",action="store_true")
    args = ap.parse_args()
    if args.mode=="freeze": freeze()
    elif args.mode=="prepare": prepare()
    elif args.mode=="run": run(args.resume)
    elif args.mode=="analyse": print(json.dumps(analyse(),ensure_ascii=False,indent=2))
    else: print(json.dumps(read(BASE/"status.json"),ensure_ascii=False,indent=2))
