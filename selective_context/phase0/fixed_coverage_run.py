"""Twenty frozen C2 path generations; references reused, structural controls deferred."""
import argparse,json,time
from dataclasses import replace
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from selective_context.schema import SelectiveContextRequest,AccessMode
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.masks import build_additive_attention
from selective_context.prompting import load_request_bundle,persist_request_bundle
from selective_context.phase0.multi_late import source
from selective_context.phase0.real_smoke import save,append,evaluate
from selective_context.phase0.thinking_pilot import rows_from,generation_budget,extract_final_draft

IDS=['1226','719','577','513','1358']
SEEDS=[2027,12027,22027,32027]


def prepare(root):
    audit=json.loads((root/'docs/quick_validation/fixed_coverage_preflight_20260913.json').read_text(encoding='utf-8'))
    annotation=json.loads((root/'docs/quick_validation/fixed_coverage_annotations_v1_20260913.json').read_text(encoding='utf-8'))
    jobs=[]
    for seed in SEEDS:
        for pid in IDS:
            item=audit[pid];check=item['real_C2_sanity']
            assert item['nested_edges'] and item['C1_reusable_edge_identity']
            assert check['layers']==36 and check['blocked_max']==check['final_logits_mutation_delta']==0
            frozen=SelectiveContextRequest.from_dict(item['levels']['C2']['request'])
            run=source(root,pid,seed);enc,requests=load_request_bundle(run/'bundles'/f'{pid}.r2_r4.json')
            ref=next(r for r in requests if r.condition_id=='R2')
            for k in ['input_ids','prompt_sha256','input_ids_sha256','draft_token_span']:
                assert getattr(frozen,k)==getattr(ref,k)
            config=json.loads((run/'config.json').read_text())
            assert tuple(config[k] for k in ['temperature','top_p','top_k','context_size'])==(.6,.95,20,32768)
            row=json.loads((run/'pairs'/f'{pid}.json').read_text())
            assert row['traj1']==annotation['questions'][pid]['draft']
            req=replace(frozen,sample_seed=ref.sample_seed);req.validate()
            assert req.access_mode is AccessMode.PATH_BLOCK and req.path_block_units
            old=root/f'outputs/game24-qwen3-mx-late-path-20260913/seed-{seed}/results.jsonl'
            c1=next(r for r in rows_from(old) if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id']=='P_X')
            c1req=SelectiveContextRequest.from_dict(c1['init_response_generations_metadata']['intervention'])
            frozen_c1=SelectiveContextRequest.from_dict(item['levels']['C1']['request'])
            assert c1req.mask_token_spans==frozen_c1.mask_token_spans==frozen_c1.path_block_units
            assert c1req.sample_seed==req.sample_seed and c1req.input_ids==req.input_ids
            references=[r for r in rows_from(run/'results.jsonl') if r['id']==pid and
                r['init_response_generations_metadata']['intervention']['condition_id'] in ['R0','R2','R3','R4']]
            assert len(references)==4
            jobs.append((seed,row,enc,req,references+[c1],str(run.relative_to(root)),str(old.relative_to(root))))
    assert len(jobs)==20
    return audit,annotation,jobs


@torch.inference_mode()
def cached_sanity(model,req):
    ids=torch.tensor([req.input_ids],device=model.device);n=ids.shape[1]
    def mask(q,k):
        return build_additive_attention(batch_size=1,query_positions=q,key_length=k,
            draft_token_span=req.draft_token_span,mask_token_spans=req.mask_token_spans,
            path_block_units=req.path_block_units,access_mode=req.access_mode,
            prompt_length=n,device=model.device,dtype=model.dtype)
    pre=model(input_ids=ids,attention_mask=mask(range(n),n),use_cache=True)
    out=model(input_ids=pre.logits[:,-1].argmax(-1).view(1,1),past_key_values=pre.past_key_values,
              attention_mask=mask([n],n+1),use_cache=True,output_attentions=True)
    maximum=max(float(a[:,:,:,lo:hi].abs().max()) for a in out.attentions for lo,hi in req.path_block_units)
    assert maximum==0
    return dict(layers=len(out.attentions),decode_blocked_max=maximum)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];audit,annotation,jobs=prepare(root)
    print('FIXED_C2_PREFLIGHT_PASSED 20 requests; original four paired seeds; frozen C2',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'annotations.json',annotation);save(args.output/'preflight.json',audit)
    model_path='/data2/huangrj/models/qwen3-8b'
    save(args.output/'config.json',dict(ids=IDS,seed_bases=SEEDS,new_generations=20,
        conditions=['fixed_C2'],reference_conditions=['R0','R2','R3','R4','P_X'],
        model=model_path,enable_thinking=True,temperature=.6,top_p=.95,top_k=20,context_size=32768,
        backend='hf_eager_bfloat16',sampling_dtype='float32',path_definition='fixed_units_v1',
        structural_control='deferred by explicit user decision',
        scope='coverage diagnostic only; no claim of error specificity; no early stopping on outcome'))
    manifest=[]
    for seed,row,enc,req,refs,src,old in jobs:
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f"{row['id']}.fixed_C2.json",enc,[req])
        for r in refs:append(dest/'references.jsonl',r)
        manifest.append(dict(id=row['id'],seed_base=seed,sample_seed=req.sample_seed,
            baseline_source=src,C1_source=old,C1_original_condition='P_X'))
    save(args.output/'manifest.json',manifest)
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,use_fast=True)
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,
        torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tokenizer)
    checks={row['id']:cached_sanity(model,req) for _,row,_,req,_,_,_ in jobs[:5]}
    save(args.output/'decode_sanity.json',checks)
    print('FIXED_C2_DECODE_SANITY_PASSED five cases x36 layers',flush=True)
    for number,(seed,row,enc,req,_,_,_) in enumerate(jobs,1):
        started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=number,total=20,id=row['id'],seed_base=seed,condition=req.condition_id)),flush=True)
        def progress(tokens):
            print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids))
        result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        record=evaluate(row,enc,req,result)
        final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,
            max_new_tokens=budget,seed_base=seed,coverage_level='C2',path_definition='fixed_units_v1')
        append(args.output/f'seed-{seed}'/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,total=20,id=row['id'],
            correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason,
            seconds=round(record['generation_seconds'],1))),flush=True)
    assert sum(len(rows_from(args.output/f'seed-{s}'/'results.jsonl')) for s in SEEDS)==20
    print('FIXED_C2_FINISHED',flush=True)


if __name__=='__main__':main()
