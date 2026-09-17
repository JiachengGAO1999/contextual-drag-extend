"""Frozen X versus X+CALC, four fresh paired seeds, six development questions."""
from selective_context.phase0.x_calc_union_run import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
    annotation, coverage, old_jobs = prepare(root, tokenizer)
    jobs = []
    for old in old_jobs:
        x = SelectiveContextRequest.from_dict(old['xrecord']['init_response_generations_metadata']['intervention'])
        for request in (x, old['req']):
            req = replace(request, sample_seed=request.sample_seed + 40000)
            req.validate()
            assert req.input_ids == old['req'].input_ids
            assert req.mask_token_spans == request.mask_token_spans
            jobs.append(dict(old, req=req, seed=old['seed']+40000))
    assert len(jobs) == 48
    assert len({(j['id'], j['seed'], j['req'].condition_id) for j in jobs}) == 48
    save(args.output.parent / (args.output.name+'-preflight.json'), dict(total=48, seed_bases=[42027,52027,62027,72027], coverage=coverage))
    print('REPLICATION_PREFLIGHT_PASSED 48 requests; only sample seeds changed', flush=True)
    if args.preflight_only:
        return
    if args.output.exists():
        raise ValueError('Refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'config.json', dict(model=MODEL, ids=list(annotation['questions']), seed_bases=[42027,52027,62027,72027], new_generations=48, conditions=['M_X','L_XCALC_v1'], temperature=.6, top_p=.95, top_k=20, context_size=32768, enable_thinking=True, backend='hf_eager_bfloat16', sampling_dtype='float32', access_mode='late_block', first_token='full_prefill_logits', primary='fresh-seed X+CALC minus X; development reproducibility only'))
    save(args.output/'coverage.json', coverage)
    save(args.output/'annotations.json', annotation)
    save(args.output/'manifest.json', [dict(id=j['id'],seed_base=j['seed'],sample_seed=j['req'].sample_seed,condition=j['req'].condition_id,source=j['source']) for j in jobs])
    for j in jobs:
        persist_request_bundle(args.output/f"seed-{j['seed']}"/'bundles'/f"{j['id']}.{j['req'].condition_id}.json",j['enc'],[j['req']])
    model = AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
    backend = SelectiveHFBackend(model,tokenizer)
    checks = {}
    for j in jobs:
        key=j['id']+'/'+j['req'].condition_id
        if key not in checks: checks[key]=sanity(model,j['req'])
    save(args.output/'decode_sanity.json',checks)
    print('REPLICATION_ATTENTION_PASSED 12 masks',flush=True)
    first = {}
    for n,j in enumerate(jobs,1):
        t=time.monotonic()
        print(json.dumps(dict(event='generation_start',number=n,total=48,id=j['id'],seed_base=j['seed'],condition=j['req'].condition_id)),flush=True)
        budget=generation_budget(len(j['req'].input_ids))
        def progress(tokens):
            print(json.dumps(dict(event='progress',number=n,tokens=tokens,seconds=round(time.monotonic()-t,1))),flush=True)
        result=backend.generate(j['req'],max_new_tokens=budget,temperature=.6,top_p=.95,top_k=20,progress_callback=progress)
        key=j['id'],j['seed']
        if key in first: assert first[key]==result.generated_token_ids[0]
        else: first[key]=result.generated_token_ids[0]
        record=evaluate(j['row'],j['enc'],j['req'],result)
        final,status=extract_final_draft(result.text,j['enc'].text,tokenizer.eos_token)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        record.update(final_response=final,thinking_status=status,generation_seconds=time.monotonic()-t,max_new_tokens=budget,seed_base=j['seed'])
        append(args.output/f"seed-{j['seed']}"/'results.jsonl',record)
        print(json.dumps(dict(event='generation_finish',number=n,total=48,id=j['id'],condition=j['req'].condition_id,correct=record['init_response_generations'][0]['correctness'],finish=result.finish_reason,seconds=round(time.monotonic()-t,1))),flush=True)
    print('REPLICATION_FINISHED 48/48',flush=True)


if __name__ == '__main__':
    main()
