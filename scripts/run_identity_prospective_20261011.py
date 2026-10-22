"""Frozen new-question history x representation experiment; one A100, no failure screening."""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import Budget, BudgetExceeded, append, save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression, score_response
from selective_context.tasks import independent_prompt, GAME24_SUFFIX

CONDITIONS = ("COUNT_CLEAN", "COUNT_HISTORY", "IDENTITY_CLEAN", "IDENTITY_HISTORY")
MODEL = "/data2/huangrj/models/qwen3-8b"
DESIGN_SEED = 20261011
DRAFT_SEED = 20261014
REPAIR_SEEDS = (20261012, 20261013)
SUBDIR = "identity_prospective"


def solve(numbers):
    """CPU feasibility only. The witness is metadata, never included in any prompt."""
    dead = set()

    def visit(items):
        key = tuple(sorted(v for v, _ in items))
        if key in dead:
            return None
        if len(items) == 1:
            return items[0][1] if items[0][0] == 24 else None
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, at = items[i]
                b, bt = items[j]
                rest = [x for k, x in enumerate(items) if k not in (i, j)]
                variants = [(a+b, f"({at}+{bt})"), (a*b, f"({at}*{bt})"),
                            (a-b, f"({at}-{bt})"), (b-a, f"({bt}-{at})")]
                if b: variants.append((a/b, f"({at}/{bt})"))
                if a: variants.append((b/a, f"({bt}/{at})"))
                for value, expression in variants:
                    found = visit(rest + [(value, expression)])
                    if found: return found
        dead.add(key)
        return None

    return visit([(Fraction(n), str(n)) for n in numbers])


def recorded_numbers(value):
    """Read declared operands, never infer them from generated expressions."""
    if isinstance(value, dict):
        for name in ("answer", "numbers"):
            ns = value.get(name)
            if isinstance(ns, list) and len(ns) == 4 and all(type(n) is int and 1 <= n <= 13 for n in ns):
                yield tuple(sorted(ns))
        for child in value.values():
            yield from recorded_numbers(child)
    elif isinstance(value, list):
        for child in value:
            yield from recorded_numbers(child)


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    excluded, sources = set(), []
    prior_exposure = out / "prior_exposure.json"
    if prior_exposure.exists():
        extra = load(prior_exposure)
        excluded.update(tuple(ns) for ns in extra["number_multisets"])
        sources.append(dict(path=str(prior_exposure.resolve().relative_to(ROOT)),number_multisets=len(extra["number_multisets"])))
    # Include all locally recorded Game24 manifests/configs/pair lists, including baseline-only
    # exposure. This is stronger than excluding just the recent 23+24 intervention items.
    paths = list((ROOT / "outputs").rglob("*manifest*.json"))
    paths += list((ROOT / "outputs").rglob("config.json"))
    paths += list((ROOT / "outputs").rglob("*pairs*.jsonl"))
    for path in sorted(set(paths)):
        if SUBDIR in path.parts or not ("game24" in str(path).lower() or output.name in path.parts):
            continue
        data = rows(path) if path.suffix == ".jsonl" else load(path)
        ns = set(recorded_numbers(data))
        if ns:
            excluded.update(ns)
            sources.append(dict(path=str(path.relative_to(ROOT)), number_multisets=len(ns)))
    candidates = [ns for ns in itertools.combinations_with_replacement(range(1, 14), 4) if ns not in excluded]
    rng = random.Random(DESIGN_SEED)
    rng.shuffle(candidates)
    orders = list(itertools.permutations(CONDITIONS))
    questions = []
    for ns in candidates:
        witness = solve(ns)
        if not witness: continue
        i = len(questions)
        labels = rng.sample(list("ABCD"), 4)
        questions.append(dict(id="new-" + "-".join(map(str, ns)), answer=list(ns),
            problem="Use the numbers " + ", ".join(map(str, ns)) +
                " exactly once each, with addition, subtraction, multiplication, division and parentheses, "
                "to make 24. Provide an expression using the original four numbers.",
            bindings=dict(zip(labels, ns)), condition_order=list(orders[i % len(orders)]),
            cpu_solution_metadata_only=witness))
        if len(questions) == 64: break
    if len(questions) != 64:
        raise RuntimeError("Insufficient unused solvable number multisets; do not silently replace the design")
    m = dict(model=MODEL, dtype="bfloat16", backend="native_vllm_0.11.0", attention="FLASH_ATTN",
        design_seed=DESIGN_SEED, draft_seed=DRAFT_SEED, repair_seeds=list(REPAIR_SEEDS),
        conditions=list(CONDITIONS), questions=questions, excluded_multisets=len(excluded), exclusion_sources=sources,
        excluded_number_multisets=[list(ns) for ns in sorted(excluded)],
        sampling=dict(temperature=.6, top_p=.95, top_k=20), draft_max_new_tokens=16384,
        repair_max_new_tokens=8192, max_model_len=32768, max_num_seqs=8,
        maximum_requests=576, shared_budget_hours=24,
        estimate=dict(max_generated_tokens=5242880, tokens_per_second=350, loading_seconds=300),
        source="Seeded permutation of four-number multisets from 1..13, excluding recorded prior exposure; retain first 64 CPU-solvable. No LM outcome selection.",
        history="One native Thinking numeric initial draft per question; retain its final answer verbatim after removing Thinking and EOS as in prior protocol. Feedback truthful. No final text means missing history, no replacement. Store full raw source trajectory.",
        primary="Question-level interaction (IDENTITY_HISTORY-COUNT_HISTORY)-(IDENTITY_CLEAN-COUNT_CLEAN), averaging two seeds within each question.",
        analysis="Report all simple effects, recovery/harm, source correctness strata, duplicate-value strata, clustered bootstrap and complete coverage. Natural source correctness is observational. Truncation stays in outcome denominator; missing sources are separate, not failures.",
        stop="One frozen batch, shared 24 GPU-hour cap including loading; no retries, failure screening, extra questions/seeds, neural search or automatic mechanism followup.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", draft_completed=0, repair_completed=0, maximum_requests=576))
    return m


def source_record(raw, q):
    score = score_response(raw["text"], dict(q, old_expression=None), "COUNT_SOURCE")
    final = raw["text"].rsplit("</think>", 1)[1] if "</think>" in raw["text"] else ""
    # EOS is transport, not draft content; the complete generated text remains in drafts.jsonl.
    for token in ("<|im_end|>", "<|endoftext|>"):
        final = final.removesuffix(token)
    usable = bool(final.strip())
    verdict = ("CORRECT" if score["correct"] else "INCORRECT") if score.get("parsed") else "UNDETERMINED"
    return dict(id=q["id"], usable=usable, feedback=verdict,
        draft=final if usable else None, old_expression=score.get("extracted_answer"),
        score=score, finish_reason=raw["finish_reason"], generated_tokens=raw["generated_tokens"])


def repair_prompt(q, source, condition):
    text = f"Original problem:\n{q['problem']}\n"
    if condition.endswith("HISTORY"):
        if not source["usable"]: raise ValueError("No usable history")
        label = (f"The following draft has a {source['feedback']} final answer." if source["feedback"] != "UNDETERMINED"
                 else "The correctness of the following draft's final answer could not be determined.")
        text += f"\n{label}\n-- beginning of the draft --\n{source['draft']}\n-- end of the draft --\n"
    text += "\n" + GAME24_SUFFIX
    counts = ", ".join(f"{n}: {count}" for n, count in sorted(Counter(q["answer"]).items()))
    text += ("\nRequired occurrence counts of the original numerical values: " + counts +
             ". Use exactly these quantities and no other operands, with only +, -, *, / and parentheses.")
    if condition.startswith("IDENTITY"):
        table = ", ".join(f"{name}={value}" for name, value in q["bindings"].items())
        text += ("\nTreat the four original number occurrences as four distinct cards: " + table +
            ". Cards with equal numerical values are still different cards. "
            "In your final boxed expression, use the card letters A, B, C and D exactly once each "
            "instead of numerical literals. Each card letter evaluates to its assigned number. Do not add other operands.")
    else:
        text += "\nIn your final boxed expression, use numerical literals with exactly the required occurrence counts."
    return text


def summarise(m, out, status=None, error=None):
    drafts = {r["id"]: r for r in rows(out / "source_scores.jsonl")}
    scored = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "behaviour.jsonl")}
    complete = [q for q in m["questions"] if all((q["id"], c, s) in scored for c in CONDITIONS for s in REPAIR_SEEDS)]
    stats = {}
    for c in CONDITIONS:
        rs = [r for (qid, cond, seed), r in scored.items() if cond == c]
        stats[c] = dict(n=len(rs), correct=sum(bool(r["correct"]) for r in rs),
            inventory_illegal=sum(r.get("parsed", False) and not r.get("inventory_correct", False) for r in rs),
            old_expression_reuse=sum(bool(r.get("structural_reuse")) for r in rs),
            length_stops=sum(r["finish_reason"] == "length" for r in rs),
            unresolved=sum(not r.get("parsed", False) for r in rs),
            generated_tokens=sum(r["generated_tokens"] for r in rs),
            scorer_disagreements=sum(bool(r.get("scorer_disagreement")) for r in rs))

    def effects(questions):
        averages = {q["id"]: {c: sum(int(scored[q["id"], c, s]["correct"]) for s in REPAIR_SEEDS)/len(REPAIR_SEEDS)
                              for c in CONDITIONS} for q in questions}
        simple = {h: bootstrap([r["IDENTITY_"+h]-r["COUNT_"+h] for r in averages.values()]) for h in ("CLEAN", "HISTORY")}
        interaction = bootstrap([r["IDENTITY_HISTORY"]-r["COUNT_HISTORY"]-r["IDENTITY_CLEAN"]+r["COUNT_CLEAN"] for r in averages.values()])
        recovery = {}
        for h in ("CLEAN", "HISTORY"):
            pairs = [(scored[q["id"], "COUNT_"+h, s]["correct"], scored[q["id"], "IDENTITY_"+h, s]["correct"])
                     for q in questions for s in REPAIR_SEEDS]
            recovery[h] = dict(paired_requests=len(pairs), recovered=sum(not a and b for a,b in pairs), harmed=sum(a and not b for a,b in pairs))
        return dict(questions=len(questions), simple_effects=simple, history_interaction=interaction, recovery_harm=recovery,
            history_effects={prefix: bootstrap([r[prefix+"_HISTORY"]-r[prefix+"_CLEAN"] for r in averages.values()]) for prefix in ("COUNT", "IDENTITY")},
            by_question=[dict(id=qid, accuracy=rs, interaction=rs["IDENTITY_HISTORY"]-rs["COUNT_HISTORY"]-rs["IDENTITY_CLEAN"]+rs["COUNT_CLEAN"]) for qid, rs in averages.items()])
    strata = {label: effects([q for q in complete if drafts.get(q["id"], {}).get("feedback") == label])
              for label in ("CORRECT", "INCORRECT", "UNDETERMINED")}
    result = dict(status=status, error=error, draft_completed=len(drafts), draft_planned=64,
        source_verdicts=dict(Counter(r["feedback"] for r in drafts.values())),
        usable_sources=sum(r["usable"] for r in drafts.values()),
        missing_source_ids=[qid for qid, r in drafts.items() if not r["usable"]],
        repair_completed=len(scored), maximum_repair_requests=512,
        actual_repair_planned=sum(8 if drafts.get(q["id"], {}).get("usable") else 4 for q in m["questions"]) if len(drafts)==64 else None,
        complete_questions=len(complete), conditions=stats, primary=effects(complete), source_strata=strata,
        input_strata={"duplicate_values": effects([q for q in complete if len(set(q["answer"]))<4]),
                      "distinct_values": effects([q for q in complete if len(set(q["answer"]))==4])},
        pending_sources=[q["id"] for q in m["questions"] if q["id"] not in drafts],
        note="Seeds are averaged within question, never independent sample units. Complete paired coverage excludes unavailable histories; all completed requests remain in condition denominators. Source strata are observational.")
    save(out / "summary.json", result)
    return result


def run(output, m):
    import importlib.metadata
    import torch
    from transformers import AutoTokenizer, GenerationConfig
    if os.environ.get("SC_IDENTITY_PROSPECTIVE_LAUNCHER") != "1":
        raise RuntimeError("Use the shared launcher --identity-prospective")
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("One visible A100 required")
    if importlib.metadata.version("vllm") != "0.11.0":
        raise RuntimeError("Use the inspected native vLLM environment")
    prior = load(output / "budget.json")
    if prior.get("active"): raise RuntimeError("Shared GPU budget active")
    out = output / SUBDIR
    # Raw completion is the resume authority: score after saving, without regenerating it.
    source_raw = {r["id"]: r for r in rows(out / "drafts.jsonl")}
    repair_raw = {(r["id"],r["condition"],r["seed"]): r for r in rows(out / "generations.jsonl")}
    maximum_remaining_tokens = (64-len(source_raw))*16384 + (512-len(repair_raw))*8192
    estimate = m["estimate"]
    if maximum_remaining_tokens/estimate["tokens_per_second"]+estimate["loading_seconds"] > prior["limit_seconds"]-prior["gpu_seconds"]:
        raise RuntimeError("Frozen design no longer fits remaining budget estimate")
    budget = Budget(output / "budget.json", 24)
    status, error, phase = "completed", None, "loading_model"
    try:
        save(out / "run_state.json", dict(status="loading_model",draft_completed=len(source_raw),repair_completed=len(repair_raw),maximum_requests=576))
        os.environ.update(VLLM_WORKER_MULTIPROC_METHOD="spawn", VLLM_USE_V1="1", VLLM_ATTENTION_BACKEND="FLASH_ATTN")
        from vllm import LLM, SamplingParams
        tokenizer = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
        eos = GenerationConfig.from_pretrained(m["model"], local_files_only=True).eos_token_id
        eos = [eos] if isinstance(eos,int) else eos
        llm = LLM(model=m["model"],tokenizer=m["model"],dtype="bfloat16",max_model_len=32768,max_num_seqs=8,
            gpu_memory_utilization=.80,enable_prefix_caching=True,enable_chunked_prefill=True,
            max_num_batched_tokens=8192,enforce_eager=True,generation_config="vllm",seed=DESIGN_SEED)
        engine = llm.llm_engine
        questions = {q["id"]: q for q in m["questions"]}
        sources = {}
        started = time.monotonic()

        def score_sources():
            already = {r["id"] for r in rows(out / "source_scores.jsonl")}
            for qid, raw in source_raw.items():
                sources[qid] = source_record(raw, questions[qid])
                if qid not in already: append(out / "source_scores.jsonl", sources[qid])

        def state(active=None, queued=0):
            save(out / "run_state.json",dict(status="running",phase=phase,draft_completed=len(source_raw),
                repair_completed=len(repair_raw),maximum_requests=576,elapsed_generation_seconds=time.monotonic()-started,
                active=active or [],queued=queued))

        def batch(todo, raw_path, store):
            inflight, index = {}, 0
            while index < len(todo) or engine.has_unfinished_requests():
                budget.check()
                submitted = False
                while index < len(todo) and len(inflight)<8:
                    item = todo[index]
                    index += 1
                    ids = tokenizer.apply_chat_template([dict(role="user",content=item["prompt"])],
                        tokenize=True,add_generation_prompt=True,enable_thinking=True)
                    if len(ids)+item["max_new_tokens"] > m["max_model_len"]:
                        raise ValueError("Frozen output cap exceeds context capacity")
                    rid = str(next(llm.request_counter))
                    params = SamplingParams(**m["sampling"],seed=item["seed"],max_tokens=item["max_new_tokens"],
                        skip_special_tokens=False,ignore_eos=False,stop_token_ids=eos)
                    engine.add_request(rid,dict(prompt_token_ids=ids),params)
                    inflight[rid] = (item,time.monotonic())
                    submitted = True
                if submitted: state([dict(id=i["id"],condition=i["condition"],seed=i["seed"]) for i,_ in inflight.values()],len(todo)-index)
                for result in engine.step():
                    if not result.finished: continue
                    item, begin = inflight.pop(result.request_id)
                    g = result.outputs[0]
                    tokens = list(g.token_ids)
                    record = {k:v for k,v in item.items() if k!="prompt"}
                    record.update(text=tokenizer.decode(tokens,skip_special_tokens=False),token_ids=tokens,
                        generated_tokens=len(tokens),finish_reason="eos" if (tokens and tokens[-1] in eos) or g.stop_reason in eos else g.finish_reason,
                        stop_reason=g.stop_reason,prompt=item["prompt"],request_wall_seconds=time.monotonic()-begin,
                        request_timing_note="Concurrent requests overlap; shared budget.json measures GPU occupancy.",
                        model=m["model"],dtype=m["dtype"],sampling=m["sampling"],backend=m["backend"],
                        source=str(out/"manifest.json") if phase=="drafts" else str(out/"drafts.jsonl"))
                    append(raw_path,record)
                    store(record)
                    state([dict(id=i["id"],condition=i["condition"],seed=i["seed"]) for i,_ in inflight.values()],len(todo)-index)
                    budget.check(force=True)

        phase = "drafts"
        todo = [dict(id=q["id"],condition="NUMERIC_SOURCE",seed=DRAFT_SEED,max_new_tokens=16384,
                     prompt=independent_prompt(q["problem"])) for q in m["questions"] if q["id"] not in source_raw]
        batch(todo,out/"drafts.jsonl",lambda r: source_raw.__setitem__(r["id"],r))
        score_sources()
        phase = "repairs"
        contexts = []
        for q in m["questions"]:
            src = sources[q["id"]]
            for seed in REPAIR_SEEDS:
                for c in q["condition_order"]:
                    if c.endswith("HISTORY") and not src["usable"]: continue
                    contexts.append(dict(id=q["id"],condition=c,seed=seed,max_new_tokens=8192,prompt=repair_prompt(q,src,c)))
        save(out/"repair_requests.json",contexts)
        scored_keys = {(r["id"],r["condition"],r["seed"]) for r in rows(out/"behaviour.jsonl")}

        def store_repair(r):
            key = r["id"],r["condition"],r["seed"]
            repair_raw[key] = r
            if key not in scored_keys:
                q = dict(questions[r["id"]],old_expression=sources[r["id"]]["old_expression"])
                append(out/"behaviour.jsonl",dict(id=r["id"],condition=r["condition"],seed=r["seed"],
                    source_feedback=sources[r["id"]]["feedback"],**score_response(r["text"],q,r["condition"]),
                    finish_reason=r["finish_reason"],generated_tokens=r["generated_tokens"]))
                scored_keys.add(key)

        for r in list(repair_raw.values()): store_repair(r)
        batch([r for r in contexts if (r["id"],r["condition"],r["seed"]) not in repair_raw],out/"generations.jsonl",store_repair)
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed",repr(exc)
        raise
    finally:
        budget.close()
        # Also score completed drafts if the source phase was interrupted.
        existing = {r["id"] for r in rows(out/"source_scores.jsonl")}
        for q in m["questions"]:
            if q["id"] in source_raw and q["id"] not in existing:
                append(out/"source_scores.jsonl",source_record(source_raw[q["id"]],q))
        result = summarise(m,out,status,error)
        save(out/"run_state.json",dict(status=status,phase=phase,draft_completed=result["draft_completed"],
            repair_completed=result["repair_completed"],actual_repair_planned=result["actual_repair_planned"],maximum_requests=576,error=error))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare",action="store_true")
    p.add_argument("--resume",action="store_true")
    p.add_argument("--status",action="store_true")
    p.add_argument("--report",action="store_true")
    a=p.parse_args()
    if a.status:
        out=a.output/SUBDIR
        for name in ("run_state.json","summary.json"):
            if (out/name).exists():
                data=load(out/name)
                print(json.dumps({k:v for k,v in data.items() if k not in ("primary","source_strata","input_strata")},indent=2))
        return
    m=prepare(a.output)
    if a.prepare and os.environ.get("SC_IDENTITY_PROSPECTIVE_LAUNCHER")=="1":
        from transformers import AutoTokenizer, GenerationConfig
        tokenizer=AutoTokenizer.from_pretrained(m["model"],local_files_only=True)
        GenerationConfig.from_pretrained(m["model"],local_files_only=True)
        for q in m["questions"]:
            ids=tokenizer.apply_chat_template([dict(role="user",content=independent_prompt(q["problem"]))],
                tokenize=True,add_generation_prompt=True,enable_thinking=True)
            if len(ids)+m["draft_max_new_tokens"]+m["repair_max_new_tokens"]+1024>m["max_model_len"]:
                raise ValueError("Source plus repair cannot fit frozen context length")
    if a.resume: run(a.output,m)
    elif a.report:
        state=load(a.output/SUBDIR/"run_state.json")
        result=summarise(m,a.output/SUBDIR,state.get("status"),state.get("error"))
        print(json.dumps({k:v for k,v in result.items() if k not in ("source_strata","input_strata","pending_sources")},indent=2))
    else: print(json.dumps(dict(status="prepared",questions=len(m["questions"]),maximum_requests=m["maximum_requests"],excluded_multisets=m["excluded_multisets"])))


if __name__=="__main__": main()
