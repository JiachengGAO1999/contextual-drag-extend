"""Fixed-input, one-label task intervention on the object of auxiliary computation."""
from __future__ import annotations

import argparse
import ast
import copy
import itertools
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression
from run_check_rule_transfer_20261011 import run

SUBDIR = "subject_gated_verification"
SEED = 20261021
CONDITIONS = tuple(f"{h}_{task}_R{r}" for h, task, r in
    itertools.product(("CLEAN", "HISTORY"), ("COPY", "SAME", "OTHER"), (0, 1)))


def other_expression(q):
    node = ast.parse(q["old_audit"]["numeric_expression"], mode="eval").body
    node = copy.deepcopy(node)
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            n.value += 30
    expression = ast.unparse(node)
    audit = audit_expression(expression, [])
    if not audit["parsed"]:
        raise ValueError((q.get("id"), "Invalid shifted arithmetic"))
    original = {int(k): v for k, v in q["old_audit"]["used"].items()}
    if audit["used"] != {k + 30: v for k, v in original.items()} or set(original) & set(audit["used"]):
        raise ValueError("Shifted formula must preserve multiplicities and use disjoint values")
    return audit["numeric_expression"], audit["value"]


def prepare(output):
    out = output / SUBDIR
    if (out / "manifest.json").exists():
        return load(out / "manifest.json")
    source = load(output / "constraint_coupling/manifest.json")
    qs = copy.deepcopy(source["questions"])
    if len(qs) != 48:
        raise ValueError("Use all 48 existing sources")
    rng = random.Random(SEED)
    labels = ["A", "B"] * 24
    rng.shuffle(labels)
    for q, label in zip(qs, labels):
        q["old_label"] = label
        q["other_expression"], q["other_value"] = other_expression(q)
        q["condition_order"] = rng.sample(list(CONDITIONS), len(CONDITIONS))
        for r in (0, 1):
            numbers = q["cases"][f"T1_R{r}"]["numbers"]
            audit = audit_expression(q["old_audit"]["numeric_expression"], numbers)
            if audit["inventory_correct"] != bool(r):
                raise ValueError("Resource truth mismatch")
    m = dict(model=source["model"], dtype=source["dtype"], backend=source["backend"],
        sampling=source["sampling"], max_new_tokens=8192, max_num_seqs=8, seeds=[SEED],
        conditions=list(CONDITIONS), questions=qs, planned_requests=576,
        primary="At R0: [HISTORY(SAME-OTHER)]-[CLEAN(SAME-OTHER)] in counts false acceptance; paired by source question.",
        secondary="COPY contrasts; R1 false rejection; auxiliary arithmetic correctness, missingness, truncation and token cost. Same two booleans in every condition.",
        analysis="All 48 reused sources, existing 24/24 groups, one paired seed; no effect-based selection. Missing unknown, never rejection; source question bootstrap.",
        scope="General arithmetic audits, not original four-card solving. Both formulae and targets visible in every condition; SAME/OTHER change one task-selector character. Shifted formula is synthetic, not a natural failure. Equal tree shape does not guarantee equal model difficulty.",
        estimate=dict(tokens_per_second=350, loading_seconds=300),
        stop="One frozen batch, original shared 24 GPU-hour hard cap; no extra trials, task tuning or head search.")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared_not_launched", completed=0, planned=576))
    return m


def prompt_for(q, condition, seed):
    history, task, resource = condition.split("_")
    label = q["old_label"]
    other = "B" if label == "A" else "A"
    formulas = {label: (q["old_audit"]["numeric_expression"], q["old_audit"]["value"]),
        other: (q["other_expression"], q["other_value"])}
    prompt = ""
    if history == "HISTORY":
        prompt += (f"An earlier, separate problem was:\n{q['problem']}\n"
            "The following draft had an INCORRECT final answer for THAT earlier problem.\n"
            "-- beginning of earlier draft --\n" + q["draft"] + "\n-- end of earlier draft --\n"
            "That verdict applies to the earlier problem. Current requirements follow.\n\n")
    prompt += "CURRENT expression audits. Both rows remain available as data.\n"
    for name in ("A", "B"):
        expression, target = formulas[name]
        prompt += f"Expression {name}: {expression}\nExact arithmetic target for {name}: {target}.\n"
    numbers = q["cases"]["T1_" + resource]["numbers"]
    prompt += (f"The operand multiset applies ONLY to expression {label}: " + ", ".join(map(str, numbers)) + ".\n"
        "Metadata flag: true.\n"
        f"counts_match: Does expression {label}'s numerical operand-occurrence multiset exactly match "
        "its required multiset? Count repeated equal values separately. Other expression rows are not "
        "operands of this expression. The required list may have 4, 5 or 6 occurrences.\n")
    if task == "COPY":
        prompt += "secondary_matches: Copy the provided metadata flag; no arithmetic check is requested.\n"
    else:
        subject = label if task == "SAME" else other
        prompt += f"secondary_matches: Does expression {subject}'s exact arithmetic value equal its own listed target?\n"
    prompt += ("Judge the requested properties independently. Do not solve a new problem or select a formula. "
        "After reasoning, return one JSON object with exactly two boolean fields: counts_match and secondary_matches.")
    return prompt


def score(text, q, seed, condition):
    _, task, resource = condition.split("_")
    truth = resource == "R1"
    result = dict(parsed=False, counts_match=None, secondary_matches=None, counts_truth=truth,
        counts_correct=False, secondary_correct=False, reason="missing_final")
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
    c, s = answer.get("counts_match"), answer.get("secondary_matches")
    cp, sp = type(c) is bool, type(s) is bool
    return dict(result, parsed=cp and sp, counts_match=c if cp else None,
        secondary_matches=s if sp else None, counts_correct=cp and c == truth,
        secondary_correct=sp and s is True, reason=None if cp and sp else "missing_boolean", final_json=answer)


def summarize(m, out, status=None, error=None):
    data = {(r["id"], r["condition"], r["seed"]): r for r in rows(out / "behaviour.jsonl")}
    per = {q["id"]: {c: data[q["id"], c, SEED] for c in CONDITIONS if (q["id"], c, SEED) in data} for q in m["questions"]}
    stats = {}
    for c in CONDITIONS:
        rs = [r for r in data.values() if r["condition"] == c]
        stats[c] = dict(n=len(rs), parsed=sum(r["parsed"] for r in rs),
            counts_observed=sum(r["counts_match"] is not None for r in rs),
            counts_accepted=sum(r["counts_match"] is True for r in rs), counts_correct=sum(r["counts_correct"] for r in rs),
            secondary_observed=sum(r["secondary_matches"] is not None for r in rs),
            secondary_correct=sum(r["secondary_correct"] for r in rs),
            length_stops=sum(r["finish_reason"] == "length" for r in rs), generated_tokens=sum(r["generated_tokens"] for r in rs))
    effects = {}
    for split in ("all", "group_a", "group_b"):
        qs = [q for q in m["questions"] if split == "all" or q["split"] == split]
        contrasts = {}
        for resource in ("R0", "R1"):
            for name, a_task, b_task in (("same_minus_other", "SAME", "OTHER"),
                ("same_minus_copy", "SAME", "COPY"), ("other_minus_copy", "OTHER", "COPY")):
                values = {}
                for h in ("CLEAN", "HISTORY"):
                    a, b = f"{h}_{a_task}_{resource}", f"{h}_{b_task}_{resource}"
                    values[h] = {q["id"]: int(per[q["id"]][a]["counts_match"]) - int(per[q["id"]][b]["counts_match"])
                        for q in qs if all(c in per[q["id"]] and per[q["id"]][c]["counts_match"] is not None for c in (a,b))}
                common = sorted(values["CLEAN"].keys() & values["HISTORY"].keys())
                delta = [values["HISTORY"][qid] - values["CLEAN"][qid] for qid in common]
                contrasts[f"{resource}_{name}"] = dict(clean=bootstrap(list(values["CLEAN"].values())),
                    history=bootstrap(list(values["HISTORY"].values())), history_interaction=bootstrap(delta),
                    directions=dict(positive=sum(v>0 for v in delta), negative=sum(v<0 for v in delta), zero=sum(v==0 for v in delta)))
        effects[split] = contrasts
    result = dict(status=status, error=error, completed=len(data), planned=m["planned_requests"],
        conditions=stats, effects=effects, per_question=per,
        interpretation="Primary R0 SAME-OTHER history interaction. R1 contrasts are differences in acceptance, not false-rejection differences. SAME/OTHER differ only in auxiliary subject selector; arithmetic difficulty and object switching remain possible explanations. No neural cache or internal retrieval proven.")
    save(out / "summary.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    for flag in ("prepare", "resume", "status", "report"):
        p.add_argument("--"+flag, action="store_true")
    a = p.parse_args()
    out = a.output / SUBDIR
    if a.status:
        print(json.dumps(load(out/"run_state.json") if (out/"run_state.json").exists() else dict(status="not_started"), indent=2))
        return
    m = prepare(a.output)
    if a.resume:
        run(a.output, m, subdir=SUBDIR, prompt_fn=prompt_for, score_fn=score, summary_fn=summarize,
            launcher_env="SC_SUBJECT_GATED_LAUNCHER")
    elif a.report:
        state = load(out / "run_state.json")
        result = summarize(m, out, state.get("status"), state.get("error"))
        print(json.dumps({k:result[k] for k in ("status", "completed", "conditions", "effects")}, indent=2))
    else:
        print(json.dumps(dict(status="prepared_not_launched", questions=len(m["questions"]), requests=m["planned_requests"])))


if __name__ == "__main__":
    main()
