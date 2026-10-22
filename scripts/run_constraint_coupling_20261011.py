"""Exact same-expression interventions on current target and operand inventory."""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression
from run_check_rule_transfer_20261011 import run

SUBDIR = "constraint_coupling"
SEED = 20261020
CONDITIONS = tuple(f"{h}_T{t}_R{r}" for h in ("CLEAN", "HISTORY") for t, r in itertools.product((1, 0), repeat=2)) + ("CLEAN_COUNTS", "HISTORY_COUNTS")


def build_cases(q):
    e = q["old_audit"]["numeric_expression"]
    actual = sorted(int(n) for n, count in q["old_audit"]["used"].items() for _ in range(count))
    mismatch = sorted(q["answer"])
    if Counter(actual) == Counter(mismatch):
        mismatch[0] += 1
        mismatch.sort()
    v = Fraction(q["old_audit"]["value"])
    other = Fraction(25) if v == 24 else Fraction(24)
    cases = {}
    for t, r in itertools.product((1, 0), repeat=2):
        ns = actual if r else mismatch
        target = str(v if t else other)
        audit = audit_expression(e, ns)
        if (Fraction(audit["value"]) == Fraction(target), audit["inventory_correct"]) != (bool(t), bool(r)):
            raise ValueError("Counterfactual truth mismatch")
        cases[f"T{t}_R{r}"] = dict(numbers=ns, target=target, value_truth=bool(t), counts_truth=bool(r))
    return cases


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = load(output / "decision_verification/manifest.json")
    questions = source["questions"]
    if len(questions) != 48:
        raise ValueError("Preserve the complete 48-question pool")
    rng = random.Random(SEED)
    for q in questions:
        q["cases"] = build_cases(q)
        q["condition_order"] = rng.sample(list(CONDITIONS), len(CONDITIONS))
    m = dict(model=source["model"], dtype=source["dtype"], backend=source["backend"], sampling=source["sampling"],
        max_new_tokens=8192, max_num_seqs=8, seeds=[SEED], conditions=list(CONDITIONS), questions=questions, planned_requests=480,
        primary="Resource false acceptance T1 minus T0 at R0; report CLEAN, HISTORY and their history interaction. Same expression, resource truth and history across target intervention.",
        secondary="Value false acceptance R1 minus R0 at T0; current-truth responsiveness, counts-only baseline, false rejection, missingness and tokens.",
        scope="General arithmetic expression checking with 4-6 inputs; reused natural failed expressions but counterfactual current tasks. Not all cells are original Game24. Feedback explicitly refers to the original task; current constraints are separately declared.",
        analysis="All 48 questions retained, same prior 24/24 groups. One paired seed. Exact Fraction and Counter truths; no correct verdict, operand ledger or error location supplied. Missing is unknown, never rejection; question-level bootstrap.",
        estimate=dict(tokens_per_second=350, loading_seconds=300), stop="One frozen batch and original shared 24 GPU-hour cap; no difficulty tuning or automatic expansion.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", completed=0, planned=480))
    return m


def prompt_for(q, condition, seed):
    history = condition.startswith("HISTORY_")
    only_counts = condition.endswith("_COUNTS")
    key = "T1_R0" if only_counts else condition.split("_", 1)[1]
    case = q["cases"][key]
    prompt = ""
    if history:
        prompt += (f"An earlier, separate problem was:\n{q['problem']}\n"
            "The following draft had an INCORRECT final answer for THAT earlier problem.\n"
            "-- beginning of earlier draft --\n" + q["draft"] + "\n-- end of earlier draft --\n"
            "That verdict applies to the earlier problem. The current requirements are given below.\n\n")
    prompt += ("CURRENT expression-checking task; the input multiset can have any listed number of occurrences.\n"
        "Required operand multiset: " + ", ".join(map(str, case["numbers"])) + ".\n")
    if not only_counts:
        prompt += f"Required exact arithmetic target: {case['target']}.\n"
    prompt += f"Expression to check: {q['old_audit']['numeric_expression']}\n"
    prompt += ("counts_match asks whether the numerical operand occurrences in this expression exactly "
        "match the CURRENT required multiset, counting repeated equal values separately. "
        "Allowed operations are +, -, *, / and parentheses. ")
    if only_counts:
        prompt += ("Only operand usage is being checked; no current numerical target is specified or required. "
            "After reasoning, return one JSON object with the single boolean field counts_match.")
    else:
        prompt += ("value_matches asks whether the exact arithmetic value equals the CURRENT required target. "
            "Judge the two properties independently, even when one is false. Do not search for a new "
            "expression or adopt an answer. After reasoning, return one JSON object with the two boolean "
            "fields value_matches and counts_match.")
    return prompt


def score(text, q, seed, condition):
    only_counts = condition.endswith("_COUNTS")
    key = "T1_R0" if only_counts else condition.split("_", 1)[1]
    case = q["cases"][key]
    result = dict(parsed=False, counts_match=None, value_matches=None, counts_correct=False,
        value_correct=None if only_counts else False, counts_truth=case["counts_truth"],
        value_truth=None if only_counts else case["value_truth"], reason="missing_final")
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
    c, v = answer.get("counts_match"), answer.get("value_matches")
    cp, vp = type(c) is bool, type(v) is bool and not only_counts
    return dict(result, parsed=cp and (vp or only_counts), counts_match=c if cp else None,
        value_matches=v if vp else None, counts_correct=cp and c == case["counts_truth"],
        value_correct=vp and v == case["value_truth"] if not only_counts else None,
        reason=None if cp and (vp or only_counts) else "missing_boolean", final_json=answer)


def summarize(m, out, status=None, error=None):
    data = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "behaviour.jsonl")}
    per = {q["id"]: {c: data[q["id"], c, SEED] for c in CONDITIONS if (q["id"], c, SEED) in data} for q in m["questions"]}
    stats = {}
    for c in CONDITIONS:
        rs = [r for r in data.values() if r["condition"] == c]
        stats[c] = dict(n=len(rs), parsed=sum(r["parsed"] for r in rs),
            counts_observed=sum(r["counts_match"] is not None for r in rs), counts_accepted=sum(r["counts_match"] is True for r in rs),
            counts_correct=sum(r["counts_correct"] for r in rs),
            value_observed=sum(r["value_matches"] is not None for r in rs), value_accepted=sum(r["value_matches"] is True for r in rs),
            value_correct=sum(r["value_correct"] is True for r in rs), length_stops=sum(r["finish_reason"] == "length" for r in rs),
            generated_tokens=sum(r["generated_tokens"] for r in rs))
    effects = {}
    for split in ("all", "group_a", "group_b", "original_inventory_violation"):
        qs = [q for q in m["questions"] if split == "all" or q["split"] == split or
              (split == "original_inventory_violation" and not q["old_audit"]["inventory_correct"])]
        contrasts = {}
        for name, field, suffix_a, suffix_b in (("resource_coupling", "counts_match", "T1_R0", "T0_R0"),
            ("value_coupling", "value_matches", "T0_R1", "T0_R0"),
            ("counts_only_gain", "counts_match", "T1_R0", "COUNTS")):
            values = {}
            for h in ("CLEAN", "HISTORY"):
                a, b = f"{h}_{suffix_a}", f"{h}_{suffix_b}"
                values[h] = {q["id"]: int(per[q["id"]][a][field]) - int(per[q["id"]][b][field]) for q in qs
                    if all(c in per[q["id"]] and per[q["id"]][c][field] is not None for c in (a, b))}
            common = sorted(values["CLEAN"].keys() & values["HISTORY"].keys())
            interaction = [values["HISTORY"][qid] - values["CLEAN"][qid] for qid in common]
            contrasts[name] = dict(clean=bootstrap(list(values["CLEAN"].values())), history=bootstrap(list(values["HISTORY"].values())),
                history_interaction=bootstrap(interaction), directions=dict(positive=sum(v > 0 for v in interaction),
                    negative=sum(v < 0 for v in interaction), zero=sum(v == 0 for v in interaction)))
        effects[split] = contrasts
    result = dict(status=status, error=error, completed=len(data), planned=m["planned_requests"], conditions=stats,
        effects=effects, per_question=per, interpretation="Primary resource coupling changes only the current target within paired cells. A history main effect or counts-only benefit alone does not establish cross-constraint coupling. All 48 reused questions retained; missing judgments are unknown. Groups are not independent holdouts.")
    save(out / "summary.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    out = a.output / SUBDIR
    if a.status:
        print(json.dumps(load(out / "run_state.json") if (out / "run_state.json").exists() else dict(status="not_started"), indent=2))
        return
    m = prepare(a.output)
    if a.resume:
        run(a.output, m, subdir=SUBDIR, prompt_fn=prompt_for, score_fn=score, summary_fn=summarize,
            launcher_env="SC_CONSTRAINT_COUPLING_LAUNCHER")
    elif a.report:
        state = load(out / "run_state.json")
        r = summarize(m, out, state.get("status"), state.get("error"))
        print(json.dumps({k: r[k] for k in ("status", "completed", "conditions", "effects")}, indent=2))
    else:
        print(json.dumps(dict(status="prepared_not_launched", questions=len(m["questions"]), requests=m["planned_requests"])))


if __name__ == "__main__":
    main()
