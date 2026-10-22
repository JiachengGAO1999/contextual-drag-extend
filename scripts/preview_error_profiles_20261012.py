"""CPU material feasibility preview. Never loads a model or submits requests."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from itertools import permutations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHAPES = (((0, 1), 2), 3), ((0, (1, 2)), 3), ((0, 1), (2, 3)), (0, ((1, 2), 3)), (0, (1, (2, 3)))
OPS = ("+", "-", "*", "/")


def expression(shape, ops, leaves):
    it = iter(ops)

    def visit(node):
        if isinstance(node, int):
            return str(leaves[node])
        op = next(it)
        return f"({visit(node[0])}{op}{visit(node[1])})"

    return visit(shape)


def evaluate(shape, ops, leaves):
    it = iter(ops)

    def visit(node):
        if isinstance(node, int):
            return Fraction(leaves[node])
        op = next(it)
        a, b = visit(node[0]), visit(node[1])
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        return a / b

    try:
        return visit(shape)
    except ZeroDivisionError:
        return None


def distance(a, b):
    return sum(x != y for x, y in zip(a, b))


def material(numbers):
    legal = sorted(set(permutations(numbers)))
    required = Counter(numbers)
    illegal = sorted({a[:i] + (v,) + a[i + 1:]
                      for a in legal for i in range(4) for v in sorted(required) if v != a[i]})
    for shape_id, shape in enumerate(SHAPES):
        for ops in product(OPS, repeat=3):
            lv = {a: evaluate(shape, ops, a) for a in legal}
            good = [a for a in legal if lv[a] == 24]
            if not good:
                continue
            iv = {a: evaluate(shape, ops, a) for a in illegal}
            rs = [a for a in illegal if iv[a] == 24 and min(distance(a, g) for g in good) == 2]
            vs = [a for a in legal if lv[a] is not None and lv[a] != 24
                  and min(distance(a, g) for g in good) == 2]
            for g in good:
                for r in rs:
                    if distance(r, g) != 2:
                        continue
                    v = next((a for a in vs if distance(a, g) == 2), None)
                    b = next((a for a in sorted(set(permutations(r)))
                              if iv.get(a) is not None and iv[a] != 24 and distance(a, g) == 2
                              and min(distance(a, s) for s in good) == 2), None)
                    if v is None or b is None:
                        continue
                    profiles = {}
                    for name, a in (("BOTH_VALID", g), ("RESOURCE_ONLY_ERROR", r),
                                    ("TARGET_ONLY_ERROR", v), ("BOTH_ERROR", b)):
                        value = evaluate(shape, ops, a)
                        profiles[name] = dict(expression=expression(shape, ops, a),
                            value=str(value), target_correct=value == 24,
                            inventory_correct=Counter(a) == required, leaves=list(a),
                            substitutions_from_reference=distance(a, g),
                            minimum_substitutions_to_same_skeleton_valid=min(distance(a, s) for s in good))
                    assert Counter(r) == Counter(b)
                    return dict(shape_id=shape_id, operators=list(ops), profiles=profiles)
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005/candidate_adoption/manifest.json")
    p.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005/error_profile_preview")
    a = p.parse_args()
    source = json.loads(a.source.read_text(encoding="utf8"))
    records, missing = [], []
    for q in source["questions"]:
        m = material(q["answer"])
        if m is None:
            missing.append(dict(id=q["id"], reason="No four-profile match under the stated restrictions."))
        else:
            records.append(dict(id=q["id"], numbers=q["answer"], **m))
    result = dict(scope="CPU construction feasibility on the existing frozen question list; not a held-out experiment or execution manifest.",
        source=str(a.source), model_requests=0, gpu_launch_authorized_by_this_file=False,
        matching="Same four-leaf ordered tree and operators within a question; each failed profile has two leaf substitutions to the reference and to its closest valid leaf assignment under this fixed skeleton. Illegal profiles share the same multiset. This is not global repair distance, token-length matching or a natural-draft distribution.",
        questions=len(source["questions"]), available=len(records), missing=missing, records=records)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "preview.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(dict(questions=result["questions"], available=len(records), missing=len(missing), model_requests=0)))


if __name__ == "__main__":
    main()
