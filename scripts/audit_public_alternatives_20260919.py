"""CPU-only availability checks of downloaded public alternatives, no generation."""
import csv,json,re,sys,hashlib
from pathlib import Path
from collections import Counter
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_public_uft_20260919 import exact
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/public-alternatives-audit-20260919'

def main():
    own=list(csv.DictReader((ROOT/'outputs/protocol-parity-audit-20260917/24.csv').open(encoding='utf-8-sig')))
    lookup={tuple(sorted(map(int,r['Puzzles'].split()))):str(r['Rank']) for r in own}
    hist=json.loads((ROOT/'outputs/baseline-corpus-audit-20260917/baseline_corpus_audit.json').read_text())
    used={tuple(sorted(r['number_multiset'])) for r in hist['problems']}
    for name in ('baseline_screen_manifest_20260917.json','baseline_screen_manifest_20260918_batch02.json','baseline_manifest_batch03_20260919.json'):
        used.update(tuple(sorted(r['numbers'])) for r in json.loads((ROOT/'scripts'/name).read_text())['candidate_rows'])
    source=list(csv.DictReader((OUT/'tot_24.csv').open(encoding='utf-8-sig')))
    totals=Counter();failed_q=set();fresh_q=set();candidates=[]
    for row in json.loads((OUT/'tot_cot.json').read_text()):
        nums=tuple(sorted(map(int,source[row['idx']]['Puzzles'].split())))
        assert nums in lookup
        assert len(row['ys'])==len(row['infos'])==100
        for i,(text,info) in enumerate(zip(row['ys'],row['infos'])):
            totals['rows']+=1;totals['source_correct' if info['r']==1 else 'source_incorrect']+=1
            if info['r']!=0:continue
            failed_q.add(lookup[nums])
            ans=text.rsplit('Answer:',1)
            if len(ans)!=2:totals['no_answer_marker']+=1;continue
            expr=ans[-1].strip().split('=')[0].strip()
            try:
                if re.search(r'\d\.\d',expr):raise ValueError('decimal')
                val=exact(expr);wrong=Counter(map(int,re.findall(r'\d+',expr)))!=Counter(nums) or val!=24
            except Exception:totals['final_unresolved']+=1;continue
            if wrong:
                totals['verified_final_error']+=1
                if nums not in used:
                    fresh_q.add(lookup[nums]);candidates.append(dict(id=lookup[nums],idx=row['idx'],sample=i,numbers=nums,draft=text,final_value=str(val)))
            else:totals['source_false_but_valid_expression']+=1
    rs=pq.read_table(OUT/'jrosser.parquet').to_pylist()
    wrong=[r for r in rs if r['is_correct'] is False]
    complete=[r for r in wrong if '</think>' in r['response'] and r['model_answer'] and '\\boxed' in r['response'].rsplit('</think>',1)[-1]]
    first=wrong[0]
    math500=json.loads((OUT/'rasbt_r1.json').read_text())
    normalize=lambda s:' '.join(s.split())
    reference={normalize(r['problem']) for r in math500}
    overlap={normalize(r['problem']) for r in rs}&reference
    result=dict(tot=dict(counts=dict(totals),questions=100,questions_with_source_failure=len(failed_q),
                         fresh_questions_with_verified_final_error=len(fresh_q),fresh_error_rows=len(candidates),
                         eos_metadata=False,notes='Formula-only CPU recheck; steps and completion still need manual review'),
                jrosser=dict(rows=len(rs),questions=len({r['problem_idx'] for r in rs}),
                             source_false=len(wrong),questions_with_source_false=len({r['problem_idx'] for r in wrong}),
                             source_false_complete_looking=len(complete),
                             questions_with_complete_looking_false=len({r['problem_idx'] for r in complete}),
                             exact_whitespace_normalized_overlap_with_rasbt_math500=len(overlap),
                             first_false_example=dict(problem=first['problem'],gold=first['gt_answer'],model_answer=first['model_answer']),
                             eos_metadata=False,labels_reverified=False),
                new_generations=0,
                files_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in OUT.iterdir() if f.name in ('tot_cot.json','tot_24.csv','jrosser.parquet','rasbt_r1.json')})
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'tot_fresh_automatic_candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in candidates),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
