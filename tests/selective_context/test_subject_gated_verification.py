"""Preserve arithmetic and resource truth under a one-label task intervention."""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_constraint_coupling_20261011 import build_cases
from run_identity_mvp_20261011 import audit_expression
from run_subject_gated_verification_20261011 import other_expression, prompt_for, score


def question():
    q = dict(id="x", problem="Original Game24.", draft="Old reasoning.", answer=[1,6,6,10], old_label="B")
    q["old_audit"] = audit_expression("(6+6)*(10/(6-1))", q["answer"])
    q["cases"] = build_cases(q)
    q["other_expression"], q["other_value"] = other_expression(q)
    return q


def test_shift_preserves_every_operand_occurrence_and_exact_value():
    q = question()
    audit = audit_expression(q["other_expression"], [])
    assert audit["used"] == {k+30:v for k,v in q["old_audit"]["used"].items()}
    assert Fraction(audit["value"]) == Fraction(576)


def test_same_other_intervention_changes_only_auxiliary_subject():
    q = question()
    a = prompt_for(q, "HISTORY_SAME_R0", 21)
    b = prompt_for(q, "HISTORY_OTHER_R0", 21)
    assert a.replace("secondary_matches: Does expression B's", "secondary_matches: Does expression A's") == b
    assert "applies ONLY to expression B" in a


def test_resource_truth_is_current_multiset_and_secondary_truth_is_independent():
    q = question()
    text = '</think>' + json.dumps(dict(counts_match=False, secondary_matches=True))
    r = score(text, q, 21, "CLEAN_OTHER_R0")
    assert r["parsed"] and r["counts_correct"] and r["secondary_correct"]
    r = score(text, q, 21, "CLEAN_OTHER_R1")
    assert not r["counts_correct"] and r["secondary_correct"]


def test_missing_counts_remain_unknown_even_if_secondary_present():
    r = score('</think>{"secondary_matches": true}', question(), 21, "CLEAN_COPY_R0")
    assert not r["parsed"] and r["counts_match"] is None
