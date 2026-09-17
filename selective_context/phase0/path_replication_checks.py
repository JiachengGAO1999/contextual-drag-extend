import torch
from selective_context.masks import build_allowed_attention, build_additive_attention
from selective_context.schema import AccessMode

def allowed(req, q, k):
    return build_allowed_attention(batch_size=1,query_positions=q,key_length=k,draft_token_span=req.draft_token_span,mask_token_spans=req.mask_token_spans,path_block_units=req.path_block_units,access_mode=req.access_mode,prompt_length=len(req.input_ids))

def check_edges(jobs):
    for a,b in zip(jobs[::2],jobs[1::2]):
        x,y=a['req'],b['req'];n=len(x.input_ids)
        assert x.input_ids==y.input_ids and x.sample_seed==y.sample_seed
        assert set(x.path_block_units)<=set(y.path_block_units)
        ax,ay=allowed(x,range(n+1),n+1),allowed(y,range(n+1),n+1)
        assert not (ay & ~ax).any(), 'Expanded mask reopens old blocked edges'
        from dataclasses import replace
        for req in (x,y):
            late=replace(req,access_mode=AccessMode.LATE_BLOCK,path_block_units=())
            assert torch.equal(allowed(req,[n],n+1),allowed(late,[n],n+1))

@torch.inference_mode()
def sanity(model,req):
    ids=torch.tensor([req.input_ids],device=model.device);n=ids.shape[1]
    def mask(q,k):
        return build_additive_attention(batch_size=1,query_positions=q,key_length=k,draft_token_span=req.draft_token_span,mask_token_spans=req.mask_token_spans,path_block_units=req.path_block_units,access_mode=req.access_mode,prompt_length=n,device=model.device,dtype=model.dtype)
    pre=model(input_ids=ids,attention_mask=mask(range(n),n),use_cache=True,output_attentions=True)
    blocked=max(float(a[:,:,hi:,lo:hi].abs().max()) for a in pre.attentions for lo,hi in req.path_block_units)
    keys={i for lo,hi in req.mask_token_spans for i in range(lo,hi)}
    kept=[i for i in range(*req.draft_token_span) if i not in keys]
    retained=min(float(a[:,:,-1,kept].sum()) for a in pre.attentions)
    logits=pre.logits[:,-1].clone();past=pre.past_key_values
    del pre
    changed=ids.clone()
    for lo,hi in req.mask_token_spans:changed[:,lo:hi]=(changed[:,lo:hi]+17)%model.config.vocab_size
    mutated=model(input_ids=changed,attention_mask=mask(range(n),n),use_cache=False)
    delta=float((logits-mutated.logits[:,-1]).abs().max());del mutated
    step=model(input_ids=logits.argmax(-1).view(1,1),past_key_values=past,attention_mask=mask([n],n+1),use_cache=True,output_attentions=True)
    decode=max(float(a[...,lo:hi].abs().max()) for a in step.attentions for lo,hi in req.mask_token_spans)
    assert blocked==decode==delta==0 and retained>0
    return dict(prefill_blocked_max=blocked,decode_blocked_max=decode,final_logits_mutation_delta=delta,retained_mass_min=retained,layers=len(step.attentions))
