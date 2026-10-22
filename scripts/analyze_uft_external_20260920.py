"""Paired question-cluster analysis; no generation or outcome-based exclusions."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/game24-uft-external-20q-20260919'
CS=['R0','R2','R3','R4']

def main():
    rows=[json.loads(l) for l in (OUT/'results.jsonl').read_text(encoding='utf8').splitlines()]
    groups={}
    for r in rows:
        m=r['init_response_generations_metadata']['intervention'];key=(r['id'],m['sample_seed'])
        g=groups.setdefault(key,{})
        assert m['condition_id'] not in g
        g[m['condition_id']]=r
    assert len(rows)==160 and len(groups)==40 and all(set(g)==set(CS) for g in groups.values())
    for g in groups.values():
        ms=[g[c]['init_response_generations_metadata']['intervention'] for c in CS[1:]]
        for field in ['input_ids','prompt_sha256','input_ids_sha256','draft_token_span']:
            assert all(m[field]==ms[0][field] for m in ms)
    ids=sorted({q for q,s in groups},key=int);seeds=sorted({s for q,s in groups})
    get=lambda r:r['init_response_generations'][0]
    a=np.array([[[get(groups[q,s][c])['correctness'] is True for c in CS] for s in seeds] for q in ids],dtype=float)
    boot=a.mean(1)[np.random.default_rng(2027).integers(0,len(ids),(10000,len(ids)))].mean(1)
    effects={}
    for b,ref in [('R0','R2'),('R3','R2'),('R4','R2'),('R4','R3')]:
        bi,ri=CS.index(b),CS.index(ref);d=a[:,:,bi]-a[:,:,ri]
        effects[b+'-'+ref]=dict(effect_pp=float(d.mean()*100),ci95_pp=(np.quantile(boot[:,bi]-boot[:,ri],[.025,.975])*100).tolist(),
          wrong_to_correct=int((d==1).sum()),correct_to_wrong=int((d==-1).sum()),transition_direction=ref+' -> '+b)
    summary=dict(questions=len(ids),seeds=seeds,generations=len(rows),
      bootstrap='question cluster,10000 resamples,seed2027; null counts as not correct',
      conditions={c:dict(correct=int(a[:,:,i].sum()),n=40,accuracy=float(a[:,:,i].mean()),
        eos=sum(get(g[c])['finish_reason']=='eos' for g in groups.values()),
        scored=sum(get(g[c])['correctness'] is not None for g in groups.values()),
        parsable_thinking=sum(g[c]['thinking_status']=='parsable_thinking' for g in groups.values()),
        mean_output_tokens=float(np.mean([len(g[c]['generated_token_ids']) for g in groups.values()]))) for i,c in enumerate(CS)},
      effects=effects,per_question={q:dict(zip(CS,qa.sum(0).astype(int).tolist())) for q,qa in zip(ids,a)},
      same_text_pairs_checked=40,recovery_ratio=None,recovery_ratio_reason='No positive residual drag: R0-R2=-7.5pp')
    (OUT/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    snippets=[]
    for r in rows:
        g=get(r)
        if g['correctness'] is not True:
            m=r['init_response_generations_metadata']['intervention']
            snippets.append(dict(id=r['id'],condition=m['condition_id'],seed=m['sample_seed'],finish=g['finish_reason'],
              correctness=g['correctness'],extracted_answer=g.get('extracted_answer'),output_tail=g['generated_response'][-2000:]))
    (OUT/'failure_review.json').write_text(json.dumps(snippets,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
