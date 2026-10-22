"""CPU-only preparation. Never selects failures or starts generation."""
import argparse
import hashlib
import json
import random
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--count',type=int,required=True)
    ap.add_argument('--samples',type=int,required=True)
    ap.add_argument('--order-seed',type=int,default=20270919)
    args=ap.parse_args()
    if args.output.exists():raise ValueError('Refusing overwrite')
    from datasets import load_from_disk
    ds=load_from_disk(str(args.dataset))
    if hasattr(ds,'keys'):ds=ds['test']
    rows=[dict(task='math500',id=r['unique_id'],problem=r['problem'],answer=r['answer'],
               subject=r['subject'],level=r['level']) for r in ds]
    if len(rows)!=500 or len({r['id'] for r in rows})!=500:raise ValueError('Expected 500 unique MATH500 items')
    if not 0<args.count<=500 or args.samples<1:raise ValueError('Invalid sample budget')
    rows.sort(key=lambda r:r['id'])
    random.Random(args.order_seed).shuffle(rows)
    args.output.mkdir(parents=True)
    (args.output/'source.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
    manifest=dict(task='math500',status='prepared_not_launched',candidate_count=args.count,
        samples_per_problem=args.samples,seed=42,order_seed=args.order_seed,
        total_generations=args.count*args.samples,
        source_sha256=hashlib.sha256((args.output/'source.jsonl').read_bytes()).hexdigest(),
        candidate_rows=[dict(id=r['id'],problem_sha256=sha(r['problem']),answer_sha256=sha(r['answer'])) for r in rows[:args.count]])
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))

if __name__=='__main__':main()
