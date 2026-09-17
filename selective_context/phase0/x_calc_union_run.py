"""Fourth cell of the R2/X/CALC/X+CALC development matrix.

Reuses the frozen six-question R2 inputs and the historical M_X (complete
candidate-copy) requests, then unions the exact M_X mask with the audited
CALC spans.  Only the union condition is generated here; R2, X, and CALC are
reused for analysis.
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
ANN = "docs/quick_validation/calculation_role_annotations_v1_20260916.json"
X_ROOT = "outputs/game24-qwen3-mx-late-path-20260913"


def shifted(encoded, annotation, key):
    ds, _ = encoded.draft_character_span
    return [dict(item, character_span=[ds + item["draft_span"][0], ds + item["draft_span"][1]])
            for item in annotation[key]]


def merge_spans(spans):
    merged = []
    for lo, hi in sorted((int(lo), int(hi)) for lo, hi in spans):
        if not merged or lo > merged[-1][1]:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    return tuple((lo, hi) for lo, hi in merged)


def prepare(root, tokenizer):
    annotation = json.loads((root / ANN).read_text(encoding="utf-8"))
    jobs = []
    coverage = {}
    for seed in SEEDS:
        xfile = root / X_ROOT / f"seed-{seed}" / "results.jsonl"
        xrows = [r for r in rows_from(xfile)
                 if r["init_response_generations_metadata"]["intervention"]["condition_id"] == "M_X"]
        xbyid = {str(r["id"]): r for r in xrows}
        for pid, ann in annotation["questions"].items():
            src = source(root, pid, seed)
            encoded, requests = load_request_bundle(src / "bundles" / f"{pid}.r2_r4.json")
            ref = next(r for r in requests if r.condition_id == "R2")
            ds, de = encoded.draft_character_span
            assert encoded.text[ds:de] == ann["draft"], pid
            cfg = json.loads((src / "config.json").read_text())
            assert [cfg[k] for k in ["temperature", "top_p", "top_k", "context_size"]] == [.6, .95, 20, 32768]
            xrecord = xbyid[pid]
            xreq = SelectiveContextRequest.from_dict(xrecord["init_response_generations_metadata"]["intervention"])
            assert xreq.input_ids == ref.input_ids and xreq.sample_seed == ref.sample_seed
            assert xreq.access_mode == AccessMode.LATE_BLOCK and not xreq.path_block_units
            calc = compile_regions(tokenizer, encoded, shifted(encoded, ann, "CALC"))
            candidates = compile_regions(tokenizer, encoded, shifted(encoded, ann, "candidate_occurrences"))
            # M_X is the historical complete-candidate request; this equality
            # prevents silently changing the X cell while forming the union.
            assert tuple(xreq.mask_token_spans) == tuple(candidates["spans"]), pid
            union = merge_spans(tuple(xreq.mask_token_spans) + tuple(calc["spans"]))
            req = replace(ref, condition_id="L_XCALC_v1", access_mode=AccessMode.LATE_BLOCK,
                          mask_token_spans=union, path_block_units=())
            req.validate()
            assert req.input_ids == ref.input_ids and req.sample_seed == ref.sample_seed
            refs = [r for r in rows_from(src / "results.jsonl") if r["id"] == pid
                    and r["init_response_generations_metadata"]["intervention"]["condition_id"] in ["R0", "R2", "R3", "R4"]]
            assert len(refs) == 4
            r2 = next(r for r in refs if r["init_response_generations_metadata"]["intervention"]["condition_id"] == "R2")
            assert SelectiveContextRequest.from_dict(r2["init_response_generations_metadata"]["intervention"]) == ref
            row = json.loads((src / "pairs" / f"{pid}.json").read_text())
            assert row["traj1"] == ann["draft"]
            record = dict(
                x_span_count=len(xreq.mask_token_spans), calc_span_count=len(calc["spans"]),
                union_span_count=len(union),
                x_tokens=sum(hi - lo for lo, hi in xreq.mask_token_spans),
                calc_tokens=sum(hi - lo for lo, hi in calc["spans"]),
                union_tokens=sum(hi - lo for lo, hi in union),
                x_spans=xreq.mask_token_spans,
                calc_spans=calc["spans"], union_spans=union,
                candidate_character_items=len(ann["candidate_occurrences"]),
                calc_character_items=len(ann["CALC"]),
            )
            if pid in coverage:
                assert coverage[pid] == record
            else:
                coverage[pid] = record
            jobs.append(dict(seed=seed, id=pid, row=row, enc=encoded, req=req, refs=refs,
                             xrecord=xrecord, source=str(src.relative_to(root)),
                             first=r2["generated_token_ids"][0], x_spans=xreq.mask_token_spans,
                             calc_spans=calc["spans"]))
    assert len(jobs) == 24
    return annotation, coverage, jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
    annotation, coverage, jobs = prepare(root, tokenizer)
    save(args.output.parent / (args.output.name + "-preflight.json"),
         dict(coverage=coverage, total=24, new=24, reused=0))
    print("X_CALC_PREFLIGHT_PASSED 24 requests; union of exact M_X and CALC; no reuse", flush=True)
    for pid, info in coverage.items():
        print(json.dumps(dict(id=pid, **info)), flush=True)
    if args.preflight_only:
        return
    if args.output.exists():
        raise ValueError("Output exists; refusing overwrite")
    args.output.mkdir(parents=True)
    save(args.output / "annotations.json", annotation)
    save(args.output / "coverage.json", coverage)
    save(args.output / "config.json", dict(
        ids=list(annotation["questions"]), seed_bases=SEEDS, new_generations=24,
        model=MODEL, condition="L_XCALC_v1", base_conditions=["R2", "M_X", "L_CALC_v1"],
        temperature=.6, top_p=.95, top_k=20, context_size=32768,
        enable_thinking=True, backend="hf_eager_bfloat16", sampling_dtype="float32",
        access_mode="late_block", first_token="full_prefill_logits",
        scope="six-question R2/X/CALC/X+CALC development interaction cell",
        primary="L_XCALC_v1 minus M_X; paired accuracy, formula reuse, and candidate selection",
        limitation="union adds tokens beyond M_X; matched neutral control remains pending",
    ))
    manifest = []
    for job in jobs:
        dest = args.output / f"seed-{job['seed']}"
        dest.mkdir(exist_ok=True)
        persist_request_bundle(dest / "bundles" / f"{job['id']}.L_XCALC_v1.json", job["enc"], [job["req"]])
        for ref in job["refs"]:
            append(dest / "references.jsonl", ref)
        append(dest / "x_results.jsonl", job["xrecord"])
        manifest.append(dict(id=job["id"], seed_base=job["seed"], sample_seed=job["req"].sample_seed,
                             source=job["source"], condition="L_XCALC_v1",
                             x_condition="M_X", calc_condition="L_CALC_v1"))
    save(args.output / "manifest.json", manifest)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, local_files_only=True, torch_dtype=torch.bfloat16,
        attn_implementation="eager", device_map="cuda:0")
    backend = SelectiveHFBackend(model, tokenizer)
    checks = {}
    for job in jobs:
        if job["id"] not in checks:
            checks[job["id"]] = sanity(model, job["req"])
    save(args.output / "decode_sanity.json", checks)
    print("X_CALC_ATTENTION_PASSED 6 unique union masks; all layers", flush=True)
    for number, job in enumerate(jobs, 1):
        started = time.monotonic()
        print(json.dumps(dict(event="generation_start", number=number, total=24,
                              id=job["id"], seed_base=job["seed"])), flush=True)

        def progress(tokens):
            print(json.dumps(dict(event="progress", number=number, tokens=tokens,
                                  seconds=round(time.monotonic() - started, 1))), flush=True)

        budget = generation_budget(len(job["req"].input_ids))
        result = backend.generate(job["req"], max_new_tokens=budget, temperature=.6,
                                  top_p=.95, top_k=20, progress_callback=progress)
        assert result.generated_token_ids[0] == job["first"]
        record = evaluate(job["row"], job["enc"], job["req"], result)
        final, status = extract_final_draft(result.text, job["enc"].text, tokenizer.eos_token)
        record["init_response_generations_metadata"].update(
            enable_thinking=True, model_config_alias="Qwen3_8B_Thinking")
        record.update(final_response=final, thinking_status=status,
                      generation_seconds=time.monotonic() - started,
                      max_new_tokens=budget, seed_base=job["seed"],
                      region_annotation={"x": job["x_spans"], "calc": job["calc_spans"],
                                         "union": job["req"].mask_token_spans})
        append(args.output / f"seed-{job['seed']}" / "results.jsonl", record)
        print(json.dumps(dict(event="generation_finish", number=number, total=24,
                              id=job["id"], seed_base=job["seed"],
                              correct=record["init_response_generations"][0]["correctness"],
                              finish=result.finish_reason,
                              seconds=round(record["generation_seconds"], 1))), flush=True)
    print("X_CALC_FINISHED", flush=True)


if __name__ == "__main__":
    main()
