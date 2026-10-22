"""Frozen 20-question replication using the hash-verified paper code snapshot.

freeze/analyse are CPU-only. prepare tokenizes without loading model weights.
run requires the explicitly launched, validated selective backend.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/game24-replication-qwen3-8b-development-20261017"
DATA = ROOT / "docs/game24_100q_8b"
SEEDS = [927001, 927002]
CONDITIONS = ["R0", "R2", "R3"]
sys.path.insert(0, str(ROOT))
REFERENCE = Path("/data2/gaojc/tmp/game24-batch03-validation-20260924")
if REFERENCE.is_dir():
    sys.path.insert(0, str(REFERENCE))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    if not path.exists():
        return []
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_rows(path, values):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for value in values:
            f.write(json.dumps(value, ensure_ascii=False) + "\n")


def state(status, **extra):
    obj = dict(status=status, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
    save(BASE / "status.json", obj)
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def freeze():
    """Select drafts without loading any intervention outcomes or held-out raw text."""
    if BASE.exists():
        raise RuntimeError("Refusing to overwrite a replication freeze")
    split = read(DATA / "game24_split_manifest.json")
    eligible = rows(DATA / "game24_eligible_100.jsonl")
    by_id = {r["canonical_question_id"]: r for r in eligible}
    development, held = split["development"], split["held_out"]
    if (split["state"] != "frozen" or len(by_id) != 102 or len(development) != 20
            or len(held) != 82 or set(development) & set(held)
            or set(development + held) != set(by_id)):
        raise RuntimeError("Unexpected frozen pool/split")
    trajectories = {r["trajectory_id"]: r for r in rows(DATA / "game24_trajectory_pool.jsonl")}
    pairs, sources = [], []
    cache = {}
    for qid in development:
        cohort = [trajectories[t] for t in by_id[qid]["trajectory_ids"]]
        if len(cohort) != 8 or {r["sample_index"] for r in cohort} != set(range(8)):
            raise RuntimeError("Incomplete eligible cohort")
        pool = sorted((r for r in cohort if r["classification"] == "substantive_error"),
                      key=lambda r: (r["source_model"], r["sample_index"]))
        if len(pool) < 2 or any(r["source_model"] != "Qwen3_8B_Thinking" for r in cohort):
            raise RuntimeError("Unexpected anchor/witnesses")
        choice = random.Random("20261017:" + qid).choice(pool)
        source = ROOT / choice["source_path"]
        if source not in cache:
            cache[source] = source.read_text(encoding="utf-8").splitlines()
        line = cache[source][choice["source_line"] - 1]
        if hashlib.sha256(line.encode()).hexdigest() != choice["raw_record_sha256"]:
            raise RuntimeError("Raw source checksum mismatch")
        raw = json.loads(line)
        draft = raw["final_response"]
        if (not draft.strip() or raw["thinking_status"] != "parsable_thinking"
                or raw["init_response_generations"][0]["finish_reason"] not in ("eos", "stop")
                or sorted(raw["answer"]) != sorted(by_id[qid]["numbers"])):
            raise RuntimeError("Invalid complete source draft")
        pairs.append(dict(id=qid, task="game24", problem=raw["problem"], answer=raw["answer"],
            traj1=draft, audit_status="substantive_failed", stratum="frozen_new_development",
            benchmark="Game24", source_model="Qwen3_8B_Thinking", target_model="Qwen3_8B_Thinking",
            self_or_cross="self", source_trajectory_id=choice["trajectory_id"],
            source_path=choice["source_path"], source_line=choice["source_line"],
            raw_record_sha256=choice["raw_record_sha256"], source_sample_index=choice["sample_index"],
            draft_sha256=hashlib.sha256(draft.encode()).hexdigest(), eligible_failed_pool_size=len(pool)))
        sources.append(dict(trajectory=choice, raw_record=raw))
    BASE.mkdir(parents=True)
    write_rows(BASE / "pairs.jsonl", pairs)
    write_rows(BASE / "selected_source_records.jsonl", sources)
    plan = dict(protocol="frozen_development_R0_R2_R3_replication_v1", status="frozen_before_outcomes",
        created_utc=datetime.now(timezone.utc).isoformat(), questions=development, held_out_count=82,
        held_out_generation_authorized_by_this_plan=False, conditions=CONDITIONS, seeds=SEEDS,
        scientific_requests=120, engineering_requests=4, engineering_max_new_tokens=4,
        draft_selection="random.Random('20261017:'+canonical_id).choice(substantive errors sorted by model/sample_index)",
        draft_representation="Complete final_response, including its solution steps, exactly as in old paper; Thinking text remains in source archive.",
        predictions=["R0-R2 > 0: failed history causes drag", "R3-R2 > 0: late blocking improves accuracy"],
        possible_refutation="Zero/negative effects or wide intervals limit the old claim; do not reselect questions/drafts.",
        primary_effects=["R0-R2", "R3-R2"],
        statistics="Average two paired seeds within each question; 5000 percentile question bootstrap draws, seed20261017. Report paired recovery and damage.",
        scoring="Same official Game24 scorer as paper. correctness is True counts as success; None/truncations/missing stay in all-request denominators and are separately reported.",
        sampling=dict(temperature=.6, top_p=.95, top_k=20, context=32768, max_new_tokens=32768,
                      batch_size=8, enable_thinking=True, prefix_caching=False),
        backend="vllm_selective_flex_0.11.0", model="/data2/huangrj/models/qwen3-8b",
        execution="Reuse idle project-owned A100 GPU4 resident; no new weights/environment or unrelated process changes.",
        timing=dict(reference_requests=64, reference_seconds=20362.94637685269,
                    scaled_estimate_hours=20362.94637685269/64*120/3600,
                    stop_starting_new_batches_after_hours=16,
                    limit_scope="16 hours from run start, checked between batches; an in-flight batch may finish later."),
        expected_storage="Under 1 GiB for manifests/raw results/logs; no weights/checkpoints copied.",
        reference_config="runs/game24_batch03_validation_20260925_raw/config.json",
        next_step="CPU heterogeneity on development only, then review one falsifiable extension; no automatic R4, local masks, extra drafts, seeds, or held-out requests.",
        hashes={str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in
                [DATA/"game24_split_manifest.json", DATA/"game24_eligible_100.jsonl",
                 DATA/"game24_trajectory_pool.jsonl", BASE/"pairs.jsonl", BASE/"selected_source_records.jsonl"]})
    save(BASE / "plan.json", plan)
    state("frozen_cpu_only", completed=0, total=120)


def prepare(tokenizer_path):
    from transformers import AutoTokenizer
    from selective_context.prompting import (encode_direct_prompt, encode_prompt, make_request,
        make_r2_r4_requests, persist_request_bundle, render_chat_prompt)
    from selective_context.schema import AccessMode
    from selective_context.tasks import independent_prompt
    from selective_context.vllm_mask import NEVER, key_block_onsets, request_metadata
    plan = read(BASE / "plan.json")
    for name in ("pairs.jsonl", "selected_source_records.jsonl"):
        relative = (BASE / name).relative_to(ROOT).as_posix()
        if sha(BASE / name) != plan["hashes"][relative]:
            raise RuntimeError("Frozen source changed")
    target = BASE / "prepared"
    if target.exists():
        raise RuntimeError("Refusing prepared-bundle overwrite")
    tok = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True, use_fast=True)
    target.mkdir()
    clean, paired, lengths = [], [], []
    for row in rows(BASE / "pairs.jsonl"):
        key = row["id"].split(":")[-1]
        pair_path = target / (key + ".pair.json")
        save(pair_path, row)
        for seed in SEEDS:
            r0 = encode_direct_prompt(tok, render_chat_prompt(tok, independent_prompt(row["problem"], task="game24"), True))
            r2 = encode_prompt(tok, render_chat_prompt(tok, independent_prompt(row["problem"], row["traj1"], "game24"), True))
            direct = make_request(r0, "R0", AccessMode.FULL, seed)
            interventions = [r for r in make_r2_r4_requests(r2, seed) if r.condition_id in ("R2", "R3")]
            for name, enc, requests in [("r0", r0, [direct]), ("r2_r3", r2, interventions)]:
                n = len(enc.input_ids)
                if 32768-n < 8192:
                    raise RuntimeError("Insufficient generation room; do not truncate/reselect")
                lengths.append(n)
                path = target / (f"{key}.{seed}.{name}.json")
                persist_request_bundle(path, enc, requests)
                for req in requests:
                    req.validate()
                    onsets = key_block_onsets(request_metadata(req))
                    lo, hi = req.draft_token_span
                    expected = [n if req.condition_id == "R3" and lo <= i < hi else NEVER for i in range(n)]
                    if onsets != expected:
                        raise RuntimeError("Incorrect late/full mask")
                    item = dict(task="game24", bundle=path.relative_to(ROOT).as_posix(),
                                pair=pair_path.relative_to(ROOT).as_posix(), condition=req.condition_id)
                    (clean if name == "r0" else paired).append(item)
    # Forty R0s form five full batches; each R2/R3 pair then shares a batch.
    manifest = clean + paired
    if len(manifest) != 120 or len(clean) != 40:
        raise RuntimeError("Incorrect request count")
    save(target / "manifest.json", manifest)
    # Check unchanged old prompt tokenization against actual frozen paper bundles.
    reference = REFERENCE
    old_manifest = reference / "outputs/game24-batch03-8q-prepared/manifest.json"
    from selective_context.prompting import load_request_bundle
    parity = 0
    for item in read(old_manifest):
        enc, _ = load_request_bundle(reference / item["bundle"])
        old = read(reference / item["pair"])
        direct = item["condition"] == "R0"
        prompt = independent_prompt(old["problem"], None if direct else old["traj1"], "game24")
        new = (encode_direct_prompt if direct else encode_prompt)(tok, render_chat_prompt(tok, prompt, True))
        if new.input_ids != enc.input_ids:
            raise RuntimeError("Old paper prompt/tokenizer parity failed")
        parity += 1
    files = [BASE/"plan.json", BASE/"pairs.jsonl", BASE/"selected_source_records.jsonl", Path(__file__)] + sorted(target.glob("*.json"))
    old_preflight = read(reference / "preflight.json")
    for name, digest in old_preflight["hashes"].items():
        if sha(reference / name) != digest:
            raise RuntimeError("Paper snapshot checksum mismatch: " + name)
    save(BASE / "preflight.json", dict(passed=True, scientific_requests=120, paired_units=40,
        reference_root=str(reference), reference_preflight_sha256=sha(reference/"preflight.json"),
        reference_files_verified=len(old_preflight["hashes"]),
        old_prompt_tokenization_parity_requests=parity, minimum_prompt_tokens=min(lengths),
        maximum_prompt_tokens=max(lengths), minimum_completion_room=32768-max(lengths),
        versions={k: importlib.metadata.version(k) for k in ("vllm", "torch", "transformers")},
        hashes={p.relative_to(ROOT).as_posix(): sha(p) for p in files}))
    state("prepared_cpu_only", completed=0, total=120)


def verify_first_tokens(records):
    groups = {}
    for record in records:
        meta = record["init_response_generations_metadata"]["intervention"]
        if meta["condition_id"] in ("R2", "R3"):
            groups.setdefault((record["id"], meta["sample_seed"]), {})[meta["condition_id"]] = record
    checked = 0
    for group in groups.values():
        if set(group) != {"R2", "R3"}:
            raise RuntimeError("Incomplete in-batch R2/R3 pair")
        a, b = group["R2"], group["R3"]
        ma = a["init_response_generations_metadata"]["intervention"]
        mb = b["init_response_generations_metadata"]["intervention"]
        if (a["init_response_prompt"] != b["init_response_prompt"]
                or ma["input_ids"] != mb["input_ids"]
                or ma["draft_token_span"] != mb["draft_token_span"]
                or not a["generated_token_ids"] or not b["generated_token_ids"]
                or a["generated_token_ids"][0] != b["generated_token_ids"][0]):
            raise RuntimeError("R2/R3 text/token/span/first-token invariant failed")
        checked += 1
    return checked


def run(backend=None):
    """Initialize only inside the launcher after the exact snapshot passes verification."""
    from selective_context.prompting import load_request_bundle
    from selective_context.phase0.real_smoke import evaluate
    from selective_context.phase0.thinking_pilot import extract_final_draft
    preflight = read(BASE / "preflight.json")
    if not preflight["passed"] or importlib.metadata.version("vllm") != "0.11.0":
        raise RuntimeError("Unvalidated runtime")
    for name, digest in preflight["hashes"].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError("Frozen input changed: " + name)
    if sha(REFERENCE/"preflight.json") != preflight["reference_preflight_sha256"]:
        raise RuntimeError("Paper snapshot manifest changed")
    for name, digest in read(REFERENCE/"preflight.json")["hashes"].items():
        if sha(REFERENCE/name) != digest:
            raise RuntimeError("Paper snapshot changed: " + name)
    if (BASE / "results.jsonl").exists() or (BASE / "launch.json").exists():
        raise RuntimeError("No automatic restart/retry")
    plan = read(BASE / "plan.json")
    manifest = read(BASE / "prepared/manifest.json")
    jobs = []
    for item in manifest:
        enc, requests = load_request_bundle(ROOT / item["bundle"])
        req = next(r for r in requests if r.condition_id == item["condition"])
        jobs.append((enc, req, read(ROOT / item["pair"])))
    started = time.monotonic()
    save(BASE / "launch.json", dict(started_utc=datetime.now(timezone.utc).isoformat(),
        pid=os.getpid(), gpu=os.environ.get("CUDA_VISIBLE_DEVICES"),
        model=plan["model"], backend=plan["backend"], existing_resident_reused=False,
        reference_root=str(REFERENCE),
        scientific_requests=120, plan_sha256=sha(BASE / "plan.json"), preflight_sha256=sha(BASE / "preflight.json")))
    completed = checked = 0
    state("engineering_smoke", completed=0, total=120)
    try:
        if backend is None:
            if os.environ.get("SC_REPLICATION_LAUNCHER") != "1":
                raise RuntimeError("Use the bounded replication launcher")
            import selective_context.vllm_backend as module
            if Path(module.__file__).resolve() != REFERENCE/"selective_context/vllm_backend.py":
                raise RuntimeError("Incorrect selective backend source")
            backend = module.SelectiveVLLMBackend(plan["model"], max_num_seqs=8)
        if backend.backend_name != "vllm_selective_flex_0.11.0" or backend.engine.llm_engine.has_unfinished_requests():
            raise RuntimeError("Backend version mismatch or busy engine")
        # Same pair, synchronous and durable callback paths. Four short requests.
        probes = [j[1] for j in jobs[40:42]]
        a = backend.generate_batch(probes, max_new_tokens=4)
        got = {}
        b = backend.generate_batch(probes, max_new_tokens=4, on_result=lambda i, g: got.setdefault(i, g.generated_token_ids))
        if (len(got) != 2 or [g.generated_token_ids for g in a] != [g.generated_token_ids for g in b]
                or any(got[i] != g.generated_token_ids for i, g in enumerate(b))
                or a[0].generated_token_ids[0] != a[1].generated_token_ids[0]):
            raise RuntimeError("Engineering callback/first-token smoke failed")
        save(BASE / "engineering_smoke.json", dict(passed=True, requests=4, max_new_tokens=4, excluded_from_science=True))
        with (BASE / "results.jsonl").open("x", encoding="utf-8") as f:
            for start in range(0, len(jobs), 8):
                if time.monotonic()-started >= 16*3600:
                    state("stopped_time_limit_no_expansion", completed=completed, total=120, paired_checks=checked)
                    analyse()
                    return
                batch, records = jobs[start:start+8], []
                state("running", completed=completed, total=120, paired_checks=checked, batch_start=start,
                      elapsed_seconds=time.monotonic()-started)
                def persist(index, generation):
                    nonlocal completed
                    enc, req, row = batch[index]
                    record = evaluate(row, enc, req, generation, task="game24")
                    final, status = extract_final_draft(generation.text, enc.text, backend.tokenizer.eos_token)
                    record.update(final_response=final, thinking_status=status, stratum=row["stratum"],
                                  source_trajectory_id=row["source_trajectory_id"])
                    record["init_response_generations_metadata"].update(enable_thinking=True, model_config_alias="Qwen3_8B_Thinking")
                    f.write(json.dumps(record, ensure_ascii=False)+"\n")
                    f.flush()
                    os.fsync(f.fileno())
                    records.append(record)
                    completed += 1
                    state("running", completed=completed, total=120, paired_checks=checked,
                          elapsed_seconds=time.monotonic()-started,
                          last_saved=dict(id=row["id"], seed=req.sample_seed, condition=req.condition_id))
                backend.generate_batch([j[1] for j in batch], max_new_tokens=32768,
                                       temperature=.6, top_p=.95, top_k=20, on_result=persist)
                checked += verify_first_tokens(records)
        if completed != 120 or checked != 40:
            raise RuntimeError("Incomplete generation/pair audit")
        save(BASE / "completion.json", dict(completed=120, paired_checks=40, seconds=time.monotonic()-started))
        analyse()
        state("complete_no_expansion", completed=120, total=120, paired_checks=40, seconds=time.monotonic()-started)
    except BaseException as exc:
        state("failed_no_retry", completed=completed, total=120, error=f"{type(exc).__name__}: {exc}")
        raise


def bootstrap(values, draws=5000):
    rng = random.Random(20261017)
    n = len(values)
    samples = sorted(sum(rng.choice(values) for _ in range(n))/n for _ in range(draws))
    return [samples[int((draws-1)*p)] for p in (.025, .975)]


def analyse():
    plan = read(BASE / "plan.json")
    records = rows(BASE / "results.jsonl")
    expected = {(q, s, c) for q in plan["questions"] for s in SEEDS for c in CONDITIONS}
    indexed = {}
    for record in records:
        m = record["init_response_generations_metadata"]["intervention"]
        key = record["id"], m["sample_seed"], m["condition_id"]
        if key not in expected or key in indexed:
            raise RuntimeError("Unexpected/duplicate scientific result")
        indexed[key] = record
    summary = dict(completed=len(records), expected=120, missing=len(expected-set(indexed)),
                   independent_questions=20, conditions={}, effects={}, inferential_status="incomplete")
    for c in CONDITIONS:
        rs = [r for (q, s, condition), r in indexed.items() if condition == c]
        correct = sum(r["init_response_generations"][0].get("correctness") is True for r in rs)
        summary["conditions"][c] = dict(correct=correct, requested=40, saved=len(rs), missing=40-len(rs),
            accuracy_over_all_requested=correct/40,
            unknown_score=sum(r["init_response_generations"][0].get("correctness") is None for r in rs),
            finish_reasons=dict(Counter(r["init_response_generations"][0]["finish_reason"] for r in rs)),
            generated_tokens=[len(r["generated_token_ids"]) for r in rs])
    if set(indexed) == expected:
        summary["paired_invariant_checks"] = verify_first_tokens(records)
        score = lambda q, s, c: int(indexed[q, s, c]["init_response_generations"][0].get("correctness") is True)
        per_question = []
        for q in plan["questions"]:
            per_question.append(dict(id=q, **{c: sum(score(q,s,c) for s in SEEDS)/2 for c in CONDITIONS}))
        for a, b in [("R0", "R2"), ("R3", "R2")]:
            values = [q[a]-q[b] for q in per_question]
            summary["effects"][a+"-"+b] = dict(estimate=sum(values)/20, question_bootstrap_95ci=bootstrap(values),
                recovery=sum(score(q,s,a)>score(q,s,b) for q in plan["questions"] for s in SEEDS),
                damage=sum(score(q,s,a)<score(q,s,b) for q in plan["questions"] for s in SEEDS),
                per_question_differences=values)
        summary.update(inferential_status="complete_question_cluster_bootstrap", per_question=per_question)
    save(BASE / "analysis.json", summary)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["freeze", "prepare", "run", "analyse", "status"])
    ap.add_argument("--tokenizer", default="/data2/huangrj/models/qwen3-8b")
    args = ap.parse_args()
    if args.mode == "freeze": freeze()
    elif args.mode == "prepare": prepare(args.tokenizer)
    elif args.mode == "run": run()
    elif args.mode == "analyse": print(json.dumps(analyse(), ensure_ascii=False, indent=2))
    else: print(json.dumps(read(BASE/"status.json"), ensure_ascii=False, indent=2))
