import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import run_identity_prospective_20261011 as prospective
from audit_identity_trajectories_20261011 import inspect


def test_exact_solver_checks_inventory_and_unsolvable_case():
    ns=[3,3,8,8]
    expression=prospective.solve(ns)
    assert prospective.audit_expression(expression,ns)["correct"]
    assert prospective.solve([1,1,1,1]) is None


def test_count_and_identity_share_truthful_feedback_and_verbatim_history():
    q=dict(problem="Use 3,3,8,8 to make 24.",answer=[3,3,8,8],bindings=dict(A=3,B=3,C=8,D=8))
    for verdict in ("CORRECT","INCORRECT","UNDETERMINED"):
        source=dict(usable=True,feedback=verdict,draft="An untouched draft\n\\boxed{8/(3-8/3)}")
        for condition in prospective.CONDITIONS:
            prompt=prospective.repair_prompt(q,source,condition)
            assert "3: 2, 8: 2" in prompt
            assert (source["draft"] in prompt)==condition.endswith("HISTORY")
            if condition.endswith("HISTORY"):
                assert ("could not be determined" if verdict=="UNDETERMINED" else f"a {verdict} final answer") in prompt
            assert ("A=3, B=3, C=8, D=8" in prompt)==condition.startswith("IDENTITY")


def test_legal_mention_is_not_endorsement_or_recognition():
    q=dict(answer=[5,7,8,8],bindings=dict(A=7,B=5,C=8,D=8),draft="old")
    text="Could try `8*(7-5)+8=24`, but set it aside. </think>old final"
    r=inspect(text,q,"NUMERIC_HISTORY",dict(correct=False,structural_reuse=True))
    assert r["legal_construct_observed"] and r["old_illegal_final_reused"]
    assert r["legal_construct_mentions"][0]["adoption_status"]=="not_inferred_from_mention"
    assert not r["resource_error_review_candidates"]


def test_two_seeds_average_within_question_and_missing_history_is_not_wrong(tmp_path):
    import pytest
    pytest.importorskip("numpy")
    m=dict(questions=[dict(id="q1",answer=[3,3,8,8]),dict(id="q2",answer=[1,1,1,8])])
    prospective.append(tmp_path/"source_scores.jsonl",dict(id="q1",usable=True,feedback="INCORRECT"))
    prospective.append(tmp_path/"source_scores.jsonl",dict(id="q2",usable=False,feedback="UNDETERMINED"))
    for c in prospective.CONDITIONS:
        for s in prospective.REPAIR_SEEDS:
            prospective.append(tmp_path/"behaviour.jsonl",dict(id="q1",condition=c,seed=s,
                correct=c=="IDENTITY_HISTORY" and s==prospective.REPAIR_SEEDS[0],parsed=True,
                inventory_correct=True,finish_reason="eos",generated_tokens=10))
    r=prospective.summarise(m,tmp_path,"running")
    assert r["complete_questions"]==1
    assert r["primary"]["history_interaction"]["n"]==1
    assert r["primary"]["history_interaction"]["mean"]==.5
    assert r["missing_source_ids"]==["q2"]
    assert r["conditions"]["COUNT_HISTORY"]["n"]==2
