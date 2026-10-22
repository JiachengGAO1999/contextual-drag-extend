"""Counterfactual truth labels and missing observations must stay distinct."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_check_rule_transfer_20261011 import change_value, leaves, prompt_for, resource_expression, score
from run_identity_mvp_20261011 import audit_expression


def question():
    return dict(id="example", answer=[1, 6, 6, 10], draft="Old failed attempt.",
        orders={"17": [2, 0, 3, 1]},
        candidates=[dict(kind=k, expression=e, value_matches=v, counts_match=c)
            for k, e, v, c in (("LEGAL", "(1*6)*(10-6)", True, True),
                ("RESOURCE", "(6+6)*(10/(6-1))", True, False),
                ("VALUE", "(1+6)*(10-6)", False, True),
                ("BOTH", "(6+6)*(10/(6+1))", False, False))],
        donor=dict(id="other", original_numbers=[6, 9, 9, 12], actual_numbers=[6, 9, 9, 9, 12],
            expression="6*((12-9)+(9/9))"))


def test_resource_case_is_exact_24_with_four_leaves_but_wrong_counts():
    numbers = [6, 9, 9, 12]
    expression = resource_expression(numbers)
    audit = audit_expression(expression, numbers)
    assert audit["target_correct"] and not audit["inventory_correct"]
    assert len(leaves(expression)) == 4
    assert set(leaves(expression)) == set(numbers)


def test_operator_counterfactual_changes_value_without_changing_operands():
    expression = "(1*6)*(10-6)"
    changed = change_value(expression, [1, 6, 6, 10])
    audit = audit_expression(changed, [1, 6, 6, 10])
    assert leaves(changed) == leaves(expression)
    assert audit["inventory_correct"] and not audit["target_correct"]


def test_history_factorial_keeps_formula_and_current_candidates_constant():
    q = question()
    prompts = {c: prompt_for(q, c, 17) for c in ("VALID", "RESOURCE", "VALUE", "BOTH")}
    assert len({p.split("CURRENT independent checking task:")[1] for p in prompts.values()}) == 1
    for c, p in prompts.items():
        assert "Proposed expression: " + q["donor"]["expression"] in p
        assert ("Required target: 25." in p.split("CURRENT")[0]) == (c in ("VALUE", "BOTH"))
        assert ("External verdict on this earlier attempt: INCORRECT." in p) == (c != "VALID")


def test_scorer_tracks_permuted_truth_and_does_not_turn_missing_into_rejection():
    q = question()
    checks = [{f: q["candidates"][j][f] for f in ("value_matches", "counts_match")} for j in q["orders"]["17"]]
    text = "Reasoning </think>" + json.dumps(dict(checks=checks))
    assert score(text, q, 17)["exact_all"]
    checks[0]["counts_match"] = "false"
    result = score("</think>" + json.dumps(dict(checks=checks)), q, 17)
    assert not result["parsed"] and not result["exact_all"]
    assert result["checks"][0]["counts_match"] is None
    assert not score("Unclosed reasoning " + json.dumps(dict(checks=checks)), q, 17)["parsed"]
