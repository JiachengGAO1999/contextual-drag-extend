"""Six fixed resource-error drafts: candidate-linked arithmetic late blocking."""
import argparse,json,time
from dataclasses import replace
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from selective_context.schema import AccessMode,SelectiveContextRequest
from selective_context.prompting import load_request_bundle,persist_request_bundle
from selective_context.multi_region import compile_regions
from selective_context.phase0.multi_late import source,sanity
from selective_context.phase0.real_smoke import save,append,evaluate
from selective_context.phase0.thinking_pilot import rows_from,generation_budget,extract_final_draft
from selective_context.hf_backend import SelectiveHFBackend

MODEL='/data2/huangrj/models/qwen3-8b'
SEEDS=[2027,12027,22027,32027]
ANN='docs/quick_validation/calculation_role_annotations_v1_20260916.json'
HISTORY=['game24-multi-late-20260912','game24-qwen3-mx-late-path-20260913','game24-region-late-20260912','game24-morphology-surgery-20260915','game24-qwen3-ten-validity-late-20260915']

def prepare(root,tokenizer):
    ann=json.loads((root/ANN).read_text(encoding='utf-8'));jobs=[];coverage={}
    for seed in SEEDS:
        old=[]
        for name in HISTORY:
            for file in ['results.jsonl','reused_results.jsonl']:
                p=root/'outputs'/name/f'seed-{seed}'/file
                old.extend((r,str(p.relative_to(root))) for r in rows_from(p))
        for pid,a in ann['questions'].items():
            src=source(root,pid,seed);enc,requests=load_request_bundle(src/'bundles'/f'{pid}.r2_r4.json')
            ref=next(r for r in requests if r.condition_id=='R2');ds,de=enc.draft_character_span
            assert enc.text[ds:de]==a['draft']
            cfg=json.loads((src/'config.json').read_text())
            assert [cfg[k] for k in ['temperature','top_p','top_k','context_size']]==[.6,.95,20,32768]
            def compile(items):return compile_regions(tokenizer,enc,[dict(u,character_span=[ds+u['draft_span'][0],ds+u['draft_span'][1]]) for u in items])
            target=compile(a['CALC']);retained=compile(a['candidate_occurrences']+a['E'])
            keys=lambda spans:{i for lo,hi in spans for i in range(lo,hi)}
            assert not keys(target['spans']) & keys(retained['spans']),'Semantic/token overlap with retained formula or E'
            req=replace(ref,condition_id='L_CALC_v1',access_mode=AccessMode.LATE_BLOCK,mask_token_spans=target['spans'],path_block_units=())
            req.validate()
            refs=[r for r in rows_from(src/'results.jsonl') if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id'] in ['R0','R2','R3','R4']]
            assert len(refs)==4
            r2=next(r for r in refs if r['init_response_generations_metadata']['intervention']['condition_id']=='R2')
            assert SelectiveContextRequest.from_dict(r2['init_response_generations_metadata']['intervention'])==ref
            matches=[]
            for r,path in old:
                if r['id']!=pid:continue
                old_req=SelectiveContextRequest.from_dict(r['init_response_generations_metadata']['intervention'])
                if replace(old_req,condition_id=req.condition_id)==req:matches.append((r,path))
            reuse=matches[0] if matches else None
            row=json.loads((src/'pairs'/f'{pid}.json').read_text());assert row['traj1']==a['draft']
            if pid in coverage:assert coverage[pid]['compilation']==target
            else:coverage[pid]=dict(compilation=target,prompt_tokens=len(req.input_ids),retained_formula_and_E_tokens=True,checked_history=HISTORY)
            jobs.append(dict(seed=seed,id=pid,row=row,enc=enc,req=req,refs=refs,reuse=reuse,source=str(src.relative_to(root)),first=r2['generated_token_ids'][0]))
    assert len(jobs)==24
    return ann,coverage,jobs

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[2];tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True,use_fast=True)
    ann,cov,jobs=prepare(root,tok);new=[j for j in jobs if j['reuse'] is None]
    save(args.output.parent/(args.output.name+'-preflight.json'),dict(coverage=cov,total=24,new=len(new),reused=24-len(new)))
    print(f'CALC_ROLE_PREFLIGHT_PASSED 24 requests;{len(new)} new;{24-len(new)} exact reuse;formula/E tokens retained',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True);save(args.output/'annotations.json',ann);save(args.output/'coverage.json',cov)
    save(args.output/'config.json',dict(ids=list(ann['questions']),seed_bases=SEEDS,new_generations=len(new),model=MODEL,
        condition='L_CALC_v1',temperature=.6,top_p=.95,top_k=20,context_size=32768,enable_thinking=True,
        backend='hf_eager_bfloat16',sampling_dtype='float32',access_mode='late_block',first_token='full_prefill_logits',
        scope='six development drafts, no morphology-category effect or semantic specificity claim',
        primary='L_CALC_v1 minus R2; accuracy; question-cluster CI exploratory'))
    manifest=[]
    for j in jobs:
        dest=args.output/f"seed-{j['seed']}";dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f"{j['id']}.L_CALC_v1.json",j['enc'],[j['req']])
        for r in j['refs']:append(dest/'references.jsonl',r)
        if j['reuse']:append(dest/'reused_results.jsonl',j['reuse'][0])
        manifest.append(dict(id=j['id'],seed_base=j['seed'],sample_seed=j['req'].sample_seed,source=j['source'],
            condition='L_CALC_v1',reused_source=j['reuse'][1] if j['reuse'] else None))
    save(args.output/'manifest.json',manifest)
    model=AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tok);checks={}
    for j in new:
        if j['id'] not in checks:checks[j['id']]=sanity(model,j['req'])
    save(args.output/'decode_sanity.json',checks)
    print(f'CALC_ROLE_ATTENTION_PASSED {len(checks)} unique masks;all layers',flush=True)
    for number,j in enumerate(new,1):
        started=time.monotonic();req=j['req'];enc=j['enc']
        print(json.dumps(dict(event='generation_start',number=number,total=len(new),id=j['id'],seed_base=j['seed'])),flush=True)
        def progress(tokens):print(json.dumps(dict(event='progress',number=number,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids));result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        assert result.generated_token_ids[0]==j['first']
        record=evaluate(j['row'],enc,req,result);final,status=extract_final_draft(result.text,enc.text,tok.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,max_new_tokens=budget,seed_base=j['seed'])
        append(args.output/f"seed-{j['seed']}"/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=number,total=len(new),id=j['id'],correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason)),flush=True)
    print('CALC_ROLE_FINISHED',flush=True)

if __name__=='__main__':main()
