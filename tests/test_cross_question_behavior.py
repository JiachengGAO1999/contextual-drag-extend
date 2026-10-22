"""CPU checks for paired analysis and incomplete-output denominators."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_cross_question_behavior_20261009 import CONDITIONS, summarize


def manifest():
    return dict(questions=[dict(id=q, seeds=[20261009], condition_order=list(CONDITIONS),
        prior_baseline_direction="endorse") for q in ("a", "b")])


def row(q, condition, correct, *, finish="eos", score=False):
    return dict(id=q, seed=20261009, condition=condition, correct=correct,
        score_status=score, structural_reuse=False, route_available=True,
        answer_route_parseable=False, finish_reason=finish, scorer_disagreement=None,
        generated_tokens=10, extracted_answer=None)


def test_truncated_unresolved_outputs_stay_in_denominator(tmp_path):
    rows = [row("a", "FULL", True, score=True), row("a", "CANDIDATE", False, finish="length", score=None),
        row("a", "CONTROL", True, score=True), row("b", "FULL", False),
        row("b", "CANDIDATE", True, score=True), row("b", "CONTROL", True, score=True)]
    summary = summarize(manifest(), rows, "completed", tmp_path)
    candidate = summary["conditions"]["CANDIDATE"]
    assert candidate["n"] == 2 and candidate["accuracy"] == .5
    assert candidate["length"] == 1 and candidate["unresolved"] == 1
    comparison = summary["comparisons"]["CANDIDATE_minus_CONTROL"]
    assert comparison["accuracy"]["n"] == 2 and comparison["accuracy"]["mean"] == -.5
    assert comparison["recovered"] == 0 and comparison["harmed"] == 1
    assert summary["pending"] == []


def test_unfinished_triplet_is_not_treated_as_zero_accuracy(tmp_path):
    rows = [row("a", "FULL", True), row("a", "CANDIDATE", False)]
    summary = summarize(manifest(), rows, "budget_exhausted", tmp_path)
    assert summary["completed_requests"] == 2 and len(summary["pending"]) == 4
    assert summary["complete_questions"] == 0
    assert summary["comparisons"]["CANDIDATE_minus_FULL"]["accuracy"]["n"] == 0
    assert summary["conditions"]["CANDIDATE"]["n"] == 1
