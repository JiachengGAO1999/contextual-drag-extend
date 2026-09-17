"""Bounded real-model check of frozen M_X path boundaries; no evaluation run."""
import json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM
from selective_context.masks import build_additive_attention
from selective_context.prompting import load_request_bundle
from selective_context.schema import AccessMode


def main():
    root = Path.cwd()
    coverage = json.loads((root / 'outputs/game24-multi-late-20260912-coverage.json').read_text())
    model = AutoModelForCausalLM.from_pretrained('/data2/huangrj/models/qwen3-8b',
        torch_dtype=torch.bfloat16, attn_implementation='eager', local_files_only=True).to('cuda').eval()
    reports = []
    for pid in ('1226', '719', '577', '1358'):
        base = ('outputs/game24-independent-control-20260910' if pid == '1358'
                else 'outputs/game24-stage-b-paired-20260911/seed-2027')
        _, requests = load_request_bundle(root / base / 'bundles' / (pid + '.r2_r4.json'))
        req = next(r for r in requests if r.condition_id == 'R2')
        spans = tuple(tuple(s) for s in coverage[pid]['M_X']['spans'])
        ids = torch.tensor([req.input_ids],device='cuda')
        n = ids.shape[1]
        def mask(q,k):
            return build_additive_attention(batch_size=1,query_positions=q,key_length=k,
                draft_token_span=req.draft_token_span,mask_token_spans=spans,
                access_mode=AccessMode.PATH_BLOCK,prompt_length=n,device=ids.device,dtype=model.dtype)
        changed = ids.clone()
        for lo,hi in spans:
            changed[:,lo:hi] = (changed[:,lo:hi] + 17) % model.config.vocab_size
        with torch.inference_mode():
            a = model(input_ids=ids,attention_mask=mask(range(n),n),use_cache=True,output_attentions=True)
            blocked = max(float(layer[:,:,hi:,lo:hi].abs().max())
                          for layer in a.attentions for lo,hi in spans)
            keep = [k for k in range(*req.draft_token_span) if not any(lo<=k<hi for lo,hi in spans)]
            retained = min(float(layer[:,:,-1,keep].sum()) for layer in a.attentions)
            logits = a.logits[:,spans[-1][1]:].clone()
            past = a.past_key_values
            del a
            b = model(input_ids=changed,attention_mask=mask(range(n),n),use_cache=True)
            delta = float((logits-b.logits[:,spans[-1][1]:]).abs().max())
            decode_logits = []
            decode_blocked = 0.0
            for cache in (past,b.past_key_values):
                out = model(input_ids=ids[:,-1:],past_key_values=cache,
                            attention_mask=mask([n],n+1),use_cache=True,output_attentions=True)
                decode_blocked = max(decode_blocked,max(float(layer[:,:,:,lo:hi].abs().max())
                    for layer in out.attentions for lo,hi in spans))
                decode_logits.append(out.logits.clone())
                del out
            decode_delta = float((decode_logits[0]-decode_logits[1]).abs().max())
            assert blocked == decode_blocked == delta == decode_delta == 0.0
            assert retained > 0
            reports.append(dict(id=pid,spans=spans,layers=model.config.num_hidden_layers,
                blocked_attention_max=blocked,decode_blocked_attention_max=decode_blocked,
                post_last_span_logits_max_delta=delta,decode_logits_max_delta=decode_delta,
                retained_draft_attention_min_layer=retained))
            print(json.dumps(reports[-1]),flush=True)
            del b,past,logits,decode_logits
    target = root / 'docs/quick_validation/multi_path_sanity_20260913.json'
    target.write_text(json.dumps(dict(model='Qwen3-8B',dtype='bfloat16',results=reports),indent=2)+'\n')


if __name__ == '__main__':
    main()
