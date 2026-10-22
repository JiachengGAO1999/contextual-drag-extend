import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("identity_mvp", ROOT / "scripts/run_identity_mvp_20261011.py")
mvp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mvp)


def test_correct_value_does_not_excuse_reused_number_or_reused_equal_value_card():
    assert not mvp.audit_expression('(13-1)*6/(4-1)=24', [1,4,6,13])["inventory_correct"]
    bindings = dict(A=3, B=3, C=3, D=8)
    bad = mvp.audit_expression('(A+B+C)*(D/A)', [3,3,3,8], bindings)
    assert bad["target_correct"] and not bad["identity_correct"] and not bad["correct"]
    # Reusing A while omitting B also fails even when the numeric multiset is right.
    bad = mvp.audit_expression('D*A*(A/C)', [3,3,3,8], bindings)
    assert bad["target_correct"] and not bad["identity_correct"] and not bad["correct"]
    good = mvp.audit_expression('D*A*(B/C)', [3,3,3,8], bindings)
    assert good["correct"] and good["numeric_expression"] == '((8*3)*(3/3))'
    # The value-alias control must allow its declared multiplicity, but not an extra use.
    alias = dict(A=3,D=8)
    assert mvp.audit_expression('D*A*(A/A)', [3,3,3,8], alias, dict(A=3,D=1))["correct"]
    assert not mvp.audit_expression('D*A*(A/A)', [3,3,3,8], alias, dict(A=2,D=1))["correct"]


def test_final_card_expression_rejects_literals_unknown_symbols_and_unfinished_thinking():
    bindings = dict(A=1,B=4,C=6,D=13)
    q = dict(answer=[1,4,6,13],bindings=bindings,old_expression='(13-1)*6/(4-1)')
    for expression in ('A+B+C+13', 'A+B+C+E', 'A**B+C+D', '__import__("os")'):
        assert not mvp.audit_expression(expression,q['answer'],bindings)["parsed"]
    assert not mvp.score_response(r'\boxed{A+B+C+D}',q,'IDENTITY_HISTORY')["correct"]
    assert mvp.audit_expression(r'A+B+C+D',q['answer'],bindings)["correct"]


def test_substitution_matches_official_score():
    import pytest
    pytest.importorskip('math_verify')
    q = dict(answer=[1,4,6,13],bindings=dict(A=1,B=4,C=6,D=13),old_expression='(13-1)*6/(4-1)')
    assert mvp.score_response(r'</think>\boxed{A+B+C+D}',q,'IDENTITY_HISTORY')["correct"]
    numeric = mvp.score_response(r'</think>\boxed{1+4+6+13}',q,'IDENTITY_HISTORY')
    assert numeric["correct"] and not numeric["protocol_correct"]
    q = dict(answer=[3,3,3,8],bindings=dict(A=3,B=3,C=3,D=8),old_expression='8+3+3+3')
    repeated = mvp.score_response(r'</think>\boxed{D*A*(A/C)}',q,'IDENTITY_HISTORY')
    assert repeated["correct"] and not repeated["identity_correct"] and not repeated["protocol_correct"]
