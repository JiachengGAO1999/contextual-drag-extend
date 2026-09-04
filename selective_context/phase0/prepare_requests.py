from __future__ import annotations

import argparse
import json
from pathlib import Path

from selective_context.prompting import (
    encode_direct_prompt,
    encode_prompt,
    make_r2_r4_requests,
    make_request,
    persist_request_bundle,
    render_chat_prompt,
    render_official_prompt,
)
from selective_context.schema import AccessMode


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze R0-R4 token IDs from local files without allowing checkpoint downloads.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL with id, problem, traj1")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tokenizer", required=True, help="Existing local tokenizer directory")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--enable-thinking", action="store_true")
    args = parser.parse_args()
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, use_fast=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index = []
    with args.input.open("r", encoding="utf-8") as handle:
        for row_number, line in enumerate(handle):
            if not line.strip():
                continue
            row = json.loads(line)
            row_id = str(row.get("id", row_number))
            problem, draft = row["problem"], row["traj1"]
            r0_text = render_chat_prompt(tokenizer, render_official_prompt(args.repo_root, "R0", problem), args.enable_thinking)
            r0_encoded = encode_direct_prompt(tokenizer, r0_text)
            r0 = make_request(r0_encoded, "R0", AccessMode.FULL, args.seed)
            r1_text = render_chat_prompt(tokenizer, render_official_prompt(args.repo_root, "R1", problem, draft), args.enable_thinking)
            r1_encoded = encode_prompt(tokenizer, r1_text)
            r1 = make_request(r1_encoded, "R1", AccessMode.FULL, args.seed)
            r2_text = render_chat_prompt(tokenizer, render_official_prompt(args.repo_root, "R2", problem, draft), args.enable_thinking)
            r2_encoded = encode_prompt(tokenizer, r2_text)
            bundles = [("r0", r0_encoded, [r0]), ("r1", r1_encoded, [r1]), ("r2_r4", r2_encoded, make_r2_r4_requests(r2_encoded, args.seed))]
            for suffix, encoded, requests in bundles:
                destination = args.output_dir / f"{row_id}.{suffix}.json"
                persist_request_bundle(destination, encoded, requests)
                index.append({"id": row_id, "bundle": suffix, "path": destination.name})
    (args.output_dir / "manifest.json").write_text(json.dumps({"schema_version": 1, "records": index}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
