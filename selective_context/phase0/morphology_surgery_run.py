"""Morphology-guided candidate/construction late-block pilot.

This is a deliberately small causal follow-up to morphology_pilot.py.  It
uses three already-audited fixed-ten questions representing oscillatory,
repair/checking, and linear traces.  The two new conditions mask only the
audited candidate occurrences (Mask-C) or construction evidence
(Mask-D).  Existing R2, R0, R3, R4, and L_E_v1 records remain the reference
conditions; this runner does not regenerate them.
"""
import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from selective_context.schema import AccessMode, SelectiveContextRequest
from selective_context.prompting import load_request_bundle, persist_request_bundle
from selective_context.multi_region import compile_regions
from selective_context.phase0.multi_late import source, sanity
from selective_context.phase0.real_smoke import append, evaluate, save
from selective_context.phase0.thinking_pilot import rows_from, generation_budget, extract_final_draft
from selective_context.hf_backend import SelectiveHFBackend


MODEL = "/data2/huangrj/models/qwen3-8b"
SEEDS = [2027, 12027, 22027, 32027]
IDS = ["71", "804", "1189"]
CONDITIONS = ["MASK_C", "MASK_D"]
ANNOTATIONS = "docs/quick_validation/ten_validity_annotations_v1_20260915.json"


def shifted_items(encoded, annotation, key):
    ds, _ = encoded.draft_character_span
    return [dict(item, character_span=[ds + item["draft_span"][0], ds + item["draft_span"][1]])
            for item in annotation[key]]


def interval_overlap(left, right):
    total = 0
    for a, b in left:
        for c, d in right:
            total += max(0, min(b, d) - max(a, c))
    return total


def compile_masks(tokenizer, encoded, annotation):
    candidate = compile_regions(tokenizer, encoded,
                                shifted_items(encoded, annotation, "candidate_occurrences"))
    construction = compile_regions(tokenizer, encoded,
                                   shifted_items(encoded, annotation, "construction_evidence"))
    candidate_chars = [(x["character_span"][0], x["character_span"][1])
                       for x in shifted_items(encoded, annotation, "candidate_occurrences")]
    construction_chars = [(x["character_span"][0], x["character_span"][1])
                          for x in shifted_items(encoded, annotation, "construction_evidence")]
    return {
        "MASK_C": candidate,
        "MASK_D": construction,
        "audit": {
            "candidate_character_tokens": candidate["token_count"],
            "construction_character_tokens": construction["token_count"],
            "candidate_construction_character_overlap": interval_overlap(candidate_chars, construction_chars),
            "candidate_spans": candidate["spans"],
            "construction_spans": construction["spans"],
        },
    }


def prepare(root, tokenizer):
    annotation = json.loads((root / ANNOTATIONS).read_text(encoding="utf-8"))
    jobs = []
    coverage = {}
    for seed in SEEDS:
        for pid in IDS:
            a = annotation["questions"][pid]
            run = source(root, pid, seed)
            encoded, requests = load_request_bundle(run / "bundles" / f"{pid}.r2_r4.json")
            ref = next(r for r in requests if r.condition_id == "R2")
            ds, de = encoded.draft_character_span
            assert encoded.text[ds:de] == a["draft"], pid
            config = json.loads((run / "config.json").read_text())
            assert [config[k] for k in ["temperature", "top_p", "top_k", "context_size"]] == [.6, .95, 20, 32768]
            masks = compile_masks(tokenizer, encoded, a)
            if pid not in coverage:
                coverage[pid] = masks
            else:
                assert coverage[pid] == masks
            row = json.loads((run / "pairs" / f"{pid}.json").read_text())
            assert row["traj1"] == a["draft"]
            refs = [r for r in rows_from(run / "results.jsonl") if r["id"] == pid
                    and r["init_response_generations_metadata"]["intervention"]["condition_id"] in ["R0", "R2", "R3", "R4"]]
            assert len(refs) == 4
            r2_record = next(r for r in refs if r["init_response_generations_metadata"]["intervention"]["condition_id"] == "R2")
            assert SelectiveContextRequest.from_dict(r2_record["init_response_generations_metadata"]["intervention"]) == ref
            for condition in CONDITIONS:
                req = replace(ref, condition_id=condition, access_mode=AccessMode.LATE_BLOCK,
                              mask_token_spans=masks[condition]["spans"], path_block_units=())
                req.validate()
                assert req.input_ids == ref.input_ids and req.sample_seed == ref.sample_seed
                jobs.append((seed, pid, row, encoded, req, refs, masks[condition],
                             str(run.relative_to(root)), r2_record["generated_token_ids"][0]))
    assert len(jobs) == len(SEEDS) * len(IDS) * len(CONDITIONS)
    return annotation, coverage, jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
    annotation, coverage, jobs = prepare(root, tokenizer)
    save(args.output.parent / (args.output.name + "-preflight.json"), coverage)
    print(f"MORPHOLOGY_PREFLIGHT_PASSED {len(jobs)} jobs; 3 strata x 2 masks x 4 seeds", flush=True)
    for pid in IDS:
        print(json.dumps({"id": pid, "audit": coverage[pid]["audit"]}), flush=True)
    if args.preflight_only:
        return
    if args.output.exists():
        raise ValueError("Output exists; refusing overwrite")
    args.output.mkdir(parents=True)
    save(args.output / "annotations.json", annotation)
    save(args.output / "coverage.json", coverage)
    save(args.output / "config.json", dict(
        model=MODEL, ids=IDS, seed_bases=SEEDS, conditions=CONDITIONS,
        total_jobs=len(jobs), new_generations=len(jobs), temperature=.6,
        top_p=.95, top_k=20, context_size=32768, enable_thinking=True,
        backend="hf_eager_bfloat16", sampling_dtype="float32",
        first_token="full_prefill_logits; must equal paired R2",
        comparison="MASK_C/MASK_D minus R2, with existing L_E_v1 joined in analysis",
        scope="three fixed-ten audited questions; morphology-guided causal pilot",
        mask_C="candidate_occurrences",
        mask_D="construction_evidence; overlap with candidate spans audited in coverage.json",
        malformed_or_long_loop_excluded=True,
    ))
    manifest = []
    for seed, pid, row, encoded, req, refs, region, source_run, first in jobs:
        dest = args.output / f"seed-{seed}"
        dest.mkdir(exist_ok=True)
        persist_request_bundle(dest / "bundles" / f"{pid}.{req.condition_id}.json", encoded, [req])
        for ref_record in refs:
            append(dest / "references.jsonl", ref_record)
        manifest.append(dict(id=pid, seed_base=seed, sample_seed=req.sample_seed,
                             condition=req.condition_id, source_run=source_run,
                             reference_condition="R2", record_file=f"seed-{seed}/results.jsonl"))
    save(args.output / "manifest.json", manifest)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL, local_files_only=True, torch_dtype=torch.bfloat16,
        attn_implementation="eager", device_map="cuda:0")
    backend = SelectiveHFBackend(model, tokenizer)
    checks = {}
    for seed, pid, row, encoded, req, refs, region, source_run, first in jobs:
        key = f"{pid}/{req.condition_id}"
        if key not in checks:
            checks[key] = sanity(model, req)
    save(args.output / "decode_sanity.json", checks)
    print(f"MORPHOLOGY_ATTENTION_PASSED {len(checks)} conditions; all layers", flush=True)

    for number, (seed, pid, row, encoded, req, refs, region, source_run, first) in enumerate(jobs, 1):
        started = time.monotonic()
        print(json.dumps(dict(event="generation_start", number=number, total=len(jobs),
                              id=pid, condition=req.condition_id, seed_base=seed)), flush=True)

        def progress(tokens):
            print(json.dumps(dict(event="progress", number=number, tokens=tokens,
                                  seconds=round(time.monotonic() - started, 1))), flush=True)

        budget = generation_budget(len(req.input_ids))
        result = backend.generate(req, max_new_tokens=budget, temperature=.6,
                                  top_p=.95, top_k=20, progress_callback=progress)
        assert result.generated_token_ids[0] == first, "Late first token differs from paired R2"
        record = evaluate(row, encoded, req, result)
        final, status = extract_final_draft(result.text, encoded.text, tokenizer.eos_token)
        record["init_response_generations_metadata"].update(
            enable_thinking=True, model_config_alias="Qwen3_8B_Thinking")
        record.update(final_response=final, thinking_status=status,
                      generation_seconds=time.monotonic() - started,
                      max_new_tokens=budget, seed_base=seed, region_annotation=region)
        append(args.output / f"seed-{seed}" / "results.jsonl", record)
        item = record["init_response_generations"][0]
        print(json.dumps(dict(event="generation_finish", number=number, total=len(jobs),
                              id=pid, condition=req.condition_id,
                              correct=item["correctness"], finish=result.finish_reason,
                              seconds=round(record["generation_seconds"], 1))), flush=True)
    print("MORPHOLOGY_SURGERY_FINISHED", flush=True)


if __name__ == "__main__":
    main()
