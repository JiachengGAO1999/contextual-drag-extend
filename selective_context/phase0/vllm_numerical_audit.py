"""Compare logits at first greedy divergence, with identical forced prefixes."""
import argparse,json
from pathlib import Path
import torch
from selective_context.phase0.vllm_acceptance import fixtures,MODEL
from selective_context.phase0.real_smoke import save
from selective_context.masks import build_additive_attention

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['hf','vllm'],required=True);ap.add_argument('--output',type=Path,default=Path('outputs/vllm-acceptance-20260917'));args=ap.parse_args()
    root=Path(__file__).resolve().parents[2];dest=args.output;requests=fixtures(root)
    if args.mode=='vllm':
        from selective_context.vllm_backend import SelectiveVLLMBackend
        b=SelectiveVLLMBackend(MODEL)
        gs=b.generate_batch(requests,max_new_tokens=256,temperature=0,logprobs=20)
        save(dest/'vllm_logprobs.json',[dict(id=r.condition_id,tokens=g.generated_token_ids,logprobs=g.metadata['logprobs']) for r,g in zip(requests,gs)])
        return
    from transformers import AutoModelForCausalLM
    model=AutoModelForCausalLM.from_pretrained(MODEL,local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0').eval()
    vv=json.loads((dest/'vllm_logprobs.json').read_text());hh=json.loads((dest/'hf.json').read_text())['results'];report=[]
    with torch.inference_mode():
        for r,v,h in zip(requests,vv,hh):
            d=next((i for i,(x,y) in enumerate(zip(v['tokens'],h['tokens'])) if x!=y),None)
            if d is None:
                report.append(dict(id=r.condition_id,exact_prefix=True));continue
            n=len(r.input_ids);ids=torch.tensor([r.input_ids],device=model.device)
            def mask(q,k):return build_additive_attention(batch_size=1,query_positions=q,key_length=k,draft_token_span=r.draft_token_span,mask_token_spans=r.mask_token_spans,path_block_units=r.path_block_units,access_mode=r.access_mode,prompt_length=n,dtype=model.dtype,device=model.device)
            pre=model(input_ids=ids,attention_mask=mask(range(n),n) if r.access_mode.value=='path_block' else torch.ones_like(ids),use_cache=True)
            logits=pre.logits[:,-1];past=pre.past_key_values;del pre
            for i,token in enumerate(v['tokens'][:d]):
                out=model(input_ids=torch.tensor([[token]],device=model.device),past_key_values=past,attention_mask=mask([n+i],n+i+1) if r.access_mode.value!='full' else torch.ones((1,n+i+1),device=model.device,dtype=torch.long),use_cache=True)
                logits=out.logits[:,-1];past=out.past_key_values
            lp=torch.log_softmax(logits.float(),-1)[0]
            hf_top=int(lp.argmax());vl_top=v['tokens'][d]
            common=v['logprobs'][d];diffs={k:float(lp[int(k)])-x for k,x in common.items()}
            report.append(dict(id=r.condition_id,divergence_token=d,hf_top=hf_top,vllm_top=vl_top,hf_logprob_hf_top=float(lp[hf_top]),hf_logprob_vllm_top=float(lp[vl_top]),vllm_logprob_hf_top=common.get(str(hf_top)),vllm_logprob_vllm_top=common[str(vl_top)],max_top20_logprob_delta=max(map(abs,diffs.values()))))
            del past,logits
    save(dest/'numerical_audit.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
