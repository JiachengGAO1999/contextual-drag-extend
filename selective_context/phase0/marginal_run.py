"""Sixteen add-one / leave-one-out generations on two frozen diagnostic units."""
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

IDS=['719','1358']
SEEDS=[2027,12027,22027,32027]


def prepare(root):
    from selective_context.phase0.fixed_coverage_run import prepare as prepare_c2
    from selective_context.multi_region import merge_spans
    from selective_context.masks import build_allowed_attention
    audit,annotation,original=prepare_c2(root)
    jobs=[]
    for seed,row,enc,c2,refs,src,old in original:
        pid=row['id']
        if pid not in IDS:continue
        uid={'1358':'B3','719':'B5'}[pid]
        unit=tuple(audit[pid]['compiled_units'][uid]['spans'][0])
        c1=SelectiveContextRequest.from_dict(audit[pid]['levels']['C1']['request'])
        c1=replace(c1,sample_seed=c2.sample_seed)
        assert unit in c2.path_block_units and unit not in c1.path_block_units
        add_units=tuple(sorted(set(c1.path_block_units+(unit,))))
        remove_units=tuple(u for u in c2.path_block_units if u!=unit)
        add=replace(c1,condition_id='C1_plus_U',path_block_units=add_units,mask_token_spans=merge_spans(add_units))
        remove=replace(c2,condition_id='C2_minus_U',path_block_units=remove_units,mask_token_spans=merge_spans(remove_units))
        def mask(req):
            n=len(req.input_ids)
            return build_allowed_attention(batch_size=1,query_positions=range(n+1),key_length=n+1,
                prompt_length=n,draft_token_span=req.draft_token_span,access_mode=req.access_mode,
                mask_token_spans=req.mask_token_spans,path_block_units=req.path_block_units)
        m1,m2,ma,mr=map(mask,(c1,c2,add,remove))
        assert not (ma & ~m1).any() and not (m2 & ~mr).any()
        assert torch.equal(m1 & ~ma,mr & ~m2) and (m1 & ~ma).any()
        previous=root/f'outputs/game24-qwen3-fixed-c2-path-20260913/seed-{seed}/results.jsonl'
        c2_record=next(r for r in rows_from(previous) if r['id']==pid)
        assert c2_record['init_response_generations_metadata']['intervention']==json.loads(json.dumps(c2.to_dict()))
        for req in (add,remove):
            req.validate()
            jobs.append((seed,row,enc,req,refs+[c2_record],src,old))
    assert len(jobs)==16
    return audit,annotation,jobs


@torch.inference_mode()
def cached_sanity(model,req,unit):
    ids=torch.tensor([req.input_ids],device=model.device);n=ids.shape[1]
    def mask(q,k):
        return build_additive_attention(batch_size=1,query_positions=q,key_length=k,
            draft_token_span=req.draft_token_span,mask_token_spans=req.mask_token_spans,
            path_block_units=req.path_block_units,access_mode=req.access_mode,
            prompt_length=n,device=model.device,dtype=model.dtype)
    pre=model(input_ids=ids,attention_mask=mask(range(n),n),use_cache=True,output_attentions=True)
    pre_max=max(float(a[:,:,hi:,lo:hi].abs().max()) for a in pre.attentions for lo,hi in req.path_block_units)
    assert pre_max==0
    out=model(input_ids=pre.logits[:,-1].argmax(-1).view(1,1),past_key_values=pre.past_key_values,
              attention_mask=mask([n],n+1),use_cache=True,output_attentions=True)
    maximum=max(float(a[:,:,:,lo:hi].abs().max()) for a in out.attentions for lo,hi in req.path_block_units)
    assert maximum==0
    lo,hi=unit
    unit_mass=min(float(a[:,:,:,lo:hi].sum()) for a in out.attentions)
    if req.condition_id=='C2_minus_U':assert unit_mass>0
    else:assert unit_mass==0
    return dict(layers=len(out.attentions),decode_blocked_max=maximum,prefill_blocked_max=pre_max,unit_attention_min_layer=unit_mass)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];audit,annotation,jobs=prepare(root)
    print('MARGINAL_PREFLIGHT_PASSED 16 requests; original four paired seeds; frozen units',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'annotations.json',annotation);save(args.output/'preflight.json',audit)
    model_path='/data2/huangrj/models/qwen3-8b'
    save(args.output/'config.json',dict(ids=IDS,seed_bases=SEEDS,new_generations=16,
        conditions=['C1_plus_U','C2_minus_U'],reference_conditions=['R0','R2','R3','R4','P_X','fixed_C2'],
        model=model_path,enable_thinking=True,temperature=.6,top_p=.95,top_k=20,context_size=32768,
        backend='hf_eager_bfloat16',sampling_dtype='float32',path_definition='fixed_units_v1',
        structural_control='deferred by explicit user decision',
        scope='two-case background-dependent marginal diagnostic; no claim of error specificity; no early stopping on outcome'))
    manifest=[]
    for seed,row,enc,req,refs,src,old in jobs:
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f"{row['id']}.{req.condition_id}.json",enc,[req])
        if req.condition_id=='C1_plus_U':
            for r in refs:append(dest/'references.jsonl',r)
        manifest.append(dict(id=row['id'],seed_base=seed,sample_seed=req.sample_seed,
            baseline_source=src,C1_source=old,C1_original_condition='P_X',condition=req.condition_id,unit={'1358':'B3','719':'B5'}[row['id']],C2_source=f'outputs/game24-qwen3-fixed-c2-path-20260913/seed-{seed}/results.jsonl'))
    save(args.output/'manifest.json',manifest)
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,use_fast=True)
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,
        torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tokenizer)
    checks={row['id']+'/'+req.condition_id:cached_sanity(model,req,audit[row['id']]['compiled_units'][{'1358':'B3','719':'B5'}[row['id']]]['spans'][0]) for _,row,_,req,_,_,_ in jobs[:4]}
    save(args.output/'decode_sanity.json',checks)
    print('MARGINAL_DECODE_SANITY_PASSED four conditions x36 layers',flush=True)
    for number,(seed,row,enc,req,_,_,_) in enumerate(jobs,1):
        started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=number,total=16,id=row['id'],seed_base=seed,condition=req.condition_id)),flush=True)
        def progress(tokens):
            print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids))
        result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        record=evaluate(row,enc,req,result)
        final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,
            max_new_tokens=budget,seed_base=seed,coverage_level=req.condition_id,path_definition='fixed_units_v1')
        append(args.output/f'seed-{seed}'/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,total=16,id=row['id'],
            correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason,
            seconds=round(record['generation_seconds'],1))),flush=True)
    assert sum(len(rows_from(args.output/f'seed-{s}'/'results.jsonl')) for s in SEEDS)==16
    print('MARGINAL_FINISHED',flush=True)


if __name__=='__main__':main()
