"""Prepare Correct-full/Correct-late request bundles; never starts generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selective_context.prompting import encode_prompt, make_request, persist_request_bundle, render_chat_prompt
from selective_context.schema import AccessMode
from selective_context.tasks import GAME24_SUFFIX


def correct_history_prompt(problem: str, draft: str) -> str:
    return (
        f"Original problem:\n{problem}\n"
        "\nThe following draft has a CORRECT final answer.\n"
        f"-- beginning of the draft --\n{draft}\n-- end of the draft --\n"
        f"\n{GAME24_SUFFIX}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    if len(args.seeds) != len(set(args.seeds)):
        raise ValueError("duplicate seeds")

    rows = [json.loads(line) for line in args.pairs.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 8 or len({str(row["id"]) for row in rows}) != 8:
        raise ValueError("expected eight unique frozen correct-control pairs")
    for row in rows:
        if row.get("correct_source_correctness") is not True:
            raise ValueError(f"correct-source gate failed for {row.get('id')}")
        if row.get("correct_source_finish_reason") != "eos":
            raise ValueError(f"EOS gate failed for {row.get('id')}")
        if row.get("correct_source_thinking_status") != "parsable_thinking":
            raise ValueError(f"thinking gate failed for {row.get('id')}")

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, use_fast=True)
    output.mkdir(parents=True)
    manifest = []
    for row in rows:
        key = hashlib.sha256(str(row["id"]).encode("utf-8")).hexdigest()[:24]
        pair_path = output / f"{key}.pair.json"
        pair_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        rendered = render_chat_prompt(
            tokenizer,
            correct_history_prompt(row["problem"], row["correct_traj"]),
            True,
        )
        encoded = encode_prompt(tokenizer, rendered)
        if len(encoded.input_ids) >= 32768:
            raise ValueError(f"no completion budget for {row['id']}; do not truncate")
        for seed in args.seeds:
            requests = [
                make_request(encoded, "C_FULL", AccessMode.FULL, seed),
                make_request(encoded, "C_LATE", AccessMode.LATE_BLOCK, seed),
            ]
            bundle_path = output / f"{key}.{seed}.correct_full_late.json"
            persist_request_bundle(bundle_path, encoded, requests)
            for request in requests:
                manifest.append(
                    {
                        "task": "game24",
                        "bundle": bundle_path.relative_to(ROOT).as_posix(),
                        "pair": pair_path.relative_to(ROOT).as_posix(),
                        "condition": request.condition_id,
                    }
                )
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Prepared {len(manifest)} frozen correct-specificity requests; no generation started")


if __name__ == "__main__":
    main()
