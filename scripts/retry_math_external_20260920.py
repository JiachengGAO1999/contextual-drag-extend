"""Same frozen requests; completed answers saved immediately; no automatic retry."""
import json,os,time
from pathlib import Path
from selective_context.prompting import load_request_bundle
from selective_context.vllm_backend import SelectiveVLLMBackend
from selective_context.phase0.real_smoke import evaluate
from selective_context.phase0.thinking_pilot import extract_final_draft
ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'outputs'/os.environ.get('SC_PREP','math-external-16q-20260920-prepared')
OUT=ROOT/'outputs'/os.environ.get('SC_MATH_RUN','math-external-16q-20260920-retry1')

def main():
    assert os.environ['CUDA_VISIBLE_DEVICES']==os.environ.get('SC_GPU','0')
    task=os.environ.get('SC_TASK','math500')
    total=int(os.environ.get('SC_TOTAL','128'))
    resume=os.environ.get('SC_MATH_RESUME')=='1'
    assert resume or not OUT.exists()
    manifest=json.loads((PREP/'manifest.json').read_text())
    assert len(manifest)==total
    jobs=[]
    for item in manifest:
        enc,reqs=load_request_bundle(ROOT/item['bundle'])
        req=next(r for r in reqs if r.condition_id==item['condition'])
        row=json.loads((ROOT/item['pair']).read_text())
        jobs.append((enc,req,row))
    done=set()
    if resume:
        assert json.loads((OUT/'manifest.json').read_text())==manifest
        for line in (OUT/'results.jsonl').read_text().splitlines():
            record=json.loads(line);m=record['init_response_generations_metadata']['intervention']
            key=(record['id'],m['condition_id'],m['sample_seed'])
            assert key not in done
            done.add(key)
        expected={(row['id'],req.condition_id,req.sample_seed) for enc,req,row in jobs}
        assert done<=expected
        jobs=[j for j in jobs if (j[2]['id'],j[1].condition_id,j[1].sample_seed) not in done]
        print(f'RESUME preserved{len(done)} pending{len(jobs)}',flush=True)
    OUT.mkdir(exist_ok=resume)
    if not resume:
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    condition_ids=sorted({req.condition_id for enc,req,row in jobs} | {
        item['condition'] for item in manifest
    })
    question_ids=sorted({str(row['id']) for enc,req,row in jobs})
    if resume:
        question_ids=sorted({
            str(json.loads((ROOT/item['pair']).read_text())['id']) for item in manifest
        })
    (OUT/('resume_config.json' if resume else 'config.json')).write_text(json.dumps(dict(task=task,questions=len(question_ids),generations=total,
        temperature=.6,top_p=.95,top_k=20,context=32768,batch_size=8,
        change='Guard physical padding; no mask cudagraph capture; per-finished-request fsync.',
        prepared_manifest=str(PREP/'manifest.json'),preserved_results=len(done),source_stratified=True,
        condition_ids=condition_ids),indent=2))
    backend=SelectiveVLLMBackend('/data2/huangrj/models/qwen3-8b',max_num_seqs=8)
    # Short engineering test only, excluded from scientific results.
    probe=[j[1] for j in jobs[:4]]
    received={}
    baseline=backend.generate_batch(probe,max_new_tokens=4,temperature=.6,top_p=.95,top_k=20)
    streamed=backend.generate_batch(probe,max_new_tokens=4,temperature=.6,top_p=.95,top_k=20,
                                    on_result=lambda i,g:received.setdefault(i,g.generated_token_ids))
    assert len(received)==4
    assert [g.generated_token_ids for g in baseline]==[g.generated_token_ids for g in streamed]
    assert all(received[i]==g.generated_token_ids for i,g in enumerate(streamed))
    (OUT/'streaming_smoke.json').write_text(json.dumps(dict(passed=True,engineering_requests=2*len(probe),max_new_tokens=4,
        condition_ids=condition_ids,callback_matches_original_api=True,excluded_from_science=True)))
    print(f'STREAMING_SMOKE_PASS; pending{len(jobs)} frozen scientific requests',flush=True)
    started=time.monotonic();completed=len(done)
    with (OUT/'results.jsonl').open('a',encoding='utf8') as f:
        for start in range(0,len(jobs),8):
            batch=jobs[start:start+8]
            def save(i,g):
                nonlocal completed
                enc,req,row=batch[i]
                record=evaluate(row,enc,req,g,task=task)
                final,status=extract_final_draft(g.text,enc.text,backend.tokenizer.eos_token)
                record.update(final_response=final,thinking_status=status,stratum=row['stratum'],benchmark=row['benchmark'])
                record['init_response_generations_metadata'].update(enable_thinking=True,model_config_alias='Qwen3_8B_Thinking')
                f.write(json.dumps(record,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
                completed+=1
                print(json.dumps(dict(event='request_saved',completed=completed,total=total,id=row['id'],condition=req.condition_id,seconds=time.monotonic()-started)),flush=True)
            backend.generate_batch([j[1] for j in batch],max_new_tokens=32768,temperature=.6,top_p=.95,top_k=20,on_result=save)
    (OUT/'completion.json').write_text(json.dumps(dict(completed=completed,seconds=time.monotonic()-started)))
    print(f'COMPLETE{total}; releasing GPU',flush=True)

if __name__=='__main__':main()
