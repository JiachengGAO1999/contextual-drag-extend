"""The readout must distinguish correct checks, inconsistent adoption, and unknowns."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_decision_verification_20261011 import prompt_for, score


def question():
    return dict(answer=[1, 6, 6, 10], problem="Use 1, 6, 6, 10 to make 24.",
        draft="An old failed attempt.", old_index=2, old_numeric="(6+6)*(10/(6-1))",
        legal_numeric="(1*6)*(10-6)", old_audit=dict(target_correct=True, inventory_correct=False))


def answer():
    return dict(option_1_valid=True, option_2_valid=False, choice=1,
        option_1_value_matches=True, option_1_counts_match=True,
        option_2_value_matches=True, option_2_counts_match=False)


def test_correct_atomic_checks_do_not_hide_inconsistent_overall_acceptance():
    a = answer()
    a["option_2_valid"] = True
    r = score("</think>" + json.dumps(a), question(), 19, "HISTORY_ADOPT_FACTORIZED")
    assert r["properties_correct"] and r["old_accepted"]
    assert r["correct_properties_but_old_accepted"]
    assert r["conjunction_consistent"] is False


def test_audit_has_no_choice_accuracy_and_missing_validity_is_not_rejection():
    a = answer()
    a["choice"] = None
    r = score("</think>" + json.dumps(a), question(), 19, "CLEAN_AUDIT_FACTORIZED")
    assert r["parsed"] and r["judgments_correct"]
    assert r["choice_correct"] is None
    del a["option_2_valid"]
    r = score("</think>" + json.dumps(a), question(), 19, "CLEAN_AUDIT_FACTORIZED")
    assert not r["judgments_parsed"] and r["old_accepted"] is None


def test_goal_and_granularity_leave_history_inventory_and_candidates_identical():
    q = question()
    ps = [prompt_for(q, f"HISTORY_{d}_{g}", 19) for d in ("AUDIT", "ADOPT") for g in ("HOLISTIC", "FACTORIZED")]
    assert len({p.split("Evaluate both options")[0] for p in ps}) == 1
    assert "Option 1: " + q["legal_numeric"] in ps[0]
    assert "Option 2: " + q["old_numeric"] in ps[0]
    assert "value null" in ps[0] and "integer value 1 or 2" in ps[2]
