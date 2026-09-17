"""Frozen ten-question R1 supplement; reuse exact existing paired seeds."""
import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.phase0.real_smoke import append, evaluate, save
from selective_context.phase0.thinking_pilot import independent_prompt, rows_from, extract_final_draft, generation_budget
from selective_context.prompting import encode_prompt, render_chat_prompt, make_request, persist_request_bundle
from selective_context.schema import AccessMode

ORACLE = '\nThe following draft has an INCORRECT final answer.\n'


def r1_prompt(problem, draft):
    # Remove only the oracle sentence; preserve the existing draft delimiters/task.
    full = independent_prompt(problem, draft)
    assert full.count(ORACLE) == 1
    return full.replace(ORACLE, '\n', 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    model_path = '/data2/huangrj/models/qwen3-8b'
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, use_fast=True)
    jobs = []
    for seed_base in [2027,12027,22027,32027]:
        old = root/'outputs/game24-independent-control-20260910' if seed_base == 2027 else root/f'outputs/game24-independent-stage-a-20260910/seed-{seed_base}'
        new = root/f'outputs/game24-stage-b-paired-20260911/seed-{seed_base}'
        for run in [old,new]:
            config = json.loads((run/'config.json').read_text())
            assert (config['temperature'],config['top_p'],config['top_k'],config['context_size']) == (.6,.95,20,32768)
            for record in rows_from(run/'results.jsonl'):
                meta = record['init_response_generations_metadata']['intervention']
                if meta['condition_id'] != 'R2': continue
                row = json.loads((run/'pairs'/f"{record['id']}.json").read_text())
                full = encode_prompt(tokenizer, render_chat_prompt(tokenizer, independent_prompt(row['problem'],row['traj1']),enable_thinking=True))
                prior = json.loads((run/'bundles'/f"{row['id']}.r2_r4.json").read_text())['requests'][0]
                assert list(full.input_ids) == prior['input_ids'], 'Existing R2 prompt changed'
                encoded = encode_prompt(tokenizer,render_chat_prompt(tokenizer,r1_prompt(row['problem'],row['traj1']),enable_thinking=True))
                request = make_request(encoded,'R1',AccessMode.FULL,prior['sample_seed'])
                generation_budget(len(request.input_ids))
                jobs.append((seed_base,row,encoded,request,str(run.relative_to(root))))
    assert len(jobs)==40
    assert len({(s,r['id']) for s,r,_,_,_ in jobs})==40
    print('PREFLIGHT_PASSED: 40 unique jobs; exact existing R2 tokenization and paired seeds verified',flush=True)
    if args.preflight_only: return
    if args.output.exists(): raise RuntimeError('Output exists; no implicit resume/overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'config.json',dict(model=model_path,conditions=['R1'],count=40,temperature=.6,top_p=.95,top_k=20,context_size=32768,enable_thinking=True,backend='hf_eager_bfloat16',sampling_dtype='float32',change='Only remove R2 oracle sentence; preserve draft delimiters and independent suffix',seed_rule='Exact sample_seed from corresponding persisted R2 bundle',r1_template=r1_prompt('{problem}','{draft}')))
    save(args.output/'manifest.json',[dict(seed_base=s,id=r['id'],sample_seed=q.sample_seed,source=src) for s,r,e,q,src in jobs])
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tokenizer)
    for number,(seed_base,row,encoded,request,source) in enumerate(jobs,1):
        run=args.output/f'seed-{seed_base}'
        run.mkdir(exist_ok=True)
        persist_request_bundle(run/'bundles'/f"{row['id']}.r1.json",encoded,[request])
        started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=number,total=40,id=row['id'],seed_base=seed_base)),flush=True)
        def progress(tokens):
            print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(request.input_ids))
        result=backend.generate(request,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        record=evaluate(row,encoded,request,result)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        final,status=extract_final_draft(result.text,encoded.text,tokenizer.eos_token)
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,max_new_tokens=budget)
        append(run/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,id=row['id'],seed_base=seed_base,correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason)),flush=True)
    print('R1_SUPPLEMENT_FINISHED',flush=True)


if __name__=='__main__': main()
