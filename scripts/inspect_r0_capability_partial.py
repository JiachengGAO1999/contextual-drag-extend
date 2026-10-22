"""Read-only summary for a partial target-model capability run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer
    eos_token_id = AutoTokenizer.from_pretrained(
        args.model, local_files_only=True, use_fast=True
    ).eos_token_id
    rows = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(json.dumps({"rows": len(rows)}, ensure_ascii=False))
    for row in rows:
        generation = row["init_response_generations"][0]
        tokens = row["generated_token_ids"]
        print(json.dumps({
            "id": row["id"],
            "correctness": generation["correctness"],
            "finish_reason": generation["finish_reason"],
            "tokens": len(tokens),
            "tokenizer_eos_token_id": eos_token_id,
            "eos_count": tokens.count(eos_token_id),
            "first_eos_index": tokens.index(eos_token_id) if eos_token_id in tokens else None,
            "last_tokens": tokens[-10:],
            "generation_keys": sorted(generation),
            "text_tail": row.get("final_response", "")[-200:],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
