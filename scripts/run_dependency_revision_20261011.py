"""One bounded dependency-revision falsification batch; uses existing HF scorer."""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_dependency_revocation_20261011 import build_materials, audit_materials, SEED
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, save, append

CONDITIONS = ("CLEAN", "GENERAL", "CORRECT_ROOT")
MODEL = "/data2/huangrj/models/qwen3-8b"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]


def prepare(output, tokenizer_path=None):
    out = output/"dependency_revision"
    if (out/"manifest.json").exists(): return load(out/"manifest.json")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path or MODEL, local_files_only=True)
    questions = build_materials(32)
    audit = audit_materials(questions)
    lengths, candidate_lengths = [], []
    for question in questions:
        root_value = question["parameters"][0]
        for variant in question["variants"]:
            general = variant["prompts"]["GENERAL"]
            variant["prompts"] = {"CLEAN": variant["prompts"]["CLEAN"], "GENERAL": general,
                "CORRECT_ROOT": general.rsplit("Verified feedback:", 1)[0] +
                f"Verified feedback: the old cached value of S1 is incorrect. The correct value of S1 is {root_value}.\n"}
            variant["contexts"] = {}
            for condition, prompt in variant["prompts"].items():
                text = tokenizer.apply_chat_template([dict(role="user", content=prompt)],
                    tokenize=False, add_generation_prompt=True, enable_thinking=True)
                ids = tokenizer.encode(text, add_special_tokens=False)
                lengths.append(len(ids))
                readouts = []
                for readout in variant["readouts"]:
                    stem_ids = tokenizer.encode(readout["stem"], add_special_tokens=False)
                    if tokenizer.encode(text+readout["stem"], add_special_tokens=False) != ids+stem_ids:
                        raise ValueError("Unstable context/readout token boundary")
                    candidates = {}
                    for name, candidate in readout["candidates"].items():
                        candidate_ids = tokenizer.encode(candidate, add_special_tokens=False)
                        if tokenizer.encode(text+readout["stem"]+candidate, add_special_tokens=False) != ids+stem_ids+candidate_ids:
                            raise ValueError("Unstable candidate token boundary")
                        candidate_lengths.append(len(candidate_ids))
                        candidates[name] = dict(text=candidate, ids=candidate_ids)
                    readouts.append({**readout, "stem_ids": stem_ids, "candidates": candidates})
                variant["contexts"][condition] = dict(input_ids=ids, text=text, readouts=readouts)
    orders = list(itertools.permutations(CONDITIONS))
    manifest = dict(status="frozen_short_falsification_batch", model=MODEL, dtype="bfloat16",
        attention="sdpa", thinking_template=True, seed=SEED, gpu_hours=24,
        questions=questions, conditions=list(CONDITIONS), planned_base_graphs=32,
        planned_score_units=32*2*3*3,
        condition_orders={q["id"]: list(orders[i%6]) for i,q in enumerate(questions)},
        hypothesis="Even when supplied the exact corrected root value, downstream readouts may retain stale dependent values while unrelated correct values should remain stable.",
        primary="CORRECT_ROOT minus CLEAN in dependent corrected-minus-old margin, averaged over the two wirings within each base graph.",
        required_context="Report root correction and independent preservation separately. A negative dependent margin is not revision failure if CLEAN is also poor. No postselection on root performance.",
        secondary=["Independent preservation", "Root corrected-minus-old margin", "Dependency selectivity", "CORRECT_ROOT minus GENERAL", "Joint root-correct/dependent-stale/independent-correct pattern", "Length-normalized scores"],
        scope="Constructed arithmetic DAG, numeric teacher-forcing readouts inside the Qwen3 thinking template; not natural recognition, free-generation accuracy or a confirmed neural mechanism.",
        sampling="First 32 seed-shuffled parameter sets; no model/effect screening. Earlier eight CPU examples retained; no earlier model outcomes.",
        statistics="5000 paired base-graph bootstrap draws, seed 20261011; each contrast requires both wirings; list incomplete groups. Wiring/readout/token variants are not independent items.",
        stop="One frozen batch only. Shared original 24 GPU-hour cap, no automatic retry, expansion, head search or natural-generation followup.")
    audit.update(status="cpu_arithmetic_and_token_boundaries_passed", context_tokens=[min(lengths),max(lengths)],
        candidate_tokens=sorted(set(candidate_lengths)), conditions=list(CONDITIONS),
        scope="Exact arithmetic and counterfactual dependency audit plus every rendered Qwen3 context/stem/candidate token boundary.")
    save(out/"manifest.json", manifest)
    save(out/"material_audit.json", audit)
    save(out/"summary.json", dict(status="prepared_gpu_not_started", completed=0, planned=576))
    return manifest


def bootstrap(values):
    import numpy as np
    a = np.asarray(values, dtype=float)
    if not len(a): return dict(n=0, mean=None, ci=None)
    rng = np.random.default_rng(SEED)
    means = a[rng.integers(0, len(a), size=(5000,len(a)))].mean(axis=1)
    return dict(n=len(a), mean=float(a.mean()), ci=np.quantile(means,[.025,.975]).tolist())


def analyse(manifest, out, status=None, error=None):
    records = rows(out/"scores.jsonl")
    keyed = {(r["id"],r["wiring"],r["condition"],r["node"]):r for r in records}
    per_question, missing = [], []
    for question in manifest["questions"]:
        qid = question["id"]
        expected = [(qid,v["wiring"],c,r["node"]) for v in question["variants"]
                    for c in CONDITIONS for r in v["readouts"]]
        absent = [key for key in expected if key not in keyed]
        if absent:
            missing.append(dict(id=qid, missing=[list(x[1:]) for x in absent]))
            continue
        def margins(c, field):
            root, dependent, independent = [], [], []
            for variant in question["variants"]:
                for readout in variant["readouts"]:
                    row = keyed[qid,variant["wiring"],c,readout["node"]]
                    target = root if readout["node"]=="S1" else dependent if readout["depends_on_error"] else independent
                    target.append(row[field])
            return {"root":sum(root)/len(root), "dependent":sum(dependent)/len(dependent),
                    "independent":sum(independent)/len(independent)}
        values = {c:margins(c,"margin") for c in CONDITIONS}
        normalized = {c:margins(c,"mean_margin") for c in CONDITIONS}
        joint = {}
        for condition in CONDITIONS:
            counts = dict(root_correct=0, dependent_correct=0, independent_preserved=0,
                          all_correct=0, root_correct_dependent_stale_independent_correct=0)
            for variant in question["variants"]:
                data = {r["node"]:keyed[qid,variant["wiring"],condition,r["node"]] for r in variant["readouts"]}
                root = data["S1"]["margin"] > 0
                dep = next(r for r in variant["readouts"] if r["node"]!="S1" and r["depends_on_error"])
                ind = next(r for r in variant["readouts"] if not r["depends_on_error"])
                dep_correct, ind_correct = data[dep["node"]]["margin"]>0, data[ind["node"]]["margin"]<0
                counts["root_correct"] += root
                counts["dependent_correct"] += dep_correct
                counts["independent_preserved"] += ind_correct
                counts["all_correct"] += root and dep_correct and ind_correct
                counts["root_correct_dependent_stale_independent_correct"] += root and data[dep["node"]]["margin"]<0 and ind_correct
            joint[condition] = counts
        per_question.append(dict(id=qid, margins=values, normalized=normalized, joint=joint))
    primary = bootstrap([q["margins"]["CORRECT_ROOT"]["dependent"]-q["margins"]["CLEAN"]["dependent"] for q in per_question])
    normalized_primary = bootstrap([q["normalized"]["CORRECT_ROOT"]["dependent"]-q["normalized"]["CLEAN"]["dependent"] for q in per_question])
    by_condition = {}
    for condition in CONDITIONS:
        by_condition[condition] = dict(
            margins={key:bootstrap([q["margins"][condition][key] for q in per_question]) for key in ("root","dependent","independent")},
            normalized_margins={key:bootstrap([q["normalized"][condition][key] for q in per_question]) for key in ("root","dependent","independent")},
            wiring_denominator=2*len(per_question),
            counts={key:sum(q["joint"][condition][key] for q in per_question) for key in per_question[0]["joint"][condition]} if per_question else {})
    result = dict(status=status or ("completed" if len(keyed)==manifest["planned_score_units"] else "partial"),
        completed_score_units=len(keyed), planned_score_units=manifest["planned_score_units"],
        complete_base_graphs=len(per_question), primary=primary, length_normalized_primary=normalized_primary,
        conditions=by_condition, by_question=per_question, missing=missing, error=error,
        interpretation="Root preference is not spontaneous recognition; score counts are not natural accuracy. No claim of functional separation from nonsignificance. This batch is a falsification screen, not a new benchmark or neural mechanism proof.")
    save(out/"summary.json", result)
    (out/"report.md").write_text("# Dependency revision: short falsification screen\n\n"+
        "Root-correction feedback gives the exact answer at S1. Dependent and independent readouts must be considered together.\n\n```json\n"+
        json.dumps({k:v for k,v in result.items() if k not in ("by_question","missing")},indent=2)+"\n```\n", encoding="utf8")
    return result


def run(output, manifest):
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.route_revocation import RouteRevocationBackend
    if os.environ.get("SC_DEPENDENCY_LAUNCHER") != "1":
        raise RuntimeError("Use the shared launcher --dependency-revision")
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    if load(output/"budget.json").get("active"):
        raise RuntimeError("Shared budget already active")
    out = output/"dependency_revision"
    done = {(r["id"],r["wiring"],r["condition"],r["node"]) for r in rows(out/"scores.jsonl")}
    budget = Budget(output/"budget.json",24)
    status, error = "completed", None
    try:
        save(out/"run_state.json",dict(status="loading_model",completed=len(done)))
        model = AutoModelForCausalLM.from_pretrained(manifest["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0")
        backend = RouteRevocationBackend(model, budget.check)
        started = time.monotonic()
        for question in manifest["questions"]:
            qid = question["id"]
            for variant in question["variants"]:
                wiring = variant["wiring"]
                for condition in manifest["condition_orders"][qid]:
                    context = variant["contexts"][condition]
                    todo = [r for r in context["readouts"] if (qid,wiring,condition,r["node"]) not in done]
                    if not todo: continue
                    ids = context["input_ids"]
                    history = dict(draft_token_span=[0,0],cutoff=len(ids))
                    prefill = backend.advance(ids,None,(0,0),"FULL",len(ids))
                    for readout in todo:
                        request = dict(id=qid,wiring=wiring,condition=condition,node=readout["node"])
                        save(out/"current_request.json",request)
                        begin = time.monotonic()
                        scores = backend.score(prefill,history,"FULL",readout)
                        if not (out/"engine_acceptance.json").exists():
                            # One direct, native-causal teacher-forcing reference for the new numeric readout.
                            reference, differences = {}, []
                            with torch.inference_mode():
                                base = ids + readout["stem_ids"]
                                for name, candidate in readout["candidates"].items():
                                    all_ids = base + candidate["ids"]
                                    logits = model(input_ids=torch.tensor([all_ids],device=backend.device),
                                        use_cache=False,return_dict=True).logits[0,len(base)-1:len(all_ids)-1]
                                    lp = logits.float().log_softmax(-1)
                                    reference[name] = float(lp.gather(1,torch.tensor(candidate["ids"],device=backend.device).view(-1,1)).sum())
                                    differences.append(abs(reference[name]-scores[name]["log_probability"]))
                            save(out/"engine_acceptance.json",dict(request=request,passed=max(differences)<=.15,
                                reference=reference,cached_scores=scores,max_sum_logp_difference=max(differences),
                                tolerance=.15,scope="First numeric readout: existing cached FULL scorer versus native causal full forward, including token boundaries."))
                            if max(differences)>.15:
                                raise RuntimeError("Cached numeric scoring disagrees with native full forward")
                        row = dict(**request, scores=scores, gold=readout["gold"],
                            depends_on_error=readout["depends_on_error"],
                            margin=scores["changed"]["log_probability"]-scores["old"]["log_probability"],
                            mean_margin=scores["changed"]["mean_log_probability"]-scores["old"]["mean_log_probability"],
                            source="manifest.json", model=manifest["model"], parameters=dict(dtype="bfloat16",attention="sdpa",thinking_template=True),
                            prefix_tokens=len(ids), gpu_seconds=time.monotonic()-begin)
                        append(out/"scores.jsonl",row)
                        done.add((qid,wiring,condition,readout["node"]))
                        elapsed = time.monotonic()-started
                        save(out/"run_state.json",dict(status="running",completed=len(done),planned=576,
                            elapsed_scoring_seconds=elapsed,estimated_remaining_seconds=elapsed/max(1,len(done))*(576-len(done))))
                        budget.check(force=True)
                    del prefill
            analyse(manifest,out,"running")
    except BudgetExceeded:
        status="budget_exhausted"
    except Exception as exc:
        status,error="failed",repr(exc)
        raise
    finally:
        budget.close()
        result = analyse(manifest,out,status,error)
        save(out/"run_state.json",dict(status=status,completed=result["completed_score_units"],error=error))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--tokenizer",type=str)
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--analyse",action="store_true")
    parser.add_argument("--status",action="store_true")
    args=parser.parse_args()
    out=args.output/"dependency_revision"
    if args.status:
        for name in ("run_state.json","summary.json"):
            if (out/name).exists():
                data=load(out/name)
                print(json.dumps({k:v for k,v in data.items() if k not in ("by_question","missing","conditions")},indent=2))
        return
    manifest=prepare(args.output,args.tokenizer)
    if args.analyse: analyse(manifest,out)
    elif args.resume: run(args.output,manifest)
    else: print(json.dumps(dict(status="prepared",graphs=32,planned_score_units=576,
        material_audit=load(out/"material_audit.json"))))


if __name__=="__main__":
    main()
