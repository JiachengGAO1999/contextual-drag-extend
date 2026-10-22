"""Read-only inspection of installed vLLM and a tokenizer's stop semantics."""
from __future__ import annotations

import argparse
import inspect

from transformers import AutoTokenizer
from vllm import SamplingParams


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, use_fast=True)
    params = SamplingParams(
        ignore_eos=True,
        stop_token_ids=[tokenizer.eos_token_id],
        max_tokens=10,
    )
    print({
        "eos_token": tokenizer.eos_token,
        "eos_token_id": tokenizer.eos_token_id,
        "special_tokens_map": tokenizer.special_tokens_map,
        "chat_tail": tokenizer.apply_chat_template(
            [{"role": "user", "content": "Solve 1+1."}],
            tokenize=False,
            add_generation_prompt=True,
        )[-300:],
        "sampling_params": repr(params),
        "sampling_params_source": inspect.getsourcefile(SamplingParams),
    })


if __name__ == "__main__":
    main()
