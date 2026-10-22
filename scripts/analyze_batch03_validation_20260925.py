"""Audit completed Batch03 validation without changing persisted scorer labels."""
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from build_iclr2027_evidence_20260925 import normalized, check_factorial, stats, INPUTS
from analyze_batch03_partial_20260924 import expression_measurement

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'runs/game24_batch03_validation_20260925_raw'
OUT = ROOT / 'runs/game24_batch03_validation_20260925_analysis'
CONDITIONS = ('R0','R2','R3','R4')

def main():
    OUT.mkdir(exist_ok=True)
    path = RAW/'results.jsonl'
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == 'f57efbe634fca66ea13e983ffccff04e13ce3101405497e45d6918f8f6dc63ea', 'Remote snapshot mismatch'
    plan = json.loads((ROOT/'runs/batch03_next_experiment_20260924/plan.json').read_text())
    assert hashlib.sha256((ROOT/plan['pairs_file']).read_bytes()).hexdigest() == plan['pairs_sha256']
    completion=json.loads((RAW/'completion.json').read_text())
    assert completion['completed']==64
    assert json.loads((RAW/'streaming_smoke.json').read_text())['passed']
    rows=normalized(path)
    assert set(r['id'] for r in rows)==set(plan['question_ids'])
    assert set(r['seed'] for r in rows)==set(plan['seeds'])
    audit=check_factorial(rows,CONDITIONS,8)
    old=normalized(INPUTS['game24_qwen8_7'])+normalized(INPUTS['game24_qwen8_8'])
    assert not set(r['id'] for r in rows)&set(r['id'] for r in old)
    raws=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    old_raws=[json.loads(line) for p in (INPUTS['game24_qwen8_7'],INPUTS['game24_qwen8_8']) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert not {tuple(sorted(r['answer'])) for r in raws}&{tuple(sorted(r['answer'])) for r in old_raws}
    score_review=[]
    for r,n in zip(raws,rows):
        g=r['init_response_generations'][0]
        expression=g.get('extracted_answer') or ''
        measurement=expression_measurement(expression,r['answer'])
        assert measurement['evaluation_status']=='ok', (n['id'],n['condition'],measurement)
        assert measurement['exact_game24']==bool(n['correct']), (n['id'],n['condition'],measurement)
        score_review.append(dict(id=n['id'],seed=n['seed'],condition=n['condition'],score_status=n['score_status'],finish_reason=n['finish_reason'],extracted_answer=expression,measurement=measurement,final_response=r.get('final_response')))
    per_question=[]
    for q in sorted(set(r['id'] for r in rows),key=int):
        item=dict(id=q)
        for c in CONDITIONS:
            selected=[r for r in rows if r['id']==q and r['condition']==c]
            item[c]=sum(r['correct'] for r in selected)
        per_question.append(item)
    diagnostics={c:dict(finish_reasons=dict(Counter(r['finish_reason'] for r in rows if r['condition']==c)),score_status=dict(Counter(r['score_status'] for r in rows if r['condition']==c)),tokens_mean=statistics.mean(r['generated_tokens'] for r in rows if r['condition']==c),tokens_median=statistics.median(r['generated_tokens'] for r in rows if r['condition']==c),tokens_max=max(r['generated_tokens'] for r in rows if r['condition']==c)) for c in CONDITIONS}
    exclude=[r for r in rows if r['id']!='381']
    pooled=old+rows
    panels={}
    for name,items,n in [('new_8_questions',rows,8),('new_excluding_381',exclude,7),('pooled_23_questions',pooled,23),('pooled_excluding_381',old+exclude,22)]:
        panels[name]=dict(audit=check_factorial(items,CONDITIONS,n),stats=stats(items))
    report=dict(source_sha256=sha,completion=completion,audit=audit,diagnostics=diagnostics,per_question=per_question,panels=panels,scoring_verification=score_review,notes=['Persisted scorer labels unchanged; unresolved counted incorrect.','Percentile 95% question-cluster bootstrap, 50000 draws; seeds kept together.','New set and old 15 questions disjoint by ID and number multiset.','Pooled results are Qwen3-8B only; other target models still cover 15 questions.','Completed-prefix selection and adaptive acquisition limit generalization.'])
    (OUT/'analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (OUT/'per_question.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=['id',*CONDITIONS]);w.writeheader();w.writerows(per_question)
    (OUT/'score_review.json').write_text(json.dumps(score_review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'audit':audit,'all_64_expressions_match_frozen_scores':True,'effects':{k:v['stats']['effects']['R3-R2'] for k,v in panels.items()}},indent=2))

if __name__=='__main__':
    main()
