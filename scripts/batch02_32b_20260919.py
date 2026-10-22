"""Finish the entire frozen Batch02 second anchor; stop before intervention."""
import collections
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/game24-batch02-qwen32b-20260919'
BASE=ROOT/'outputs/game24-baseline-screen-vllm-20260918-batch02'

def save(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def audit():
    counts=collections.defaultdict(collections.Counter)
    by_model=collections.defaultdict(collections.Counter)
    review=[]
    sources=[('Qwen3_8B_Thinking',BASE/'draft_candidates.jsonl')]
    sources += [('Qwen3_32B',f) for f in sorted(OUT.glob('chunk-*/draft_candidates.jsonl'))]
    for alias,path in sources:
        for line in path.read_text().splitlines():
            r=json.loads(line);g=r['init_response_generations'][0];q=str(r['id'])
            by_model[q][alias]+=1
            valid=g['finish_reason']=='eos' and r['thinking_status']=='parsable_thinking'
            cat='excluded'
            if valid and g.get('correctness') is True:cat='correct'
            elif valid and g.get('correctness') is False:
                cat='official_false'
                review.append(dict(model=alias,id=q,draft_key=r['draft_key'],
                    extracted_answer=g.get('extracted_answer'),final_response=r['final_response'],
                    answer=r['answer'],source=str(path),manual_status='pending'))
            counts[q][cat]+=1
    eligible=[q for q,c in counts.items() if c['correct']>=2 and c['official_false']>=2
              and by_model[q]['Qwen3_8B_Thinking']==16 and by_model[q]['Qwen3_32B']==16]
    save(OUT/'pooled_scorer_summary.json',dict(counts=dict(counts),samples=dict(by_model),
         scorer_eligible=eligible,substantive_eligibility='pending manual audit; do not freeze from official_false',
         intervention_generations=0))
    save(OUT/'manual_review_queue.json',review)

def main():
    m=json.loads((ROOT/'scripts/baseline_screen_manifest_20260918_batch02.json').read_text())
    cfg=json.loads((BASE/'config.json').read_text())
    assert len(m['candidate_rows'])==32 and m['samples_per_problem']==16
    assert cfg['candidate_ids']==[r['id'] for r in m['candidate_rows']]
    OUT.mkdir(exist_ok=False)
    save(OUT/'manifest.json',dict(m,second_anchor='Qwen3_32B',new_generation_cap=512,
         eligibility='>=2 completed parseable True and >=2 manually substantive False pooled',
         selection='entire frozen batch; no filtering by 8B outcomes',interventions=False))
    status=dict(state='running',completed_generations=0,total=512,started_unix=time.time())
    t=time.monotonic()
    try:
        for i in range(0,32,2):
            name=f'chunk-{i:02d}'
            cm=dict(m,candidate_rows=m['candidate_rows'][i:i+2],candidate_count=2,total_generations=32)
            mp=OUT/f'{name}.json';save(mp,cm)
            status.update(current_chunk=name,elapsed_seconds=time.monotonic()-t)
            save(OUT/'status.json',status)
            cmd=[sys.executable,str(ROOT/'scripts/baseline_screen_vllm_20260917.py'),
                 '--model','/data/zhaoyi/liujunyuan/models/Qwen3-32B','--model-alias','Qwen3_32B',
                 '--input','/data2/gaojc/data/game24-tot-8050e67/24.csv',
                 '--source-revision','8050e67d0e3a0fddc424d7fa5801538722a4c4cc',
                 '--manifest',str(mp),'--output',str(OUT/name),
                 '--max-num-seqs','4','--max-num-batched-tokens','2048','--gpu-memory-utilization','.95']
            print('START',name,flush=True)
            with (OUT/f'{name}.log').open('w') as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            assert json.loads((OUT/name/'summary.json').read_text())['generations']==32
            status['completed_generations']+=32
            audit()
            save(OUT/'status.json',status)
            print('COMPLETE',name,status['completed_generations'],flush=True)
        status['state']='complete_awaiting_manual_pooled_audit'
    except Exception as exc:
        status.update(state='failed_no_fallback',error=repr(exc))
        raise
    finally:
        status['elapsed_seconds']=time.monotonic()-t
        save(OUT/'status.json',status)
        audit()

if __name__=='__main__':main()
