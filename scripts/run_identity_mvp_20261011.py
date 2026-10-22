"""Bounded 2x2 history-by-resource-identity MVP on all existing 24 Game24 items."""
from __future__ import annotations

import argparse
import ast
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
from run_information_followup_20261005 import same_tree, tree
from selective_context.tasks import extract_math_box, independent_prompt

CONDITIONS = ("NUMERIC_CLEAN", "NUMERIC_HISTORY", "IDENTITY_CLEAN", "IDENTITY_HISTORY")
SEED = 20261011


def audit_expression(expression, numbers, bindings=None, binding_counts=None, allow_literals=False):
    """Exact value and occurrence inventory; no evaluation of executable input."""
    node = tree(expression)
    if node is None:
        return dict(parsed=False, correct=False, reason="unparsed_expression")
    used, symbols = Counter(), Counter()

    def evaluate(n):
        if isinstance(n, ast.Constant) and type(n.value) is int and (bindings is None or allow_literals):
            used[n.value] += 1
            return Fraction(n.value), str(n.value)
        if isinstance(n, ast.Name) and bindings is not None and n.id in bindings:
            symbols[n.id] += 1
            used[bindings[n.id]] += 1
            return Fraction(bindings[n.id]), str(bindings[n.id])
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            value, text = evaluate(n.operand)
            return (value, f"(+{text})") if isinstance(n.op, ast.UAdd) else (-value, f"(-{text})")
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, at = evaluate(n.left)
            b, bt = evaluate(n.right)
            if isinstance(n.op, ast.Add): value, op = a + b, "+"
            elif isinstance(n.op, ast.Sub): value, op = a - b, "-"
            elif isinstance(n.op, ast.Mult): value, op = a * b, "*"
            else: value, op = a / b, "/"
            return value, f"({at}{op}{bt})"
        raise ValueError("Only the permitted arithmetic operands and operators are allowed")

    try:
        value, numeric = evaluate(node)
    except (ValueError, ZeroDivisionError):
        return dict(parsed=False, correct=False, reason="invalid_operand_or_operation")
    inventory = Counter(numbers)
    identity_correct = symbols == Counter(binding_counts or {k: 1 for k in bindings}) if bindings is not None else True
    inventory_correct = used == inventory
    return dict(parsed=True, correct=value == 24 and inventory_correct and identity_correct,
                value=str(value), target_correct=value == 24,
                inventory_correct=inventory_correct, identity_correct=identity_correct,
                used=dict(used), used_symbols=dict(symbols),
                excess=dict(used - inventory), missing=dict(inventory - used),
                numeric_expression=numeric)


def score_response(text, q, condition):
    if "</think>" not in text:
        return dict(parsed=False, correct=False, reason="thinking_not_closed", final_available=False)
    expression = extract_math_box(text.rsplit("</think>", 1)[1])
    if not expression:
        return dict(parsed=False, correct=False, reason="no_complete_final_box", final_available=True)
    audit = audit_expression(expression, q["answer"],
                             q["bindings"] if condition.startswith(("IDENTITY", "VALUE")) else None,
                             q.get("binding_counts"), allow_literals=True)
    result = dict(audit, extracted_answer=expression, final_available=True)
    result["protocol_correct"] = audit["correct"]
    result["structural_reuse"] = same_tree(q["old_expression"], audit.get("numeric_expression"))
    if audit["parsed"]:
        from utils.verifiable_evaluation.math_eval.utils.verification_utils import is_correct_game_of_24
        official = is_correct_game_of_24(audit["numeric_expression"], q["answer"])
        result["official_correct"] = official
        task_correct = audit["target_correct"] and audit["inventory_correct"]
        result["scorer_disagreement"] = official is not None and bool(official) != task_correct
        result["correct"] = task_correct and official is True
    return result


def prepare(output):
    out = output / "identity_mvp"
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = load(output / "cross_question/manifest.json")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(source["model"], local_files_only=True)
    rng = random.Random(SEED)
    orders = list(itertools.permutations(CONDITIONS))
    questions = []
    for i, q in enumerate(source["questions"]):
        labels = rng.sample(list("ABCD"), 4)
        bindings = dict(zip(labels, q["answer"]))
        contexts = {}
        for condition in CONDITIONS:
            history = q["draft"] if condition.endswith("HISTORY") else None
            prompt = independent_prompt(q["problem"], history)
            if condition.startswith("IDENTITY"):
                table = ", ".join(f"{name}={value}" for name, value in bindings.items())
                prompt += ("\nTreat the four original number occurrences as four distinct cards: " + table + ". "
                    "Cards with equal numerical values are still different cards. "
                    "In your final boxed expression, use the card letters A, B, C and D exactly once each "
                    "instead of numerical literals, with only +, -, *, / and parentheses. "
                    "Each card letter evaluates to its assigned number. Do not add other operands.")
            text = tokenizer.apply_chat_template([dict(role="user", content=prompt)], tokenize=False,
                                                  add_generation_prompt=True, enable_thinking=True)
            contexts[condition] = dict(text=text, input_ids=tokenizer.encode(text, add_special_tokens=False))
        questions.append(dict(id=q["id"], answer=q["answer"], problem=q["problem"],
            draft=q["draft"], old_expression=q["old_expression"], bindings=bindings,
            source=q["source"], source_line=q["source_line"],
            condition_order=list(orders[i % len(orders)]), contexts=contexts))
    if len(questions) != 24:
        raise ValueError("Use all 24 existing items, without effect-based filtering")
    m = dict(model=source["model"], dtype="bfloat16", attention="FLASH_ATTN", seed=SEED,
        sampling=dict(temperature=0.6, top_p=0.95, top_k=20), max_new_tokens=8192,
        backend="native_vllm_0.11.0", max_num_seqs=8, max_model_len=32768,
        conditions=list(CONDITIONS), planned_requests=96, questions=questions, gpu_hours=24,
        primary="Question-level interaction: (IDENTITY_HISTORY-NUMERIC_HISTORY) minus (IDENTITY_CLEAN-NUMERIC_CLEAN) in final-answer accuracy. Positive means identity helps more with failed history than without it.",
        secondary=["Identity versus numeric accuracy with history", "Clean competence in both representations",
                   "Inventory violations versus target-value failures", "Mapped final AST reuse",
                   "EOS, truncation, format failures, output tokens, paired recovered/harmed"],
        scope="Prospective method/representation comparison on reused 24 items and one fresh paired seed. Not an independent dataset, neural causal explanation, proven novelty, or general mathematical repair method.",
        method="Assign one unique symbol to each given operand occurrence. Retain failed draft verbatim. Final expression refers to those symbols, then deterministically substitute their values. No solution, error location or feasibility oracle is supplied; no constrained decoding, selection, retry or training.",
        execution="All four conditions rerun on one native vLLM backend with native Thinking and independent KV state; one fresh paired seed; 24 condition permutations balance order.",
        analysis="Complete four-condition questions for paired bootstrap (5000 draws); all completed requests in condition denominators. Unclosed thinking, invalid format and truncation stay in denominators. Report each simple effect with the interaction; never call ordinary clean gains history-specific. Same seed does not imply the same trajectory.",
        stop="One 96-request batch; original shared 24 GPU-hour hard cap, loading included. No automatic tuning, extra seeds, problem replacement, model expansion or neural head search.",
        estimate=dict(max_generated_tokens=96*8192, reference_tokens_per_second=30,
                      conservative_generation_hours=96*8192/30/3600, loading_allowance_seconds=300))
    save(out / "manifest.json", m)
    save(out / "summary.json", dict(status="prepared_not_launched", completed=0, planned=96))
    return m


def prepare_alias_control(output):
    import copy
    out = output / "identity_alias"
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = load(output / "identity_mvp/manifest.json")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(source["model"], local_files_only=True)
    m = copy.deepcopy(source)
    m.update(output_subdir="identity_alias", conditions=["VALUE_CLEAN", "VALUE_HISTORY"], planned_requests=48)
    for i, q in enumerate(m["questions"]):
        first_name, bindings, counts = {}, {}, Counter()
        for name, value in q["bindings"].items():
            if value not in first_name:
                first_name[value] = name
                bindings[name] = value
            counts[first_name[value]] += 1
        q["bindings"], q["binding_counts"] = bindings, dict(counts)
        q["condition_order"] = m["conditions"] if i%2 == 0 else list(reversed(m["conditions"]))
        q["contexts"] = {}
        for c in m["conditions"]:
            prompt = independent_prompt(q["problem"], q["draft"] if c.endswith("HISTORY") else None)
            if len(bindings) == 4:
                # The two representations coincide for four distinct input values.
                context = source["questions"][i]["contexts"][c.replace("VALUE", "IDENTITY")]
                q["contexts"][c] = copy.deepcopy(context)
                continue
            table = ", ".join(f"{name}={value}" for name,value in bindings.items())
            quotas = ", ".join(f"{name}: {count}" for name,count in counts.items())
            prompt += ("\nName each distinct numerical value with a letter: " + table + ". "
                "Equal numerical values share the same letter. "
                "In your final boxed expression, use these letters instead of numerical literals, "
                "with only +, -, *, / and parentheses. The required occurrence counts are " + quotas + ". "
                "Each letter evaluates to its assigned number. Do not add other operands.")
            text = tokenizer.apply_chat_template([dict(role="user",content=prompt)],tokenize=False,
                add_generation_prompt=True,enable_thinking=True)
            q["contexts"][c] = dict(text=text,input_ids=tokenizer.encode(text,add_special_tokens=False))
    m.update(primary="Occurrence identities versus value aliases: paired history interaction, reusing the completed identity MVP occurrence responses.",
        method="One symbol per distinct numerical value with explicit multiplicities; same old numeric draft and symbolic final format. Isolate occurrence separation from a generic numeric-to-symbol surface change.",
        analysis="All 24 reused items, same seed, backend and cap. Primary effects use complete VALUE and existing IDENTITY conditions. Report duplicate-input subset descriptively; four-distinct-value prompts are identical and provide a null comparison. Not independent confirmation.",
        stop="One predeclared conditional 48-request distinction only, if original MVP is promising and shared remaining budget fits. No automatic tuning or further experiments.",
        estimate=dict(max_generated_tokens=48*8192,reference_tokens_per_second=30,
                      conservative_generation_hours=48*8192/30/3600,loading_allowance_seconds=300))
    save(out / "manifest.json",m)
    save(out / "summary.json",dict(status="prepared_not_launched",completed=0,planned=48))
    return m


def analyse(m, out, status, error=None):
    keyed = {(r["id"], r["condition"]): r for r in rows(out / "behaviour.jsonl")}
    conditions = m["conditions"]
    is_alias = m.get("output_subdir") == "identity_alias"
    if is_alias:
        keyed.update({(r["id"],r["condition"]):r for r in rows(out.parent/"identity_mvp/behaviour.jsonl")
                      if r["condition"].startswith("IDENTITY")})
    paired_conditions = conditions + ["IDENTITY_CLEAN", "IDENTITY_HISTORY"] if is_alias else conditions
    complete = [q["id"] for q in m["questions"] if all((q["id"], c) in keyed for c in paired_conditions)]
    fields = ("correct", "protocol_correct", "identity_correct", "parsed", "inventory_correct", "target_correct", "structural_reuse", "scorer_disagreement")
    stats = {}
    for condition in conditions:
        rs = [r for (qid, c), r in keyed.items() if c == condition]
        stats[condition] = dict(n=len(rs), **{f: sum(bool(r.get(f)) for r in rs) for f in fields},
            eos=sum(r["finish_reason"] == "eos" for r in rs),
            length_stops=sum(r["finish_reason"] == "length" for r in rs),
            unresolved=sum(not r.get("parsed", False) for r in rs),
            tokens=sum(r["generated_tokens"] for r in rs))
    simple = {}
    before_prefix = "VALUE_" if is_alias else "NUMERIC_"
    for history in ("CLEAN", "HISTORY"):
        before, after = before_prefix + history, "IDENTITY_" + history
        simple[history] = dict(accuracy=bootstrap([int(keyed[q, after]["correct"]) - int(keyed[q, before]["correct"]) for q in complete]),
            recovered=sum(not keyed[q, before]["correct"] and keyed[q, after]["correct"] for q in complete),
            harmed=sum(keyed[q, before]["correct"] and not keyed[q, after]["correct"] for q in complete))
    interaction = bootstrap([int(keyed[q, "IDENTITY_HISTORY"]["correct"]) - int(keyed[q, before_prefix+"HISTORY"]["correct"])
                            - int(keyed[q, "IDENTITY_CLEAN"]["correct"]) + int(keyed[q, before_prefix+"CLEAN"]["correct"])
                            for q in complete])
    result = dict(status=status, completed=sum(c in conditions for q,c in keyed), planned=m["planned_requests"], complete_questions=len(complete),
        conditions=stats, simple_effects=simple, history_specific_interaction=interaction,
        by_question=[dict(id=q, results={c: keyed[q, c] for c in paired_conditions if (q, c) in keyed})
                     for q in [x["id"] for x in m["questions"]]], error=error,
        pending=[dict(id=q["id"], condition=c) for q in m["questions"] for c in conditions if (q["id"], c) not in keyed])
    save(out / "summary.json", result)
    return result


def run(output, m):
    import importlib.metadata
    import torch
    from transformers import AutoTokenizer, GenerationConfig
    if os.environ.get("SC_IDENTITY_MVP_LAUNCHER") != "1":
        raise RuntimeError("Use shared launcher --identity-mvp")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
        raise RuntimeError("One visible A100 required")
    if importlib.metadata.version("vllm") != "0.11.0" or m.get("backend") != "native_vllm_0.11.0":
        raise RuntimeError("Use the inspected native vLLM 0.11.0 engine and prelaunch manifest")
    prior = load(output / "budget.json")
    if prior.get("active"):
        raise RuntimeError("Shared budget active")
    out = output / m.get("output_subdir", "identity_mvp")
    raw = {(r["id"], r["condition"]): r for r in rows(out / "generations.jsonl")}
    done = {(r["id"], r["condition"]) for r in rows(out / "behaviour.jsonl")}
    planned = m["planned_requests"]
    pending = planned-len(done)
    estimate = m["estimate"]
    if pending*m["max_new_tokens"]/estimate["reference_tokens_per_second"] + estimate["loading_allowance_seconds"] > prior["limit_seconds"]-prior["gpu_seconds"]:
        raise RuntimeError("Frozen design no longer fits remaining budget estimate; do not silently shrink")
    budget = Budget(output / "budget.json", 24)
    status, error = "completed", None
    try:
        save(out / "run_state.json", dict(status="loading_model", completed=len(done), planned=planned))
        os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
        os.environ["VLLM_USE_V1"] = "1"
        os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"
        from vllm import LLM, SamplingParams
        tokenizer = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
        eos = GenerationConfig.from_pretrained(m["model"], local_files_only=True).eos_token_id
        eos = [eos] if isinstance(eos, int) else eos
        llm = LLM(model=m["model"], tokenizer=m["model"], dtype="bfloat16",
            max_model_len=m["max_model_len"], max_num_seqs=m["max_num_seqs"],
            gpu_memory_utilization=0.80, enable_prefix_caching=True,
            enable_chunked_prefill=True, max_num_batched_tokens=8192,
            enforce_eager=True, generation_config="vllm", seed=SEED,
            disable_log_stats=False)
        engine = llm.llm_engine
        todo = []
        for q in m["questions"]:
            for c in q["condition_order"]:
                key = q["id"], c
                if key in done: continue
                if key in raw:
                    record = raw[key]
                    append(out / "behaviour.jsonl", dict(id=q["id"], condition=c, seed=SEED,
                        **score_response(record["text"], q, c), finish_reason=record["finish_reason"],
                        generated_tokens=record["generated_tokens"]))
                    done.add(key)
                else:
                    todo.append((q,c))
        started, initial = time.monotonic(), len(done)
        inflight, next_index = {}, 0
        while next_index < len(todo) or engine.has_unfinished_requests():
            budget.check()
            submitted = False
            while len(inflight) < m["max_num_seqs"] and next_index < len(todo):
                q, c = todo[next_index]
                rid = str(next(llm.request_counter))
                context = q["contexts"][c]
                if len(context["input_ids"])+m["max_new_tokens"] > m["max_model_len"]:
                    raise ValueError("Frozen output cap exceeds context capacity")
                params = SamplingParams(**m["sampling"], seed=SEED, max_tokens=m["max_new_tokens"],
                    skip_special_tokens=False, ignore_eos=False, stop_token_ids=eos)
                engine.add_request(rid, dict(prompt_token_ids=context["input_ids"]), params)
                inflight[rid] = (q,c,time.monotonic())
                next_index += 1
                submitted = True
            if submitted:
                save(out / "current_request.json", dict(active=[dict(id=q["id"],condition=c) for q,c,_ in inflight.values()],
                    queued=len(todo)-next_index))
            for output_record in engine.step():
                if not output_record.finished: continue
                q, c, begin = inflight.pop(output_record.request_id)
                generation = output_record.outputs[0]
                tokens = list(generation.token_ids)
                record = dict(id=q["id"], condition=c, seed=SEED,
                    text=tokenizer.decode(tokens, skip_special_tokens=False), token_ids=tokens,
                    generated_tokens=len(tokens),
                    finish_reason="eos" if (tokens and tokens[-1] in eos) or generation.stop_reason in eos else generation.finish_reason,
                    stop_reason=generation.stop_reason,
                    request_wall_seconds=time.monotonic()-begin,
                    request_timing_note="Concurrent requests overlap; shared budget.json gives GPU occupancy.",
                    model=m["model"], dtype=m["dtype"], sampling=m["sampling"], backend=m["backend"],
                    max_new_tokens=m["max_new_tokens"], source=q["source"], source_line=q["source_line"])
                append(out / "generations.jsonl", record)
                raw[q["id"],c] = record
                append(out / "behaviour.jsonl", dict(id=q["id"],condition=c,seed=SEED,
                    **score_response(record["text"],q,c), finish_reason=record["finish_reason"],
                    generated_tokens=record["generated_tokens"]))
                done.add((q["id"],c))
                elapsed=time.monotonic()-started
                save(out / "run_state.json",dict(status="running",completed=len(done),planned=planned,
                    elapsed_generation_seconds=elapsed,
                    estimated_remaining_seconds=elapsed/max(1,len(done)-initial)*(planned-len(done))))
                budget.check(force=True)
                if len(done)%4==0: analyse(m,out,"running")
    except BudgetExceeded:
        status = "budget_exhausted"
    except Exception as exc:
        status, error = "failed", repr(exc)
        raise
    finally:
        budget.close()
        result = analyse(m, out, status, error)
        save(out / "run_state.json", dict(status=status, completed=result["completed"], planned=planned, error=error))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT/"outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--value-alias", action="store_true", help="Inspect or prepare the separate value-alias distinction")
    a = p.parse_args()
    is_alias = a.value_alias or os.environ.get("SC_IDENTITY_MVP_MODE") == "value_alias_control"
    out = a.output / ("identity_alias" if is_alias else "identity_mvp")
    if a.status:
        for name in ("run_state.json", "summary.json"):
            if (out/name).exists():
                state = load(out/name)
                print(json.dumps({k:v for k,v in state.items() if k not in ("by_question", "pending")}, indent=2))
        return
    m = prepare_alias_control(a.output) if is_alias else prepare(a.output)
    if a.resume: run(a.output, m)
    else: print(json.dumps(dict(status="prepared", requests=m["planned_requests"])))


if __name__ == "__main__":
    main()
