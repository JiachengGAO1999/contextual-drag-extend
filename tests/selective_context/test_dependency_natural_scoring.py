import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("natural_revision",ROOT/"scripts/run_dependency_natural_20261011.py")
natural=importlib.util.module_from_spec(spec);spec.loader.exec_module(natural)
from prepare_dependency_revocation_20261011 import make_variant


def test_same_response_has_correct_root_stale_dependent_and_preserved_independent():
    variant=make_variant((12,7,8,1,4,2),False)
    text='Reasoning.</think>\n{"S1":12,"S2":13,"S3":17,"S4":17,"S5":34,"S6":34}'
    scored=natural.score_response(text,variant)
    assert scored["root_correct"] and scored["dependent_stale"] and scored["independent_preserved"]
    assert not scored["correct"] and scored["root_correct_dependent_stale_independent_correct"]


def test_unfinished_thinking_json_and_partial_final_are_not_success():
    variant=make_variant((12,7,8,1,4,2),False)
    correct='{"S1":12,"S2":13,"S3":16,"S4":17,"S5":32,"S6":34}'
    assert not natural.score_response(correct,variant)["parsed"]
    assert not natural.score_response('</think>{"S1":12}',variant)["parsed"]
    assert natural.score_response('</think>'+correct,variant)["correct"]
