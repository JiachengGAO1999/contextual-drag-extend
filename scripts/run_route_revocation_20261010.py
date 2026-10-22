"""CPU prepare/status/analyse, or explicit A100 resume via the shared launcher."""
from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from selective_context.route_revocation_data import CONDITIONS, SEED, analyse, audit_materials, build_materials


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]


def collect_exclusions():
    seen, sources = set(), []
    def visit(obj):
        if isinstance(obj, dict):
            numbers = obj.get("answer", obj.get("numbers"))
            if (isinstance(numbers, list) and len(numbers) == 4 and
                    all(type(x) is int and 1 <= x <= 13 for x in numbers)):
                seen.add(tuple(sorted(numbers)))
            for key, value in obj.items():
                if isinstance(value, (list, dict)) and key not in ("input_ids", "generated_token_ids", "tokens"):
                    visit(value)
        elif isinstance(obj, list):
            for value in obj:
                if isinstance(value, (dict, list)): visit(value)
    for directory in ("runs", "outputs"):
        for path in sorted((ROOT/directory).rglob("*")):
            if not path.is_file() or not (path.name in ("manifest.json", "results.jsonl", "draft_candidates.json")
                                         or "draft_candidates" in path.name and path.suffix == ".jsonl"):
                continue
            if "route_revocation" in path.parts: continue
            before = len(seen)
            with path.open(encoding="utf8") as handle:
                if path.suffix == ".jsonl":
                    for line in handle:
                        if line.strip(): visit(json.loads(line))
                else: visit(json.load(handle))
            sources.append(dict(path=path.relative_to(ROOT).as_posix(), newly_seen=len(seen)-before))
    return dict(combinations=sorted(seen), sources=sources,
                scope="Recorded local runs/outputs manifests, results and draft candidates; pretraining exposure is unknown.")


def prepare(output, model, tokenizer_path=None):
    out = output/"route_revocation"
    out.mkdir(parents=True, exist_ok=True)
    if (out/"manifest.json").exists(): return load(out/"manifest.json")
    exclusions = load(out/"exclusions.json")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path or model, local_files_only=True)
    questions, skips = build_materials(tokenizer, exclusions["combinations"])
    save(out/"material_audit.json", audit_materials(tokenizer, questions, exclusions["combinations"]))
    orders = list(itertools.permutations(CONDITIONS))
    manifest = dict(model=model, dtype="bfloat16", attention="sdpa", seed=SEED, gpu_hours=24,
        questions=questions, planned_questions=32, actual_questions=len(questions),
        planned_score_units=len(questions)*12, gpu_started=False,
        material_selection="Seed-shuffled 1..13 four-number multisets; exclude recorded prior combinations; exact-arithmetic and equal-token-position eligibility only; no model/effect screening.",
        exclusions_source="exclusions.json", excluded_combinations=len(exclusions["combinations"]),
        eligibility_skips=skips, conditions=list(CONDITIONS),
        condition_orders={q["id"]: list(orders[i % 6]) for i, q in enumerate(questions)},
        history_orders={q["id"]: (["A", "B"] if i % 2 == 0 else ["B", "A"]) for i, q in enumerate(questions)},
        primary="Per-question, averaged over A/B: REBUILD_BLOCKED minus LATE_BLOCK in log P(legal expression) minus log P(old expression).",
        secondary=["Length-normalized primary", "Post-feedback reject-minus-endorse judgment", "History A/B identity interaction", "LATE_BLOCK minus FULL adoption"],
        analysis="5000 paired question bootstrap draws, seed 20261010; require both histories/all conditions for a question contrast; retain all missing; no token/history pseudo-replication.",
        cutoff="The LAST fixed critique query is blocked in LATE_BLOCK and REBUILD_BLOCKED; all readout-stem and candidate queries are then blocked. FULL retains normal access. REBUILD uses existing whole-draft R4 from draft_end onward.",
        provenance="Synthetic wrong expressions with true external feedback and forced critique; does not establish spontaneous error recognition.",
        identity_acceptance="REBUILD A/B scores must coincide because input tokens outside equal-position blocked D coincide. Zero identity here is structurally guaranteed, not empirical novelty.",
        implementation="Existing masks.py LATE_BLOCK threshold=decision cutoff; PATH_BLOCK is existing whole-draft R4. No new head search or attention hook.",
        budget="Shared original budget.json, 24 GPU hours including loading and A100 acceptance; no new allowance. Stop with missing rows on exhaustion; no retries/automatic expansion.",
        pilot="Fixed first two questions also form the first engineering timing samples. Keep all 32 frozen; stop at shared budget rather than selecting coverage after effects.",
        bridge="Separate future decision only; no free generation is implemented or queued by this entrypoint.")
    save(out/"manifest.json", manifest)
    lines = ["# Controlled route-revocation materials", "", "CPU arithmetic/tokenization only; no model outcomes.", "",
             "| ID | Numbers | Wrong A | Wrong B | Legal candidate | Prefix tokens |", "|---|---|---|---|---|---|"]
    for q in questions:
        a, b = q["histories"]["A"], q["histories"]["B"]
        lines.append(f"| {q['id']} | {q['numbers']} | `{a['route']['expression']}` | `{b['route']['expression']}` | `{q['legal']}` | {len(a['input_ids'])} |")
    save(out/"preparation.json", dict(status="cpu_prepared_gpu_not_started", questions=len(questions),
         requested_questions=32, score_units=len(questions)*12, exclusions=len(exclusions["combinations"]),
         skips=len(skips), pending=["Server deployment", "A100 acceptance", "First-two-question timing", "Main score batch"],
         gpu_model_calls=0))
    (out/"materials.md").write_text("\n".join(lines)+"\n", encoding="utf8")
    return manifest


def run(output, manifest):
    import torch
    from transformers import AutoModelForCausalLM
    from selective_context.route_revocation import RouteRevocationBackend
    out = output/"route_revocation"
    if os.environ.get("SC_ROUTE_LAUNCHER") != "1":
        raise RuntimeError("GPU execution requires --route-revocation on the shared launcher")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Exactly one visible A100 is required")
    if load(output/"budget.json").get("active"):
        raise RuntimeError("Shared budget is active; do not start another batch")
    budget = Budget(output/"budget.json", 24)
    started = time.monotonic()
    try:
        if not (out/"acceptance.json").exists():
            subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/selective_context/test_route_revocation.py"],
                           cwd=ROOT, check=True)
            save(out/"acceptance.json", dict(status="passed_on_a100", gpu_seconds=time.monotonic()-started))
        budget.check(force=True)
        model = AutoModelForCausalLM.from_pretrained(manifest["model"], local_files_only=True,
                    torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0")
        backend = RouteRevocationBackend(model, budget.check)
        done = {(r["id"], r["history"], r["condition"], r["outcome"]) for r in rows(out/"scores.jsonl")}
        save(out/"run_state.json", dict(status="running", model_loaded_seconds=time.monotonic()-started))
        for qi, q in enumerate(manifest["questions"]):
            question_started = time.monotonic()
            early_reference = None
            for h in manifest["history_orders"][q["id"]]:
                history = q["histories"][h]
                if qi >= 2 and all((q["id"], h, c, o) in done for c in CONDITIONS for o in q["readouts"]): continue
                t0 = time.monotonic()
                states = backend.prefill_pair(history)
                prefill_seconds = time.monotonic()-t0
                if qi < 2:
                    early_logits = states["REBUILD_BLOCKED"].logits.detach().clone()
                    if early_reference is None:
                        early_reference = early_logits
                    else:
                        difference = float((early_logits.float()-early_reference.float()).abs().max())
                        append(out/"model_acceptance.jsonl", dict(id=q["id"],
                            early_AB_logit_max_difference=difference, expected="same outside blocked D"))
                        if not torch.isfinite(early_logits).all() or difference > 1e-5:
                            raise RuntimeError("Real-model early-block A/B invariance failed; stop before proceeding")
                for c in manifest["condition_orders"][q["id"]]:
                    for outcome, readout in q["readouts"].items():
                        key = (q["id"], h, c, outcome)
                        if key in done: continue
                        save(out/"current_request.json", dict(id=q["id"], history=h, condition=c, outcome=outcome))
                        t0 = time.monotonic()
                        scores = backend.score(states[c], history, c, readout)
                        append(out/"scores.jsonl", dict(id=q["id"], history=h, condition=c, outcome=outcome,
                            model=manifest["model"], dtype="bfloat16", scores=scores,
                            cutoff=history["cutoff"], draft_token_span=history["draft_token_span"],
                            source="manifest.json", gpu_seconds=time.monotonic()-t0))
                        done.add(key)
                        budget.check(force=True)
                        print(f"route_revocation {len(done)}/{manifest['planned_score_units']} {key}", flush=True)
                del states
                append(out/"timings.jsonl", dict(id=q["id"], history=h, shared_prefill_seconds=prefill_seconds))
            append(out/"timings.jsonl", dict(id=q["id"], question_seconds=time.monotonic()-question_started))
            if qi == 1:
                save(out/"engineering_timing.json", dict(status="first_two_completed", frozen_questions=len(manifest["questions"]),
                      elapsed_including_loading_seconds=time.monotonic()-started,
                      note="Timing only; does not select questions/components or automatically expand."))
        save(out/"run_state.json", dict(status="completed", completed_score_units=len(done)))
    except BudgetExceeded:
        save(out/"run_state.json", dict(status="budget_exhausted", completed_score_units=len(rows(out/"scores.jsonl"))))
    except Exception as exc:
        save(out/"run_state.json", dict(status="failed_no_automatic_retry", error=repr(exc)))
        raise
    finally:
        budget.close()
        if (out/"run_state.json").exists() and load(out/"run_state.json")["status"] == "failed_no_automatic_retry":
            save(out/"summary.json", dict(status="failed_not_interpreted", completed_score_units=len(rows(out/"scores.jsonl")),
                                        note="Inspect run_state.json before interpreting any partial scores."))
        else:
            save(out/"summary.json", analyse(manifest["questions"], rows(out/"scores.jsonl")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--model", default="/data2/huangrj/models/qwen3-8b")
    parser.add_argument("--tokenizer", default=None, help="CPU-only local copy of the model's tokenizer")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--collect-exclusions", action="store_true")
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--status", action="store_true")
    action.add_argument("--analyse", action="store_true")
    action.add_argument("--audit-materials", action="store_true")
    action.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    out = args.output/"route_revocation"
    if args.collect_exclusions:
        data = collect_exclusions(); save(out/"exclusions.json", data)
        print(json.dumps(dict(prior_combinations=len(data["combinations"]), source_files=len(data["sources"]))))
        return
    if args.prepare:
        m = prepare(args.output, args.model, args.tokenizer)
        print(json.dumps(dict(status="cpu_prepared_gpu_not_started", questions=len(m["questions"]), score_units=m["planned_score_units"])))
        return
    if args.status:
        status = dict(completed_score_units=len(rows(out/"scores.jsonl")))
        for name in ("preparation", "run_state", "engineering_timing", "acceptance"):
            if (out/f"{name}.json").exists(): status[name] = load(out/f"{name}.json")
        print(json.dumps(status, indent=2)); return
    manifest = load(out/"manifest.json")
    if args.audit_materials:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer or manifest["model"], local_files_only=True)
        audit = audit_materials(tokenizer, manifest["questions"], load(out/"exclusions.json")["combinations"])
        save(out/"material_audit.json", audit)
        print(json.dumps(dict(status=audit["status"], questions=audit["questions"]))); return
    if args.analyse:
        summary = analyse(manifest["questions"], rows(out/"scores.jsonl"))
        save(out/"summary.json", summary)
        print(json.dumps({k: v for k, v in summary.items() if k not in ("per_question", "effects", "missing")}, indent=2))
        return
    run(args.output, manifest)


if __name__ == "__main__":
    main()
