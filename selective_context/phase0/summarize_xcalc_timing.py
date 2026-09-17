"""Summarize the completed fresh-seed 2x2 matrix without further generation."""
import json, random
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[2]
    data={}
    for folder in ['game24-qwen3-x-vs-xcalc-fresh-seeds-20260916','game24-qwen3-x-vs-xcalc-path-fresh-seeds-20260916']:
        for f in (root/'outputs'/folder).glob('seed-*/results.jsonl'):
            for line in f.read_text().splitlines():
                r=json.loads(line);c=r['init_response_generations_metadata']['intervention']['condition_id']
                k=(r['id'],r['seed_base'],c);assert k not in data;data[k]=r
    cs=['M_X','L_XCALC_v1','P_X_fixed','P_XCALC_fixed'];ids=sorted({k[0] for k in data});seeds=[42027,52027,62027,72027]
    assert len(data)==96 and len(ids)==6
    val=lambda p,s,c:int(data[p,s,c]['init_response_generations'][0]['correctness'] is True)
    for p in ids:
        for s in seeds:
            reqs=[data[p,s,c]['init_response_generations_metadata']['intervention'] for c in cs]
            for r in reqs[1:]:
                for field in ['input_ids','sample_seed','prompt_sha256','input_ids_sha256','draft_token_span']:assert r[field]==reqs[0][field]
            assert reqs[0]['mask_token_spans']==reqs[2]['mask_token_spans']
            assert reqs[1]['mask_token_spans']==reqs[3]['mask_token_spans']
    def ci(means):
        rng=random.Random(2027);b=sorted(sum(rng.choice(means) for _ in means)/len(means)*100 for _ in range(10000));return [b[249],b[9749]]
    def effect(a,b):
        ds=[val(p,s,b)-val(p,s,a) for p in ids for s in seeds]
        return dict(delta_pp=sum(ds)/24*100,recovery=ds.count(1),harm=ds.count(-1),ci95=ci([sum(val(p,s,b)-val(p,s,a) for s in seeds)/4 for p in ids]))
    report=dict(n_questions=6,n_pairs=24,conditions={},effects={},per_question={})
    for c in cs:
        rs=[data[p,s,c] for p in ids for s in seeds];gs=[r['init_response_generations'][0] for r in rs]
        report['conditions'][c]=dict(correct=sum(g['correctness'] is True for g in gs),n=24,eos=sum(g['finish_reason']=='eos' for g in gs),parse=sum(g['correctness'] is not None for g in gs),mean_tokens=sum(len(r['generated_token_ids']) for r in rs)/24)
    for a,b in [(cs[0],cs[1]),(cs[2],cs[3]),(cs[0],cs[2]),(cs[1],cs[3])]:report['effects'][a+'->'+b]=effect(a,b)
    means=[sum(val(p,s,cs[3])-val(p,s,cs[2])-val(p,s,cs[1])+val(p,s,cs[0]) for s in seeds)/4 for p in ids]
    report['timing_coverage_interaction']=dict(delta_pp=sum(means)/6*100,ci95=ci(means))
    for p in ids:report['per_question'][p]={c:sum(val(p,s,c) for s in seeds) for c in cs}
    dest=root/'outputs/game24-xcalc-timing-comparison-20260916';dest.mkdir(exist_ok=True)
    (dest/'summary.json').write_text(json.dumps(report,indent=2))
    lines=['# Fresh-seed timing and coverage comparison','', 'Development set: six questions, four paired seeds. Old seeds are not pooled. Null scores count as noncorrect. No semantic-specificity claim.','', '|Condition|Correct / 24|EOS|Parse|','|---|---:|---:|---:|']
    for c,r in report['conditions'].items():lines.append(f"|{c}|{r['correct']}|{r['eos']}|{r['parse']}|")
    lines+=['','```json',json.dumps(report['effects'],indent=2),'```']
    (dest/'REPORT.md').write_text('\n'.join(lines))
    print('TIMING_COMPARISON_SAVED',flush=True)

if __name__=='__main__':main()
