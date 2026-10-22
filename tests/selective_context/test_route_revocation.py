import copy

import pytest
import torch

from selective_context.masks import build_allowed_attention
from selective_context.schema import AccessMode
from selective_context.route_revocation_data import CONDITIONS, analyse, inspect_expression, solve, wrong_routes


def test_constructed_routes_have_exact_value_but_wrong_four_leaf_inventory():
    numbers = [1, 3, 4, 6]
    legal = inspect_expression(solve(numbers))
    assert legal["value"] == "24" and legal["inventory"] == numbers
    wrong = wrong_routes(numbers)
    assert len(wrong) >= 2
    for route in wrong:
        assert route["value"] == "24" and len(route["leaves"]) == 4
        assert route["inventory"] != numbers
        actual = list(numbers); actual.remove(route["omitted"]); actual.append(route["duplicated"])
        assert sorted(actual) == route["inventory"]


def test_early_and_late_masks_share_decision_access_but_not_state_building():
    masks = {c: build_allowed_attention(batch_size=1, query_positions=list(range(10)), key_length=10,
            draft_token_span=(2, 5), prompt_length=8,
            access_mode={"FULL": AccessMode.FULL, "LATE_BLOCK": AccessMode.LATE_BLOCK,
                         "REBUILD_BLOCKED": AccessMode.PATH_BLOCK}[c]) for c in CONDITIONS}
    full, late, early = [masks[c] for c in CONDITIONS]
    assert torch.equal(late[..., :8, :], full[..., :8, :])
    assert torch.equal(early[..., :5, :], full[..., :5, :])
    assert late[..., 5:8, 2:5].all() and not early[..., 5:, 2:5].any()
    assert torch.equal(late[..., 8:, :], early[..., 8:, :])
    assert not late[..., 8:, 2:5].any()


def test_analysis_collapses_histories_before_question_bootstrap_and_keeps_missing():
    rows = []
    for qid, effect in (("q1", 1), ("q2", 3)):
        for h in ("A", "B"):
            for c in CONDITIONS:
                for outcome in ("judgment", "adoption"):
                    values = dict(A=-3., B=-3., legal=-3.+(effect if c == "REBUILD_BLOCKED" else 0),
                                  reject=-2., endorse=-4.)
                    rows.append(dict(id=qid, history=h, condition=c, outcome=outcome,
                        scores={k:dict(log_probability=v, mean_log_probability=v) for k,v in values.items()}))
    result = analyse([dict(id="q1"), dict(id="q2"), dict(id="missing")], rows)
    assert result["effects"]["rebuild_minus_late_adoption"]["n"] == 2
    assert result["effects"]["rebuild_minus_late_adoption"]["mean"] == 2
    assert result["effects"]["REBUILD_BLOCKED_identity"]["mean"] == 0
    assert result["missing"][0]["id"] == "missing"


def test_a100_state_rebuild_identity_boundary_and_branch_independence():
    if not torch.cuda.is_available() or "A100" not in torch.cuda.get_device_name(0):
        pytest.skip("Model checks run on the A100 only")
    from selective_context.phase0.tiny_model import make_tiny_qwen
    from selective_context.route_revocation import RouteRevocationBackend
    model = make_tiny_qwen().to("cuda:0")
    model.config._attn_implementation = "sdpa"
    backend = RouteRevocationBackend(model)
    a = dict(input_ids=[1, 5, 6, 7, 30, 31, 32, 33], draft_token_span=[1, 4], cutoff=7)
    b = dict(a, input_ids=[1, 8, 9, 10, 30, 31, 32, 33])
    states_a, states_b = backend.prefill_pair(a), backend.prefill_pair(b)
    standard = model(input_ids=torch.tensor([a["input_ids"]], device="cuda:0"), use_cache=True)
    torch.testing.assert_close(states_a["FULL"].logits, standard.logits[:, -1, :], rtol=0, atol=1e-5)
    # Complete early blocking must remove A/B identity outside D, with positions fixed.
    torch.testing.assert_close(states_a["REBUILD_BLOCKED"].logits, states_b["REBUILD_BLOCKED"].logits, rtol=0, atol=1e-6)
    # Independent full-prefix reference includes the blocked query producing the first candidate logit.
    reference = backend.advance(a["input_ids"], None, a["draft_token_span"], "LATE_BLOCK", a["cutoff"])
    torch.testing.assert_close(states_a["LATE_BLOCK"].logits, reference.logits, rtol=0, atol=1e-5)
    readout = dict(stem_ids=[34, 35], candidates=dict(x=dict(ids=[36, 37]), y=dict(ids=[38, 39])))
    before = states_a["LATE_BLOCK"].cache.get_seq_length()
    first = backend.score(states_a["LATE_BLOCK"], a, "LATE_BLOCK", readout)
    reverse = copy.deepcopy(readout)
    reverse["candidates"] = dict(reversed(list(reverse["candidates"].items())))
    assert first == backend.score(states_a["LATE_BLOCK"], a, "LATE_BLOCK", reverse)
    assert states_a["LATE_BLOCK"].cache.get_seq_length() == before
