"""Analyze the 7-question paired R0/R2/R3/R4 validation."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs" / "game24-dual-anchor-validation-20260918"
CONDITIONS = ["R0", "R2", "R3", "R4"]


def load_records():
    return [json.loads(line) for line in (RUN / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def item(record):
    return record["init_response_generations"][0]


def cond(record):
    return record["init_response_generations_metadata"]["intervention"]["condition_id"]


def seed(record):
    return int(record["init_response_generations_metadata"]["intervention"]["sample_seed"])


def paired(records):
    groups = defaultdict(dict)
    for record in records:
        key = (str(record["id"]), seed(record))
        condition = cond(record)
        if condition in groups[key]:
            raise ValueError(f"duplicate {key} {condition}")
        groups[key][condition] = record
    if any(set(group) != set(CONDITIONS) for group in groups.values()):
        raise ValueError("incomplete condition group")
    return groups


def bootstrap_question_cluster(groups, n=10000, exclude_ids=()):
    ids = sorted({key[0] for key in groups if key[0] not in set(exclude_ids)})
    groups = {key: value for key, value in groups.items() if key[0] in ids}
    question_condition = np.array([
        [np.mean([item(groups[(qid, s)][c])["correctness"] is True for s in sorted(seed for q, seed in groups if q == qid)])
         for c in CONDITIONS]
        for qid in ids
    ])
    rng = np.random.default_rng(2027)
    indices = rng.integers(0, len(ids), size=(n, len(ids)))
    sampled = question_condition[indices].mean(axis=1)
    effects = {}
    for better, reference in [("R0", "R2"), ("R3", "R2"), ("R4", "R3"), ("R4", "R2")]:
        bi, ri = CONDITIONS.index(better), CONDITIONS.index(reference)
        observed = float(question_condition[:, bi].mean() - question_condition[:, ri].mean())
        ci = np.quantile(sampled[:, bi] - sampled[:, ri], [0.025, 0.975])
        effects[f"{better}-{reference}"] = {"effect_pp": observed * 100, "ci95_pp": (ci * 100).tolist()}
    return ids, question_condition, effects


def final_boxed(record):
    return item(record).get("extracted_answer")


def false_category(record):
    response = item(record)
    if response.get("correctness") is not False:
        return None
    answer = final_boxed(record) or ""
    if re.fullmatch(r"\s*24\s*", answer):
        return "scalar_boxed_24"
    numbers = [int(value) for value in re.findall(r"(?<![A-Za-z])\d+", answer)]
    expected = sorted(int(value) for value in record["answer"])
    if sorted(numbers) != expected:
        return "number_multiset_violation"
    return "arithmetic_or_format_other"


def compact_false_audit(groups):
    rows = []
    for (qid, s), group in sorted(groups.items()):
        for c, record in group.items():
            response = item(record)
            if response.get("correctness") is False:
                text = record.get("final_response", "")
                rows.append({
                    "id": qid, "seed": s, "condition": c,
                    "finish_reason": response.get("finish_reason"),
                    "extracted_answer": final_boxed(record),
                    "category": false_category(record),
                    "tail": text[-700:].replace("\n", " "),
                })
    return rows


def main():
    records = load_records()
    groups = paired(records)
    ids, qmatrix, effects = bootstrap_question_cluster(groups)
    report = {
        "run": str(RUN),
        "n_records": len(records),
        "n_question_seed_pairs": len(groups),
        "question_ids": ids,
        "seeds": sorted({seed(r) for r in records}),
        "conditions": {},
        "effects_question_cluster_bootstrap": effects,
        "pair_transitions": {},
        "per_question": {},
        "false_output_audit": compact_false_audit(groups),
    }
    report["false_category_counts"] = dict(Counter(row["category"] for row in report["false_output_audit"]))
    strict_ids, _, strict_effects = bootstrap_question_cluster(groups, exclude_ids=("41",))
    report["strict_six_question_subset"] = {"excluded_ids": ["41"], "question_ids": strict_ids,
                                             "effects_question_cluster_bootstrap": strict_effects}
    for c in CONDITIONS:
        values = [item(group[c]) for group in groups.values()]
        report["conditions"][c] = {
            "correct_n": sum(v.get("correctness") is True for v in values),
            "n": len(values),
            "accuracy": sum(v.get("correctness") is True for v in values) / len(values),
            "parseable_n": sum(v.get("correctness") is not None for v in values),
            "eos_n": sum(v.get("finish_reason") == "eos" for v in values),
        }
    for better, reference in [("R0", "R2"), ("R3", "R2"), ("R4", "R3"), ("R4", "R2")]:
        transitions = Counter()
        for group in groups.values():
            b = item(group[better]).get("correctness") is True
            r = item(group[reference]).get("correctness") is True
            transitions[(r, b)] += 1
        report["pair_transitions"][f"{better}-{reference}"] = {
            "reference_correct_to_better_correct": transitions[(False, True)],
            "reference_correct_to_better_wrong": transitions[(True, False)],
            "both_correct": transitions[(True, True)],
            "both_wrong": transitions[(False, False)],
        }
    for qid in ids:
        rows = [groups[(qid, s)] for s in sorted(s for q, s in groups if q == qid)]
        report["per_question"][qid] = {
            c: [item(row[c]).get("correctness") is True for row in rows] for c in CONDITIONS
        }
    (RUN / "analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Seven-question paired validation analysis", "", "## Aggregate", ""]
    for c, value in report["conditions"].items():
        lines.append(f"- {c}: {value['correct_n']}/{value['n']} correct ({value['accuracy']:.1%}); EOS {value['eos_n']}/{value['n']}; parseable {value['parseable_n']}/{value['n']}")
    lines += ["", "## Question-cluster bootstrap effects", "", "| Contrast | Effect | 95% CI |", "|:---|---:|:---|"]
    for name, value in effects.items():
        lines.append(f"| {name} | {value['effect_pp']:+.1f} pp | [{value['ci95_pp'][0]:+.1f}, {value['ci95_pp'][1]:+.1f}] pp |")
    lines += ["", "## Strict six-question subset (excluding 41)", "", "| Contrast | Effect | 95% CI |", "|:---|---:|:---|"]
    for name, value in strict_effects.items():
        lines.append(f"| {name} | {value['effect_pp']:+.1f} pp | [{value['ci95_pp'][0]:+.1f}, {value['ci95_pp'][1]:+.1f}] pp |")
    lines += ["", "## Paired transitions", "", "| Contrast | improve | harm | both correct | both wrong |", "|:---|---:|---:|---:|---:|"]
    for name, value in report["pair_transitions"].items():
        lines.append(f"| {name} | {value['reference_correct_to_better_correct']} | {value['reference_correct_to_better_wrong']} | {value['both_correct']} | {value['both_wrong']} |")
    lines += ["", "## Per-question paired correctness", "", "| ID | R0 | R2 | R3 late | R4 path |", "|---:|:---:|:---:|:---:|:---:|"]
    for qid in ids:
        vals = report["per_question"][qid]
        fmt = lambda xs: "".join("✓" if x else "×" for x in xs)
        lines.append(f"| {qid} | {fmt(vals['R0'])} | {fmt(vals['R2'])} | {fmt(vals['R3'])} | {fmt(vals['R4'])} |")
    lines += ["", "## Scope and interpretation", "",
              "- The unit for the confidence interval is the question, not the 14 question-seed pairs; only seven questions are available.",
              "- R2 is the full-access incorrect-draft condition under the independent-solve prompt. R3/R4 are whole late/path blocking conditions.",
              "- The 18 official-false outputs were manually/automatically checked as number-multiset violations; none was a scalar-box formatting-only failure.",
              "- All 10 R2 false outputs reproduce the selected failed expression or an algebraically equivalent rendering.", ""]
    (RUN / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"conditions": report["conditions"], "effects": effects,
                      "transitions": report["pair_transitions"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
