"""Semantic checks: independent worksheet execution and strict outcome scoring."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("gate0", Path(__file__).parents[1] / "scripts/gate0_credit_assignment_20261013.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_independent_execution_and_exactly_one_injected_fault():
    tasks = g.make_tasks()
    assert len(tasks) == 32 and sum(q["sentinel"] for q in tasks) == 8
    assert len({g.task_text(q) for q in tasks}) == 32
    for q in tasks:
        env = {}
        # Execute only our generated closed straight-line specification as a
        # second evaluator, separate from the trace implementation.
        lines = g.task_text(q).splitlines()[1:]
        exec("\n".join(lines), {"__builtins__": {}}, env)
        assert {k: env[k] for k in ("A", "B", "Y")} == q["truth"]
        assert q["old"]["B"] == q["truth"]["B"]
        assert q["old"]["Y"] == 3*q["old"]["A"]-2*q["truth"]["B"]
        assert q["old"]["Y"] != q["truth"]["Y"]


def test_invalid_truncated_and_duplicate_keys_cannot_receive_credit():
    q = g.make_tasks()[0]
    answer = json.dumps(q["truth"])
    assert g.score(answer, q)["joint"]
    assert not g.score(answer, q, truncated=True)["joint"]
    assert not g.score(answer + " then another answer", q)["joint"]
    assert not g.score('{"A": 1, "A": 2, "B": 3, "Y": 4}', q)["format_valid"]
    bad_type = dict(q["truth"], B=str(q["truth"]["B"]))
    assert not g.score(json.dumps(bad_type), q)["format_valid"]
    assert g.score(json.dumps(q["old"]), q)["correct"] == dict(A=False, B=True, Y=False)


def test_source_swap_preserves_computation_and_feedback_is_not_a_gold_answer():
    for q in g.make_tasks():
        a = g.user_text(q, "history", "shared", "local")
        b = g.user_text(q, "history", "split", "local")
        assert a.count("Recorder") == b.count("Recorder") == 2
        for branch in "AB":
            assert g.branch_record(q, branch) in a and g.branch_record(q, branch) in b
        assert str(q["truth"]["A"]) not in g.FEEDBACK["local"]
        assert str(q["truth"]["B"]) not in g.FEEDBACK["confirm"]
