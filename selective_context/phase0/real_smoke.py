"""Bounded real-model Game24 smoke. Explicit local input; no automatic downloads."""
from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from selective_context.hf_backend import SelectiveHFBackend
from selective_context.masks import build_additive_attention
from selective_context.official_compat import make_official_record
from selective_context.prompting import (encode_direct_prompt, encode_prompt, make_request,
    make_r2_r4_requests, persist_request_bundle, load_request_bundle,
    render_chat_prompt, render_official_prompt)
from selective_context.schema import AccessMode
# Import official evaluator directly: never permit the local fallback here.
from utils.verifiable_evaluation.math_eval.utils.evaluation_utils import evaluate_single_entry
from utils.verifiable_evaluation.math_eval.utils.verification_utils import is_correct_game_of_24


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def append(path, value):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def evaluate(row, encoded, request, result):
    record = make_official_record(problem_id=row["id"], problem=row["problem"],
        answer=row["answer"], prompt=encoded.text, request=request,
        generations=[result], model_config_alias="Qwen3_8B")
    record = evaluate_single_entry(record, "answer", "init_response_generations", is_correct_game_of_24)
    record["generated_token_ids"] = result.generated_token_ids
    return record


@torch.inference_mode()
def sanity(model, request):
    """Real-model attention edges and post-draft invariance, using the actual prompt."""
    ids = torch.tensor([request.input_ids], device=model.device)
    n = ids.shape[1]
    start, end = request.draft_token_span
    if end >= n:
        raise RuntimeError("No post-draft prompt state available for sanity check")
    kwargs = dict(batch_size=1, query_positions=range(n), key_length=n,
        draft_token_span=(start, end), prompt_length=n, dtype=model.dtype, device=model.device)
    path_mask = build_additive_attention(access_mode=AccessMode.PATH_BLOCK, **kwargs)
    output = model(input_ids=ids, attention_mask=path_mask, use_cache=False,
                   output_attentions=True, return_dict=True)
    path_max = max(float(a[..., end:, start:end].abs().max()) for a in output.attentions)
    reference = output.logits[:, -1].clone()
    del output
    changed = ids.clone()
    changed[:, start:end] = (changed[:, start:end] + 1) % model.config.vocab_size
    altered = model(input_ids=changed, attention_mask=path_mask, use_cache=False).logits[:, -1]
    difference = float((reference - altered).abs().max())
    torch.testing.assert_close(reference, altered, rtol=0, atol=0)
    del altered, path_mask
    full = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=True)
    token = full.logits[:, -1].argmax(-1).view(1, 1)
    late_mask = build_additive_attention(batch_size=1, query_positions=[n], key_length=n+1,
        draft_token_span=(start, end), prompt_length=n, dtype=model.dtype,
        device=model.device, access_mode=AccessMode.LATE_BLOCK)
    late = model(input_ids=token, past_key_values=full.past_key_values,
        attention_mask=late_mask, use_cache=True, output_attentions=True)
    late_max = max(float(a[..., start:end].abs().max()) for a in late.attentions)
    if path_max != 0 or late_max != 0:
        raise RuntimeError("Blocked attention edges have nonzero probability")
    return {"path_block_max_attention": path_max, "late_block_max_attention": late_max,
        "path_postdraft_logits_change_after_draft_token_mutation": difference,
        "layers_checked": len(late.attentions), "prompt_tokens": n,
        "position_ids": "unchanged implicit absolute positions 0..prompt_length-1",
        "r3_first_token_boundary": "full-prefill logits, unchanged"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", type=Path, required=True, help="Explicit Game24 CSV")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--max-candidates", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Use a fresh output directory; do not overwrite an earlier run")
    args.output.mkdir(parents=True)
    repo = Path(__file__).resolve().parents[2]
    config = dict(model=args.model, source=str(args.input), source_revision=args.source_revision,
        purpose="engineering_smoke_only_no_scientific_go_no_go",
        count=args.count, max_candidates=args.max_candidates, max_new_tokens=args.max_new_tokens,
        temperature=0.6, top_p=0.95, top_k=None, enable_thinking=False,
        seed_order=2027, draft_seed_base=102027, evaluation_seed_base=2027,
        selection="first completed, officially parseable incorrect draft per unique problem; one independent draft attempt per candidate; no selection on R0-R4 outcomes",
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        git_status=subprocess.check_output(["git", "status", "--short"], cwd=repo, text=True),
        torch=torch.__version__, transformers=transformers.__version__,
        dtype="bfloat16", attention="eager", physical_kv_eviction=False)
    save(args.output / "config.json", config)
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
        torch_dtype=torch.bfloat16, attn_implementation="eager", device_map="cuda:0")
    backend = SelectiveHFBackend(model, tokenizer)
    gen = dict(max_new_tokens=args.max_new_tokens, temperature=0.6, top_p=0.95)
    with args.input.open(encoding="utf-8-sig") as handle:
        raw_rows = list(csv.DictReader(handle))
    random.Random(2027).shuffle(raw_rows)
    completed = []
    seen = set()
    began = time.monotonic()
    for index, raw in enumerate(raw_rows[:args.max_candidates]):
        numbers = [int(x) for x in raw["Puzzles"].split()]
        key = tuple(sorted(numbers))
        if key in seen:
            continue
        seen.add(key)
        row = {"id": str(raw.get("Rank", index)), "answer": numbers,
            "problem": f"Use the numbers {', '.join(map(str, numbers))} exactly once each, with addition, subtraction, multiplication, division and parentheses, to make 24. Provide an expression using the original four numbers."}
        direct = encode_direct_prompt(tokenizer, render_chat_prompt(tokenizer,
            render_official_prompt(repo, "R0", row["problem"])))
        draft_request = make_request(direct, "R0", AccessMode.FULL, 102027 + index)
        draft_result = backend.generate(draft_request, **gen)
        draft_record = evaluate(row, direct, draft_request, draft_result)
        draft_eval = draft_record["init_response_generations"][0]
        append(args.output / "draft_candidates.jsonl", draft_record)
        print(json.dumps({"candidate": index+1, "id": row["id"], "draft_correct": draft_eval["correctness"],
            "finish": draft_result.finish_reason, "tokens": len(draft_result.generated_token_ids)}, ensure_ascii=False), flush=True)
        if draft_eval["correctness"] is not False or draft_result.finish_reason != "eos":
            continue
        # Keep raw generation in draft_candidates, but do not insert terminal chat
        # control tokens into a user-message draft (same semantics as HF decoding).
        row["traj1"] = tokenizer.decode(draft_result.generated_token_ids, skip_special_tokens=True)
        seed = 2027 + index
        r1 = encode_prompt(tokenizer, render_chat_prompt(tokenizer,
            render_official_prompt(repo, "R1", row["problem"], row["traj1"])))
        r2 = encode_prompt(tokenizer, render_chat_prompt(tokenizer,
            render_official_prompt(repo, "R2", row["problem"], row["traj1"])))
        append(args.output / "boundary_audits.jsonl", {"id": row["id"],
            "conditions": {c: {"draft_character_span": e.draft_character_span,
                "masked_character_span": e.masked_character_span, "draft_token_span": e.draft_token_span,
                "boundary_spillover": e.boundary_spillover} for c, e in [("R1", r1), ("R2_R3_R4", r2)]}})
        bundles = [("r0", direct, [make_request(direct, "R0", AccessMode.FULL, seed)]),
            ("r1", r1, [make_request(r1, "R1", AccessMode.FULL, seed)]),
            ("r2_r4", r2, make_r2_r4_requests(r2, seed))]
        append(args.output / "paired_examples.jsonl", row)
        if not completed:
            save(args.output / "intervention_sanity.json", sanity(model, bundles[-1][2][0]))
            print("REAL_MODEL_INTERVENTION_SANITY_PASSED", flush=True)
        outcomes = {}
        for suffix, encoded, requests in bundles:
            path = args.output / "bundles" / f"{row['id']}.{suffix}.json"
            persist_request_bundle(path, encoded, requests)
            encoded, requests = load_request_bundle(path)
            for request in requests:
                result = backend.generate(request, **gen)
                record = evaluate(row, encoded, request, result)
                record["elapsed_seconds"] = time.monotonic() - began
                append(args.output / "results.jsonl", record)
                item = record["init_response_generations"][0]
                outcomes[request.condition_id] = {"correct": item["correctness"] is True,
                    "parseable": item["correctness"] is not None, "completed": result.finish_reason == "eos",
                    "first_token": result.generated_token_ids[0], "tokens": len(result.generated_token_ids)}
                print(json.dumps({"paired": len(completed)+1, "id": row["id"], "condition": request.condition_id,
                    **outcomes[request.condition_id]}, ensure_ascii=False), flush=True)
        assert outcomes["R2"]["first_token"] == outcomes["R3"]["first_token"]
        completed.append(outcomes)
        summary = {"n": len(completed), "elapsed_seconds": time.monotonic()-began,
            "conditions": {c: {metric: sum(x[c][metric] for x in completed)/len(completed)
                for metric in ("correct", "parseable", "completed")} for c in outcomes}}
        save(args.output / "summary.json", summary)
        if len(completed) >= args.count:
            print("SMOKE_FINISHED " + json.dumps(summary), flush=True)
            return
    raise RuntimeError(f"Only {len(completed)} paired examples within candidate cap; ask before expanding")


if __name__ == "__main__":
    main()
