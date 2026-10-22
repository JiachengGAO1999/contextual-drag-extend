"""Natural worksheet responses; clean competence stage first, no automatic followup."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_generation_diagnostics_20261005 import Budget,BudgetExceeded,save,append
from run_dependency_revision_20261011 import load,rows,bootstrap


def score_response(text,variant):
    # The thinking opener is in the prompt. Do not grade JSON inside unfinished thinking.
    if "</think>" not in text:
        return dict(parsed=False,reason="thinking_not_closed",correct=False)
    final=text.rsplit("</think>",1)[1]
    expected={r["id"]:Fraction(r["true_value"]) for r in variant["oracle"]}
    values=None
    for match in re.finditer(r"\{[^{}]*\}",final):
        try:
            candidate=json.loads(match.group())
            if set(candidate)!=set(expected) or any(isinstance(x,bool) for x in candidate.values()):continue
            values={k:Fraction(str(v)) for k,v in candidate.items()}
        except (ValueError,TypeError,ZeroDivisionError,json.JSONDecodeError):
            continue
    if values is None:return dict(parsed=False,reason="no_complete_six_step_json",correct=False)
    right={k:values[k]==v for k,v in expected.items()}
    dep=next(r["node"] for r in variant["readouts"] if r["node"]!="S1" and r["depends_on_error"])
    ind=next(r["node"] for r in variant["readouts"] if not r["depends_on_error"])
    cached={s["id"]:Fraction(s["cached"]) for s in variant["steps"]}
    return dict(parsed=True,correct=all(right.values()),step_correct=right,
        values={k:str(v) for k,v in values.items()},root_correct=right["S1"],
        dependent_correct=right[dep],independent_preserved=right[ind],
        dependent_stale=values[dep]==cached[dep],
        root_correct_dependent_stale_independent_correct=right["S1"] and values[dep]==cached[dep] and right[ind])


def prepare(output):
    out=output/"dependency_natural"
    if (out/"manifest.json").exists():return load(out/"manifest.json")
    source=load(output/"dependency_revision/manifest.json")
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(source["model"],local_files_only=True)
    questions=source["questions"]
    for q in questions:
        for v in q["variants"]:
            v["natural_contexts"]={}
            for condition in ("CLEAN","CORRECT_ROOT"):
                prompt=v["prompts"][condition]
                old="Return only the value of the requested step."
                if prompt.count(old)!=1:raise ValueError("Worksheet instruction not found exactly once")
                prompt=prompt.replace(old,"In your final answer, provide a JSON object with the recomputed values of S1, S2, S3, S4, S5 and S6.")
                text=tokenizer.apply_chat_template([dict(role="user",content=prompt)],tokenize=False,
                    add_generation_prompt=True,enable_thinking=True)
                v["natural_contexts"][condition]=dict(text=text,input_ids=tokenizer.encode(text,add_special_tokens=False))
    manifest=dict(model=source["model"],dtype="bfloat16",attention="sdpa",seed=source["seed"],
        thinking_template=True,do_sample=False,max_new_tokens=2048,gpu_hours=24,questions=questions,
        conditions=["CLEAN","CORRECT_ROOT"],first_stage="CLEAN",first_stage_requests=64,
        possible_total_requests=128,
        selection="Same frozen 32 base graphs and both wirings. No selection on short scores.",
        analysis="Raw response first, then six-value final JSON after closed thinking. All six values, root, dependent and independent readouts from SAME actual generation. Parameter groups are the statistical unit.",
        stop="Run CLEAN only by default. Never auto-start CORRECT_ROOT; review clean competence first. No retry, extra seeds, question replacement or head search. Shared original 24 GPU-hour cap.")
    save(out/"manifest.json",manifest)
    save(out/"summary.json",dict(status="prepared_clean_stage",completed=0,planned_clean=64))
    return manifest


def analyse(manifest,out,status,phase,error=None):
    keyed={(r["id"],r["wiring"],r["condition"]):r for r in rows(out/"behaviour.jsonl")}
    groups=[]
    for q in manifest["questions"]:
        needed=[(q["id"],v["wiring"],phase) for v in q["variants"]]
        if all(k in keyed for k in needed):groups.append([keyed[k] for k in needed])
    records=[r for r in keyed.values() if r["condition"]==phase]
    result=dict(status=status,phase=phase,completed=len(records),planned=64,complete_base_groups=len(groups),
        correctness=bootstrap([sum(r["correct"] for r in g)/2 for g in groups]),
        counts={field:sum(bool(r.get(field)) for r in records) for field in
            ("parsed","correct","root_correct","dependent_correct","independent_preserved","dependent_stale","root_correct_dependent_stale_independent_correct")},
        length_stops=sum(r["finish_reason"]=="length" for r in records),
        total_generated_tokens=sum(r["generated_tokens"] for r in records),
        error=error,next="Review CLEAN competence before any CORRECT_ROOT generation. No automatic followup.")
    save(out/"summary.json",result)
    return result


def run(output,manifest,phase):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    if os.environ.get("SC_DEPENDENCY_NATURAL_LAUNCHER")!="1":raise RuntimeError("Use shared launcher --dependency-natural")
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):raise RuntimeError("Exactly one visible A100 required")
    if load(output/"budget.json").get("active"):raise RuntimeError("Shared budget already active")
    out=output/"dependency_natural"
    raw={(r["id"],r["wiring"],r["condition"]):r for r in rows(out/"generations.jsonl")}
    done={(r["id"],r["wiring"],r["condition"]) for r in rows(out/"behaviour.jsonl")}
    budget=Budget(output/"budget.json",24)
    class Heartbeat(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):budget.check();return False
    status,error="clean_stage_completed" if phase=="CLEAN" else "corrected_stage_completed",None
    try:
        save(out/"run_state.json",dict(status="loading_model",phase=phase))
        tokenizer=AutoTokenizer.from_pretrained(manifest["model"],local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(manifest["model"],local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation="sdpa",device_map="cuda:0").eval()
        torch.manual_seed(manifest["seed"])
        started=time.monotonic()
        finished=sum(k[2]==phase for k in done)
        initial_finished=finished
        for q in manifest["questions"]:
            for v in q["variants"]:
                key=(q["id"],v["wiring"],phase)
                if key in done:continue
                request=dict(id=q["id"],wiring=v["wiring"],condition=phase)
                save(out/"current_request.json",request)
                if key not in raw:
                    context=v["natural_contexts"][phase]
                    ids=torch.tensor([context["input_ids"]],device=model.device)
                    begin=time.monotonic()
                    with torch.inference_mode():
                        result=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                            do_sample=False,max_new_tokens=manifest["max_new_tokens"],
                            pad_token_id=tokenizer.eos_token_id,stopping_criteria=StoppingCriteriaList([Heartbeat()]))
                    tokens=result[0,len(context["input_ids"]):].tolist()
                    eos=model.generation_config.eos_token_id
                    eos=[eos] if isinstance(eos,int) else eos
                    record=dict(**request,text=tokenizer.decode(tokens,skip_special_tokens=False),
                        token_ids=tokens,generated_tokens=len(tokens),
                        finish_reason="eos" if tokens and tokens[-1] in eos else "length",
                        gpu_seconds=time.monotonic()-begin,source="manifest.json",model=manifest["model"],
                        parameters=dict(dtype="bfloat16",thinking_template=True,do_sample=False,max_new_tokens=2048))
                    append(out/"generations.jsonl",record)
                    raw[key]=record
                record=raw[key]
                append(out/"behaviour.jsonl",dict(**request,**score_response(record["text"],v),
                    finish_reason=record["finish_reason"],generated_tokens=record["generated_tokens"]))
                done.add(key);finished+=1
                elapsed=time.monotonic()-started
                save(out/"run_state.json",dict(status="running",phase=phase,completed=finished,planned=64,
                    elapsed_generation_seconds=elapsed,estimated_remaining_seconds=elapsed/max(1,finished-initial_finished)*(64-finished)))
                budget.check(force=True)
            analyse(manifest,out,"running",phase)
    except BudgetExceeded:status="budget_exhausted"
    except Exception as exc:status,error="failed",repr(exc);raise
    finally:
        budget.close()
        result=analyse(manifest,out,status,phase,error)
        save(out/"run_state.json",dict(status=status,phase=phase,completed=result["completed"],error=error))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare",action="store_true");p.add_argument("--resume",action="store_true");p.add_argument("--status",action="store_true")
    a=p.parse_args();out=a.output/"dependency_natural"
    if a.status:
        for name in ("run_state.json","summary.json"):
            if (out/name).exists():print((out/name).read_text())
        return
    m=prepare(a.output)
    if a.resume:run(a.output,m,os.environ.get("SC_DEPENDENCY_NATURAL_PHASE","CLEAN"))
    else:print(json.dumps(dict(status="prepared",phase="CLEAN",requests=64,max_new_tokens=2048)))


if __name__=="__main__":main()
