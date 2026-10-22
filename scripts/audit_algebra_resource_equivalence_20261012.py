"""CPU audit of a specific explanation: illegal algebraic expansions of legal forms.

Enumerate all binary four-card expressions over +,-,*,/. Distinct numeric values
become independent formal variables; equal card values share a variable. Exact
probe evaluations reject nonidentities, and SymPy verifies surviving identities.
This cannot establish what a language model represents or infer causality.
"""

import ast
from collections import Counter
from fractions import Fraction
from functools import lru_cache
import json
from pathlib import Path

import sympy as sp


def evaluate(node, values):
    if isinstance(node, ast.Expression):
        return evaluate(node.body, values)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return values[node.value]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -evaluate(node.operand, values)
    if isinstance(node, ast.BinOp):
        left, right = evaluate(node.left, values), evaluate(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    raise ValueError("Unsupported expression")


def four_card_forms(numbers):
    @lru_cache(None)
    def forms(mask):
        if mask and not (mask & (mask - 1)):
            value = numbers[mask.bit_length() - 1]
            return {str(value): Fraction(value)}
        result = {}
        left_mask = (mask - 1) & mask
        while left_mask:
            right_mask = mask ^ left_mask
            for left, lv in forms(left_mask).items():
                for right, rv in forms(right_mask).items():
                    for op, value in [("+", lv + rv), ("-", lv - rv),
                                      ("*", lv * rv)]:
                        result[f"({left}{op}{right})"] = value
                    if rv:
                        result[f"({left}/{right})"] = lv / rv
            left_mask = (left_mask - 1) & mask
        return result
    return forms((1 << len(numbers)) - 1)


def inspect(numbers, expression):
    tree = ast.parse(expression, mode="eval")
    used = Counter(n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and type(n.value) is int)
    card_values = sorted(set(numbers))
    if not set(used).issubset(card_values):
        raise ValueError("Expression contains a value outside its card set")
    numeric = evaluate(tree, {v: Fraction(v) for v in card_values})
    direct_neutral = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and ast.dump(node.left) == ast.dump(node.right):
            if isinstance(node.op, ast.Div):
                direct_neutral.append({"type": "identical_subtree_ratio",
                                       "subtree": ast.unparse(node)})
            elif isinstance(node.op, ast.Sub):
                direct_neutral.append({"type": "identical_subtree_difference",
                                       "subtree": ast.unparse(node)})
    result = {
        "numbers": numbers, "old_expression": expression,
        "old_value": str(numeric), "used": dict(used),
        "same_value_set": set(used) == set(numbers),
        "same_value_multiset": used == Counter(numbers),
        "direct_neutral_subtrees": direct_neutral,
    }
    if numeric != 24:
        return {**result, "status": "target_wrong_not_eligible_for_24_identity"}

    symbols = {v: sp.Symbol(f"x{i}") for i, v in enumerate(card_values)}
    old_symbolic = evaluate(tree, symbols)
    probe_primes = [7, 11, 17, 23, 31, 43, 59, 71]
    probes = []
    for shift in range(4):
        values = {v: Fraction(probe_primes[i + shift])
                  for i, v in enumerate(card_values)}
        try:
            probes.append((values, evaluate(tree, values)))
        except ZeroDivisionError:
            pass
    matches = []
    candidates = [(text, value) for text, value in four_card_forms(numbers).items()
                  if value == 24]
    exact_checks = 0
    for text, _ in candidates:
        candidate_tree = ast.parse(text, mode="eval")
        rejected = False
        for values, old_probe in probes:
            try:
                new_probe = evaluate(candidate_tree, values)
            except ZeroDivisionError:
                # A point outside the candidate's domain cannot refute a
                # rational identity on their common domain.
                continue
            if old_probe != new_probe:
                rejected = True
                break
        if rejected:
            continue
        exact_checks += 1
        candidate_symbolic = evaluate(candidate_tree, symbols)
        if sp.cancel(old_symbolic - candidate_symbolic) == 0:
            matches.append(text)
    return {
        **result, "status": "formal_identity_checked",
        "symbol_map": {str(v): str(s) for v, s in symbols.items()},
        "old_symbolic_reduced": str(sp.cancel(old_symbolic)),
        "legal_numeric_24_candidates": len(candidates),
        "exact_symbolic_checks": exact_checks,
        "formally_equivalent_legal_candidates": len(matches),
        "legal_identity_witness": matches[0] if matches else None,
    }


if __name__ == "__main__":
    # A known distributivity witness verifies that the audit can detect the
    # proposed relation. It is not a research sample or model-generated case.
    control = inspect([2, 3, 5, 8], "((2*3)+(2*5))+8")
    if not control["formally_equivalent_legal_candidates"]:
        raise AssertionError("Failed to recover known distributivity identity")
    base = Path("outputs/generation-diagnostics-20261005")
    source = base / "candidate_adoption/failure_pool.json"
    questions = json.loads(source.read_text(encoding="utf-8"))["questions"]
    records = [{"id": q["id"], "source": q["source"],
                **inspect(q["answer"], q["old_audit"]["numeric_expression"])}
               for q in questions]
    eligible = [r for r in records if r["status"] == "formal_identity_checked"]
    summary = {
        "status": "cpu_only_no_model_calls",
        "source": str(source), "questions": len(records),
        "target_correct_questions": len(eligible),
        "same_value_set_questions": sum(r["same_value_set"] for r in records),
        "wrong_value_multiset_questions": sum(not r["same_value_multiset"] for r in records),
        "with_direct_neutral_subtree": sum(bool(r["direct_neutral_subtrees"]) for r in records),
        "formal_legal_identity_questions": sum(
            bool(r["formally_equivalent_legal_candidates"]) for r in eligible),
        "control": control,
        "scope": (
            "Formal equivalence treats every distinct input value, including 1, "
            "as a variable and duplicate equal values as one shared variable. "
            "Identities hold on common defined domains; numeric coincidences "
            "and implicit free constants are not formal identities here. "
            "Neither associations nor identities establish model mechanisms."
        ),
    }
    output = base / "algebra_resource_preview"
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_text(json.dumps(
        {"summary": summary, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
