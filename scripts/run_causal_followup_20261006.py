"""Frozen source-direction control and time localization; share the original GPU budget."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_generation_diagnostics_20261005 import Budget,BudgetExceeded,Experiment,save
from run_semantic_rejection_20261005 import measure
from run_information_followup_20261005 import freeze,natural_summary
from selective_context.diagnostic_data import read_jsonl,paired_effect

EVENTS={
    "434":dict(reference="Let me try the 6×4 approach",expansion="If I do 11 divided by 11",
               reason="After 11-5, only one 11 remains; the next division reuses 11."),
    "956":dict(reference="Oh, the draft had",expansion="So, 8 divided by 8 is 1",
               reason="Replays the draft computation after quoting an expression with three 8s."),
    "1305":dict(reference="First, let me look at the original draft's approach.",expansion="So using 10 ÷ 5",
                reason="Expands number allocation for the old construction, which uses three 10s."),
    "230":dict(reference="Oh, the draft's final answer was",expansion="First, 11 divided by 11",
               reason="Replays the old expression before accepting its number-use validity."),
}


def prepare(manifest,tokenizer,output,probes,heads):
    annotations={};missing={}
    for q in manifest["questions"]:
        if q["id"] not in manifest["discovery"]:continue
        if q["id"] not in EVENTS or q["id"] not in probes["probes"]:
            missing[q["id"]]="No reviewed expansion and subsequent endorsement within 512 tokens.";continue
        event=EVENTS[q["id"]];tokens=q["suffixes"]["wrong"]["tokens"][:512]
        text=tokenizer.decode(tokens)
        boundaries={len(tokenizer.decode(tokens[:i])):i for i in range(len(tokens)+1)}
        def index(anchor):
            start=text.index(anchor)
            return boundaries[max(p for p in boundaries if p<=start)]
        e=index(event["expansion"]);p=probes["probes"][q["id"]]["index"]
        if not 32<=e or e+32>p:
            raise ValueError("Expansion window must precede the reviewed acceptance")
        windows=dict(EARLY=(0,32),EXPANSION=(e,e+32),PRE_ACCEPT=(p-32,p))
        # Neutral only when a disjoint full-length interval fits between events.
        gap=p-32-(e+32)
        if gap>=32:
            start=e+32+(gap-32)//2;windows["NEUTRAL"]=(start,start+32)
        annotations[q["id"]]=dict(reference=index(event["reference"]),expansion=e,acceptance=p,
            windows=windows,reason=event["reason"],
            classification="Source calculation replay followed by explicit invalid-construction endorsement; quotation alone is not commitment.",
            post_acceptance="Missing unambiguous subsequent decision within the frozen replay limit.")
    frozen=json.loads((output/"semantic_candidate.json").read_text())
    config=dict(model=manifest["model"],dtype="bfloat16",heads=heads,strength=frozen["strength"],
        annotations=annotations,missing=missing,replay_limit=512,window_length=32,
        metric=probes["metric"],
        source_gate="Candidate > FULL and candidate > same-site norm-matched NON_DRAFT control on mean rejection preference.",
        timing_gate="Best semantic window > FULL, EARLY and NEUTRAL on common annotated questions; no missing neutral fallback.",
        bridge_ids=manifest["validation"][8:12],max_generations=32,
        bridge_window_rule="Median discovery onset of the frozen window type, same absolute query window across all bridge questions/seeds.",
        limitations=["Norm matched per head before o_proj, not after projection.",
                     "Generation-bridge timing is a fixed absolute window, not an online semantic event detector.",
                     "Seven remaining questions have no current natural-generation runs; some had earlier semantic probes."])
    freeze(output/"causal_followup_config.json",config)
    return config


def effects(rows,phase,condition,before="FULL",ids=None):
    rr=[r for r in rows if r["phase"]==phase and (ids is None or r["id"] in ids)]
    return paired_effect(rr,before,condition)


def run(backend,manifest,probes,config,output,budget):
    from selective_context.diagnostics import Intervention
    heads=tuple(tuple(h) for h in config["heads"])
    candidate=Intervention("VALUE_ZERO",heads)
    control=Intervention("NON_DRAFT_MATCHED",heads)
    def measure_phase(phase,conditions,one_config=probes):
        return measure(backend,manifest,one_config,output,budget,conditions,phase,
                       result_file="causal_diagnostics.jsonl")
    save(output/"causal_summary.json",dict(status="running_source_control"))
    rows=measure_phase("source_control",[("FULL",Intervention()),("CANDIDATE",candidate),("CONTROL",control)])
    ce=effects(rows,"source_control","CANDIDATE")
    re=effects(rows,"source_control","CONTROL")
    contrast=effects(rows,"source_control","CANDIDATE",before="CONTROL")
    source=dict(candidate=ce,control=re,candidate_vs_control=contrast)
    save(output/"causal_source_control.json",source)
    if ce["mean"] is None or contrast["mean"] is None or ce["mean"]<=0 or contrast["mean"]<=0:
        save(output/"causal_summary.json",dict(status="stopped_source_specificity_not_supported",source=source));return

    save(output/"causal_summary.json",dict(status="running_query_windows",source=source))
    for qid,event in config["annotations"].items():
        one=dict(probes,probes={qid:probes["probes"][qid]})
        conditions=[("FULL",Intervention()),("PERSISTENT",candidate)]
        conditions += [(name,Intervention("VALUE_ZERO",heads,query_window=tuple(window)))
                       for name,window in event["windows"].items()]
        rows=measure_phase("query_windows",conditions,one)
    timing={c:effects(rows,"query_windows",c) for c in ("PERSISTENT","EARLY","EXPANSION","PRE_ACCEPT","NEUTRAL")}
    # Require comparisons on identical question sets; missing neutral is not zero.
    eligible=[qid for qid,e in config["annotations"].items() if "NEUTRAL" in e["windows"]]
    comparisons={c:dict(vs_full=effects(rows,"query_windows",c,ids=eligible),
                        vs_early=effects(rows,"query_windows",c,before="EARLY",ids=eligible),
                        vs_neutral=effects(rows,"query_windows",c,before="NEUTRAL",ids=eligible))
                 for c in ("EXPANSION","PRE_ACCEPT")}
    valid=[c for c,d in comparisons.items() if all(e["mean"] is not None and e["mean"]>0 for e in d.values())]
    save(output/"causal_timing.json",dict(effects=timing,common_questions=eligible,comparisons=comparisons))
    if not valid:
        save(output/"causal_summary.json",dict(status="stopped_no_semantic_window_specificity",source=source,timing=timing));return
    chosen=max(valid,key=lambda c:comparisons[c]["vs_full"]["mean"])
    start=int(statistics.median(config["annotations"][qid]["windows"][chosen][0] for qid in eligible))
    window=(start,start+32)
    frozen=dict(window_type=chosen,query_window=window,heads=heads,mode="VALUE_ZERO",strength=1.,
                common_questions=eligible,comparisons=comparisons[chosen],bridge_ids=config["bridge_ids"])
    freeze(output/"causal_window_candidate.json",frozen)

    # Patch only the selected query window, donors use the same token prefix.
    save(output/"causal_summary.json",dict(status="running_window_patch",window=frozen))
    for qid in eligible:
        w=tuple(config["annotations"][qid]["windows"][chosen])
        one=dict(probes,probes={qid:probes["probes"][qid]})
        rows=measure_phase("window_patch",[("FULL",Intervention()),("MASK_WINDOW",Intervention("MASK",query_window=w)),
            ("R2_FROM_R3",Intervention("PATCH",heads,query_window=w)),
            ("R3_FROM_R2",Intervention("PATCH_MASK",heads,query_window=w))],one)
    patch=dict(forward=effects(rows,"window_patch","R2_FROM_R3"),
               reverse=effects(rows,"window_patch","R3_FROM_R2",before="MASK_WINDOW"))
    save(output/"causal_window_patch.json",patch)
    if (patch["forward"]["mean"] or 0)<=0 or (patch["reverse"]["mean"] or 0)>=0:
        save(output/"causal_summary.json",dict(status="stopped_window_patch_not_supported",window=frozen,patch=patch));return

    out=output/"causal_behaviour";out.mkdir(exist_ok=True)
    experiment=Experiment(backend,manifest,out,budget)
    save(output/"causal_summary.json",dict(status="running_window_bridge",window=frozen))
    experiment.bridge(config["bridge_ids"],candidate,conditions=[("FULL",Intervention()),("CANDIDATE",candidate),
        ("WINDOW",Intervention("VALUE_ZERO",heads,query_window=window)),
        ("CONTROL",Intervention("NON_DRAFT_MATCHED",heads,query_window=window))])
    stats=natural_summary(read_jsonl(out/"behaviour.jsonl"))
    save(output/"causal_behaviour_summary.json",dict(stats=stats,window=frozen))
    save(output/"causal_summary.json",dict(status="completed_causal_followup",source=source,window=frozen,patch=patch,behaviour=stats))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--status",action="store_true")
    args=parser.parse_args();output=args.output
    if args.status:
        from collections import Counter
        rows=read_jsonl(output/"causal_diagnostics.jsonl")
        result=dict(requests=dict(Counter(r["phase"] for r in rows)),
                    behaviour_requests=len(read_jsonl(output/"causal_behaviour/behaviour.jsonl")))
        for name in ("budget","causal_summary","causal_source_control","causal_timing","causal_window_patch"):
            f=output/(name+".json")
            if f.exists():result[name]=json.loads(f.read_text())
        print(json.dumps(result,indent=2));return
    manifest=json.loads((output/"manifest.json").read_text())
    probes=json.loads((output/"semantic_probes.json").read_text())
    frozen=json.loads((output/"semantic_candidate.json").read_text())
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(manifest["model"],local_files_only=True)
    config=prepare(manifest,tokenizer,output,probes,frozen["heads"])
    # Preserve the original discovery split; absent annotations stay absent.
    probes=dict(probes,probes={qid:probes["probes"][qid] for qid in config["annotations"]})
    from selective_context.tasks import score_record
    from selective_context.official_compat import make_official_record
    from selective_context.phase0.thinking_pilot import extract_final_draft
    if args.prepare:
        print(json.dumps(dict(annotations=config["annotations"],missing=config["missing"],
            bridge_ids=config["bridge_ids"],max_generations=32),indent=2));return
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.diagnostics import DiagnosticBackend
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 required")
    budget=Budget(output/"budget.json",manifest["gpu_hours"])
    try:
        acceptance=output/"causal_engine_acceptance.json"
        if not acceptance.exists():
            subprocess.run([sys.executable,"-m","pytest","-q","tests/selective_context/test_diagnostics.py"],cwd=ROOT,check=True)
            save(acceptance,dict(passed=True,scope="Norm-matched direction, window causality, windowed donor patch, prior backend regressions"))
            budget.check(force=True)
        model=AutoModelForCausalLM.from_pretrained(manifest["model"],local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation="sdpa",device_map="cuda:0")
        backend=DiagnosticBackend(model,tokenizer,budget.check)
        run(backend,manifest,probes,config,output,budget)
    except BudgetExceeded:
        save(output/"causal_summary.json",dict(status="budget_exhausted"))
    except Exception as exc:
        save(output/"causal_summary.json",dict(status="failed",type=type(exc).__name__,message=str(exc)));raise
    finally:
        budget.close()
        path=output/"causal_summary.json"
        if path.exists():
            (output/"causal_report.md").write_text("# Source specificity and generated-query timing\n\n"
                "Same frozen heads, no new head search. Windows index queries, not prediction tokens. "
                "Norm control matches pre-o_proj head-vector magnitude, not its direction or projected norm. "
                "Accept/reject probes are conditional sequence preferences, not solution accuracy.\n\n```json\n"+
                path.read_text()+"\n```\n",encoding="utf-8")


if __name__=="__main__":main()
