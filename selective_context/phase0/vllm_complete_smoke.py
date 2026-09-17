"""Actual end-to-end Thinking completions using frozen full/late/path inputs."""
import argparse,json,time
from pathlib import Path
from selective_context.phase0.vllm_acceptance import fixtures,MODEL
from selective_context.phase0.multi_late import source
from selective_context.phase0.real_smoke import save,append,evaluate
from selective_context.phase0.thinking_pilot import extract_final_draft
from selective_context.prompting import load_request_bundle
from selective_context.vllm_backend import SelectiveVLLMBackend

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--gate-directory',type=Path,default=Path('outputs/vllm-acceptance-20260917'));args=ap.parse_args()
    root=Path(__file__).resolve().parents[2]
    gate=args.gate_directory/'status.json'
    if not gate.exists() or json.loads(gate.read_text())['engineering_smoke']!='passed':raise RuntimeError('Engineering gates not passed')
    if args.output.exists():raise ValueError('Refusing overwrite')
    args.output.mkdir(parents=True)
    requests=fixtures(root)
    save(args.output/'requests.json',[r.to_dict() for r in requests])
    save(args.output/'config.json',dict(scope='engineering completed-output smoke; not scientific replication',model=MODEL,backend='vllm_selective_flex_0.11.0',temperature=.6,top_p=.95,top_k=20,context_size=32768,conditions=['full','late','path'],questions=['1189','577','1084'],generations=9))
    backend=SelectiveVLLMBackend(MODEL,max_num_seqs=8)
    t=time.monotonic();results=backend.generate_batch(requests,max_new_tokens=32768,temperature=.6,top_p=.95,top_k=20)
    for req,g in zip(requests,results):
        pid=req.condition_id.split('/')[0]
        src=source(root,pid,2027)
        row=json.loads((src/'pairs'/f'{pid}.json').read_text())
        enc,_=load_request_bundle(src/'bundles'/f'{pid}.r2_r4.json')
        record=evaluate(row,enc,req,g)
        record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
        final,status=extract_final_draft(g.text,enc.text,backend.tokenizer.eos_token)
        record.update(final_response=final,thinking_status=status)
        append(args.output/'results.jsonl',record)
    save(args.output/'summary.json',dict(n=9,eos=sum(g.finish_reason=='eos' for g in results),tokens=sum(len(g.generated_token_ids) for g in results),seconds=time.monotonic()-t))
    benchmark=[]
    for batch in [1,2,4,8]:
        backend.generate_batch(requests[:batch],max_new_tokens=16,temperature=.6)
        started=time.monotonic();count=0
        for i in range(0,8,batch):
            gs=backend.generate_batch(requests[i:i+batch],max_new_tokens=256,temperature=.6)
            count+=sum(len(g.generated_token_ids) for g in gs)
        elapsed=time.monotonic()-started
        benchmark.append(dict(batch=batch,tokens=count,seconds=elapsed,tokens_per_second=count/elapsed,warmup_tokens=16))
        save(args.output/'warm_benchmark.json',benchmark)
    print('VLLM_COMPLETED_OUTPUT_SMOKE_FINISHED',flush=True)

if __name__=='__main__':main()
