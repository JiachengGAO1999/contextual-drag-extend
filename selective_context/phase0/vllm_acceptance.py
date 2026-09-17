"""Bounded engineering gates; not a scientific accuracy experiment."""
import argparse,json,time
from pathlib import Path
from dataclasses import replace
from selective_context.schema import AccessMode,token_ids_sha256
from selective_context.prompting import load_request_bundle
from selective_context.phase0.real_smoke import save

MODEL='/data2/huangrj/models/qwen3-8b'

def fixtures(root):
    run=root/'outputs/game24-qwen3-x-vs-xcalc-path-fresh-seeds-20260916/seed-42027/bundles'
    requests=[]
    for pid in ['1189','577','1084']:
        enc,rs=load_request_bundle(run/f'{pid}.P_XCALC_fixed.json');p=rs[0]
        requests.extend([
            replace(p,condition_id=pid+'/full',access_mode=AccessMode.FULL,mask_token_spans=(),path_block_units=()),
            replace(p,condition_id=pid+'/late',access_mode=AccessMode.LATE_BLOCK,path_block_units=()),
            replace(p,condition_id=pid+'/path')])
    return requests

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['hf','vllm'],required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[2];requests=fixtures(root)
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=='hf':
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        from selective_context.hf_backend import SelectiveHFBackend
        tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
        backend=SelectiveHFBackend(model,tok)
        t=time.monotonic();results=[backend.generate(r,max_new_tokens=256,temperature=0) for r in requests]
        save(args.output/'hf.json',dict(seconds=time.monotonic()-t,results=[dict(id=r.condition_id,tokens=g.generated_token_ids) for r,g in zip(requests,results)]))
        print('HF_REFERENCE_SAVED',flush=True);return
    from selective_context.vllm_backend import SelectiveVLLMBackend
    backend=SelectiveVLLMBackend(MODEL,max_num_seqs=8,gpu_memory_utilization=.65)
    t=time.monotonic();results=backend.generate_batch(requests,max_new_tokens=256,temperature=0,logprobs=20)
    save(args.output/'vllm_logprobs.json',[dict(id=r.condition_id,tokens=g.generated_token_ids,logprobs=g.metadata['logprobs']) for r,g in zip(requests,results)])
    save(args.output/'vllm.json',dict(seconds=time.monotonic()-t,results=[dict(id=r.condition_id,tokens=g.generated_token_ids,text=g.text,metadata=g.metadata) for r,g in zip(requests,results)]))
    for i in range(0,9,3):assert results[i].generated_token_ids[0]==results[i+1].generated_token_ids[0], 'Late first-token boundary mismatch'
    hf=json.loads((args.output/'hf.json').read_text())
    matches=[]
    for ref,g in zip(hf['results'],results):
        a,b=ref['tokens'],g.generated_token_ids
        prefix=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
        matches.append(dict(id=ref['id'],matching_prefix=prefix,hf_length=len(a),vllm_length=len(b),exact=a==b))
    save(args.output/'hf_vllm_greedy_comparison.json',matches)
    # Exact isolation property of path, tested within the same backend.
    mutation=[]
    for req in requests[2::3]:
        ids=list(req.input_ids)
        for lo,hi in req.mask_token_spans:
            for i in range(lo,hi):ids[i]=(ids[i]+17)%len(backend.tokenizer)
        changed=replace(req,condition_id=req.condition_id+'/mutated',input_ids=ids,input_ids_sha256=token_ids_sha256(ids))
        pair=backend.generate_batch([req,changed],max_new_tokens=64,temperature=0)
        mutation.append(dict(id=req.condition_id,equal=pair[0].generated_token_ids==pair[1].generated_token_ids))
    save(args.output/'path_mutation.json',mutation)
    assert all(x['equal'] for x in mutation), 'Path isolation failure'
    workload=requests[:8];bench=[]
    for batch in [1,2,4,8]:
        t=time.monotonic();generated=0
        for i in range(0,8,batch):
            gs=backend.generate_batch(workload[i:i+batch],max_new_tokens=256,temperature=.6)
            generated+=sum(len(g.generated_token_ids) for g in gs)
        seconds=time.monotonic()-t;bench.append(dict(batch=batch,tokens=generated,seconds=seconds,tokens_per_second=generated/seconds))
        save(args.output/'benchmark.json',bench)
    save(args.output/'status.json',dict(engineering_smoke='passed',hf_exact=sum(x['exact'] for x in matches),hf_total=9,scientific_migration='pending numerical divergence review and completed-output smoke',benchmark=bench))
    print('VLLM_ENGINEERING_SMOKE_FINISHED; review gates before scientific migration',flush=True)

if __name__=='__main__':main()
