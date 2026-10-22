"""Frozen feedback-polarity intervention on natural Game24 continuations, not a new CD formula."""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression, score_response
from run_identity_prospective_20261011 import repair_prompt
from selective_context.tasks import extract_math_box

SUBDIR = "feedback_decoding"
SEED = 20261022
CONDITIONS = ("FULL_TRUE", "FULL_FALSE", "GUIDED_TRUE", "GUIDED_FALSE")


def feedback_pair(q, history, truthful):
    actual = "INCORRECT" if history == "BAD" else "CORRECT"
    opposite = "CORRECT" if history == "BAD" else "INCORRECT"
    labels = (actual, opposite) if truthful else (opposite, actual)
    return [repair_prompt(q, dict(usable=True, feedback=label, draft=q["histories"][history]["draft"]),
                          "COUNT_HISTORY") for label in labels]


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = output / "candidate_adoption"
    m0 = load(source / "manifest.json")
    raw = {(r["id"], r["phase"], r["condition"], r["seed"]): (line, r)
           for line, r in enumerate(rows(source / "generations.jsonl"), 1)}
    scores = {(r["id"], r["phase"], r["condition"], r["seed"]): r
              for r in rows(source / "behaviour.jsonl")}
    rng = random.Random(SEED)
    qs = []
    # The FIRST 12 in the previously frozen shuffled order. No intervention outcome selection.
    for original in m0["questions"][:12]:
        q = dict(original)
        if audit_expression(q["old_expression"], q["answer"]).get("correct"):
            raise ValueError("Expected a verified natural failed history")
        q["histories"] = dict(BAD=dict(draft=q["draft"], source=q["source"], source_line=q["source_line"]))
        q["good_missing"] = True
        for seed in sorted(m0["seeds"]):
            key = q["id"], "NATURAL", "COUNT_CLEAN", seed
            if key not in raw or not scores.get(key, {}).get("correct"):
                continue
            line, r = raw[key]
            final = r["text"].rsplit("</think>", 1)[1].strip()
            for stop in ("<|im_end|>", "<|endoftext|>"):
                final = final.removesuffix(stop).rstrip()
            if not audit_expression(extract_math_box(final), q["answer"]).get("correct"):
                raise ValueError("Correct history failed exact recheck")
            q["histories"]["GOOD"] = dict(draft=final, source=str((source / "generations.jsonl").relative_to(ROOT)),
                source_line=line, source_seed=seed, source_condition="COUNT_CLEAN", source_phase="NATURAL")
            q["good_missing"] = False
            break
        q["history_order"] = rng.sample(list(q["histories"]), len(q["histories"]))
        q["condition_order"] = rng.sample(list(CONDITIONS), len(CONDITIONS))
        qs.append(q)
    planned = sum(len(q["histories"])*len(CONDITIONS) for q in qs)
    m = dict(model=m0["model"], dtype="bfloat16", backend="hf_sdpa_paired_feedback", seeds=[SEED],
        sampling=m0["sampling"], max_new_tokens=8192, strength=1.0, conditions=list(CONDITIONS),
        questions=qs, planned_requests=planned, max_requests_per_batch=4,
        selection="First 12 questions of the existing 30-question shuffled manifest; keep missing GOOD histories, never replace questions. First verified COUNT_CLEAN final draft by historical seed order.",
        primary="BAD history GUIDED_TRUE minus FULL_TRUE accuracy; GOOD history same contrast separately. Reverse-feedback gain contrast distinguishes polarity-sensitive change from polarity-insensitive decoding effects.",
        diagnostic="Within each history: (GUIDED_TRUE-FULL_TRUE)-(GUIDED_FALSE-FULL_FALSE). FALSE conditions deliberately provide incorrect verifier status; these are experimental controls, not deployed feedback.",
        limits="Known ID/CFG formula, oracle binary draft status, reused questions, one seed, exploratory MVP. A gain is not evidence of accurate error diagnosis, neural state reset or a new decoding algorithm. GOOD availability is selected on past clean success.",
        estimate=dict(selected_tokens_per_second=50, loading_seconds=300,
                      maximum_gpu_seconds=planned*8192/50+300),
        stop="One frozen batch, original shared 24 GPU-hour cap. No retries, coefficient sweeps, new failures or automatic expansion. Length stops remain incorrect in denominator.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", completed=0, planned=planned))
    return m


def summarize(m, out, status=None, error=None):
    data = {(r["id"], r["history"], r["condition"]): r for r in rows(out / "behaviour.jsonl")}
    counts, effects = {}, {}
    for history in ("BAD", "GOOD"):
        qs = [q for q in m["questions"] if history in q["histories"]]
        counts[history] = {}
        for c in CONDITIONS:
            rs = [data[q["id"], history, c] for q in qs if (q["id"], history, c) in data]
            counts[history][c] = dict(completed=len(rs), planned=len(qs), correct=sum(r["correct"] for r in rs),
                length_stops=sum(r["finish_reason"] == "length" for r in rs),
                old_reuse=sum(bool(r.get("structural_reuse")) for r in rs),
                tokens=sum(r["generated_tokens"] for r in rs))
        paired = [q for q in qs if all((q["id"], history, c) in data for c in CONDITIONS)]
        per = []
        for q in paired:
            values = {c: int(data[q["id"], history, c]["correct"]) for c in CONDITIONS}
            true = values["GUIDED_TRUE"] - values["FULL_TRUE"]
            false = values["GUIDED_FALSE"] - values["FULL_FALSE"]
            per.append(dict(id=q["id"], **values, true_gain=true, false_gain=false, polarity_interaction=true-false))
        effects[history] = dict(paired_questions=len(per), per_question=per,
            true_gain=bootstrap([r["true_gain"] for r in per]) if per else None,
            false_gain=bootstrap([r["false_gain"] for r in per]) if per else None,
            polarity_interaction=bootstrap([r["polarity_interaction"] for r in per]) if per else None)
    result = dict(status=status, error=error, completed=len(data), planned=m["planned_requests"],
        counts=counts, effects=effects, good_missing=[q["id"] for q in m["questions"] if q["good_missing"]],
        interpretation="Exploratory question-level effects; GOOD/BAD cohorts have different availability. Do not pool their accuracy as a single utility score or equate non-significant GOOD loss with no harm.")
    save(out / "summary.json", result)
    return result


def run(output, m):
    if os.environ.get("SC_FEEDBACK_DECODING_LAUNCHER") != "1":
        raise RuntimeError("Use shared GPU4 launcher")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
    from selective_context.feedback_decoding import generate_batch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("Single A100 required")
    prior = load(output / "budget.json")
    if prior.get("active"):
        raise RuntimeError("Shared budget already active")
    out = output / SUBDIR
    raw = {(r["id"], r["history"], r["condition"]): r for r in rows(out / "generations.jsonl")}
    scored = {(r["id"], r["history"], r["condition"]) for r in rows(out / "behaviour.jsonl")}
    qs = {q["id"]: q for q in m["questions"]}
    needed = (m["planned_requests"]-len(raw))*m["max_new_tokens"]/m["estimate"]["selected_tokens_per_second"] + 300
    if needed > prior["limit_seconds"] - prior["gpu_seconds"]:
        raise RuntimeError("Frozen maximum estimate exceeds remaining budget")
    tokenizer = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
    requests = []
    for q in m["questions"]:
        for h in q["history_order"]:
            for c in q["condition_order"]:
                prompts = feedback_pair(q, h, c.endswith("_TRUE"))
                ids = [tokenizer.apply_chat_template([dict(role="user", content=p)], tokenize=True,
                       add_generation_prompt=True, enable_thinking=True) for p in prompts]
                if max(map(len, ids)) + m["max_new_tokens"] > 32768:
                    raise ValueError("Frozen prompt exceeds context allowance")
                requests.append(dict(id=q["id"], history=h, condition=c, seed=SEED, prompts=prompts,
                    prompt_ids=ids, strength=m["strength"] if c.startswith("GUIDED") else 0.0,
                    source=q["histories"][h]["source"], source_line=q["histories"][h]["source_line"]))
    save(out / "requests.json", requests)
    def persist_score(r):
        key = r["id"], r["history"], r["condition"]
        if key not in scored:
            append(out / "behaviour.jsonl", dict(id=r["id"], history=r["history"], condition=r["condition"],
                seed=r["seed"], **score_response(r["text"], qs[r["id"]], "COUNT_HISTORY"),
                generated_tokens=r["generated_tokens"], finish_reason=r["finish_reason"]))
            scored.add(key)
    for r in raw.values():
        persist_score(r)
    budget = Budget(output / "budget.json", 24)
    status, error = "completed", None
    current = []
    begun = time.monotonic()
    def state(step=None):
        save(out / "run_state.json", dict(status="running", completed=len(raw), planned=m["planned_requests"],
            elapsed_seconds=time.monotonic()-begun, active=[{k:r[k] for k in ("id","history","condition")} for r in current],
            batch_decode_steps=step))
    try:
        save(out / "run_state.json", dict(status="loading_model", completed=len(raw), planned=m["planned_requests"]))
        model = AutoModelForCausalLM.from_pretrained(m["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda:0").eval()
        eos = GenerationConfig.from_pretrained(m["model"], local_files_only=True).eos_token_id
        eos = {eos} if isinstance(eos, int) else set(eos)
        todo = [r for r in requests if (r["id"],r["history"],r["condition"]) not in raw]
        def finish(r, tokens, reason, seconds):
            record = dict(r, text=tokenizer.decode(tokens, skip_special_tokens=False), token_ids=list(tokens),
                generated_tokens=len(tokens), finish_reason=reason, batch_wall_seconds=seconds,
                model=m["model"], dtype=m["dtype"], backend=m["backend"], sampling=m["sampling"],
                max_new_tokens=m["max_new_tokens"])
            append(out / "generations.jsonl", record)
            raw[r["id"],r["history"],r["condition"]] = record
            persist_score(record)
            print(f"{len(raw)}/{m['planned_requests']} {r['id']} {r['history']} {r['condition']} {reason} tokens={len(tokens)}", flush=True)
            state()
        def heartbeat(step, active):
            budget.check()
            if step % 128 == 0:
                state(step)
        for start in range(0, len(todo), m["max_requests_per_batch"]):
            current = todo[start:start+m["max_requests_per_batch"]]
            state(0)
            generate_batch(model, tokenizer, current, max_new_tokens=m["max_new_tokens"], sampling=m["sampling"],
                eos_ids=eos, on_finish=finish, heartbeat=heartbeat)
            budget.check(force=True)
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed", repr(exc)
        raise
    finally:
        budget.close()
        summary = summarize(m, out, status, error)
        save(out / "run_state.json", dict(status=status, error=error, completed=summary["completed"], planned=m["planned_requests"]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--status", action="store_true")
    a = p.parse_args()
    m = prepare(a.output)
    if a.resume:
        run(a.output, m)
    elif a.status:
        print(json.dumps(load(a.output/SUBDIR/"run_state.json"), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(dict(planned=m["planned_requests"], good_missing=[q["id"] for q in m["questions"] if q["good_missing"]],
                             estimate=m["estimate"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
