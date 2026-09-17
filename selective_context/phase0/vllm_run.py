"""Run frozen request bundles through the validated selective vLLM backend.

Manifest entries: bundle (path), pair (original problem/draft JSON), condition.
All paths are relative to the repository root; no new prompt construction here.
"""
import argparse,json,time
from pathlib import Path
from selective_context.prompting import load_request_bundle
from selective_context.phase0.real_smoke import append,evaluate,save
from selective_context.phase0.thinking_pilot import extract_final_draft
from selective_context.vllm_backend import SelectiveVLLMBackend

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--batch-size',type=int,default=8)
    args=ap.parse_args();root=Path(__file__).resolve().parents[2]
    if not 1<=args.batch_size<=8:raise ValueError('Validated batch range: 1..8')
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'));jobs=[]
    for entry in manifest:
        enc,reqs=load_request_bundle(root/entry['bundle'])
        req=next(r for r in reqs if r.condition_id==entry['condition']);req.validate()
        row=json.loads((root/entry['pair']).read_text(encoding='utf-8'))
        ds,de=enc.draft_character_span
        if req.access_mode.value!='full':assert enc.text[ds:de]==row['traj1']
        jobs.append((enc,req,row))
    if args.output.exists():raise ValueError('Refusing overwrite')
    args.output.mkdir(parents=True)
    save(args.output/'manifest.json',manifest)
    save(args.output/'config.json',dict(backend='vllm_selective_flex_0.11.0',model='/data2/huangrj/models/qwen3-8b',temperature=.6,top_p=.95,top_k=20,context_size=32768,batch_size=args.batch_size,enable_thinking=True,prefix_caching=False,scope='all comparisons must use the same backend; old HF outputs are reference only'))
    backend=SelectiveVLLMBackend('/data2/huangrj/models/qwen3-8b',max_num_seqs=args.batch_size)
    total_tokens=0;started=time.monotonic()
    for start in range(0,len(jobs),args.batch_size):
        batch=jobs[start:start+args.batch_size]
        results=backend.generate_batch([j[1] for j in batch],max_new_tokens=32768,temperature=.6,top_p=.95,top_k=20)
        for (enc,req,row),g in zip(batch,results):
            record=evaluate(row,enc,req,g)
            final,status=extract_final_draft(g.text,enc.text,backend.tokenizer.eos_token)
            record.update(final_response=final,thinking_status=status)
            record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
            append(args.output/'results.jsonl',record);total_tokens+=len(g.generated_token_ids)
        print(json.dumps(dict(event='batch_complete',completed=min(start+args.batch_size,len(jobs)),total=len(jobs),tokens=total_tokens,seconds=time.monotonic()-started)),flush=True)
    save(args.output/'completion.json',dict(completed=len(jobs),tokens=total_tokens,seconds=time.monotonic()-started))

if __name__=='__main__':main()
