"""Natural failed-history replication, then same-candidate checking and adoption."""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import os
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_generation_diagnostics_20261005 import Budget,BudgetExceeded,append,save
from run_dependency_revision_20261011 import bootstrap,load,rows
from run_identity_mvp_20261011 import audit_expression,score_response
from run_identity_prospective_20261011 import repair_prompt
from run_information_followup_20261005 import tree

SUBDIR="candidate_adoption"
SEED=20261015
SEEDS=(20261015,20261016)
CONDITIONS=("COUNT_CLEAN","COUNT_HISTORY","IDENTITY_CLEAN","IDENTITY_HISTORY")
PHASES=("NATURAL","CANDIDATES")


def symbolise(expression,bindings):
    """Preserve arithmetic tree/value while giving original occurrences explicit names.

    A legal numeric candidate uses each card once. Excess occurrences cycle back to
    an existing same-value card and remain illegal; out-of-inventory values stay literals.
    """
    by_value={}
    for name,value in bindings.items(): by_value.setdefault(value,[]).append(name)
    used=Counter()
    class Convert(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int and node.value in by_value:
                names=by_value[node.value]
                name=names[used[node.value]%len(names)]
                used[node.value]+=1
                return ast.copy_location(ast.Name(id=name,ctx=ast.Load()),node)
            return node
    return ast.unparse(Convert().visit(tree(expression)))


def prepare(output):
    out=output/SUBDIR
    if (out/"manifest.json").exists(): return load(out/"manifest.json")
    pool=load(out/"failure_pool.json")
    questions=[q for q in pool["questions"] if not q["prior_identity_exposure"]]
    questions.sort(key=lambda q:tuple(q["answer"]))
    rng=random.Random(SEED)
    rng.shuffle(questions)
    if len(questions)!=30: raise ValueError("Expected the audited 30 identity-unseen natural failed histories")
    orders=list(itertools.permutations(CONDITIONS))
    for i,q in enumerate(questions):
        q.update(split="discovery" if i<15 else "replication",bindings=dict(zip(rng.sample(list("ABCD"),4),q["answer"])),
                 condition_order=list(orders[i%len(orders)]),first_seed_old_index=1+i%2)
        q["old_numeric"]=q["old_audit"]["numeric_expression"]
        q["legal_numeric"]=audit_expression(q["legal_expression"],q["answer"])["numeric_expression"]
        q["old_symbolic"]=symbolise(q["old_numeric"],q["bindings"])
        q["legal_symbolic"]=symbolise(q["legal_numeric"],q["bindings"])
        legal=audit_expression(q["legal_symbolic"],q["answer"],q["bindings"])
        bad=audit_expression(q["old_symbolic"],q["answer"],q["bindings"],allow_literals=True)
        if not legal.get("correct") or bad.get("correct") or bad.get("value")!=q["old_audit"]["value"]:
            raise ValueError("Candidate conversion changed legality or arithmetic value")
    m=dict(model="/data2/huangrj/models/qwen3-8b",dtype="bfloat16",backend="native_vllm_0.11.0",
        sampling=dict(temperature=.6,top_p=.95,top_k=20),design_seed=SEED,seeds=list(SEEDS),
        conditions=list(CONDITIONS),phases=list(PHASES),questions=questions,max_new_tokens=8192,
        max_model_len=32768,max_num_seqs=8,planned_requests=480,
        source_pool="candidate_adoption/failure_pool.json",
        cohort="All 30 same-model Thinking natural failures not used in identity_mvp or identity_prospective; model failure eligibility, not intervention outcome selection. Histories and some questions have appeared in older unrelated diagnostics; not a pristine dataset.",
        discovery=[q["id"] for q in questions[:15]],replication=[q["id"] for q in questions[15:]],
        selection="Fixed source priority and first eligible completed false-scored parseable draft per number multiset; all 30, seeded split before GPU. No fresh draft screening.",
        hypotheses=["Identity improves natural repair beyond explicit numeric quotas, especially with failed history.",
                    "With the same legal and illegal candidates available, failed history changes validity judgment or final choice.",
                    "The candidate task can separate explicit correct rejection from subsequent old-candidate adoption; it cannot establish an internal neural mechanism."],
        primary="Within-phase history interaction in final task/choice accuracy; two seeds averaged within question, discovery and replication reported separately and pooled.",
        candidate_metrics=["Choice of valid candidate", "Both validity judgments correct", "Acceptance of old invalid candidate", "Old invalid candidate selected", "Both judgments correct but old invalid candidate selected"],
        analysis="All 30 questions retained including three non-inventory-only errors. Candidate order reverses between seeds and is balanced by question. Same JSON output in both candidate representations. Source error type and duplicates are descriptive strata. No claim from a chosen successful case or short score without natural generation.",
        estimate=dict(max_generated_tokens=480*8192,tokens_per_second=350,loading_seconds=300),
        stop="Original shared 24 GPU-hour cap; no automatic resampling, parameter tuning, model expansion or head search. Both phases fixed before measurement. Report nulls and failures as well as positives.")
    save(out/"manifest.json",m)
    save(out/"run_state.json",dict(status="prepared_not_launched",completed=0,planned=480))
    return m


def old_index(q,seed):
    return q["first_seed_old_index"] if seed==SEEDS[0] else 3-q["first_seed_old_index"]


def prompt_for(q,condition,phase,seed):
    if phase=="NATURAL":
        return repair_prompt(q,dict(usable=True,feedback="INCORRECT",draft=q["draft"]),condition)
    prompt=f"Original problem:\n{q['problem']}\n"
    if condition.endswith("HISTORY"):
        prompt+=("\nThe following draft has an INCORRECT final answer.\n-- beginning of the draft --\n"+
                 q["draft"]+"\n-- end of the draft --\n")
    counts=", ".join(f"{n}: {count}" for n,count in sorted(Counter(q["answer"]).items()))
    prompt+=("\nRequired occurrence counts of the original numerical values: "+counts+
             ". A valid expression must equal 24, use exactly these quantities and no other operands, "
             "with only +, -, *, / and parentheses.\n")
    if condition.startswith("IDENTITY"):
        table=", ".join(f"{name}={value}" for name,value in q["bindings"].items())
        prompt+=("Treat the original number occurrences as distinct cards: "+table+
                 ". Equal numerical values are still different cards. A valid expression must use A, B, C and D exactly once each.\n")
        bad,good=q["old_symbolic"],q["legal_symbolic"]
    else: bad,good=q["old_numeric"],q["legal_numeric"]
    candidates=[bad,good] if old_index(q,seed)==1 else [good,bad]
    prompt+=(f"\nOption 1: {candidates[0]}\nOption 2: {candidates[1]}\n\n"
        "Evaluate both options against all original constraints, then choose the valid option. "
        "You do not need to search for a new expression. After your reasoning, give your final answer as a JSON object "
        "with exactly the keys option_1_valid, option_2_valid and choice. The first two values must be booleans "
        "true or false; choice must be the integer 1 or 2. Do not give an expression in place of the JSON object.")
    return prompt


def score_candidate(text,q,seed):
    result=dict(parsed=False,correct=False,judgments_correct=False,old_accepted=False,
        old_selected=False,recognized_but_selected_old=False,old_index=old_index(q,seed))
    if "</think>" not in text: return dict(result,reason="thinking_not_closed")
    final=text.rsplit("</think>",1)[1]
    positions=[m.start() for m in re.finditer(r"\{",final)]
    if not positions: return dict(result,reason="no_json_object")
    # An incomplete last object never falls back to an earlier completed one.
    try: answer,_=json.JSONDecoder().raw_decode(final[positions[-1]:])
    except json.JSONDecodeError: return dict(result,reason="invalid_final_json")
    if not isinstance(answer,dict): return dict(result,reason="invalid_final_json")
    oi=old_index(q,seed); gi=3-oi
    choice=answer.get("choice")
    choice_parsed=type(choice) is int and choice in (1,2)
    judgments_parsed=all(type(answer.get(f"option_{i}_valid")) is bool for i in (1,2))
    judgments_correct=judgments_parsed and answer[f"option_{oi}_valid"] is False and answer[f"option_{gi}_valid"] is True
    return dict(result,parsed=choice_parsed and judgments_parsed,choice_parsed=choice_parsed,
        correct=choice_parsed and choice==gi,judgments_correct=judgments_correct,
        judgments_parsed=judgments_parsed,old_accepted=judgments_parsed and answer[f"option_{oi}_valid"] is True,
        old_selected=choice_parsed and choice==oi,
        recognized_but_selected_old=judgments_correct and choice_parsed and choice==oi,final_json=answer)


def candidate_observations(records):
    """Keep missing judgments distinct from observable rejection of the old option."""
    judged=[r for r in records if r.get("judgments_parsed")]
    chosen=[r for r in records if r.get("choice_parsed")]
    return dict(total=len(records),judgments_observed=len(judged),judgments_missing=len(records)-len(judged),
        old_accepted_observed=sum(bool(r.get("old_accepted")) for r in judged),
        old_rejected_observed=sum(not r.get("old_accepted") for r in judged),
        choices_observed=len(chosen),choices_missing=len(records)-len(chosen),
        valid_chosen_observed=sum(bool(r.get("correct")) for r in chosen),
        old_chosen_observed=sum(bool(r.get("old_selected")) for r in chosen),
        both_judgments_correct_but_old_chosen=sum(bool(r.get("recognized_but_selected_old")) for r in records))


def cross_phase_observations(m,scored):
    """Descriptive task pairs, not evidence of a temporal transition within one run."""
    conditions={}
    by_question=[]
    for q in m["questions"]:
        observations={}
        for c in CONDITIONS:
            pairs=[]
            for seed in SEEDS:
                natural=scored.get((q["id"],"NATURAL",c,seed))
                candidate=scored.get((q["id"],"CANDIDATES",c,seed))
                if natural is None or candidate is None: continue
                pairs.append(dict(seed=seed,natural_correct=bool(natural.get("correct")),
                    natural_old_reuse=bool(natural.get("structural_reuse")),
                    candidate_correct=bool(candidate.get("correct")),
                    candidate_judgments_correct=bool(candidate.get("judgments_correct")),
                    candidate_choice_observed=bool(candidate.get("choice_parsed")),
                    candidate_old_selected=bool(candidate.get("old_selected"))))
            observations[c]=pairs
        by_question.append(dict(id=q["id"],split=q["split"],conditions=observations))
    for c in CONDITIONS:
        pairs=[p for q in by_question for p in q["conditions"][c]]
        conditions[c]=dict(paired_requests=len(pairs),
            natural_wrong_candidate_right=sum(not p["natural_correct"] and p["candidate_correct"] for p in pairs),
            natural_right_candidate_wrong=sum(p["natural_correct"] and not p["candidate_correct"] for p in pairs),
            both_wrong=sum(not p["natural_correct"] and not p["candidate_correct"] for p in pairs),
            both_right=sum(p["natural_correct"] and p["candidate_correct"] for p in pairs),
            natural_old_reuse_candidate_right=sum(p["natural_old_reuse"] and p["candidate_correct"] for p in pairs))
    return dict(conditions=conditions,by_question=by_question,
        scope="Same question and seed across different tasks; candidate availability, instructions and output all change. These pairs do not locate an internal failure stage or measure a within-trajectory repair.")


def summarise(m,out,status=None,error=None):
    scored={(r["id"],r["phase"],r["condition"],r["seed"]):r for r in rows(out/"behaviour.jsonl")}
    phases={}
    fields=("correct","judgments_correct","old_accepted","old_selected","recognized_but_selected_old","structural_reuse")
    for phase in PHASES:
        complete=[q for q in m["questions"] if all((q["id"],phase,c,s) in scored for c in CONDITIONS for s in SEEDS)]
        def effects(qs,field="correct"):
            per={q["id"]:{c:sum(bool(scored[q["id"],phase,c,s].get(field)) for s in SEEDS)/2 for c in CONDITIONS} for q in qs}
            return dict(n=len(qs),simple_effects={h:bootstrap([r["IDENTITY_"+h]-r["COUNT_"+h] for r in per.values()]) for h in ("CLEAN","HISTORY")},
                interaction=bootstrap([r["IDENTITY_HISTORY"]-r["COUNT_HISTORY"]-r["IDENTITY_CLEAN"]+r["COUNT_CLEAN"] for r in per.values()]),
                history_effects={p:bootstrap([r[p+"_HISTORY"]-r[p+"_CLEAN"] for r in per.values()]) for p in ("COUNT","IDENTITY")},
                by_question=[dict(id=qid,**r) for qid,r in per.items()])
        stats={}
        for c in CONDITIONS:
            rs=[r for (qid,p,cond,s),r in scored.items() if p==phase and cond==c]
            stats[c]=dict(n=len(rs),**{f:sum(bool(r.get(f)) for r in rs) for f in fields},
                parsed=sum(bool(r.get("parsed")) for r in rs),length_stops=sum(r["finish_reason"]=="length" for r in rs),
                tokens=sum(r["generated_tokens"] for r in rs),scorer_disagreements=sum(bool(r.get("scorer_disagreement")) for r in rs))
            if phase=="CANDIDATES": stats[c]["observations"]=candidate_observations(rs)
            else:
                stats[c]["failure_types"]=dict(
                    unparsed=sum(not r.get("parsed") for r in rs),
                    resource_only=sum(bool(r.get("parsed")) and bool(r.get("target_correct")) and not r.get("inventory_correct") for r in rs),
                    value_only=sum(bool(r.get("parsed")) and not r.get("target_correct") and bool(r.get("inventory_correct")) for r in rs),
                    value_and_resource=sum(bool(r.get("parsed")) and not r.get("target_correct") and not r.get("inventory_correct") for r in rs))
        phases[phase]=dict(completed=sum(s["n"] for s in stats.values()),planned=240,complete_questions=len(complete),conditions=stats,
            primary=effects(complete),split={label:effects([q for q in complete if q["split"]==label]) for label in ("discovery","replication")},
            error_strata={label:effects([q for q in complete if q["error_type"]==label]) for label in ("inventory_only","value_only","both")},
            candidate_effects={f:effects(complete,f) for f in fields[1:5]} if phase=="CANDIDATES" else {})
    result=dict(status=status,error=error,completed=len(scored),planned=480,phases=phases,
        cross_phase=cross_phase_observations(m,scored),
        pending=[dict(id=q["id"],phase=p,condition=c,seed=s) for p in PHASES for q in m["questions"] for s in SEEDS for c in CONDITIONS if (q["id"],p,c,s) not in scored],
        interpretation="Question is the sampling unit; phase differences include candidate availability, task and output changes, so they do not causally localize a natural trajectory. JSON judgments and adoption in one answer are observable behavior, not proof of hidden cognition.")
    save(out/"summary.json",result)
    return result


def run(output,m):
    import importlib.metadata
    import torch
    from transformers import AutoTokenizer,GenerationConfig
    if os.environ.get("SC_FAILURE_ADOPTION_LAUNCHER")!="1": raise RuntimeError("Use shared launcher --failure-adoption")
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0): raise RuntimeError("One visible A100 required")
    if importlib.metadata.version("vllm")!="0.11.0": raise RuntimeError("Use native vLLM 0.11.0")
    prior=load(output/"budget.json")
    if prior.get("active"): raise RuntimeError("Shared GPU budget active")
    out=output/SUBDIR
    raw={(r["id"],r["phase"],r["condition"],r["seed"]):r for r in rows(out/"generations.jsonl")}
    scored={(r["id"],r["phase"],r["condition"],r["seed"]) for r in rows(out/"behaviour.jsonl")}
    estimate=m["estimate"]
    if (480-len(raw))*8192/estimate["tokens_per_second"]+estimate["loading_seconds"]>prior["limit_seconds"]-prior["gpu_seconds"]:
        raise RuntimeError("Frozen design no longer fits remaining budget estimate")
    requests=[]
    for phase in PHASES:
        for q in m["questions"]:
            for seed in SEEDS:
                for c in q["condition_order"]:
                    requests.append(dict(id=q["id"],phase=phase,condition=c,seed=seed,prompt=prompt_for(q,c,phase,seed)))
    save(out/"requests.json",requests)
    qs={q["id"]:q for q in m["questions"]}
    def score(r):
        key=r["id"],r["phase"],r["condition"],r["seed"]
        if key in scored: return
        q=qs[r["id"]]
        s=score_response(r["text"],q,r["condition"]) if r["phase"]=="NATURAL" else score_candidate(r["text"],q,r["seed"])
        append(out/"behaviour.jsonl",dict(id=r["id"],phase=r["phase"],condition=r["condition"],seed=r["seed"],
            split=q["split"],error_type=q["error_type"],**s,finish_reason=r["finish_reason"],generated_tokens=r["generated_tokens"]))
        scored.add(key)
    for r in raw.values(): score(r)
    budget=Budget(output/"budget.json",24)
    status,error,phase="completed",None,"loading_model"
    try:
        save(out/"run_state.json",dict(status="loading_model",completed=len(raw),planned=480))
        os.environ.update(VLLM_WORKER_MULTIPROC_METHOD="spawn",VLLM_USE_V1="1",VLLM_ATTENTION_BACKEND="FLASH_ATTN")
        from vllm import LLM,SamplingParams
        tokenizer=AutoTokenizer.from_pretrained(m["model"],local_files_only=True)
        eos=GenerationConfig.from_pretrained(m["model"],local_files_only=True).eos_token_id
        eos=[eos] if isinstance(eos,int) else eos
        llm=LLM(model=m["model"],tokenizer=m["model"],dtype="bfloat16",max_model_len=32768,max_num_seqs=8,
            gpu_memory_utilization=.80,enable_prefix_caching=True,enable_chunked_prefill=True,
            max_num_batched_tokens=8192,enforce_eager=True,generation_config="vllm",seed=SEED)
        engine=llm.llm_engine
        for phase in PHASES:
            todo=[r for r in requests if r["phase"]==phase and (r["id"],phase,r["condition"],r["seed"]) not in raw]
            started,initial=time.monotonic(),len(raw)
            inflight,index={},0
            def state():
                completed=len(raw)-initial
                save(out/"run_state.json",dict(status="running",phase=phase,completed=len(raw),planned=480,
                    phase_completed=sum(key[1]==phase for key in raw),phase_planned=240,
                    phase_seconds=time.monotonic()-started,estimated_phase_remaining_seconds=(time.monotonic()-started)/max(1,completed)*(len(todo)-completed),
                    active=[dict(id=r["id"],condition=r["condition"],seed=r["seed"]) for r,_ in inflight.values()],queued=len(todo)-index))
            while index<len(todo) or engine.has_unfinished_requests():
                budget.check()
                submitted=False
                while index<len(todo) and len(inflight)<8:
                    item=todo[index]; index+=1
                    ids=tokenizer.apply_chat_template([dict(role="user",content=item["prompt"])],tokenize=True,add_generation_prompt=True,enable_thinking=True)
                    if len(ids)+8192>32768: raise ValueError("Frozen prompt and cap exceed context")
                    rid=str(next(llm.request_counter))
                    engine.add_request(rid,dict(prompt_token_ids=ids),SamplingParams(**m["sampling"],seed=item["seed"],max_tokens=8192,
                        skip_special_tokens=False,ignore_eos=False,stop_token_ids=eos))
                    inflight[rid]=(item,time.monotonic()); submitted=True
                if submitted: state()
                for result in engine.step():
                    if not result.finished: continue
                    item,begin=inflight.pop(result.request_id); g=result.outputs[0]; tokens=list(g.token_ids)
                    record=dict(item,text=tokenizer.decode(tokens,skip_special_tokens=False),token_ids=tokens,generated_tokens=len(tokens),
                        finish_reason="eos" if (tokens and tokens[-1] in eos) or g.stop_reason in eos else g.finish_reason,
                        stop_reason=g.stop_reason,request_wall_seconds=time.monotonic()-begin,
                        model=m["model"],dtype=m["dtype"],backend=m["backend"],sampling=m["sampling"],max_new_tokens=8192,
                        source=qs[item["id"]]["source"],source_line=qs[item["id"]]["source_line"],
                        request_timing_note="Overlapping request times are not summed; use shared budget.json.")
                    append(out/"generations.jsonl",record)
                    raw[item["id"],phase,item["condition"],item["seed"]]=record
                    score(record); state(); budget.check(force=True)
            summarise(m,out,"running")
    except BudgetExceeded: status="budget_exhausted"
    except Exception as exc:
        status,error="failed",repr(exc)
        raise
    finally:
        budget.close()
        result=summarise(m,out,status,error)
        save(out/"run_state.json",dict(status=status,phase=phase,completed=result["completed"],planned=480,error=error))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare",action="store_true")
    p.add_argument("--resume",action="store_true")
    p.add_argument("--status",action="store_true")
    p.add_argument("--report",action="store_true")
    a=p.parse_args(); out=a.output/SUBDIR
    if a.status:
        state=load(out/"run_state.json") if (out/"run_state.json").exists() else dict(status="not_started",completed=0,planned=480,
            note="No experiment state yet. Check the live launcher/tmux and runner.log for queue status.")
        print(json.dumps(state,indent=2)); return
    m=prepare(a.output)
    if a.prepare and os.environ.get("SC_FAILURE_ADOPTION_LAUNCHER")=="1":
        from transformers import AutoTokenizer,GenerationConfig
        tokenizer=AutoTokenizer.from_pretrained(m["model"],local_files_only=True)
        GenerationConfig.from_pretrained(m["model"],local_files_only=True)
        lengths=[len(tokenizer.apply_chat_template([dict(role="user",content=prompt_for(q,c,p,s))],tokenize=True,add_generation_prompt=True,enable_thinking=True))
                 for q in m["questions"] for c in CONDITIONS for p in PHASES for s in SEEDS]
        if max(lengths)+8192>32768: raise ValueError("Prompt and generation cap exceed context")
        save(out/"preflight.json",dict(max_prompt_tokens=max(lengths),max_new_tokens=8192,requests=len(lengths)))
    if a.resume: run(a.output,m)
    elif a.report:
        state=load(out/"run_state.json") if (out/"run_state.json").exists() else dict(status="not_started")
        result=summarise(m,out,state.get("status"),state.get("error"))
        print(json.dumps(dict(status=result["status"],completed=result["completed"],planned=480,
            phases={p:dict(conditions=r["conditions"],primary={k:v for k,v in r["primary"].items() if k!="by_question"},
                          split={s:{k:v for k,v in rs.items() if k!="by_question"} for s,rs in r["split"].items()}) for p,r in result["phases"].items()}),indent=2))
    else: print(json.dumps(dict(status="prepared",questions=30,discovery=15,replication=15,requests=480)))


if __name__=="__main__": main()
