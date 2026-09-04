import torch

from selective_context.masks import allowed_to_additive, build_additive_attention, build_allowed_attention
from selective_context.schema import AccessMode


def allowed(mode, queries, key_length=8, span=(2, 5), prompt_length=7, batch=1):
    return build_allowed_attention(batch_size=batch, query_positions=queries, key_length=key_length, draft_token_span=span, access_mode=mode, prompt_length=prompt_length)


def test_shape_dtype_batch_and_causal_boundary():
    mask = allowed(AccessMode.FULL, [2, 5], batch=3)
    assert mask.shape == (3, 1, 2, 8)
    assert mask.dtype == torch.bool
    assert mask[:, :, 0, :3].all()
    assert not mask[:, :, 0, 3:].any()
    additive = allowed_to_additive(mask, torch.float32)
    assert additive.dtype == torch.float32
    assert torch.all(additive[mask] == 0)
    assert torch.all(additive[~mask] == torch.finfo(torch.float32).min)


def test_empty_span_is_strict_noop_for_all_modes():
    full = allowed(AccessMode.FULL, list(range(7)), key_length=7, span=(3, 3))
    for mode in (AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK):
        assert torch.equal(full, allowed(mode, list(range(7)), key_length=7, span=(3, 3)))


def test_late_prefill_full_then_decode_blocks_draft():
    queries = list(range(7))
    assert torch.equal(allowed(AccessMode.FULL, queries, key_length=7), allowed(AccessMode.LATE_BLOCK, queries, key_length=7))
    decode = allowed(AccessMode.LATE_BLOCK, [7])[0, 0, 0]
    assert not decode[2:5].any()
    assert decode[:2].all() and decode[5:].all()


def test_path_blocks_postdraft_and_generation_queries():
    mask = allowed(AccessMode.PATH_BLOCK, [5, 6], key_length=7)[0, 0]
    assert not mask[:, 2:5].any()
    decode = allowed(AccessMode.PATH_BLOCK, [7])[0, 0, 0]
    assert not decode[2:5].any()


def test_only_intended_legal_edges_are_changed():
    full = allowed(AccessMode.FULL, list(range(7)), key_length=7)
    path = allowed(AccessMode.PATH_BLOCK, list(range(7)), key_length=7)
    changed = full ^ path
    expected = torch.zeros_like(changed)
    expected[:, :, 5:7, 2:5] = True
    assert torch.equal(changed, expected)


def test_bad_shapes_and_ranges_fail():
    try:
        allowed_to_additive(torch.ones(2, 2), torch.float32)
        assert False
    except ValueError:
        pass
    try:
        allowed(AccessMode.PATH_BLOCK, [8])
        assert False
    except ValueError:
        pass
