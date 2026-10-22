"""Changing a target must not silently change resource truth or expression evidence."""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_constraint_coupling_20261011 import build_cases, prompt_for, score
from run_identity_mvp_20261011 import audit_expression


def question(expression="(6+6)*(10/(6-1))"):
    q = dict(answer=[1, 6, 6, 10], problem="Original Game24 task.", draft="Original draft.")
    q["old_audit"] = audit_expression(expression, q["answer"])
    q["cases"] = build_cases(q)
    return q


def test_four_counterfactuals_have_exact_independent_truths():
    q = question()
    for key, case in q["cases"].items():
        audit = audit_expression(q["old_audit"]["numeric_expression"], case["numbers"])
        assert (Fraction(audit["value"]) == Fraction(case["target"])) == case["value_truth"]
        assert audit["inventory_correct"] == case["counts_truth"]
    assert q["cases"]["T1_R0"]["numbers"] == q["cases"]["T0_R0"]["numbers"]
    assert q["cases"]["T1_R0"]["target"] == q["cases"]["T1_R1"]["target"]


def test_value_only_source_still_has_a_real_resource_mismatch_cell():
    q = question("(1+6)*(10-6)")
    assert q["old_audit"]["inventory_correct"]
    assert not audit_expression(q["old_audit"]["numeric_expression"], q["cases"]["T0_R0"]["numbers"])["inventory_correct"]
    assert q["cases"]["T1_R0"]["target"] == "28"
    assert q["cases"]["T0_R0"]["target"] == "24"


def test_target_intervention_only_changes_the_target_line():
    q = question()
    a = prompt_for(q, "HISTORY_T1_R0", 20)
    b = prompt_for(q, "HISTORY_T0_R0", 20)
    assert a.replace("Required exact arithmetic target: 24.", "Required exact arithmetic target: 25.") == b


def test_counts_only_does_not_invent_a_value_judgment_or_treat_missing_as_false():
    q = question()
    r = score('</think>' + json.dumps(dict(counts_match=False)), q, 20, "CLEAN_COUNTS")
    assert r["parsed"] and r["counts_correct"] and r["value_matches"] is None
    r = score('</think>{"value_matches": false}', q, 20, "CLEAN_T0_R0")
    assert not r["parsed"] and r["counts_match"] is None
