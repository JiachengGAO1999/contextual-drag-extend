"""Run frozen target-model R2/R3 interventions after a passed R0 gate.

The runner keeps the frozen manifest intact, writes every completed request
durably, and checks the R2/R3 first-generated-token boundary invariant for
each question-seed pair before continuing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

from selective_context.phase0.real_smoke import evaluate
from selective_context.phase0.thinking_pilot import extract_final_draft
from selective_context.prompting import load_request_bundle
from selective_context.vllm_mask import NEVER, key_block_onsets, request_metadata


class HFSequentialBackend:
    """Reference eager backend shared by R2 and R3 for heterogeneous models."""

    def __init__(self, model: str, *, max_model_len: int):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from selective_context.hf_backend import SelectiveHFBackend

        tokenizer = AutoTokenizer.from_pretrained(
            model, local_files_only=True, use_fast=True, trust_remote_code=True
        )
        loaded = AutoModelForCausalLM.from_pretrained(
            model,
            local_files_only=True,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            device_map="cuda:0",
        )
        self.backend = SelectiveHFBackend(loaded, tokenizer)
        self.tokenizer = tokenizer
        self.max_model_len = max_model_len

    def generate_batch(self, requests, *, max_new_tokens: int, temperature: float,
                       top_p: float, top_k: int, on_result=None):
        results = []
        for index, request in enumerate(requests):
            budget = min(max_new_tokens, self.max_model_len - len(request.input_ids))
            if budget < 1:
                raise ValueError("No generation budget")
            result = self.backend.generate(
                request,
                max_new_tokens=budget,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )
            results.append(result)
            if on_result is not None:
                on_result(index, result)
        return results


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def git_metadata(root: Path) -> tuple[str, str]:
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=root, text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable_non_git_snapshot", "unavailable_non_git_snapshot"
    return head, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--r0-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--task", default="game24")
    parser.add_argument("--expected-questions", type=int, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=32768)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--backend", choices=("selective", "hf"), default="selective")
    parser.add_argument(
        "--worker-cls",
        default="selective_context.vllm_worker.SelectiveWorker",
    )
    parser.add_argument(
        "--enable-thinking", action=argparse.BooleanOptionalAction, default=True
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    prepared = args.prepared.resolve()
    r0_gate = args.r0_gate.resolve()
    output = args.output.resolve()
    output.relative_to(root)
    if output.exists():
        raise RuntimeError("Refusing to overwrite an existing target intervention run")
    if args.batch_size != 1:
        raise RuntimeError("Frozen target-model intervention protocol requires batch_size=1")
    if len(set(args.seeds)) != len(args.seeds):
        raise RuntimeError("Duplicate seeds")

    gate = json.loads((r0_gate / "gate_decision.json").read_text(encoding="utf-8"))
    gate_config = json.loads((r0_gate / "config.json").read_text(encoding="utf-8"))
    gate_completion = json.loads((r0_gate / "completion.json").read_text(encoding="utf-8"))
    if gate_config.get("backend") != args.backend:
        raise RuntimeError(
            f"R0/R2/R3 backend mismatch: gate={gate_config.get('backend')}, run={args.backend}"
        )
    expected_gate_total = args.expected_questions * len(args.seeds)
    frozen_gate = gate_config.get("gate_frozen_before_outcomes") or {}
    if (
        gate.get("status") != "passed"
        or gate.get("total") != expected_gate_total
        or gate.get("correct", -1) < frozen_gate.get("correct_at_least", expected_gate_total + 1)
        or gate.get("normal_parseable", -1)
        < frozen_gate.get("normal_and_officially_parseable_at_least", expected_gate_total + 1)
    ):
        raise RuntimeError(f"Unexpected or failed frozen R0 gate: {gate}")
    if gate_completion.get("completed") != expected_gate_total:
        raise RuntimeError("R0 gate is incomplete")

    manifest_path = prepared / "manifest.json"
    if gate_config.get("prepared_manifest_sha256") != file_sha256(manifest_path):
        raise RuntimeError("Prepared manifest differs from the one used by the R0 gate")
    full_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [row for row in full_manifest if row["condition"] in ("R2", "R3")]
    expected = args.expected_questions * len(args.seeds) * 2
    if len(selected) != expected:
        raise RuntimeError(f"Expected {expected} R2/R3 requests, found {len(selected)}")

    jobs = []
    prompt_lengths = []
    for item in selected:
        encoded, requests = load_request_bundle(root / item["bundle"])
        request = next(r for r in requests if r.condition_id == item["condition"])
        request.validate()
        row = json.loads((root / item["pair"]).read_text(encoding="utf-8"))
        if row.get("audit_status") != "substantive_failed":
            raise RuntimeError(f"Non-audited source pair for {row.get('id')}")
        prompt_lengths.append(len(request.input_ids))
        jobs.append((encoded, request, row, item))

    keys = [(str(row["id"]), req.sample_seed, req.condition_id)
            for _, req, row, _ in jobs]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate question-seed-condition key")
    if len({key[0] for key in keys}) != args.expected_questions:
        raise RuntimeError("Unexpected question count")
    expected_counts = Counter({seed: args.expected_questions * 2 for seed in args.seeds})
    if Counter(key[1] for key in keys) != expected_counts:
        raise RuntimeError("Unexpected seed coverage")
    if Counter(key[2] for key in keys) != {"R2": expected // 2, "R3": expected // 2}:
        raise RuntimeError("Unexpected condition coverage")

    paired = {}
    for encoded, request, row, _ in jobs:
        paired.setdefault((str(row["id"]), request.sample_seed), {})[
            request.condition_id
        ] = (encoded, request)
    if len(paired) != args.expected_questions * len(args.seeds):
        raise RuntimeError("Unexpected paired-unit count")
    for key, conditions in paired.items():
        if set(conditions) != {"R2", "R3"}:
            raise RuntimeError(f"Missing paired condition for {key}")
        r2_encoded, r2 = conditions["R2"]
        r3_encoded, r3 = conditions["R3"]
        if r2.input_ids != r3.input_ids or r2_encoded.text != r3_encoded.text:
            raise RuntimeError(f"R2/R3 same-text contract failed for {key}")
        n = len(r2.input_ids)
        lo, hi = r2.draft_token_span
        if not 0 <= lo < hi <= n:
            raise RuntimeError(f"Invalid draft span for {key}")
        if key_block_onsets(request_metadata(r2)) != [NEVER] * n:
            raise RuntimeError(f"R2 access mask is not full for {key}")
        expected_r3 = [n if lo <= token < hi else NEVER for token in range(n)]
        if key_block_onsets(request_metadata(r3)) != expected_r3:
            raise RuntimeError(f"R3 late-block mask mismatch for {key}")
    min_completion_room = args.max_model_len - max(prompt_lengths)
    if min_completion_room < 8192:
        raise RuntimeError(f"Insufficient completion room: {min_completion_room}")

    output.mkdir(parents=True)
    git_head, git_status = git_metadata(root)
    write_json(output / "manifest.json", selected)
    write_json(output / "preflight.json", {
        "passed": True,
        "requests": expected,
        "paired_units": len(paired),
        "conditions": {"R2": expected // 2, "R3": expected // 2},
        "same_text_contract_pairs": len(paired),
        "mask_contract_pairs": len(paired),
        "maximum_prompt_tokens": max(prompt_lengths),
        "minimum_completion_room": min_completion_room,
    })
    write_json(output / "config.json", {
        "purpose": "target_model_scale_generalization_R2_vs_R3",
        "model": args.model,
        "model_config_alias": args.model_alias,
        "task": args.task,
        "questions": args.expected_questions,
        "seeds": args.seeds,
        "conditions": ["R2", "R3"],
        "requests": expected,
        "sampling": {"temperature": 0.6, "top_p": 0.95, "top_k": 20},
        "context": args.max_model_len,
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "prepared_manifest": str(manifest_path),
        "prepared_manifest_sha256": file_sha256(manifest_path),
        "passed_r0_gate": str(r0_gate / "gate_decision.json"),
        "passed_r0_gate_sha256": file_sha256(r0_gate / "gate_decision.json"),
        "git_head": git_head,
        "git_status": git_status,
        "durability": "each finished request is flushed and fsynced",
        "enable_thinking": args.enable_thinking,
        "backend": args.backend,
        "worker_cls": args.worker_cls if args.backend == "selective" else None,
        "eos_policy": (
            "HF backend stops on the union of model generation/config and tokenizer EOS token IDs"
            if args.backend == "hf"
            else "ignore_eos=False; tokenizer EOS also explicit stop token"
        ),
    })

    if args.backend == "hf":
        backend = HFSequentialBackend(args.model, max_model_len=args.max_model_len)
    else:
        from selective_context.vllm_backend import SelectiveVLLMBackend
        backend = SelectiveVLLMBackend(
            args.model,
            max_model_len=args.max_model_len,
            max_num_seqs=args.batch_size,
            gpu_memory_utilization=args.gpu_memory_utilization,
            worker_cls=args.worker_cls,
        )

    began = time.monotonic()
    completed = 0
    first_tokens = {}
    boundary_checks = []
    condition_correct = Counter()
    condition_parseable = Counter()
    with (output / "results.jsonl").open("a", encoding="utf-8") as handle:
        for encoded, request, row, _ in jobs:
            def save(_index, generation):
                nonlocal completed
                record = evaluate(row, encoded, request, generation, task=args.task)
                if args.enable_thinking:
                    final_response, thinking_status = extract_final_draft(
                        generation.text, encoded.text, backend.tokenizer.eos_token
                    )
                else:
                    final_response = generation.text.strip()
                    thinking_status = "not_applicable_non_thinking_model"
                tokens = generation.generated_token_ids
                if not tokens:
                    raise RuntimeError("Empty generation")
                generation_record = record["init_response_generations"][0]
                generation_record.update(
                    first_generated_token_id=tokens[0],
                    generated_token_count=len(tokens),
                )
                record.update(
                    final_response=final_response,
                    thinking_status=thinking_status,
                    stratum=row["stratum"],
                    benchmark=row["benchmark"],
                )
                record["init_response_generations_metadata"].update(
                    enable_thinking=args.enable_thinking,
                    model_config_alias=args.model_alias,
                )
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                completed += 1
                condition = request.condition_id
                condition_correct[condition] += int(generation_record["correctness"] is True)
                condition_parseable[condition] += int(
                    generation.finish_reason == "eos"
                    and generation_record["correctness"] is not None
                )
                pair_key = (str(row["id"]), request.sample_seed)
                first_tokens.setdefault(pair_key, {})[condition] = tokens[0]
                if set(first_tokens[pair_key]) == {"R2", "R3"}:
                    check = {
                        "id": row["id"],
                        "seed": request.sample_seed,
                        "R2_first_token": first_tokens[pair_key]["R2"],
                        "R3_first_token": first_tokens[pair_key]["R3"],
                        "matches": first_tokens[pair_key]["R2"] == first_tokens[pair_key]["R3"],
                    }
                    boundary_checks.append(check)
                    write_json(output / "boundary_checks.json", boundary_checks)
                    if not check["matches"]:
                        write_json(output / "invalid_boundary.json", check)
                        raise RuntimeError(f"R2/R3 first-token boundary invariant failed: {pair_key}")
                print(json.dumps({
                    "event": "request_saved",
                    "completed": completed,
                    "total": expected,
                    "id": row["id"],
                    "seed": request.sample_seed,
                    "condition": condition,
                    "seconds": round(time.monotonic() - began, 1),
                }), flush=True)

            backend.generate_batch(
                [request],
                max_new_tokens=args.max_new_tokens,
                temperature=0.6,
                top_p=0.95,
                top_k=20,
                on_result=save,
            )

    if len(boundary_checks) != len(paired) or not all(x["matches"] for x in boundary_checks):
        raise RuntimeError("Incomplete R2/R3 boundary audit")
    write_json(output / "completion.json", {
        "completed": completed,
        "seconds": time.monotonic() - began,
        "correct": dict(condition_correct),
        "normal_parseable": dict(condition_parseable),
        "boundary_pairs_passed": len(boundary_checks),
    })
    print(f"COMPLETE {completed}/{expected}; releasing GPU", flush=True)


if __name__ == "__main__":
    main()
