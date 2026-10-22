"""Same-prefix rejection of reviewed invalid Game24 constructions; no new text sampling."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, Experiment, append, save
from selective_context.diagnostic_data import read_jsonl, paired_effect

# Reviewed before intervention: each assertion refers to the repeated-number draft.
# These probe rejection of an invalid construction, not successful solution discovery.
REVIEWS = {
    "434": dict(anchor="Yes, each number is used once.", offset=0,
                preferred="No, a number is reused.", alternative="Yes, each number is used once.",
                expression="(11-5)*(5-11/11)", reason="Three 11s are used; only two supplied."),
    "956": dict(anchor="So yes, all numbers are used once.", offset=3,
                preferred="no, a number is reused.", alternative="yes, all numbers are used once.",
                expression="(12-8)*(7-8/8)", reason="Three 8s are used; only two supplied."),
    "1305": dict(anchor="So all numbers are used once.", offset=3,
                 preferred="not all numbers are used once.", alternative="all numbers are used once.",
                 expression="(10/5)*(13-10/10)", reason="Three 10s are used; only two supplied."),
    "230": dict(anchor="So that seems valid.", offset=len("So that seems "),
                preferred="invalid.", alternative="valid.",
                expression="3*12-(11+11/11)", reason="Three 11s are used; only two supplied."),
    "44": dict(anchor="Yes: 12, 12, 10, 10. Each number is used once.", offset=0,
               preferred="No, a number is reused.", alternative="Yes: 12, 12, 10, 10. Each number is used once.",
               expression="12*(12/12+10/10)",reason="Three 12s are used; only two supplied."),
    "1057": dict(anchor="Each exactly once.",offset=0,
                 preferred="A number is reused.",alternative="Each exactly once.",
                 expression="6*((12-9)+9/9)",reason="Three 9s are used; only two supplied."),
    "717": dict(anchor="Each exactly once.",offset=0,
                preferred="A number is reused.",alternative="Each exactly once.",
                expression="6/(1-(7-4)/4)",reason="Two 4s are used; only one supplied."),
    "413": dict(anchor="Yes, all four numbers are used once.",offset=0,
                preferred="No, a number is reused.",alternative="Yes, all four numbers are used once.",
                expression="6*((9-5)*(9/9))",reason="Three 9s are used; only two supplied."),
    "1112": dict(anchor="Each is used exactly once.",offset=0,
                 preferred="A number is reused.",alternative="Each is used exactly once.",
                 expression="5*4+8/(10-8)",reason="Two 8s are used; only one supplied."),
}


def prepare(manifest, tokenizer, split="discovery"):
    probes, missing = {}, {}
    for q in manifest["questions"]:
        if q["id"] not in manifest[split]:
            continue
        review = REVIEWS.get(q["id"])
        if review is None or "wrong" not in q["suffixes"]:
            missing[q["id"]] = "No unambiguous reviewed invalid-construction endorsement within 512 tokens."
            continue
        tokens = q["suffixes"]["wrong"]["tokens"][:512]
        text = tokenizer.decode(tokens)
        start = text.index(review["anchor"]) + review["offset"]
        boundaries = {len(tokenizer.decode(tokens[:i])): i for i in range(len(tokens)+1)}
        boundary=max(pos for pos in boundaries if pos<=start)
        leading=text[boundary:start]
        if leading.strip():
            raise ValueError(f"{q['id']}: assertion splits a non-whitespace token")
        start=boundary
        index = boundaries[start]
        prefix = tokens[:index]
        candidates = {}
        for key in ("preferred", "alternative"):
            # Encode jointly to preserve the tokenizer's exact whitespace boundary.
            joint = tokenizer.encode(text[:start]+leading+review[key], add_special_tokens=False)
            if joint[:index] != prefix:
                raise ValueError(f"{q['id']}: candidate changes the fixed prefix")
            candidates[key] = joint[index:]
            if index+len(candidates[key]) > 512:
                raise ValueError("Reviewed probe exceeds the frozen replay window")
        probes[q["id"]] = dict(index=index, prefix_tokens=prefix, candidates=candidates,
                                  suffix="wrong", semantic=True, **review)
    return dict(metric="sum_log_probability(preferred)-sum_log_probability(alternative)",
                interpretation="Counterfactual rejection of an invalid construction on its historical wrong prefix; not solution accuracy.",
                discovery=manifest["discovery"], validation=manifest["validation"],
                probes=probes, missing=missing, replay_limit=512)


def measure(backend, manifest, config, output, budget, conditions, phase="semantic_screen",result_file="semantic_diagnostics.jsonl"):
    from selective_context.diagnostics import Intervention
    path=output/result_file
    rows=read_jsonl(path)
    done={(r["phase"],r["id"],r["condition"]) for r in rows}
    questions={q["id"]:q for q in manifest["questions"]}
    for qid, probe in config["probes"].items():
        todo=[(name,spec) for name,spec in conditions if (phase,qid,name) not in done]
        if not todo:
            continue
        q=questions[qid]
        pre=backend.prefill(q["request"]["input_ids"])
        for name,spec in todo:
            started=time.monotonic()
            scores={}
            for key, candidate in probe["candidates"].items():
                tokens=probe["prefix_tokens"]+candidate
                span=q["request"]["draft_token_span"]
                donor=None
                if spec.mode in ("PATCH","PATCH_MASK"):
                    source=Intervention("MASK" if spec.mode=="PATCH" else "FULL",query_window=spec.query_window)
                    donor=backend.teacher_force(pre,tokens,span,source,capture=True)["outputs"]
                result=backend.teacher_force(pre,tokens,span,spec,donor=donor)
                values=result["log_probs"][probe["index"]:]
                scores[key]=dict(sum_logp=sum(values),mean_logp=sum(values)/len(values),tokens=len(values))
            row=dict(phase=phase,id=qid,condition=name,mode=spec.mode,heads=spec.heads,query_window=spec.query_window,
                index=probe["index"],scores=scores,
                margin=scores["preferred"]["sum_logp"]-scores["alternative"]["sum_logp"],
                mean_margin=scores["preferred"]["mean_logp"]-scores["alternative"]["mean_logp"],
                gpu_seconds=time.monotonic()-started,source=q["suffixes"]["wrong"]["source"],
                model=manifest["model"],strength=spec.strength)
            append(path,row);rows.append(row);budget.check(force=True)
            print(f"{phase} {qid} {name} rejection_margin={row['margin']:.5f}",flush=True)
        del pre
    return rows


def report(output,config,rows):
    effects={c:paired_effect([r for r in rows if r['phase']=='semantic_screen'],"FULL",c)
             for c in ("VALUE_ZERO","MASK")}
    supported=[c for c,e in effects.items() if e["mean"] is not None and e["mean"]>0]
    status="semantic_signal_requires_localization" if supported else "stopped_no_semantic_rejection_signal"
    summary=dict(status=status,effects=effects,available_questions=len(config["probes"]),
                 missing=config["missing"],interpretation=config["interpretation"],
                 selected_branch=max(supported,key=lambda c:effects[c]["mean"]) if supported else None)
    save(output/"semantic_summary.json",summary)
    (output/"semantic_report.md").write_text(
        "# Reviewed invalid-construction rejection\n\n"+config["interpretation"]+
        "\n\nMissing questions were retained, without replacement. Candidate sequences are scored on exactly the same historical prefix. "
        "Their absolute margin is not a calibrated binary probability. Intervention effects compare each question against FULL.\n\n```json\n"+
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n```\n",encoding="utf-8")
    return summary


def localize(backend, manifest, config, validation, output, budget, screen):
    import random
    from selective_context.diagnostics import Intervention
    mode=screen["selected_branch"]
    if mode is None:
        return
    layers=len(backend.layers)
    groups=[tuple((l,h) for l in range(layers*i//4,layers*(i+1)//4)
                  for h in range(backend.n_heads)) for i in range(4)]
    specs=[(f"GROUP_{i}",Intervention(mode,g)) for i,g in enumerate(groups)]
    rows=measure(backend,manifest,config,output,budget,[("FULL",Intervention())]+specs,"semantic_groups")
    def effects(phase, names):
        return {name:paired_effect([r for r in rows if r["phase"]==phase],"FULL",name) for name in names}
    ge=effects("semantic_groups",[n for n,_ in specs])
    best=max(ge,key=lambda n:ge[n]["mean"] if ge[n]["mean"] is not None else -float("inf"))
    if ge[best]["mean"] is None or ge[best]["mean"]<=0:
        save(output/"semantic_summary.json",dict(status="stopped_no_semantic_layer_group",screen=screen,groups=ge));return
    parent=groups[int(best.split("_")[-1])]
    active=parent
    candidate=None
    candidate_effect=-float("inf")
    subdivisions=[]
    # Causal binary subdivision, including collective head sets; no singleton gate.
    # Freeze only a proper subset so a matched random control can differ from it.
    for depth in range(8):
        if len(active)<=8:
            break
        halves=(active[:len(active)//2],active[len(active)//2:])
        phase=f"semantic_subdivision_{depth}"
        names=[f"HALF_{i}" for i in range(2)]
        rows=measure(backend,manifest,config,output,budget,
                     [("FULL",Intervention())]+[(n,Intervention(mode,h)) for n,h in zip(names,halves)],phase)
        ee=effects(phase,names)
        subdivisions.append(dict(phase=phase,effects=ee))
        choice=max(names,key=lambda n:ee[n]["mean"] if ee[n]["mean"] is not None else -float("inf"))
        if ee[choice]["mean"] is None or ee[choice]["mean"]<=0:
            break
        active=halves[names.index(choice)]
        if ee[choice]["mean"]>candidate_effect:
            candidate=Intervention(mode,active)
            candidate_effect=ee[choice]["mean"]
    if candidate is None:
        save(output/"semantic_summary.json",dict(status="stopped_group_signal_without_localized_subset",screen=screen,
                                               groups=ge,subdivisions=subdivisions));return
    active=candidate.heads
    frozen=dict(mode=mode,heads=candidate.heads,strength=1.,parent_group=parent,groups=ge,
                discovery_mean=candidate_effect,
                subdivisions=subdivisions,metric=config["metric"],
                scope="Collective subset; does not assert any individual head is harmful.")
    path=output/"semantic_candidate.json"
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(frozen)):
        raise ValueError("Frozen semantic candidate changed")
    save(path,frozen)
    if mode=="VALUE_ZERO":
        names=["R2_FROM_R3","R3_FROM_R2"]
        rows=measure(backend,manifest,config,output,budget,[("FULL",Intervention()),("MASK",Intervention("MASK")),
            (names[0],Intervention("PATCH",active)),(names[1],Intervention("PATCH_MASK",active))],"semantic_patch")
        rr=[r for r in rows if r["phase"]=="semantic_patch"]
        patch=dict(forward=paired_effect(rr,"FULL",names[0]),reverse=paired_effect(rr,"MASK",names[1]))
        save(output/"semantic_patch.json",patch)
        if (patch["forward"]["mean"] or 0)<=0 or (patch["reverse"]["mean"] or 0)>=0:
            save(output/"semantic_summary.json",dict(status="stopped_directional_patch_not_supported",candidate=frozen,patch=patch));return
    else:
        rows=measure(backend,manifest,config,output,budget,[("FULL",Intervention()),("MASK",candidate),
            ("VALUE_ZERO",Intervention("VALUE_ZERO",active))],"semantic_redistribution")
        save(output/"semantic_redistribution.json",effects("semantic_redistribution",["MASK","VALUE_ZERO"]))
    rng=random.Random(20261005)
    control=Intervention(mode,tuple(rng.sample(list(parent),len(active))))
    rows=measure(backend,manifest,validation,output,budget,[("FULL",Intervention()),("MASK",Intervention("MASK")),
        ("CANDIDATE",candidate),("CONTROL",control)],"semantic_validation")
    ve=effects("semantic_validation",["CANDIDATE","CONTROL"])
    save(output/"semantic_validation.json",dict(effects=ve,control_heads=control.heads,
         available_questions=len(validation["probes"]),missing=validation["missing"],
         note="Random heads sampled without replacement from the same parent layer group; overlap with candidate is allowed."))
    ce,re=ve["CANDIDATE"]["mean"],ve["CONTROL"]["mean"]
    if ce is None or re is None or ce<=0 or ce<=re:
        save(output/"semantic_summary.json",dict(status="stopped_semantic_validation_failed",candidate=frozen,validation=ve));return
    # Keep new behavioural records separate from the first run, sharing its budget.
    bridge_output=output/"semantic_behaviour"
    bridge_output.mkdir(exist_ok=True)
    experiment=Experiment(backend,manifest,bridge_output,budget)
    ids=manifest["validation"]
    experiment.bridge(ids[:4],candidate)
    first=experiment.behaviour(ids[:4])
    if first["candidate_correct"]>first["full_correct"] and first["candidate_reuse"]<first["full_reuse"]:
        experiment.bridge(ids[4:8],candidate)
    save(output/"semantic_summary.json",dict(status="completed_semantic_followup",candidate=frozen,
        validation=ve,first_bridge=first,behaviour=experiment.behaviour(ids[:8])))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--localize",action="store_true")
    args=parser.parse_args()
    manifest=json.loads((args.output/"manifest.json").read_text())
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(manifest["model"],local_files_only=True)
    config=prepare(manifest,tokenizer)
    path=args.output/"semantic_probes.json"
    if path.exists() and json.loads(path.read_text())!=config:
        raise ValueError("Frozen semantic probes changed; do not mix results")
    save(path,config)
    validation=prepare(manifest,tokenizer,"validation")
    vp=args.output/"semantic_validation_probes.json"
    if vp.exists() and json.loads(vp.read_text())!=validation:
        raise ValueError("Frozen validation probes changed")
    save(vp,validation)
    if args.prepare:
        print(json.dumps(dict(available={q:p["index"] for q,p in config["probes"].items()},missing=config["missing"],
            validation_available={q:p["index"] for q,p in validation["probes"].items()}),indent=2));return
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.diagnostics import DiagnosticBackend, Intervention
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    if not json.loads((args.output/"acceptance.json").read_text()).get("passed"):
        raise RuntimeError("Existing backend acceptance must have passed")
    budget=Budget(args.output/"budget.json",manifest["gpu_hours"])
    try:
        model=AutoModelForCausalLM.from_pretrained(manifest["model"],local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation="sdpa",device_map="cuda:0")
        backend=DiagnosticBackend(model,tokenizer,budget.check)
        if args.localize and not (args.output/"semantic_generation_acceptance.json").exists():
            q=next(q for q in manifest["questions"] if q["id"]==manifest["validation"][0])
            from selective_context.schema import SelectiveContextRequest
            request=SelectiveContextRequest.from_dict(q["request"])
            pre=backend.prefill(request.input_ids)
            checks=[]
            for mode in ("FULL","MASK","VALUE_ZERO"):
                result=backend.generate_diagnostic(pre,request,Intervention(mode),max_new_tokens=2,
                                                  **manifest["sampling"])
                assert 0<len(result.generated_token_ids)<=2 and result.finish_reason in ("eos","length")
                checks.append(dict(mode=mode,tokens=len(result.generated_token_ids),finish_reason=result.finish_reason))
            save(args.output/"semantic_generation_acceptance.json",dict(passed=True,checks=checks))
            del pre
        rows=measure(backend,manifest,config,args.output,budget,
            [("FULL",Intervention()),("VALUE_ZERO",Intervention("VALUE_ZERO")),("MASK",Intervention("MASK"))])
        screen=report(args.output,config,rows)
        print(json.dumps(screen,indent=2),flush=True)
        if args.localize:
            localize(backend,manifest,config,validation,args.output,budget,screen)
    except BudgetExceeded:
        save(args.output/"semantic_summary.json",dict(status="budget_exhausted"))
    except Exception as exc:
        save(args.output/"semantic_failure.json",dict(type=type(exc).__name__,message=str(exc)))
        save(args.output/"semantic_summary.json",dict(status="failed",type=type(exc).__name__,message=str(exc)))
        raise
    finally:
        budget.close()
        summary=args.output/"semantic_summary.json"
        if summary.exists():
            (args.output/"semantic_report.md").write_text(
                "# Reviewed invalid-construction rejection\n\n"+config["interpretation"]+
                "\n\nThe four discovery and five validation probes were reviewed before intervention effects. "
                "Missing questions are retained without replacement. Effects compare candidate sequence log probabilities "
                "on identical prefixes against FULL; these are not calibrated correctness probabilities. "
                "Collective effects do not establish harmful individual heads.\n\n```json\n"+
                summary.read_text()+"\n```\n",encoding="utf-8")


if __name__=="__main__":
    main()
