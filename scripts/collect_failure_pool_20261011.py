"""Inventory existing same-model completed natural Game24 failures; CPU only."""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_cross_question_verification_20261007 import SOURCES
from run_identity_mvp_20261011 import audit_expression
from run_identity_prospective_20261011 import solve
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import load


def collect(output):
    path=output/'candidate_adoption/failure_pool.json'
    if path.exists(): return load(path)
    paths=[ROOT/s for s in SOURCES]+sorted((ROOT/'outputs').rglob('draft_candidates.jsonl'))
    seen_paths=set(); choices={}; counts=[]
    for source in paths:
        if source in seen_paths or not source.exists() or 'game24' not in str(source): continue
        seen_paths.add(source); examined=eligible=0
        with source.open() as f:
            for line,text in enumerate(f,1):
                if not text.strip(): continue
                row=json.loads(text); meta=row.get('init_response_generations_metadata',{})
                if meta.get('model_config_alias')!='Qwen3_8B_Thinking' or not meta.get('enable_thinking'): continue
                examined+=1
                for gi,g in enumerate(row.get('init_response_generations',[])):
                    if g.get('finish_reason')!='eos' or g.get('correctness') is not False: continue
                    expression=g.get('extracted_answer'); audit=audit_expression(expression,row['answer'])
                    if not audit.get('parsed') or audit['correct']: continue
                    draft=row.get('final_response')
                    if not draft:
                        generated=g.get('generated_response','')
                        draft=generated.rsplit('</think>',1)[1] if '</think>' in generated else generated
                    draft=draft.removesuffix('<|im_end|>').removesuffix('<|endoftext|>')
                    if not draft or '<think>' in draft or '</think>' in draft or expression not in draft: continue
                    eligible+=1; ns=tuple(sorted(row['answer']))
                    if ns in choices: continue
                    witness=solve(ns)
                    if not witness: continue
                    choices[ns]=dict(id=str(row['id']),answer=list(ns),problem=row['problem'],draft=draft,old_expression=expression,
                        old_audit=audit,source=str(source.relative_to(ROOT)),source_line=line,source_generation=gi,
                        draft_key=row.get('draft_key'),legal_expression=witness,source_model=meta['model_config_alias'])
        if examined: counts.append(dict(source=str(source.relative_to(ROOT)),examined=examined,eligible=eligible))
    used=set()
    for name in ('identity_mvp','identity_prospective'):
        used.update(tuple(sorted(q['answer'])) for q in load(output/name/'manifest.json')['questions'])
    items=list(choices.values())
    for q in items:
        q['prior_identity_exposure']=tuple(q['answer']) in used
        q['error_type']='inventory_only' if q['old_audit']['target_correct'] else 'value_only' if q['old_audit']['inventory_correct'] else 'both'
    result=dict(questions=items,source_counts=counts,total_unique=len(items),unseen_identity=sum(not q['prior_identity_exposure'] for q in items),
        by_error_type=dict(Counter(q['error_type'] for q in items)),
        scope='Existing Qwen3-8B Thinking completed natural initial failures, fixed source priority then file lexical order, first eligible per number multiset. No new generations or selection by identity effect.')
    save(path,result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/generation-diagnostics-20261005')
    a=p.parse_args(); result=collect(a.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('questions','source_counts')},indent=2))
