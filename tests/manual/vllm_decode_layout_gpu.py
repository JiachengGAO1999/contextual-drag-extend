import os
os.environ['SC_VLLM_DECODE_LAYOUT']='per_request'
import torch
from types import SimpleNamespace
from selective_context.vllm_worker import _ATTENTION
from vllm.v1.attention.backends import flex_attention as f

torch.manual_seed(2027)
batch=4;length=1024;d=128
q=torch.randn(1,4,batch,d,device='cuda',dtype=torch.bfloat16)
k=torch.randn(1,2,batch*length,d,device='cuda',dtype=torch.bfloat16)
v=torch.randn_like(k)
def mask(b,h,qi,ki):
    lk=ki-qi*length
    selected=(qi>0)&(lk>=32)&(lk<64)
    return (qi<batch)&(lk>=0)&(lk<length)&~selected
bm=f.create_block_mask_compiled(mask,None,None,batch,batch*length,device='cuda',BLOCK_SIZE=(128,128))
meta=SimpleNamespace(num_actual_tokens=batch,num_reqs=batch,max_query_len=1,query_start_loc=torch.arange(batch+1,device='cuda'),mask_mod=mask)
marker=_ATTENTION.set(meta)
out=f.flex_attention_compiled(q,k,v,None,bm,d**-.5,enable_gqa=True,kernel_options={'BLOCK_M':32,'BLOCK_N':32,'FORCE_USE_FLEX_ATTENTION':True})
allowed=mask(None,None,torch.arange(batch,device='cuda')[:,None],torch.arange(batch*length,device='cuda')[None,:])
scores=(q.float()@k.repeat_interleave(2,dim=1).float().transpose(-1,-2))*d**-.5
ref=(scores.masked_fill(~allowed,float('-inf')).softmax(-1)@v.repeat_interleave(2,dim=1).float()).to(torch.bfloat16)
error=float((out-ref).abs().max());assert error<.02,error
changed=k.clone();changed_v=v.clone()
for i in range(1,batch):
    changed[:,:,i*length+32:i*length+64]+=100
    changed_v[:,:,i*length+32:i*length+64]+=100
again=f.flex_attention_compiled(q,changed,changed_v,None,bm,d**-.5,enable_gqa=True,kernel_options={'BLOCK_M':32,'BLOCK_N':32,'FORCE_USE_FLEX_ATTENTION':True})
delta=float((out-again).abs().max());assert delta==0,delta
_ATTENTION.reset(marker)
print('PER_REQUEST_DECODE_GPU_PASS',dict(dense_max_abs_error=error,masked_mutation_delta=delta))
