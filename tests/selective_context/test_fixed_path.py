import pytest
import torch
from selective_context.masks import build_allowed_attention
from selective_context.schema import AccessMode, SelectiveContextRequest, token_ids_sha256

def make(spans,units=()):
    return build_allowed_attention(batch_size=1,query_positions=list(range(12)),
        key_length=12,draft_token_span=(1,10),prompt_length=11,
        access_mode=AccessMode.PATH_BLOCK,mask_token_spans=spans,path_block_units=units)

def test_expansion_preserves_old_edges_including_overlap_and_adjacency():
    old=make(((2,4),))
    merged=make(((2,8),))
    assert not old[0,0,4,2] and merged[0,0,4,2]
    for units in [((2,4),(4,8)),((2,4),(3,8)),((2,4),(2,8))]:
        expanded=make(((2,8),),units)
        assert not (expanded & ~old).any()
        assert not expanded[0,0,4,2]
        assert expanded[0,0,6,5]

def test_fixed_units_legacy_equivalence_and_roundtrip():
    spans=((2,4),(7,9))
    assert torch.equal(make(spans),make(spans,spans))
    ids=list(range(12))
    req=SelectiveContextRequest('fixed',ids,'h',token_ids_sha256(ids),(1,10),AccessMode.PATH_BLOCK,7,((2,8),),((2,4),(4,8)))
    req.validate()
    assert SelectiveContextRequest.from_dict(req.to_dict())==req
    legacy=SelectiveContextRequest('legacy',ids,'h',token_ids_sha256(ids),(1,10),AccessMode.PATH_BLOCK,7,spans)
    assert 'path_block_units' not in legacy.to_dict()

@pytest.mark.parametrize('units',[((2,3),),((2,4),(2,4)),((4,8),(2,4)),((0,4),(4,8))])
def test_invalid_fixed_units_rejected(units):
    with pytest.raises(ValueError):make(((2,8),),units)

def test_backend_uses_fixed_units_in_prefill():
    from selective_context.hf_backend import SelectiveHFBackend
    from selective_context.phase0.tiny_model import make_tiny_qwen,NumericTokenizer
    model=make_tiny_qwen();calls=[];forward=model.forward
    def capture(*args,**kwargs):
        calls.append(kwargs['attention_mask'].clone())
        return forward(*args,**kwargs)
    model.forward=capture
    ids=list(range(12));req=SelectiveContextRequest('fixed',ids,'h',token_ids_sha256(ids),(1,10),AccessMode.PATH_BLOCK,7,((2,8),),((2,4),(4,8)))
    t=NumericTokenizer();t.eos_token_id=None
    SelectiveHFBackend(model,t).generate(req,max_new_tokens=2)
    assert calls[0][0,0,4,2]<0
    assert calls[0][0,0,6,5]==0
    assert (calls[1][0,0,0,2:8]<0).all()
