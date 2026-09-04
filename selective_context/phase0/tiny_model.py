from __future__ import annotations

import torch
from transformers import Qwen2Config, Qwen2ForCausalLM


def make_tiny_qwen(seed: int = 7) -> Qwen2ForCausalLM:
    torch.manual_seed(seed)
    config = Qwen2Config(
        vocab_size=97,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        max_position_embeddings=256,
        bos_token_id=1,
        eos_token_id=2,
        pad_token_id=0,
        use_cache=True,
        use_sliding_window=False,
        sliding_window=None,
    )
    config._attn_implementation = "eager"
    return Qwen2ForCausalLM(config).eval()


class NumericTokenizer:
    eos_token_id = 2
    pad_token_id = 0

    def decode(self, token_ids, **kwargs):
        return " ".join(str(int(value)) for value in token_ids)
