import pytest
import torch
from selective_context.schema import AccessMode, SelectiveContextRequest, token_ids_sha256
from selective_context.masks import build_allowed_attention
from selective_context.vllm_mask import request_metadata,key_block_onsets,NEVER

@pytest.mark.parametrize('mode',list(AccessMode))
@pytest.mark.parametrize('spans,units',[((),()),(((2,4),(6,8)),()),(((2,8),),((2,5),(4,8))),(((2,8),),((2,4),(4,8)))])
def test_exact_edge_equivalence(mode,spans,units):
    if mode is AccessMode.FULL:spans,units=(),()
    if mode is not AccessMode.PATH_BLOCK:units=()
    ids=list(range(12));r=SelectiveContextRequest('test',ids,'h',token_ids_sha256(ids),(1,10),mode,1,spans,units)
    onsets=key_block_onsets(request_metadata(r))+[NEVER]*4
    expected=build_allowed_attention(batch_size=1,query_positions=range(16),key_length=16,draft_token_span=r.draft_token_span,access_mode=mode,prompt_length=12,mask_token_spans=spans,path_block_units=units)[0,0]
    actual=torch.tensor([[k<=q and q<onsets[k] for k in range(16)] for q in range(16)])
    assert torch.equal(actual,expected)

def test_late_prefill_boundary():
    m=dict(mode='late_block',prompt_length=10,draft_span=[2,7],spans=[[3,5]],units=[])
    o=key_block_onsets(m)
    assert 9<o[3] and not 10<o[3] and o[5]==NEVER
