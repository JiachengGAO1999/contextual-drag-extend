"""Evidence-defined multi-span late experiment; frozen before generation."""
import argparse,json,time
from pathlib import Path
from dataclasses import replace
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from selective_context.hf_backend import SelectiveHFBackend
from selective_context.phase0.real_smoke import append,evaluate,save
from selective_context.phase0.thinking_pilot import rows_from,extract_final_draft,generation_budget
from selective_context.prompting import load_request_bundle,persist_request_bundle
from selective_context.multi_region import compile_regions
from selective_context.masks import build_additive_attention
from selective_context.schema import AccessMode

IDS=['1226','719','577','1358'];SEEDS=[2027,12027,22027,32027]
CONDITIONS=['M_X','M_V','M_XV','M_CX','M_CV','M_CXV']
SAFE_END={'1226':'### Key Insight:','719':'Let’s explore how to form','577':'Let’s consider:','1358':'### Incorporating the Number 7'}

def source(root,pid,seed):
    if pid in ['1189','1358','804']:
        return root/'outputs/game24-independent-control-20260910' if seed==2027 else root/f'outputs/game24-independent-stage-a-20260910/seed-{seed}'
    return root/f'outputs/game24-stage-b-paired-20260911/seed-{seed}'

def compile_targets(tokenizer,encoded,annotation):
    ds,de=encoded.draft_character_span
    assert encoded.text[ds:de]==annotation['draft']
    allitems=[dict(x,character_span=[ds+x['draft_span'][0],ds+x['draft_span'][1]]) for x in annotation['evidence']]
    out={}
    for c,kinds in [('M_X',['expression']),('M_V',['certification']),('M_XV',['expression','certification'])]:
        out[c]=compile_regions(tokenizer,encoded,[x for x in allitems if x['kind'] in kinds])
    return out

def with_controls(tokenizer,encoded,annotation,pid):
    out=compile_targets(tokenizer,encoded,annotation)
    ds,de=encoded.draft_character_span;draft=annotation['draft']
    stop=ds+draft.index(SAFE_END[pid])
    offsets=tokenizer(encoded.text,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
    eligible=[i for i,(a,b) in enumerate(offsets) if b>a and a>=ds and b<=stop]
    for target,control in [('M_X','M_CX'),('M_V','M_CV'),('M_XV','M_CXV')]:
        n=out[target]['token_count']
        if len(eligible)<n:raise ValueError(f'{pid}: insufficient audited control budget {n}/{len(eligible)}')
        lo,hi=eligible[0],eligible[n-1]+1
        assert hi-lo==n
        a,b=offsets[lo][0],offsets[hi-1][1]
        # Control tokens may cross word boundaries by design; source text remains intact.
        out[control]=dict(spans=((lo,hi),),token_count=n,regions=[dict(character_span=[a,b],text=encoded.text[a:b],token_span=[lo,hi],kind='matched_control',reason='Prefix of audited pre-error region; token-budget matched only, not position/number-of-spans matched')])
        assert not set(range(lo,hi)).intersection(i for v in out['M_XV']['spans'] for i in range(*v))
    return out

@torch.inference_mode()
def sanity(model,request):
    ids=torch.tensor([request.input_ids],device=model.device);n=ids.shape[1]
    full=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=True)
    token=full.logits[:,-1].argmax(-1).view(1,1)
    mask=build_additive_attention(batch_size=1,query_positions=[n],key_length=n+1,draft_token_span=request.draft_token_span,mask_token_spans=request.mask_token_spans,access_mode=AccessMode.LATE_BLOCK,prompt_length=n,device=model.device,dtype=model.dtype)
    step=model(input_ids=token,past_key_values=full.past_key_values,attention_mask=mask,use_cache=True,output_attentions=True)
    maximum=max(float(a[...,lo:hi].abs().max()) for a in step.attentions for lo,hi in request.mask_token_spans)
    blocked={i for lo,hi in request.mask_token_spans for i in range(lo,hi)}
    retained=[i for i in range(*request.draft_token_span) if i not in blocked]
    assert maximum==0 and retained
    retained_mass=min(float(a[...,retained].sum()) for a in step.attentions)
    assert retained_mass>0
    return dict(blocked_max=maximum,retained_mass_min=retained_mass,layers=len(step.attentions),scope='one decode query; every masked span plus retained draft gaps checked')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];model_path='/data2/huangrj/models/qwen3-8b'
    annotations=json.loads((root/'docs/quick_validation/multi_region_annotations_20260912.json').read_text(encoding='utf-8'))
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,use_fast=True)
    coverage={};jobs=[]
    for pid,a in annotations.items():
        enc,_=load_request_bundle(source(root,pid,2027)/'bundles'/f'{pid}.r2_r4.json')
        coverage[pid]=compile_targets(tokenizer,enc,a)
    for seed in SEEDS:
        for pid in IDS:
            run=source(root,pid,seed);enc,reqs=load_request_bundle(run/'bundles'/f'{pid}.r2_r4.json');ref=reqs[0]
            config=json.loads((run/'config.json').read_text());assert (config['temperature'],config['top_p'],config['top_k'],config['context_size'])==(.6,.95,20,32768)
            row=json.loads((run/'pairs'/f'{pid}.json').read_text())
            base=next(r for r in rows_from(run/'results.jsonl') if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id']=='R2')
            marked=with_controls(tokenizer,enc,annotations[pid],pid)
            if seed==2027:coverage[pid]=marked
            else:assert coverage[pid]==marked
            for c in CONDITIONS:
                req=replace(ref,condition_id=c,access_mode=AccessMode.LATE_BLOCK,mask_token_spans=marked[c]['spans']);req.validate()
                assert req.input_ids==ref.input_ids and req.sample_seed==ref.sample_seed
                jobs.append((seed,row,enc,req,marked[c],base['generated_token_ids'][0]))
    assert len(jobs)==96
    save(args.output.parent/(args.output.name+'-coverage.json'),coverage)
    print('MULTI_PREFLIGHT_PASSED ten annotations;96 jobs; text/tokens/seeds unchanged',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True);save(args.output/'coverage.json',coverage);save(args.output/'annotations.json',annotations)
    save(args.output/'config.json',dict(ids=IDS,seed_bases=SEEDS,conditions=CONDITIONS,total=96,model=model_path,temperature=.6,top_p=.95,top_k=20,context_size=32768,backend='hf_eager_bfloat16',sampling_dtype='float32',first_token='full-prefill unchanged',scope='selected full-expression copies and explicit certification; intermediate subexpressions and speculative descendants not masked',control='equal unique token count in pre-error region; not position or fragmentation matched',selection='four preselected diagnostic questions; no outcome-based mask revisions'))
    model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0');backend=SelectiveHFBackend(model,tokenizer)
    checks={}
    for seed,row,enc,req,v,first in jobs[:24]:checks[row['id']+'/'+req.condition_id]=sanity(model,req)
    save(args.output/'intervention_sanity.json',checks);print('MULTI_REAL_SANITY_PASSED 24 conditions x 36 layers',flush=True)
    for number,(seed,row,enc,req,v,first) in enumerate(jobs,1):
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f"{row['id']}.{req.condition_id}.json",enc,[req]);started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=number,total=96,id=row['id'],condition=req.condition_id,seed_base=seed)),flush=True)
        def progress(tokens):print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids));result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        assert result.generated_token_ids[0]==first
        record=evaluate(row,enc,req,result);final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,max_new_tokens=budget,region_annotation=v,seed_base=seed)
        append(dest/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,id=row['id'],condition=req.condition_id,correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason)),flush=True)
    print('MULTI_LATE_FINISHED',flush=True)

if __name__=='__main__':main()
