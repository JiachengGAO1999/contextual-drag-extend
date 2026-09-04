import torch

from selective_context.hf_backend import SelectiveHFBackend
from selective_context.masks import build_additive_attention
from selective_context.phase0.tiny_model import NumericTokenizer, make_tiny_qwen
from selective_context.schema import AccessMode, SelectiveContextRequest, text_sha256, token_ids_sha256


def mask(mode, queries, key_length, prompt_length=7, span=(1, 4)):
    return build_additive_attention(batch_size=1, query_positions=queries, key_length=key_length, draft_token_span=span, access_mode=mode, prompt_length=prompt_length, dtype=torch.float32)


def test_standard_causal_and_identity_custom_mask_equivalent():
    model = make_tiny_qwen()
    ids = torch.tensor([[1, 5, 6, 7, 8, 9, 10]])
    standard = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False).logits
    custom = model(input_ids=ids, attention_mask=mask(AccessMode.FULL, range(7), 7), use_cache=False).logits
    torch.testing.assert_close(standard, custom, rtol=1e-5, atol=1e-6)


def test_cached_and_non_cached_identity_decoding_equivalent():
    model = make_tiny_qwen()
    prompt = torch.tensor([[1, 5, 6, 7, 8, 9, 10]])
    token = torch.tensor([[11]])
    prefill = model(input_ids=prompt, attention_mask=mask(AccessMode.FULL, range(7), 7), use_cache=True)
    cached = model(input_ids=token, past_key_values=prefill.past_key_values, attention_mask=mask(AccessMode.FULL, [7], 8), use_cache=True).logits[:, -1]
    joined = torch.cat([prompt, token], dim=1)
    noncached = model(input_ids=joined, attention_mask=mask(AccessMode.FULL, range(8), 8, prompt_length=7), use_cache=False).logits[:, -1]
    torch.testing.assert_close(cached, noncached, rtol=1e-5, atol=1e-6)


def test_path_block_makes_postdraft_logits_invariant_to_draft_tokens():
    model = make_tiny_qwen()
    first = torch.tensor([[1, 5, 6, 7, 30, 31, 32]])
    second = torch.tensor([[1, 15, 16, 17, 30, 31, 32]])
    path_mask = mask(AccessMode.PATH_BLOCK, range(7), 7)
    logits_first = model(input_ids=first, attention_mask=path_mask, use_cache=False).logits[:, -1]
    logits_second = model(input_ids=second, attention_mask=path_mask, use_cache=False).logits[:, -1]
    torch.testing.assert_close(logits_first, logits_second, rtol=1e-5, atol=1e-6)


def test_actual_attention_probabilities_obey_late_and_path_blocks():
    model = make_tiny_qwen()
    ids = torch.tensor([[1, 5, 6, 7, 30, 31, 32]])
    # Path-complete prefill: post-draft queries cannot read draft columns.
    path = model(input_ids=ids, attention_mask=mask(AccessMode.PATH_BLOCK, range(7), 7), use_cache=True, output_attentions=True)
    for layer_attention in path.attentions:
        assert torch.count_nonzero(layer_attention[0, :, 4:, 1:4]) == 0
    # Late prefill is standard; its generated query is blocked from draft KV.
    full_prefill = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=True)
    decode = model(input_ids=torch.tensor([[33]]), past_key_values=full_prefill.past_key_values, attention_mask=mask(AccessMode.LATE_BLOCK, [7], 8), use_cache=True, output_attentions=True)
    for layer_attention in decode.attentions:
        assert torch.count_nonzero(layer_attention[0, :, 0, 1:4]) == 0


def test_toy_generation_seed_and_kv_metadata():
    model = make_tiny_qwen()
    ids = [1, 5, 6, 7, 30, 31, 32]
    request = SelectiveContextRequest("R3", ids, text_sha256("toy"), token_ids_sha256(ids), (1, 4), AccessMode.LATE_BLOCK, 99)
    backend = SelectiveHFBackend(model, NumericTokenizer())
    one = backend.generate(request, max_new_tokens=3, temperature=0.7, top_k=10)
    two = backend.generate(request, max_new_tokens=3, temperature=0.7, top_k=10)
    assert one.generated_token_ids == two.generated_token_ids
    assert one.metadata["cache_type"]
    assert one.metadata["physical_kv_eviction"] is False
