"""Does asking for adoption change validity judgments on the exact same candidates?"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression
from run_check_rule_transfer_20261011 import run

SUBDIR = "decision_verification"
SEED = 20261019
CONDITIONS = tuple("_".join(parts) for parts in itertools.product(
    ("CLEAN", "HISTORY"), ("AUDIT", "ADOPT"), ("HOLISTIC", "FACTORIZED")))


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    pool = load(output / "candidate_adoption/failure_pool.json")
    questions = sorted(pool["questions"], key=lambda q: tuple(q["answer"]))
    rng = random.Random(SEED)
    rng.shuffle(questions)
    if len(questions) != 48:
        raise ValueError("Use all 48 previously collected natural failures")
    for i, q in enumerate(questions):
        q["split"] = "group_a" if i < 24 else "group_b"
        q["old_index"] = 1 + i % 2
        old = audit_expression(q["old_expression"], q["answer"])
        good = audit_expression(q["legal_expression"], q["answer"])
        if not old.get("parsed") or old["correct"] or not good.get("correct"):
            raise ValueError(f"Incorrect candidate eligibility {q['id']}")
        q["old_numeric"], q["legal_numeric"] = old["numeric_expression"], good["numeric_expression"]
        q["old_audit"] = old
        q["condition_order"] = rng.sample(list(CONDITIONS), len(CONDITIONS))
    m = dict(model="/data2/huangrj/models/qwen3-8b", dtype="bfloat16", backend="native_vllm_0.11.0",
        sampling=dict(temperature=.6, top_p=.95, top_k=20), max_new_tokens=8192, max_num_seqs=8,
        seeds=[SEED], conditions=list(CONDITIONS), questions=questions, planned_requests=384,
        primary="HOLISTIC history interaction of ADOPT versus AUDIT on acceptance of the old illegal expression.",
        secondary="Same goal interaction under FACTORIZED, difference between interactions, history interaction of factorization in each goal, adoption accuracy, component and conjunction consistency, tokens, missingness.",
        scope="Same candidates and retained original natural histories. All 48 eligible existing failures; no fresh screening, no independent holdout. One paired seed, candidate position balanced across questions. Task intent is randomized, not a measurement of a hidden decision order.",
        estimate=dict(tokens_per_second=350, loading_seconds=300),
        stop="Shared 24 GPU-hour cap, one frozen batch; no automatic prompt or sample expansion.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", completed=0, planned=384))
    return m


def prompt_for(q, condition, seed):
    history, goal, granularity = condition.split("_")
    prompt = f"Original problem:\n{q['problem']}\n"
    if history == "HISTORY":
        prompt += ("\nThe following draft has an INCORRECT final answer.\n-- beginning of the draft --\n" +
                   q["draft"] + "\n-- end of the draft --\n")
    counts = ", ".join(f"{n}: {count}" for n, count in sorted(Counter(q["answer"]).items()))
    prompt += ("\nRequired occurrence counts of the original numerical values: " + counts +
        ". A valid expression must equal 24, use exactly these quantities and no other operands, "
        "with only +, -, *, / and parentheses.\n")
    candidates = [q["old_numeric"], q["legal_numeric"]]
    if q["old_index"] == 2:
        candidates.reverse()
    prompt += f"\nOption 1: {candidates[0]}\nOption 2: {candidates[1]}\n\n"
    prompt += "Evaluate both options against all original constraints. You do not need to search for a new expression. "
    if goal == "AUDIT":
        prompt += "This task asks only for a validity audit of both options; do not select an option to adopt. "
    else:
        prompt += "After the validity audit, select the valid option to adopt as the answer. "
    prompt += "After reasoning, return one JSON object with boolean fields option_1_valid and option_2_valid. "
    if granularity == "FACTORIZED":
        prompt += ("Also independently check and include these four boolean fields: option_1_value_matches, "
            "option_1_counts_match, option_2_value_matches, option_2_counts_match. value_matches means "
            "the exact arithmetic value equals 24; counts_match means the operand occurrences exactly match "
            "the given numerical multiset. Check each property separately even if the other is false. ")
    prompt += ("Include choice with value null because no selection is requested." if goal == "AUDIT" else
               "Include choice with integer value 1 or 2 for the option you select.")
    return prompt


def score(text, q, seed, condition):
    _, goal, granularity = condition.split("_")
    result = dict(parsed=False, judgments_parsed=False, judgments_correct=False, old_accepted=None,
        choice_parsed=False, choice_correct=None, properties_parsed=False, properties_correct=None,
        correct_properties_but_old_accepted=None, conjunction_consistent=None, reason="missing_final")
    if "</think>" not in text:
        return result
    final = text.rsplit("</think>", 1)[1]
    start = final.find("{")
    if start < 0:
        return result
    try:
        answer, _ = json.JSONDecoder().raw_decode(final[start:])
    except json.JSONDecodeError:
        return dict(result, reason="invalid_json")
    if not isinstance(answer, dict):
        return dict(result, reason="invalid_object")
    oi, gi = q["old_index"], 3-q["old_index"]
    jp = all(type(answer.get(f"option_{i}_valid")) is bool for i in (1, 2))
    choice = answer.get("choice")
    cp = ("choice" in answer and choice is None) if goal == "AUDIT" else (type(choice) is int and choice in (1, 2))
    prop_fields = [f"option_{i}_{f}" for i in (1, 2) for f in ("value_matches", "counts_match")]
    pp = granularity == "FACTORIZED" and all(type(answer.get(f)) is bool for f in prop_fields)
    props_correct = (all(answer[f"option_{i}_value_matches"] == (q["old_audit"]["target_correct"] if i == oi else True)
        and answer[f"option_{i}_counts_match"] == (q["old_audit"]["inventory_correct"] if i == oi else True)
        for i in (1, 2))) if pp else None
    conjunction = all(answer[f"option_{i}_valid"] == (answer[f"option_{i}_value_matches"] and answer[f"option_{i}_counts_match"])
        for i in (1, 2)) if jp and pp else None
    old_accepted = answer[f"option_{oi}_valid"] if type(answer.get(f"option_{oi}_valid")) is bool else None
    return dict(parsed=jp and cp and (pp if granularity == "FACTORIZED" else True),
        judgments_parsed=jp, judgments_correct=jp and answer[f"option_{oi}_valid"] is False and answer[f"option_{gi}_valid"] is True,
        old_accepted=old_accepted, choice_parsed=cp,
        choice_correct=choice == gi if goal == "ADOPT" and cp else None,
        properties_parsed=pp, properties_correct=props_correct,
        correct_properties_but_old_accepted=bool(props_correct and old_accepted) if pp and jp else None,
        conjunction_consistent=conjunction, final_json=answer, reason=None if jp and cp else "missing_judgment_or_choice")


def summarize(m, out, status=None, error=None):
    data = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "behaviour.jsonl")}
    by_question = {q["id"]: {c: data[q["id"], c, SEED] for c in CONDITIONS if (q["id"], c, SEED) in data}
                   for q in m["questions"]}
    stats = {}
    for c in CONDITIONS:
        rs = [r for r in data.values() if r["condition"] == c]
        stats[c] = dict(n=len(rs), judgments_correct=sum(r["judgments_correct"] for r in rs),
            parsed=sum(r["parsed"] for r in rs), length_stops=sum(r["finish_reason"] == "length" for r in rs),
            old_accepted=sum(r["old_accepted"] is True for r in rs), old_acceptance_observed=sum(r["old_accepted"] is not None for r in rs),
            old_acceptance_missing=sum(r["old_accepted"] is None for r in rs),
            choice_correct=sum(r["choice_correct"] is True for r in rs), choice_observed=sum(r["choice_correct"] is not None for r in rs),
            properties_correct=sum(r["properties_correct"] is True for r in rs),
            properties_observed=sum(r["properties_correct"] is not None for r in rs),
            correct_properties_but_old_accepted=sum(r["correct_properties_but_old_accepted"] is True for r in rs),
            conjunction_inconsistent=sum(r["conjunction_consistent"] is False for r in rs),
            generated_tokens=sum(r["generated_tokens"] for r in rs))
    effects = {}
    for split in ("all", "group_a", "group_b"):
        qs = [q for q in m["questions"] if split == "all" or q["split"] == split]
        contrasts = {}
        for g in ("HOLISTIC", "FACTORIZED"):
            required = [f"{h}_{d}_{g}" for h in ("CLEAN", "HISTORY") for d in ("AUDIT", "ADOPT")]
            ps = [q for q in qs if all(c in by_question[q["id"]] and by_question[q["id"]][c]["old_accepted"] is not None for c in required)]
            values, history, clean = [], [], []
            for q in ps:
                r = by_question[q["id"]]
                hd = int(r[f"HISTORY_ADOPT_{g}"]["old_accepted"]) - int(r[f"HISTORY_AUDIT_{g}"]["old_accepted"])
                cd = int(r[f"CLEAN_ADOPT_{g}"]["old_accepted"]) - int(r[f"CLEAN_AUDIT_{g}"]["old_accepted"])
                values.append(hd-cd)
                history.append(hd)
                clean.append(cd)
            contrasts[g] = dict(n=len(ps), goal_history_interaction=bootstrap(values),
                adopt_minus_audit_history=bootstrap(history), adopt_minus_audit_clean=bootstrap(clean),
                directions=dict(positive=sum(v > 0 for v in values), negative=sum(v < 0 for v in values), zero=sum(v == 0 for v in values)))
        ps = [q for q in qs if all(c in by_question[q["id"]] and by_question[q["id"]][c]["old_accepted"] is not None for c in CONDITIONS)]
        differences = []
        for q in ps:
            r = by_question[q["id"]]
            interactions = {g: int(r[f"HISTORY_ADOPT_{g}"]["old_accepted"]) - int(r[f"HISTORY_AUDIT_{g}"]["old_accepted"])
                - int(r[f"CLEAN_ADOPT_{g}"]["old_accepted"]) + int(r[f"CLEAN_AUDIT_{g}"]["old_accepted"])
                for g in ("HOLISTIC", "FACTORIZED")}
            differences.append(interactions["HOLISTIC"] - interactions["FACTORIZED"])
        contrasts["goal_interaction_holistic_minus_factorized"] = bootstrap(differences)
        contrasts["history_effects"] = {}
        for d, g in itertools.product(("AUDIT", "ADOPT"), ("HOLISTIC", "FACTORIZED")):
            a, b = f"HISTORY_{d}_{g}", f"CLEAN_{d}_{g}"
            ps = [q for q in qs if all(c in by_question[q["id"]] and by_question[q["id"]][c]["old_accepted"] is not None for c in (a, b))]
            contrasts["history_effects"][f"{d}_{g}"] = bootstrap([int(by_question[q["id"]][a]["old_accepted"]) - int(by_question[q["id"]][b]["old_accepted"]) for q in ps])
        for d in ("AUDIT", "ADOPT"):
            required = [f"{h}_{d}_{g}" for h in ("CLEAN", "HISTORY") for g in ("HOLISTIC", "FACTORIZED")]
            ps = [q for q in qs if all(c in by_question[q["id"]] and by_question[q["id"]][c]["old_accepted"] is not None for c in required)]
            vals = []
            for q in ps:
                r = by_question[q["id"]]
                vals.append(int(r[f"HISTORY_{d}_HOLISTIC"]["old_accepted"]) - int(r[f"HISTORY_{d}_FACTORIZED"]["old_accepted"])
                    - int(r[f"CLEAN_{d}_HOLISTIC"]["old_accepted"]) + int(r[f"CLEAN_{d}_FACTORIZED"]["old_accepted"]))
            contrasts[d + "_factorization_history_interaction"] = bootstrap(vals)
        effects[split] = contrasts
    result = dict(status=status, error=error, completed=len(data), planned=m["planned_requests"], conditions=stats,
        effects=effects, per_question=by_question,
        interpretation="Missing judgments are unknown; they are not counted as rejection. Primary HOLISTIC goal-history interaction frozen before GPU. Factorized/general checklist benefits alone are not a new mechanism or history-specific recovery. Groups are reused materials, not independent holdouts.")
    save(out / "summary.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--status", action="store_true")
    a = p.parse_args()
    out = a.output / SUBDIR
    if a.status:
        print(json.dumps(load(out / "run_state.json") if (out / "run_state.json").exists() else dict(status="not_started"), indent=2))
        return
    m = prepare(a.output)
    if a.resume:
        run(a.output, m, subdir=SUBDIR, prompt_fn=prompt_for, score_fn=score, summary_fn=summarize,
            launcher_env="SC_DECISION_VERIFICATION_LAUNCHER")
    elif a.report:
        state = load(out / "run_state.json")
        r = summarize(m, out, state.get("status"), state.get("error"))
        print(json.dumps({k: r[k] for k in ("status", "completed", "conditions", "effects")}, indent=2))
    else:
        print(json.dumps(dict(questions=len(m["questions"]), planned=m["planned_requests"], status="prepared_not_launched")))


if __name__ == "__main__":
    main()
