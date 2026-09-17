import pytest
import torch
from selective_context.masks import build_allowed_attention
from selective_context.schema import AccessMode,SelectiveContextRequest,token_ids_sha256
from selective_context.multi_region import merge_spans
from selective_context.multi_region import compile_regions
from selective_context.prompting import EncodedPrompt

def test_disjoint_edges_preserve_gap_and_prefill():
    kwargs=dict(batch_size=1,query_positions=[7,10,11],key_length=12,draft_token_span=(2,9),prompt_length=10,access_mode=AccessMode.LATE_BLOCK)
    full=build_allowed_attention(**dict(kwargs,access_mode=AccessMode.FULL))
    actual=build_allowed_attention(**kwargs,mask_token_spans=((2,4),(7,9)))
    expected=full.clone();expected[:,:,1:,2:4]=False;expected[:,:,1:,7:9]=False
    assert torch.equal(actual,expected)
    assert actual[0,0,1,4:7].all()

@pytest.mark.parametrize('mode', [AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK])
def test_single_span_matches_legacy(mode):
    kw=dict(batch_size=2,query_positions=list(range(11)),key_length=11,draft_token_span=(2,8),prompt_length=10,access_mode=mode)
    assert torch.equal(build_allowed_attention(**kw),build_allowed_attention(**kw,mask_token_spans=((2,8),)))

@pytest.mark.parametrize('mode', [AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK])
def test_merge_and_request_roundtrip(mode):
    assert merge_spans([(4,7),(2,5),(9,10),(10,12)])==((2,7),(9,12))
    r=SelectiveContextRequest('multi',list(range(10)),'h',token_ids_sha256(list(range(10))),(2,9),mode,7,((2,4),(7,9)))
    r.validate();assert SelectiveContextRequest.from_dict(r.to_dict())==r
    old=r.to_dict();old.pop('mask_token_spans');assert SelectiveContextRequest.from_dict(old).mask_token_spans==()

def test_reject_invalid_or_full_spans():
    kw=dict(batch_size=1,query_positions=[10],key_length=11,draft_token_span=(2,9),prompt_length=10,access_mode=AccessMode.LATE_BLOCK)
    for spans in [((1,3),),((3,6),(5,8)),((5,4),)]:
        with pytest.raises(ValueError):build_allowed_attention(**kw,mask_token_spans=spans)
    with pytest.raises(ValueError):build_allowed_attention(**dict(kw,access_mode=AccessMode.FULL),mask_token_spans=((2,4),))


def test_path_each_interval_boundary_and_decode_union():
    actual = build_allowed_attention(batch_size=2, query_positions=list(range(12)),
        key_length=12, draft_token_span=(2,10), prompt_length=11,
        access_mode=AccessMode.PATH_BLOCK, mask_token_spans=((2,4),(7,9)))
    expected = torch.tril(torch.ones(12,12,dtype=torch.bool))
    expected[4:,2:4] = False
    expected[9:,7:9] = False
    assert torch.equal(actual[0,0], expected)
    assert torch.equal(actual[1,0], expected)
    assert actual[0,0,8,7]  # Own interval remains causal.
    assert not actual[0,0,8,2]  # Earlier interval blocked inside later one.
    assert actual[0,0,11,4:7].all()  # Gap remains visible.


def test_multi_path_actual_attention_and_causal_invariance():
    from selective_context.phase0.tiny_model import make_tiny_qwen
    from selective_context.masks import build_additive_attention
    model = make_tiny_qwen()
    ids = torch.tensor([[1,5,6,7,8,9,10,11,12,13]])
    spans = ((1,3),(5,7))
    def attention(queries, length):
        return build_additive_attention(batch_size=1,query_positions=queries,
            key_length=length,draft_token_span=(1,8),prompt_length=10,
            access_mode=AccessMode.PATH_BLOCK,mask_token_spans=spans,dtype=torch.float32)
    changed = ids.clone()
    for lo,hi in spans:
        changed[:,lo:hi] += 15
    with torch.inference_mode():
        original = model(input_ids=ids, attention_mask=attention(range(10),10),
                         use_cache=True,output_attentions=True)
        mutated = model(input_ids=changed,attention_mask=attention(range(10),10),use_cache=True)
        for layer in original.attentions:
            for lo,hi in spans:
                assert torch.count_nonzero(layer[:,:,hi:,lo:hi]) == 0
            assert layer[:,:,9,3:5].sum() > 0
        torch.testing.assert_close(original.logits[:,7:],mutated.logits[:,7:],rtol=0,atol=1e-6)
        full_a = model(input_ids=ids,use_cache=False).logits[:,-1]
        full_b = model(input_ids=changed,use_cache=False).logits[:,-1]
        assert not torch.allclose(full_a,full_b,rtol=0,atol=1e-6)
        decoded = []
        for prefix in (original,mutated):
            out = model(input_ids=torch.tensor([[14]]),past_key_values=prefix.past_key_values,
                        attention_mask=attention([10],11),use_cache=True,output_attentions=True)
            for layer in out.attentions:
                for lo,hi in spans:
                    assert torch.count_nonzero(layer[:,:,:,lo:hi]) == 0
            decoded.append(out.logits)
        torch.testing.assert_close(*decoded,rtol=0,atol=1e-6)


@pytest.mark.parametrize('mode', [AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK])
def test_backend_routes_multi_regions_in_prefill_and_decode(mode):
    from selective_context.hf_backend import SelectiveHFBackend
    from selective_context.phase0.tiny_model import make_tiny_qwen, NumericTokenizer
    model = make_tiny_qwen()
    calls = []
    forward = model.forward
    def capture(*args, **kwargs):
        calls.append(kwargs['attention_mask'].clone())
        return forward(*args, **kwargs)
    model.forward = capture
    tokenizer = NumericTokenizer()
    tokenizer.eos_token_id = None
    ids = [1,5,6,7,8,9,10,11,12,13]
    req = SelectiveContextRequest('multi',ids,'h',token_ids_sha256(ids),(1,8),mode,7,((1,3),(5,7)))
    result = SelectiveHFBackend(model,tokenizer).generate(req,max_new_tokens=3)
    assert len(result.generated_token_ids) == 3
    assert len(calls) == 3
    if mode is AccessMode.PATH_BLOCK:
        assert (calls[0][0,0,3:,1:3] < 0).all()
        assert (calls[0][0,0,7:,5:7] < 0).all()
        assert calls[0][0,0,9,3] == 0
    else:
        assert calls[0].shape == (1,10) and (calls[0] == 1).all()
    for mask in calls[1:]:
        assert (mask[0,0,0,1:3] < 0).all()
        assert (mask[0,0,0,5:7] < 0).all()
        assert mask[0,0,0,3] == 0

def test_compiler_checks_text_and_union_not_bounding_box():
    text='prefix abc def xyz suffix'
    class CharacterTokenizer:
        def __call__(self,text,**kwargs):return dict(input_ids=list(range(len(text))),offset_mapping=[(i,i+1) for i in range(len(text))])
    enc=EncodedPrompt(text,list(range(len(text))),(7,18),(7,18))
    evidence=[dict(character_span=[7,10],text='abc'),dict(character_span=[15,18],text='xyz')]
    result=compile_regions(CharacterTokenizer(),enc,evidence)
    assert result['spans']==((7,10),(15,18)) and result['token_count']==6
    with pytest.raises(ValueError):compile_regions(CharacterTokenizer(),enc,[dict(character_span=[7,10],text='bad')])
    with pytest.raises(ValueError):compile_regions(CharacterTokenizer(),enc,[])
