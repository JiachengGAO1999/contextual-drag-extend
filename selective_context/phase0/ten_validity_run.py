"""Ten fixed drafts: audited endorsement-language late blocking, with exact reuse."""
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
REUSE={'577','719','1226'}

def prepare(root,tokenizer):
    annotation=json.loads((root/'docs/quick_validation/ten_validity_annotations_v1_20260915.json').read_text(encoding='utf-8'))
    jobs=[];audit={}
    for seed in SEEDS:
        for pid,a in annotation['questions'].items():
            src=source(root,pid,seed)
            enc,requests=load_request_bundle(src/'bundles'/f'{pid}.r2_r4.json')
            ref=next(r for r in requests if r.condition_id=='R2')
            ds,de=enc.draft_character_span
            assert enc.text[ds:de]==a['draft']
            cfg=json.loads((src/'config.json').read_text())
            assert [cfg[k] for k in ['temperature','top_p','top_k','context_size']]==[.6,.95,20,32768]
            evidence=[dict(u,character_span=[ds+u['draft_span'][0],ds+u['draft_span'][1]]) for u in a['E']]
            marked=compile_regions(tokenizer,enc,evidence)
            formula=compile_regions(tokenizer,enc,[dict(u,character_span=[ds+u['draft_span'][0],ds+u['draft_span'][1]]) for u in a['candidate_occurrences']])
            keys={i for lo,hi in marked['spans'] for i in range(lo,hi)}
            formula_keys={i for lo,hi in formula['spans'] for i in range(lo,hi)}
            assert not keys & formula_keys,'Token spill crosses candidate formula'
            req=replace(ref,condition_id='L_E_v1',access_mode=AccessMode.LATE_BLOCK,mask_token_spans=marked['spans'],path_block_units=())
            req.validate()
            assert req.input_ids==ref.input_ids and req.sample_seed==ref.sample_seed
            refs=[r for r in rows_from(src/'results.jsonl') if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id'] in ['R0','R2','R3','R4']]
            assert len(refs)==4
            r2=next(r for r in refs if r['init_response_generations_metadata']['intervention']['condition_id']=='R2')
            # Legacy FULL requests omit the optional empty mask field. Compare schema semantics.
            assert SelectiveContextRequest.from_dict(r2['init_response_generations_metadata']['intervention'])==ref
            reused=None
            old_path=root/f'outputs/game24-multi-late-20260912/seed-{seed}/results.jsonl'
            if pid in REUSE:
                assert a['old_M_V_character_identity']
                reused=next(r for r in rows_from(old_path) if r['id']==pid and r['init_response_generations_metadata']['intervention']['condition_id']=='M_V')
                assert SelectiveContextRequest.from_dict(reused['init_response_generations_metadata']['intervention'])==replace(req,condition_id='M_V')
                assert reused['generated_token_ids'][0]==r2['generated_token_ids'][0]
            if seed==SEEDS[0]:audit[pid]=dict(compilation=marked,prompt_tokens=len(req.input_ids),formula_tokens_retained=True,reused=pid in REUSE)
            else:assert audit[pid]['compilation']==marked
            row=json.loads((src/'pairs'/f'{pid}.json').read_text());assert row['traj1']==a['draft']
            jobs.append((seed,pid,row,enc,req,refs,reused,str(src.relative_to(root)),str(old_path.relative_to(root)),r2['generated_token_ids'][0]))
    assert len(jobs)==40 and sum(j[6] is not None for j in jobs)==12
    return annotation,audit,jobs

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True,use_fast=True)
    annotation,audit,jobs=prepare(root,tokenizer)
    save(args.output.parent/(args.output.name+'-preflight.json'),audit)
    print('TEN_VALIDITY_PREFLIGHT_PASSED 40 requests;12 exact reuses;28 new;formula tokens retained',flush=True)
    if args.preflight_only:return
    if args.output.exists():raise ValueError('Output exists; refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'annotations.json',annotation);save(args.output/'preflight.json',audit)
    save(args.output/'config.json',dict(model=MODEL,ids=list(annotation['questions']),seed_bases=SEEDS,
        new_generations=28,reused_generations=12,condition='L_E_v1',access_mode='late_block',
        enable_thinking=True,temperature=.6,top_p=.95,top_k=20,context_size=32768,
        backend='hf_eager_bfloat16',sampling_dtype='float32',first_token='full_prefill_logits',
        primary_comparison='L_E_v1 minus R2; accuracy and paired transitions',
        scope='ten development questions; no geometry control; not a semantic-specificity claim'))
    manifest=[]
    for seed,pid,row,enc,req,refs,reused,src,old,first in jobs:
        dest=args.output/f'seed-{seed}';dest.mkdir(exist_ok=True)
        persist_request_bundle(dest/'bundles'/f'{pid}.L_E_v1.json',enc,[req])
        for r in refs:append(dest/'references.jsonl',r)
        if reused is not None:append(dest/'reused_results.jsonl',reused)
        manifest.append(dict(id=pid,seed_base=seed,sample_seed=req.sample_seed,analysis_condition='L_E_v1',
            record_condition='M_V' if reused else 'L_E_v1',record_file=f'seed-{seed}/'+('reused_results.jsonl' if reused else 'results.jsonl'),
            baseline_source=src,reused_source=old if reused else None))
    save(args.output/'manifest.json',manifest)
    model=AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend=SelectiveHFBackend(model,tokenizer);checks={}
    for seed,pid,row,enc,req,refs,reused,src,old,first in jobs:
        if reused is None and pid not in checks:checks[pid]=sanity(model,req)
    assert len(checks)==7
    save(args.output/'decode_sanity.json',checks)
    print('TEN_VALIDITY_ATTENTION_PASSED seven new question masks x all layers',flush=True)
    n=0
    for seed,pid,row,enc,req,refs,reused,src,old,first in jobs:
        if reused is not None:continue
        n+=1;started=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=n,total=28,id=pid,seed_base=seed)),flush=True)
        def progress(tokens):print(json.dumps(dict(event='progress',number=n,tokens=tokens,seconds=round(time.monotonic()-started,1))),flush=True)
        budget=generation_budget(len(req.input_ids))
        result=backend.generate(req,max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        assert result.generated_token_ids[0]==first,'Late first token differs from paired R2'
        record=evaluate(row,enc,req,result)
        final,status=extract_final_draft(result.text,enc.text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-started,max_new_tokens=budget,seed_base=seed)
        append(args.output/f'seed-{seed}'/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=n,total=28,id=pid,correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason,seconds=round(record['generation_seconds'],1))),flush=True)
    assert n==28
    print('TEN_VALIDITY_FINISHED',flush=True)

if __name__=='__main__':main()
