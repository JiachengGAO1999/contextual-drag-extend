"""Frozen random-generation control, then a bounded information-separation experiment."""
from __future__ import annotations

import argparse
import ast
import json
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_generation_diagnostics_20261005 import Budget,BudgetExceeded,Experiment,append,save
from selective_context.diagnostic_data import read_jsonl,expression_measurement,paired_effect

MATERIALS={
    "434":dict(clue="5 * 5 = 25",remaining="11 and 11",other="11 - 5 = 6",
               bad="(11 - 5) * (5 - 11 / 11)",repeated=11,supplied=2,actual=3,solution="5*5-11/11"),
    "144":dict(clue="11 + 11 = 22",remaining="2 and 4",other="11 - 2 = 9",
               bad="4 * (11 - (11 - 2 - 4))",repeated=4,supplied=1,actual=2,solution="11+11+4-2"),
    "956":dict(clue="7 + 8 = 15",remaining="8 and 12",other="12 - 8 = 4",
               bad="(12 - 8) * (7 - 8 / 8)",repeated=8,supplied=2,actual=3,solution="(7+8-12)*8"),
    "754":dict(clue="9 + 9 = 18",remaining="3 and 10",other="9 / 9 = 1",
               bad="3 * (10 - (9 + 9) / 9)",repeated=9,supplied=2,actual=3,solution="(9+9-10)*3"),
}


def freeze(path,value):
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(value)):
        raise ValueError(f"Frozen configuration changed: {path.name}")
    save(path,value)


def prepare(manifest,tokenizer,output):
    from selective_context.prompting import locate_unique_draft,encode_prompt,make_request
    from selective_context.schema import AccessMode
    chosen=manifest["discovery"][:4]
    if set(chosen)!=set(MATERIALS):
        raise ValueError("Unexpected frozen discovery order")
    questions={q["id"]:q for q in manifest["questions"]}
    variants=[]
    for qid in chosen:
        q=questions[qid];material=MATERIALS[qid]
        assert expression_measurement(material["solution"],q["answer"])["exact_game24"]
        assert not expression_measurement(material["bad"],q["answer"])["exact_game24"]
        # Every useful result is a legal disjoint partial calculation, with a
        # verified full solution stored only in metadata, never in the prompt.
        for variant in ("ENDORSED","DIAGNOSED"):
            count=material["supplied"] if variant=="ENDORSED" else material["actual"]
            verdict="satisfied" if variant=="ENDORSED" else "violated"
            draft=(f"Verified partial work: {material['clue']}. This uses those two numbers once each; "
                   f"the remaining numbers are {material['remaining']}.\n\n"
                   f"Earlier candidate: {material['bad']} = 24.\n"
                   f"Number-use check: the number {material['repeated']} appears {count} times in this candidate. "
                   f"The number-use constraint is {verdict}.\n"
                   f"Final expression: \\boxed{{{material['bad']}}}")
            a,b=locate_unique_draft(q["prompt"])
            prompt=q["prompt"][:a]+draft+q["prompt"][b:]
            encoded=encode_prompt(tokenizer,prompt)
            request=make_request(encoded,"MIXED_"+variant,AccessMode.FULL,q["seeds"][0])
            new=dict(q,id=qid+"_"+variant,prompt=prompt,request=request.to_dict(),
                     original_id=qid,variant=variant,material=material,
                     source=str(output/"information_materials.json"),
                     max_new_tokens=min(q["max_new_tokens"],32768-len(request.input_ids)))
            new["probes"]=[]
            variants.append(new)
    mixed=dict(manifest,questions=variants,
               discovery=[q["id"] for q in variants],validation=[])
    freeze(output/"information_materials.json",dict(questions=variants,
        description="Useful clue held fixed. Same invalid expression. Only number-use count and verdict change.",
        limitations=["Clue-aligned answers do not prove that the clue caused the solution.",
                     "MASK removes direct generated-query access; prefill can still encode draft information elsewhere."]))
    return mixed


def tree(expression):
    """Ignore LaTeX and redundant parentheses, preserving arithmetic structure."""
    import re
    def group(s,start):
        while s[start].isspace():start+=1
        if s[start]!="{":raise ValueError("Expected fraction group")
        end=start+1;depth=1
        while depth:
            depth+=(s[end]=="{")-(s[end]=="}");end+=1
        return s[start+1:end-1],end
    if not expression:return None
    try:
        s=expression.split("=",1)[0]
        while True:
            hit=re.search(r"\\(?:d?frac)\s*",s)
            if not hit:break
            a,end=group(s,hit.end());b,end=group(s,end)
            s=s[:hit.start()]+f"(({a})/({b}))"+s[end:]
        for a,b in (("\\left",""),("\\right",""),("\\times","*"),("\\cdot","*"),("\\div","/"),
                    ("×","*"),("÷","/"),("{","("),("}",")")):
            s=s.replace(a,b)
        node=ast.parse(s.strip(),mode="eval").body
        return node if isinstance(node,ast.BinOp) else None
    except (ValueError,SyntaxError,IndexError):return None


def same_tree(a,b):
    aa,bb=tree(a),tree(b)
    return bool(aa is not None and bb is not None and ast.dump(aa)==ast.dump(bb))


def natural_summary(rows):
    stats={}
    for name in dict.fromkeys(r["condition"] for r in rows):
        rs=[r for r in rows if r["condition"]==name]
        stats[name]=dict(n=len(rs),correct=sum(r["correct"] for r in rs),
             structural_reuse=sum(same_tree(r["old_expression"],r["extracted_answer"]) for r in rs),
             route_available=sum(tree(r["old_expression"]) is not None for r in rs),
             eos=sum(r["finish_reason"]=="eos" for r in rs),
             mean_tokens=statistics.mean(len(r["generated_token_ids"]) for r in rs))
    return stats


def random_control(backend,manifest,output,budget,control,candidate):
    ids=manifest["validation"][:8]
    out=output/"random_behaviour";out.mkdir(exist_ok=True)
    experiment=Experiment(backend,manifest,out,budget)
    experiment.bridge(ids,candidate,conditions=[("CONTROL",control)])
    rows=read_jsonl(output/"semantic_behaviour/behaviour.jsonl")+read_jsonl(out/"behaviour.jsonl")
    rows=[r for r in rows if r["id"] in ids]
    stats=natural_summary(rows)
    question_rows=[]
    for qid in ids:
        for condition in ("FULL","MASK","CANDIDATE","CONTROL"):
            rs=[r for r in rows if r["id"]==qid and r["condition"]==condition]
            if len(rs)!=2:raise ValueError("Incomplete paired random-control comparison")
            question_rows.append(dict(id=qid,condition=condition,margin=statistics.mean(r["correct"] for r in rs)))
    effect=paired_effect(question_rows,"CONTROL","CANDIDATE")
    result=dict(status="passed" if effect["mean"]>0 else "stopped_candidate_not_better_than_random",
                stats=stats,candidate_vs_control=effect,
                rule="Candidate mean correctness must exceed the frozen random control; reuse is reported separately.")
    save(output/"random_generation_summary.json",result)
    print(json.dumps(result),flush=True)
    return result["status"]=="passed"


def probes(backend,manifest,output,budget,candidate):
    from selective_context.diagnostics import Intervention
    path=output/"information_probes.jsonl";rows=read_jsonl(path)
    done={(r["id"],r["condition"]) for r in rows}
    for q in manifest["questions"]:
        todo=[(name,spec) for name,spec in (("FULL",Intervention()),("MASK",Intervention("MASK")),
                                          ("CANDIDATE",candidate)) if (q["id"],name) not in done]
        if not todo:continue
        pre=backend.prefill(q["request"]["input_ids"])
        m=q["material"]
        definitions={
            "useful":dict(prefix="<think>\nThe verified partial work in the draft was ",
                          preferred=m["clue"]+".",alternative=m["other"]+"."),
            "harmful":dict(prefix=f"<think>\nChecking number usage in the earlier candidate, the number {m['repeated']} appears ",
                           preferred=f"{m['actual']} times.",alternative=f"{m['supplied']} times."),
        }
        for name,spec in todo:
            scores={}
            for kind,d in definitions.items():
                # Joint encoding preserves candidate-boundary whitespace tokens.
                prefix=backend.tokenizer.encode(d["prefix"].rstrip(),add_special_tokens=False)
                values={}
                for key in ("preferred","alternative"):
                    tokens=backend.tokenizer.encode(d["prefix"]+d[key],add_special_tokens=False)
                    if tokens[:len(prefix)]!=prefix or len(tokens)>512:
                        raise ValueError("Probe prefix mismatch or replay exceeds limit")
                    result=backend.teacher_force(pre,tokens,q["request"]["draft_token_span"],spec)
                    values[key]=sum(result["log_probs"][len(prefix):])
                scores[kind]=dict(**values,margin=values["preferred"]-values["alternative"])
            row=dict(id=q["id"],original_id=q["original_id"],variant=q["variant"],condition=name,
                scores=scores,heads=spec.heads,mode=spec.mode,model=manifest["model"])
            append(path,row);rows.append(row);budget.check(force=True)
            print("information_probe",q["id"],name,{k:v["margin"] for k,v in scores.items()},flush=True)
        del pre
    effects={}
    for kind in ("useful","harmful"):
        for variant in ("ENDORSED","DIAGNOSED"):
            rr=[dict(r,margin=r["scores"][kind]["margin"]) for r in rows if r["variant"]==variant]
            effects[kind+"_"+variant]={
                "candidate_vs_full":paired_effect(rr,"FULL","CANDIDATE"),
                "mask_vs_full":paired_effect(rr,"FULL","MASK"),
                "candidate_vs_mask":paired_effect(rr,"MASK","CANDIDATE"),
            }
    # Discovery gate: evidence for rejecting the false count AND retaining the
    # useful tagged calculation better than direct-access MASK. No accuracy claim.
    harm=effects["harmful_ENDORSED"]["candidate_vs_full"]["mean"]
    useful=effects["useful_ENDORSED"]["candidate_vs_mask"]["mean"]
    passed=harm is not None and useful is not None and harm>0 and useful>0
    summary=dict(status="passed" if passed else "stopped_no_information_separation_signal",effects=effects,
                 rule="On endorsed histories: candidate improves true-count preference over FULL and useful-clue retrieval over MASK.",
                 scope="Tagged-clue retrieval and literal number counting, not calibrated solution correctness.")
    save(output/"information_probe_summary.json",summary)
    return passed


def mixed_behaviour(backend,manifest,output,budget,candidate):
    out=output/"information_behaviour";out.mkdir(exist_ok=True)
    experiment=Experiment(backend,manifest,out,budget)
    experiment.bridge([q["id"] for q in manifest["questions"]],candidate)
    rows=read_jsonl(out/"behaviour.jsonl")
    questions={q["id"]:q for q in manifest["questions"]}
    # Observe literal subtree alignment with the useful clue; do not interpret
    # matching a solution route as proof of historical information use.
    aligned={}
    for r in rows:
        clue=tree(questions[r["id"]]["material"]["clue"].split("=")[0])
        answer=tree(r["extracted_answer"])
        hit=bool(clue is not None and answer is not None and any(
            ast.dump(node)==ast.dump(clue) for node in ast.walk(answer)))
        r["clue_aligned"]=hit
    for variant in ("ENDORSED","DIAGNOSED"):
        rs=[r for r in rows if questions[r["id"]]["variant"]==variant]
        aligned[variant]=dict(stats=natural_summary(rs),correct_clue_aligned={c:sum(
            r["correct"] and r["clue_aligned"] for r in rs if r["condition"]==c)
            for c in ("FULL","MASK","CANDIDATE")})
    save(output/"information_behaviour_summary.json",dict(variants=aligned,
         limitation="Clue-aligned answer counts describe structural route agreement, not causal use of the clue."))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--status",action="store_true",help="Read progress without using the GPU")
    args=parser.parse_args();output=args.output
    if args.status:
        result={"random_generations":len(read_jsonl(output/"random_behaviour/behaviour.jsonl")),
                "information_probe_requests":len(read_jsonl(output/"information_probes.jsonl")),
                "information_generations":len(read_jsonl(output/"information_behaviour/behaviour.jsonl"))}
        for name in ("budget","information_summary","random_generation_summary","information_probe_summary","information_behaviour_summary"):
            path=output/(name+".json")
            if path.exists():result[name]=json.loads(path.read_text())
        print(json.dumps(result,indent=2));return
    manifest=json.loads((output/"manifest.json").read_text())
    frozen=json.loads((output/"semantic_candidate.json").read_text())
    control_heads=json.loads((output/"semantic_validation.json").read_text())["control_heads"]
    freeze(output/"information_followup_config.json",dict(model=manifest["model"],dtype="bfloat16",
        budget=str(output/"budget.json"),random_ids=manifest["validation"][:8],
        candidate_heads=frozen["heads"],control_heads=control_heads,seed=20261005,
        materials_ids=manifest["discovery"][:4],sampling=manifest["sampling"],
        max_new_generations=64,random_gate="Candidate mean accuracy exceeds CONTROL",
        mixed_gate="ENDORSED: candidate harmful-count preference > FULL; useful-clue retrieval > MASK"))
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(manifest["model"],local_files_only=True)
    mixed=prepare(manifest,tokenizer,output)
    # CPU import readiness before the launcher stops its owned resident.
    from selective_context.tasks import score_record
    from selective_context.official_compat import make_official_record
    from selective_context.phase0.thinking_pilot import extract_final_draft
    if args.prepare:
        print(json.dumps(dict(random_requests=16,mixed_probe_requests=24,
              mixed_generations_max=48,materials=[q["id"] for q in mixed["questions"]])));return
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.diagnostics import DiagnosticBackend,Intervention
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    budget=Budget(output/"budget.json",manifest["gpu_hours"])
    try:
        save(output/"information_summary.json",dict(status="running_random_control"))
        model=AutoModelForCausalLM.from_pretrained(manifest["model"],local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation="sdpa",device_map="cuda:0")
        backend=DiagnosticBackend(model,tokenizer,budget.check)
        candidate=Intervention(frozen["mode"],tuple(tuple(h) for h in frozen["heads"]))
        control=Intervention(frozen["mode"],tuple(tuple(h) for h in control_heads))
        if not random_control(backend,manifest,output,budget,control,candidate):
            save(output/"information_summary.json",dict(status="stopped_random_control_gate"));return
        save(output/"information_summary.json",dict(status="running_information_probes"))
        if not probes(backend,mixed,output,budget,candidate):
            save(output/"information_summary.json",dict(status="stopped_information_probe_gate"));return
        save(output/"information_summary.json",dict(status="running_information_generation"))
        mixed_behaviour(backend,mixed,output,budget,candidate)
        save(output/"information_summary.json",dict(status="completed_information_followup"))
    except BudgetExceeded:
        save(output/"information_summary.json",dict(status="budget_exhausted"))
    except Exception as exc:
        save(output/"information_summary.json",dict(status="failed",error=repr(exc)))
        raise
    finally:
        budget.close()


if __name__=="__main__":main()
