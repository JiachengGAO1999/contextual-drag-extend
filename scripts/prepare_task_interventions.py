"""Prepare independent-solve R0/R2/R3/R4 bundles from audited fixed pairs."""
import argparse
import hashlib
import json
from pathlib import Path
from selective_context.tasks import TASKS, independent_prompt, validate_pair_task
from selective_context.prompting import (encode_direct_prompt,encode_prompt,render_chat_prompt,
    make_request,make_r2_r4_requests,persist_request_bundle)
from selective_context.schema import AccessMode

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--task',choices=TASKS,required=True)
    ap.add_argument('--pairs',type=Path,required=True)
    ap.add_argument('--tokenizer',required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seeds',type=int,nargs='+',required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output.exists():raise ValueError('Refusing overwrite')
    out=args.output.resolve();out.relative_to(root)
    rows=[json.loads(l) for l in args.pairs.read_text(encoding='utf-8').splitlines() if l.strip()]
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('Empty or duplicate pairs')
    if len(set(args.seeds))!=len(args.seeds):raise ValueError('Duplicate seeds')
    for row in rows:
        validate_pair_task(row,args.task)
        if row.get('audit_status')!='substantive_failed' or not row.get('traj1','').strip():
            raise ValueError('Require explicitly audited substantive_failed pairs')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,use_fast=True)
    out.mkdir(parents=True);manifest=[]
    for row in rows:
        # Dataset unique_id can contain slash; never use it directly as a filename.
        key=hashlib.sha256(row['id'].encode()).hexdigest()[:24]
        pair=out/f'{key}.pair.json';pair.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
        for seed in args.seeds:
            r0=encode_direct_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem'],task=args.task),True))
            r2=encode_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem'],row['traj1'],args.task),True))
            for suffix,enc,reqs in [('r0',r0,[make_request(r0,'R0',AccessMode.FULL,seed)]),('r2_r4',r2,make_r2_r4_requests(r2,seed))]:
                if len(enc.input_ids)>=32768:raise ValueError('No completion budget; do not truncate')
                path=out/f'{key}.{seed}.{suffix}.json';persist_request_bundle(path,enc,reqs)
                manifest.extend(dict(task=args.task,bundle=path.relative_to(root).as_posix(),pair=pair.relative_to(root).as_posix(),condition=r.condition_id) for r in reqs)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Prepared {len(manifest)} requests; no generation started')

if __name__=='__main__':main()
