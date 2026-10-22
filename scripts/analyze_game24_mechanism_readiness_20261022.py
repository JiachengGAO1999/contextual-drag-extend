"""Describe existing outcomes only; no model imports, new sampling, or relabeling."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from analyze_batch03_partial_20260924 import expression_measurement

DEV = ROOT/"outputs/game24-replication-qwen3-8b-development-20261017"
CONF = ROOT/"outputs/game24-replication-qwen3-8b-heldout82-20261019"
OUT = ROOT/"outputs/game24-mechanism-readiness-20261022"


def rows(p):
    return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]


def morphology(expression,numbers):
    measure=expression_measurement(expression,numbers)
    if expression.strip()=="24": return "scalar_only_unresolved",measure
    if measure["evaluation_status"]!="ok": return "unresolved_expression",measure
    a,b=measure["arithmetic_is_24"],measure["operand_multiset_matches"]
    category={(True,False):"value24_inventory_invalid",(False,True):"value_invalid_inventory_valid",
              (False,False):"both_invalid",(True,True):"exact_correct_expression"}[a,b]
    return category,measure


def main():
    source_profiles=[]
    for p in [DEV/"selected_source_records.jsonl",CONF/"selected_source_records.jsonl"]:
        for r in rows(p):
            raw=r["raw_record"]
            g=raw["init_response_generations"][0]
            label,measure=morphology(g.get("extracted_answer") or "",raw["answer"])
            source_profiles.append(dict(id="tot-rank:"+str(raw["id"]),source_trajectory_id=r["trajectory"]["trajectory_id"],
                morphology=label,measurement=measure))
    by={}; profiles=[]; counts={c:Counter() for c in ["R0","R2","R3"]}
    for p in [DEV/"results.jsonl",CONF/"results.jsonl"]:
        for r in rows(p):
            g=r["init_response_generations"][0]
            meta=r["init_response_generations_metadata"]["intervention"]
            q,s,c=r["id"],meta["sample_seed"],meta["condition_id"]
            assert c not in by.setdefault((q,s),{})
            by[q,s][c]=g.get("correctness") is True
            label,measure=morphology(g.get("extracted_answer") or "",r["answer"])
            if g["finish_reason"]=="length": label="length_limited"
            elif g.get("correctness") is True: label="official_correct"
            counts[c][label]+=1
            profiles.append(dict(id=q,seed=s,condition=c,finish_reason=g["finish_reason"],
                original_correctness=g.get("correctness"),derived_shape_category=label,measurement=measure))
    assert len(profiles)==612 and len(source_profiles)==102
    split=json.loads((ROOT/"docs/game24_100q_8b/game24_split_manifest.json").read_text(encoding="utf-8"))
    scopes={}
    for scope,ids in [("development20",split["development"]),("heldout82",split["held_out"]),
                      ("pooled102",split["development"]+split["held_out"])]:
        triples=Counter("".join(str(int(g[c])) for c in ["R0","R2","R3"]) for (q,s),g in by.items() if q in ids)
        scopes[scope]=dict(questions=len(ids),paired_seed_units=2*len(ids),triple_counts=dict(sorted(triples.items())))
    inputs=[DEV/"results.jsonl",CONF/"results.jsonl",DEV/"selected_source_records.jsonl",CONF/"selected_source_records.jsonl"]
    data=ROOT/"docs/game24_100q_8b"
    eligible_ids={t for r in rows(data/"game24_eligible_100.jsonl") for t in r["trajectory_ids"]}
    pool_counts=Counter();pool_questions={}
    for r in rows(data/"game24_trajectory_pool.jsonl"):
        if r["trajectory_id"] not in eligible_ids or r["classification"]!="substantive_error": continue
        measure=r["audit"].get("measurement",r["audit"])
        a,b=measure.get("arithmetic_is_24"),measure.get("operand_multiset_matches")
        label={(True,False):"value24_inventory_invalid",(False,True):"value_invalid_inventory_valid",
               (False,False):"both_invalid"}.get((a,b),"other_or_unresolved")
        pool_counts[label]+=1
        pool_questions.setdefault(label,set()).add(r["tot_rank"])
    inputs += [data/"game24_eligible_100.jsonl",data/"game24_trajectory_pool.jsonl"]
    summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),status="CPU_exploratory_description_only",
        new_model_requests=0,source_draft_morphology=dict(Counter(r["morphology"] for r in source_profiles)),
        response_shape_counts={c:dict(v) for c,v in counts.items()},paired_patterns=scopes,
        all_eligible_failed_trajectory_counts=dict(pool_counts),
        questions_per_source_error_type={k:len(v) for k,v in pool_questions.items()},
        questions_with_both_main_error_types=len(pool_questions.get("value24_inventory_invalid",set()) & pool_questions.get("value_invalid_inventory_valid",set())),
        interpretation="Final-expression shape and observed seed outcomes do not identify internal mechanisms, full trajectory content, or stable question phenotypes. No original correctness changed.",
        input_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    OUT.mkdir(parents=True,exist_ok=True)
    for name,value in [("summary.json",summary),("source_draft_profiles.json",source_profiles),("response_profiles.json",profiles)]:
        (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
