"""CPU test of pinned worker mask with shuffled physical KV pages and requests.
Capability is stubbed ONLY to import vLLM's CUDA-only modules without a context.
"""
import torch
torch.cuda.get_device_capability=lambda *a,**k:(8,0)
from types import SimpleNamespace as NS
from selective_context.vllm_worker import _RUNNER
from selective_context.vllm_mask import METADATA_KEY,request_metadata
from selective_context.schema import AccessMode,SelectiveContextRequest,token_ids_sha256
from selective_context.masks import build_allowed_attention
from vllm.v1.attention.backends.flex_attention import FlexAttentionMetadata,causal_mask_mod

ids=list(range(12))
def req(mode):
 return SelectiveContextRequest(mode.value,ids,'h',token_ids_sha256(ids),(1,10),mode,1,
  ((2,8),) if mode is not AccessMode.FULL else (),((2,4),(4,8)) if mode is AccessMode.PATH_BLOCK else ())
requests={m.value:req(m) for m in AccessMode}
states={k:NS(num_prompt_tokens=12,sampling_params=NS(extra_args={METADATA_KEY:request_metadata(v)})) for k,v in requests.items()}
runner=NS(requests=states,input_batch=NS(req_ids=list(states)))
count=0
for order in [list(states),list(reversed(states)),['path_block','full']]:
 runner.input_batch.req_ids=order
 for offset in [0,9,12]:
  # Three queries per request, including prefill boundary and generated queries.
  nreq=len(order);qlen=3;klen=offset+3;block=2;nblocks=(klen+1)//2
  total=nreq*nblocks
  m=object.__new__(FlexAttentionMetadata)
  m.causal=True;m.sliding_window=None;m.num_reqs=nreq
  m.block_size=block;m.block_table=torch.empty((nreq,nblocks),dtype=torch.int64)
  m.doc_ids=torch.arange(nreq).repeat_interleave(qlen)
  m.query_start_loc=torch.arange(nreq+1)*qlen
  m.decode_offset=torch.full((nreq,),offset)
  m.seq_lens=torch.full((nreq,),klen)
  m.logical_mask_mod=causal_mask_mod
  m.physical_to_logical=torch.full((nreq,total),-1,dtype=torch.int64)
  pages={}
  for ri in range(nreq):
   pages[ri]=list(reversed(range(ri*nblocks,(ri+1)*nblocks)))
   for logical,physical in enumerate(pages[ri]):m.physical_to_logical[ri,physical]=logical
  marker=_RUNNER.set(runner)
  try:mask=m.get_mask_mod()
  finally:_RUNNER.reset(marker)
  for ri,key in enumerate(order):
   r=requests[key]
   # Reference requires key_length >= original prompt length.
   expected=build_allowed_attention(batch_size=1,query_positions=range(offset,offset+qlen),key_length=max(12,klen),draft_token_span=r.draft_token_span,access_mode=r.access_mode,prompt_length=12,mask_token_spans=r.mask_token_spans,path_block_units=r.path_block_units)[0,0]
   for q in range(qlen):
    for physical in range(total*block):
     logical_block=int(m.physical_to_logical[ri,physical//block]);lk=logical_block*block+physical%block
     want=logical_block>=0 and lk<klen and bool(expected[q,lk])
     got=bool(mask(torch.tensor(0),torch.tensor(0),torch.tensor(ri*qlen+q),torch.tensor(physical)))
     assert got==want,(order,offset,ri,q,physical,lk,want,got)
     count+=1
print('PAGED_REQUEST_MAPPING_PASS',count,'edges; reorder, mixed modes, prefill and decode')
