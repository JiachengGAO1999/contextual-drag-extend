# -*- coding: utf-8 -*-
"""Frozen ten-question M_X/control x late/path, reusing 32 prior late records."""
import argparse
import json
import time
from dataclasses import replace
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.masks import build_additive_attention
from selective_context.schema import AccessMode
from selective_context.prompting import load_request_bundle, persist_request_bundle
from selective_context.phase0.multi_late import source, compile_targets, sanity as late_sanity
from selective_context.phase0.real_smoke import save, append, evaluate
from selective_context.phase0.thinking_pilot import rows_from, generation_budget, extract_final_draft

IDS = ['1226','719','577','1358','1189','804','123','71','513','1084']
OLD_IDS = IDS[:4]
SEEDS = [2027,12027,22027,32027]
CONDITIONS = {'M_X': ('M_X',AccessMode.LATE_BLOCK),
              'M_CX': ('M_CX',AccessMode.LATE_BLOCK),
              'P_X': ('M_X',AccessMode.PATH_BLOCK),
              'P_CX': ('M_CX',AccessMode.PATH_BLOCK)}
SAFE_END = {'1189':'#### Step 1:', '804':'We know that:',
            '123':'Let’s consider a promising path:', '71':'Close to 24, but not quite.',
            '513':'Let’s test the expression:', '1084':'We can use the following logic:'}


def marked_regions(tokenizer, encoded, annotation, pid, frozen):
    # Recompile as an integrity check, never regenerate annotations from outcomes.
    targets = compile_targets(tokenizer, encoded, annotation)
    assert json.loads(json.dumps(targets['M_X'])) == frozen[pid]['M_X']
    if pid in OLD_IDS:
        return {c:frozen[pid][c] for c in ('M_X','M_CX')}
    ds,_ = encoded.draft_character_span
    stop = ds + annotation['draft'].index(SAFE_END[pid])
    offsets = tokenizer(encoded.text,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
    eligible = [i for i,(a,b) in enumerate(offsets) if b>a and a>=ds and b<=stop]
    n = targets['M_X']['token_count']
    if len(eligible)<n:
        raise ValueError(f'{pid}: insufficient audited pre-error control budget')
    lo,hi = eligible[0],eligible[n-1]+1
    assert hi-lo == n
    assert not set(range(lo,hi)).intersection(k for a,b in targets['M_XV']['spans'] for k in range(a,b))
    a,b = offsets[lo][0],offsets[hi-1][1]
    control = dict(spans=[[lo,hi]],token_count=n,regions=[dict(character_span=[a,b],
        text=encoded.text[a:b],token_span=[lo,hi],kind='matched_control',
        reason='Prefix of audited pre-error region; token-budget matched only, not position/number-of-spans matched')])
    return dict(M_X=targets['M_X'],M_CX=control)


@torch.inference_mode()
def path_sanity(model, req):
    ids = torch.tensor([req.input_ids],device=model.device)
    n = ids.shape[1]
    def mask(q,k):
        return build_additive_attention(batch_size=1,query_positions=q,key_length=k,
            draft_token_span=req.draft_token_span,mask_token_spans=req.mask_token_spans,
            access_mode=AccessMode.PATH_BLOCK,prompt_length=n,device=model.device,dtype=model.dtype)
    out = model(input_ids=ids,attention_mask=mask(range(n),n),use_cache=True,output_attentions=True)
    blocked = max(float(layer[:,:,hi:,lo:hi].abs().max())
                  for layer in out.attentions for lo,hi in req.mask_token_spans)
    selected = {k for lo,hi in req.mask_token_spans for k in range(lo,hi)}
    keep = [k for k in range(*req.draft_token_span) if k not in selected]
    retained = min(float(layer[:,:,-1,keep].sum()) for layer in out.attentions)
    ref = out.logits[:,-1].clone()
    cache = out.past_key_values
    del out
    step = model(input_ids=ids[:,-1:],past_key_values=cache,attention_mask=mask([n],n+1),
                 use_cache=True,output_attentions=True)
    decode_blocked = max(float(layer[:,:,:,lo:hi].abs().max())
                        for layer in step.attentions for lo,hi in req.mask_token_spans)
    del step,cache
    changed = ids.clone()
    for lo,hi in req.mask_token_spans:
        changed[:,lo:hi] = (changed[:,lo:hi]+17) % model.config.vocab_size
    altered = model(input_ids=changed,attention_mask=mask(range(n),n),use_cache=False).logits[:,-1]
    delta = float((ref-altered).abs().max())
    assert blocked == decode_blocked == delta == 0 and retained>0
    return dict(blocked_max=blocked,decode_blocked_max=decode_blocked,
                final_prefill_logits_mutation_delta=delta,retained_mass_min=retained,
                layers=model.config.num_hidden_layers)


def prepare(root, tokenizer):
    annotations = json.loads((root/'docs/quick_validation/multi_region_annotations_20260912.json').read_text(encoding='utf-8'))
    frozen = json.loads((root/'outputs/game24-multi-late-20260912-coverage.json').read_text())
    coverage, jobs = {}, []
    for seed in SEEDS:
        for pid in IDS:
            run = source(root,pid,seed)
            encoded, requests = load_request_bundle(run/'bundles'/f'{pid}.r2_r4.json')
            ref = next(r for r in requests if r.condition_id=='R2')
            config = json.loads((run/'config.json').read_text())
            assert tuple(config[k] for k in ('temperature','top_p','top_k','context_size')) == (.6,.95,20,32768)
            row = json.loads((run/'pairs'/f'{pid}.json').read_text())
            assert row['traj1'] == annotations[pid]['draft'] and row['draft_key'] == annotations[pid]['draft_key']
            marked = json.loads(json.dumps(marked_regions(tokenizer,encoded,annotations[pid],pid,frozen)))
            if pid in coverage:
                assert coverage[pid] == marked
            else:
                coverage[pid] = marked
            base = next(r for r in rows_from(run/'results.jsonl') if r['id']==pid and
                        r['init_response_generations_metadata']['intervention']['condition_id']=='R2')
            for condition,(region,mode) in CONDITIONS.items():
                req = replace(ref,condition_id=condition,access_mode=mode,
                              mask_token_spans=tuple(tuple(s) for s in marked[region]['spans']))
                req.validate()
                reused, origin = None, None
                if pid in OLD_IDS and mode is AccessMode.LATE_BLOCK:
                    origin = root/f'outputs/game24-multi-late-20260912/seed-{seed}/results.jsonl'
                    candidates = [r for r in rows_from(origin) if r['id']==pid and
                        r['init_response_generations_metadata']['intervention']['condition_id']==condition]
                    assert len(candidates)==1
                    reused = candidates[0]
                    assert reused['init_response_prompt'] == encoded.text
                    assert reused['init_response_generations_metadata']['intervention'] == json.loads(json.dumps(req.to_dict()))
                    assert reused['region_annotation'] == marked[region]
                jobs.append(dict(seed=seed,row=row,encoded=encoded,request=req,
                    region=marked[region],first=base['generated_token_ids'][0],
                    reused=reused,origin=str(origin.relative_to(root)) if origin else None))
    assert len(jobs)==160 and sum(j['reused'] is not None for j in jobs)==32
    return annotations,coverage,jobs


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    model_path='/data2/huangrj/models/qwen3-8b'
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,use_fast=True)
    annotations,coverage,jobs=prepare(root,tokenizer)
    sidecar=args.output.parent/(args.output.name+'-coverage.json')
    if sidecar.exists():
        assert json.loads(sidecar.read_text())==coverage, 'Frozen coverage changed'
    else:
        save(sidecar,coverage)
    print('TEN_MX_PREFLIGHT_PASSED total=160 reused=32 new=128',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'annotations.json',annotations)
    save(args.output/'coverage.json',coverage)
    save(args.output/'config.json',dict(ids=IDS,seed_bases=SEEDS,conditions=list(CONDITIONS),
        total=160,reused=32,new=128,model=model_path,enable_thinking=True,
        temperature=.6,top_p=.95,top_k=20,context_size=32768,
        backend='hf_eager_bfloat16',sampling_dtype='float32',
        path_boundary='each compiled [lo,hi): block keys for all q>=hi at every layer',
        late_boundary='q>=prompt_length; full-prefill first-token unchanged',
        scope='selected full erroneous expression copies; not all errors or descendants',
        control='audited pre-error prefix, unique-token-count matched only',
        reused_source='outputs/game24-multi-late-20260912'))
    manifest=[]
    for j in jobs:
        req=j['request'];pid=j['row']['id'];seed=j['seed']
        manifest.append(dict(id=pid,condition=req.condition_id,seed_base=seed,
                             sample_seed=req.sample_seed,reused_from=j['origin']))
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f'{pid}.{req.condition_id}.json',j['encoded'],[req])
        if j['reused'] is not None:append(dest/'results.jsonl',j['reused'])
    save(args.output/'manifest.json',manifest)
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,
        torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tokenizer)
    checks={}
    for j in jobs[:40]:
        req=j['request'];key=j['row']['id']+'/'+req.condition_id
        checks[key]=(path_sanity(model,req) if req.access_mode is AccessMode.PATH_BLOCK else late_sanity(model,req))
        print(json.dumps(dict(event='sanity_pass',key=key)),flush=True)
    save(args.output/'intervention_sanity.json',checks)
    print('TEN_MX_REAL_SANITY_PASSED 40 conditions x 36 layers',flush=True)
    new_jobs=[j for j in jobs if j['reused'] is None]
    for number,j in enumerate(new_jobs,1):
        req=j['request'];row=j['row'];enc=j['encoded'];started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=number,total_new=128,
            id=row['id'],condition=req.condition_id,seed_base=j['seed'])),flush=True)
        def progress(tokens):
            print(json.dumps(dict(event='progress',number=number,tokens=tokens,
                                  seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids))
        result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,
                                top_k=20,progress_callback=progress)
        if req.access_mode is AccessMode.LATE_BLOCK:assert result.generated_token_ids[0]==j['first']
        record=evaluate(row,enc,req,result)
        final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,
                      max_new_tokens=budget,region_annotation=j['region'],seed_base=j['seed'])
        append(args.output/f"seed-{j['seed']}"/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,total_new=128,
            id=row['id'],condition=req.condition_id,correct=record['init_response_generations'][0]['correctness'],
            finish=result.finish_reason,seconds=round(record['generation_seconds'],1))),flush=True)
    assert sum(len(rows_from(args.output/f'seed-{s}'/'results.jsonl')) for s in SEEDS)==160
    print('TEN_MX_LATE_PATH_FINISHED',flush=True)


if __name__=='__main__':main()
