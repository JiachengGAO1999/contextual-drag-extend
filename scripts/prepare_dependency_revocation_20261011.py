"""CPU-only feasibility materials; no model loading or GPU launch entrypoint."""
from __future__ import annotations

import argparse
import json
import random
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261011
CONDITIONS = ("CLEAN", "GENERAL", "LOCAL")


def evaluate(steps):
    """Keep mathematical truth, cached arithmetic and ancestry separate."""
    truth, cache, ancestors, result = {}, {}, {}, []
    for step in steps:
        name, left, right = step["id"], step["left"], step["right"]
        if name in truth:
            raise ValueError(f"Duplicate node: {name}")
        parents = [x for x in (left, right) if isinstance(x, str)]
        if any(x not in truth for x in parents):
            raise ValueError(f"Forward reference or unknown parent: {name}")
        def operand(x, values):
            return values[x] if isinstance(x, str) else Fraction(x)
        def calculate(values):
            a, b = operand(left, values), operand(right, values)
            if step["op"] == "+": return a + b
            if step["op"] == "-": return a - b
            if step["op"] == "*": return a * b
            raise ValueError(f"Unsupported operation: {step['op']}")
        true_value, local_value = calculate(truth), calculate(cache)
        cached_value = Fraction(step.get("cached", local_value))
        truth[name], cache[name] = true_value, cached_value
        ancestors[name] = set(parents)
        for parent in parents:
            ancestors[name].update(ancestors[parent])
        result.append(dict(id=name, true_value=str(true_value), cached_value=str(cached_value),
            locally_consistent=cached_value == local_value,
            mathematically_correct=cached_value == true_value,
            ancestors=sorted(ancestors[name])))
    return result


def make_variant(parameters, swapped):
    t, q, r, delta, increment, multiplier = parameters
    wrong = t + delta
    steps = [
        dict(id="S1", left=t+q, op="-", right=q, cached=wrong),
        dict(id="S2", left=r, op="+", right=wrong-r),
        dict(id="S3", left="S2" if swapped else "S1", op="+", right=increment),
        dict(id="S4", left="S1" if swapped else "S2", op="+", right=increment),
        dict(id="S5", left="S3", op="*", right=multiplier),
        dict(id="S6", left="S4", op="*", right=multiplier),
    ]
    oracle = evaluate(steps)
    for step, row in zip(steps, oracle):
        step["cached"] = row["cached_value"]
    common = (
        "Recompute this arithmetic worksheet from its defining equations. "
        "Step names refer to their recomputed values, not the old cached values. "
        "Use standard exact arithmetic. Return only the value of the requested step.\n"
        "Defining equations:\n" + "\n".join(
            f"{s['id']} = {s['left']} {s['op']} {s['right']}" for s in steps) + "\n"
    )
    draft = "Old cached worksheet:\n" + "\n".join(
        f"{s['id']} = {s['cached']}" for s in steps) + "\n"
    feedback = {
        "GENERAL": "Verified feedback: the old worksheet contains an incorrect calculation.\n",
        "LOCAL": "Verified feedback: the old cached value of S1 is incorrect.\n",
    }
    prompts = {"CLEAN": common}
    prompts.update({name: common + draft + text for name, text in feedback.items()})
    readouts = []
    for node in ("S1", "S5", "S6"):
        row = next(x for x in oracle if x["id"] == node)
        # Both terminal nodes get identical candidate values in both wirings.
        corrected = t if node == "S1" else (t+increment)*multiplier
        old = wrong if node == "S1" else (wrong+increment)*multiplier
        readouts.append(dict(node=node, stem=f"Requested step: {node}\nValue:",
            candidates={"changed": f" {corrected}\n", "old": f" {old}\n"},
            gold="changed" if row["true_value"] == str(corrected) else "old",
            gold_value=row["true_value"],
            depends_on_error=node == "S1" or "S1" in row["ancestors"]))
    return dict(wiring="swapped" if swapped else "original", steps=steps, oracle=oracle,
                prompts=prompts, readouts=readouts)


def build_materials(count=8):
    # This set checks material feasibility; it is not an inferential sample size.
    pool = [(t, q, r, delta, inc, mul)
        for t in range(10, 31) for q in (5, 7, 9) for delta in (-2, -1, 1, 2)
        for r in (3, 6, 8) for inc in (3, 4, 6) for mul in (2, 3)
        if 0 < r < t+delta]
    random.Random(SEED).shuffle(pool)
    chosen, seen = [], set()
    for parameters in pool:
        key = parameters[:4]
        if key in seen: continue
        seen.add(key)
        chosen.append(dict(id=f"cpu_example_{len(chosen)+1:02d}", parameters=list(parameters),
            variants=[make_variant(parameters, False), make_variant(parameters, True)]))
        if len(chosen) == count: break
    if count <= 0 or len(chosen) != count:
        raise ValueError("Requested material count is outside the available pool")
    return chosen


def audit_materials(questions):
    for question in questions:
        a, b = question["variants"]
        assert [s["cached"] for s in a["steps"]] == [s["cached"] for s in b["steps"]]
        changed_edges = [(x["id"], field) for x, y in zip(a["steps"], b["steps"])
                         for field in x if x[field] != y[field]]
        assert changed_edges == [("S3", "left"), ("S4", "left")]
        for variant in (a, b):
            assert evaluate(variant["steps"]) == variant["oracle"]
            assert [r["id"] for r in variant["oracle"] if not r["locally_consistent"]] == ["S1"]
            assert variant["readouts"][0]["gold"] == "changed"
            assert sorted(r["gold"] for r in variant["readouts"][1:]) == ["changed", "old"]
            for row in variant["readouts"]:
                assert Fraction(row["candidates"][row["gold"]].strip()) == Fraction(row["gold_value"])
            assert "Old cached worksheet:" not in variant["prompts"]["CLEAN"]
        for x, y in zip(a["readouts"], b["readouts"]):
            assert x["stem"] == y["stem"] and x["candidates"] == y["candidates"]
            if x["node"] != "S1": assert x["gold"] != y["gold"]
    return dict(status="cpu_semantic_audit_passed_not_gpu_ready", base_examples=len(questions),
        wiring_variants=2*len(questions), seed=SEED, model_calls=0, gpu_seconds=0,
        scope="Exact arithmetic, unique local fault, two-edge swap, unchanged cached numbers, flipped terminal gold labels.",
        pending=["Mechanistic novelty decision", "Connection to natural Contextual Drag", "GPU protocol and actual timing"],
        not_claimed=["Token length matching", "Model outcomes", "Spontaneous error recognition", "Statistical confirmation"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
        default=ROOT/"outputs/generation-diagnostics-20261005/dependency_revocation_feasibility")
    args = parser.parse_args()
    questions = build_materials()
    audit = audit_materials(questions)
    args.output.mkdir(parents=True, exist_ok=True)
    payload = dict(status="design_feasibility_only_not_frozen_gpu_protocol", seed=SEED,
        domain="Constructed arithmetic DAG; not Game24 or natural model reasoning",
        conditions=list(CONDITIONS), questions=questions,
        inferential_unit="Numeric base graph; wiring/readout variants are not independent items")
    for name, value in (("examples.json", payload), ("audit.json", audit)):
        (args.output/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf8")
    lines = ["# Dependency-revocation feasibility examples", "",
        "CPU construction only. No GPU batch is frozen or queued.", "",
        "The equations and old cached values are separate. S1 is the only locally false calculation; "
        "its descendants may be locally consistent but globally wrong. Only S3/S4 parent names change across a pair.", ""]
    for question in questions:
        lines.extend([f"## {question['id']}", ""])
        for variant in question["variants"]:
            lines.extend([f"### {variant['wiring']}", "", "```text", variant["prompts"]["LOCAL"].rstrip(), "```", "",
                "| Step | True value | Old cached value | Depends on S1 |", "|---|---:|---:|---|"])
            for row in variant["oracle"]:
                lines.append(f"| {row['id']} | {row['true_value']} | {row['cached_value']} | "
                             f"{row['id'] == 'S1' or 'S1' in row['ancestors']} |")
            lines.append("")
    (args.output/"materials.md").write_text("\n".join(lines)+"\n", encoding="utf8")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
