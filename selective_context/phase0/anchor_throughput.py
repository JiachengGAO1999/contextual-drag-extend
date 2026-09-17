"""Bounded ordinary-vLLM baseline benchmark: two development questions x16.

No selective worker, no mask, no held-out acquisition. Full context budgets.
"""
import argparse
import json
import os
import time
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model',required=True)
    ap.add_argument('--alias',choices=['Qwen3_8B','Qwen3_32B','Nemotron_32B'],required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--max-num-seqs',type=int,default=16)
    ap.add_argument('--max-num-batched-tokens',type=int,default=8192)
    ap.add_argument('--gpu-memory-utilization',type=float,default=.85)
    args=ap.parse_args()
    if args.output.exists():raise ValueError('Refusing overwrite/retry without review')
    # The custom backend is deliberately not imported in this process.
    os.environ['VLLM_ATTENTION_BACKEND']='FLASH_ATTN'
    os.environ['VLLM_USE_V1']='1'
    from vllm import LLM,SamplingParams
    import importlib.metadata
    from selective_context.phase0.multi_late import source
    from selective_context.prompting import render_official_prompt,render_chat_prompt
    root=Path(__file__).resolve().parents[2]
    cfg=json.loads((root/'utils/general_inference/eval_models_params.json').read_text())[args.alias]
    context=cfg['context_length'];sample=cfg['sampling_params']
    rows=[json.loads((source(root,pid,2027)/'pairs'/f'{pid}.json').read_text()) for pid in ['577','1189']]
    args.output.mkdir(parents=True)
    save=lambda name,value:(args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    save('config.json',dict(scope='throughput only; development questions excluded from held-out',
        model=args.model,alias=args.alias,model_config=cfg,question_ids=['577','1189'],
        n=16,total_generations=32,seed=42,max_num_seqs=args.max_num_seqs,max_num_batched_tokens=args.max_num_batched_tokens,
        context=context,gpu_memory_utilization=args.gpu_memory_utilization,enforce_eager=True,
        attention_backend='FLASH_ATTN',worker='vllm default; no custom mask',
        prefix_caching=False,generation_config='vllm',stop_policy='vllm model/tokenizer defaults; no EOS override',
        version=importlib.metadata.version('vllm'),no_automatic_expansion=True))
    started=time.monotonic()
    llm=LLM(model=args.model,tokenizer=args.model,dtype='bfloat16',
        max_model_len=context,max_num_seqs=args.max_num_seqs,max_num_batched_tokens=args.max_num_batched_tokens,
        gpu_memory_utilization=args.gpu_memory_utilization,enable_prefix_caching=False,enable_chunked_prefill=True,
        enforce_eager=True,generation_config='vllm',disable_log_stats=False,seed=42)
    loaded=time.monotonic();tok=llm.get_tokenizer()
    prompts=[render_chat_prompt(tok,render_official_prompt(root,'R0',r['problem']),enable_thinking=True) for r in rows]
    ids=[tok.encode(p,add_special_tokens=False) for p in prompts]
    params=[SamplingParams(n=16,temperature=sample['temperature'],top_p=sample['top_p'],
        top_k=sample.get('top_k',-1),seed=42,max_tokens=context-len(p),skip_special_tokens=False) for p in ids]
    save('requests.json',[dict(id=r['id'],problem=r['problem'],answer=r['answer'],prompt=p,
        prompt_token_ids=t,max_tokens=context-len(t)) for r,p,t in zip(rows,prompts,ids)])
    print('ANCHOR_BENCHMARK_GENERATION_START total=32',flush=True)
    generated=time.monotonic()
    outputs=llm.generate([dict(prompt_token_ids=p) for p in ids],params,use_tqdm=False)
    elapsed=time.monotonic()-generated
    records=[]
    for row,out in zip(rows,outputs):
        assert len(out.outputs)==16
        for g in out.outputs:
            records.append(dict(id=row['id'],sample_index=g.index,answer=row['answer'],
                text=g.text,token_ids=list(g.token_ids),finish_reason=g.finish_reason,
                stop_reason=g.stop_reason,tokens=len(g.token_ids)))
    with (args.output/'results.jsonl').open('w',encoding='utf-8') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    total=sum(r['tokens'] for r in records)
    summary=dict(generations=len(records),stopped=sum(r['finish_reason']=='stop' for r in records),
        length_limited=sum(r['finish_reason']=='length' for r in records),tokens=total,
        mean_tokens=total/len(records),generation_seconds=elapsed,load_seconds=loaded-started,
        total_seconds=time.monotonic()-started,tokens_per_second=total/elapsed,
        projected_64_questions_same_anchor_gpu_hours=elapsed*(64*16/32)/3600,
        projection_limit='two development questions; lengths and completion may not represent fresh questions or other anchors')
    save('summary.json',summary)
    print('ANCHOR_BENCHMARK_COMPLETE '+json.dumps(summary),flush=True)


if __name__=='__main__':main()
