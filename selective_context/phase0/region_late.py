"""Frozen exploratory single-region late blocking; no prompt edits."""
import argparse
import json
import time
import string
from dataclasses import replace
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.phase0.real_smoke import append, evaluate, save
from selective_context.phase0.thinking_pilot import rows_from, extract_final_draft, generation_budget
from selective_context.prompting import load_request_bundle, persist_request_bundle
from selective_context.masks import build_additive_attention
from selective_context.schema import AccessMode

IDS=['1226','719','577','1358']
SEEDS=[2027,12027,22027,32027]
CONDITIONS=['L_A','L_E','L_CA','L_CE']
# First uncorrected constructive violation; not a rejected exploratory candidate.
ERRORS={
 '1226':('- Then, **6 '+chr(247)+' 2 = 3**','Reuses 6 already consumed in preceding 8-6.'),
 '719':('7 - (5 - (8 \\div 8))','Uses two 8s in the subproblem with only one 8 remaining after reserving the outer multiplier.'),
 '577':('- **(9 - 6)**  \n  This simplifies to:  \n  $ 9 - 6 = 3 $','Reuses 6 already consumed by the first proposed factor.'),
 '1358':('One clever way to do this is to **add and subtract 7** in a way that does not affect the value:\n\n$$\n(13 - 5) \\times 3 + (7 - 7) = 24 + 0 = 24\n$$','First proposed invalid repair: uses the only 7 twice. Earlier three-number candidate is explicitly rejected, not labeled as accepted error.')}


def cover(offsets, start, end):
    selected=[i for i,(a,b) in enumerate(offsets) if b>a and a<end and b>start]
    if not selected: raise ValueError('Empty target span')
    return selected[0],selected[-1]+1


def regions(tokenizer, encoded, pid):
    tokenized=tokenizer(encoded.text,add_special_tokens=False,return_offsets_mapping=True)
    assert tokenized['input_ids']==encoded.input_ids
    offsets=tokenized['offset_mapping'];ds,de=encoded.draft_character_span
    draft=encoded.text[ds:de]
    error,reason=ERRORS[pid];assert error in draft
    es=ds+draft.index(error)
    # Only the last boxed answer; earlier copies intentionally remain accessible.
    astart=draft.rindex('\\boxed{');depth=1;j=astart+len('\\boxed{')
    while depth:
        depth += (draft[j]=='{')-(draft[j]=='}');j+=1
    targets={'L_A':(ds+astart,ds+j),'L_E':(es,es+len(error))}
    result={}
    for c,(start,end) in targets.items():
        lo,hi=cover(offsets,start,end);ms,me=offsets[lo][0],offsets[hi-1][1]
        before,after=encoded.text[ms:start],encoded.text[end:me]
        if any(ch not in string.whitespace+string.punctuation for ch in before+after):
            raise ValueError('Semantic boundary spillover')
        result[c]=dict(token_span=[lo,hi],character_span=[start,end],masked_character_span=[ms,me],before=before,after=after,text=encoded.text[ms:me],reason=reason if c=='L_E' else 'Last boxed answer only; not all equivalent answer mentions')
    # Equal-token suffix windows in the first, factually valid introductory paragraph.
    # This controls mask size, not position or semantic usefulness; document this limitation.
    intro_end=ds+draft.index('\n\n')
    valid=[i for i,(a,b) in enumerate(offsets) if b>a and a>=ds and b<=intro_end]
    for target,control in [('L_A','L_CA'),('L_E','L_CE')]:
        n=result[target]['token_span'][1]-result[target]['token_span'][0]
        if len(valid)<n: raise ValueError('Insufficient eligible control tokens')
        lo,hi=valid[-n],valid[-1]+1
        assert hi-lo==n
        ms,me=offsets[lo][0],offsets[hi-1][1]
        result[control]=dict(token_span=[lo,hi],character_span=[ms,me],masked_character_span=[ms,me],before='',after='',text=encoded.text[ms:me],reason='Equal-token suffix of factual draft introduction; original problem and task suffix untouched; not position/semantics matched')
    for v in result.values():
        lo,hi=v['token_span'];assert encoded.draft_token_span[0]<=lo<hi<=encoded.draft_token_span[1]
        v['token_count']=hi-lo;v['fraction_of_draft']=(hi-lo)/(encoded.draft_token_span[1]-encoded.draft_token_span[0])
    return result


@torch.inference_mode()
def check_attention(model, request):
    ids=torch.tensor([request.input_ids],device=model.device);n=ids.shape[1]
    full=model(input_ids=ids,use_cache=True)
    token=full.logits[:,-1].argmax(-1).view(1,1)
    mask=build_additive_attention(batch_size=1,query_positions=[n],key_length=n+1,draft_token_span=request.draft_token_span,access_mode=AccessMode.LATE_BLOCK,prompt_length=n,device=model.device,dtype=model.dtype)
    step=model(input_ids=token,past_key_values=full.past_key_values,attention_mask=mask,use_cache=True,output_attentions=True)
    a,b=request.draft_token_span
    maximum=max(float(x[...,a:b].abs().max()) for x in step.attentions)
    assert maximum==0
    return dict(blocked_attention_max=maximum,layers=len(step.attentions),scope='one decode query per region; full prefill unchanged')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[2];model_path='/data2/huangrj/models/qwen3-8b'
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,use_fast=True)
    jobs=[];annotations={}
    for seed in SEEDS:
        for pid in IDS:
            run=(root/'outputs/game24-independent-control-20260910' if seed==2027 else root/f'outputs/game24-independent-stage-a-20260910/seed-{seed}') if pid=='1358' else root/f'outputs/game24-stage-b-paired-20260911/seed-{seed}'
            config=json.loads((run/'config.json').read_text())
            assert (config['temperature'],config['top_p'],config['top_k'],config['context_size'])==(.6,.95,20,32768)
            encoded,requests=load_request_bundle(run/'bundles'/f'{pid}.r2_r4.json')
            ref=requests[0];assert ref.condition_id=='R2'
            row=json.loads((run/'pairs'/f'{pid}.json').read_text())
            prior=[r for r in rows_from(run/'results.jsonl') if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id']=='R2'][0]
            marked=regions(tokenizer,encoded,pid)
            if pid in annotations:assert annotations[pid]==marked
            annotations[pid]=marked
            for c in CONDITIONS:
                v=marked[c]
                req=replace(ref,condition_id=c,draft_token_span=tuple(v['token_span']),access_mode=AccessMode.LATE_BLOCK);req.validate()
                enc=replace(encoded,draft_token_span=tuple(v['token_span']),masked_character_span=tuple(v['masked_character_span']),boundary_spillover=dict(before=v['before'],after=v['after']))
                assert req.input_ids==ref.input_ids and req.sample_seed==ref.sample_seed
                jobs.append((seed,row,enc,req,v,prior['generated_token_ids'][0]))
    assert len(jobs)==64
    preflight=args.output.parent/(args.output.name+'-annotations.json')
    save(preflight,annotations)
    print('REGION_PREFLIGHT_PASSED 64 jobs; 16 annotated regions; exact tokens/seeds retained',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise RuntimeError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'annotations.json',annotations)
    save(args.output/'config.json',dict(model=model_path,ids=IDS,seed_bases=SEEDS,conditions=CONDITIONS,target=64,temperature=.6,top_p=.95,top_k=20,context_size=32768,backend='hf_eager_bfloat16',sampling_dtype='float32',access_mode='late_block',first_token='full prefill, unchanged',control_rule='equal-token suffix in factual introductory paragraph; not position/semantics matched',error_definition='first uncorrected constructive resource violation; rejected partial candidates excluded',request_field_note='draft_token_span denotes intervention region; full draft character span and full source bundle preserved separately'))
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0');backend=SelectiveHFBackend(model,tokenizer)
    checks={}
    for seed,row,enc,req,v,first in jobs[:16]:
        checks[row['id']+'/'+req.condition_id]=check_attention(model,req)
    save(args.output/'intervention_sanity.json',checks)
    print('REAL_ATTENTION_SANITY_PASSED 16 regions x 36 layers',flush=True)
    for number,(seed,row,enc,req,v,first) in enumerate(jobs,1):
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f"{row['id']}.{req.condition_id}.json",enc,[req])
        started=time.monotonic();print(json.dumps(dict(event='generation_start',number=number,total=64,id=row['id'],condition=req.condition_id,seed_base=seed)),flush=True)
        def progress(tokens):print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids));result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        assert result.generated_token_ids[0]==first,'Full-prefill first token changed'
        record=evaluate(row,enc,req,result);final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,max_new_tokens=budget,region_annotation=v,seed_base=seed)
        append(dest/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,id=row['id'],condition=req.condition_id,correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason)),flush=True)
    print('REGION_LATE_FINISHED',flush=True)


if __name__=='__main__':main()
