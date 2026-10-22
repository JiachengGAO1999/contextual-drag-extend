import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from selective_context.diagnostic_data import first_difference, paired_effect, prepare, expression_measurement
from selective_context.diagnostics import DiagnosticBackend, Intervention, draft_contribution,matched_non_draft_contribution
from selective_context.diagnostics import partition_contributions, matched_source_contribution


def test_source_partitions_use_original_prompt_boundary_and_include_query():
    weights = torch.ones(1, 1, 1, 5)
    expanded = torch.tensor([[[[3., 0.], [0., 4.], [1., 1.], [2., 0.], [0., 2.]]]])
    parts = partition_contributions(weights, expanded, (1, 2), 4)
    torch.testing.assert_close(parts["P"], torch.tensor([[[[3., 0.]]]]))
    torch.testing.assert_close(parts["D"], torch.tensor([[[[0., 4.]]]]))
    torch.testing.assert_close(parts["F"], torch.tensor([[[[3., 1.]]]]))
    torch.testing.assert_close(parts["G"], torch.tensor([[[[0., 2.]]]]))
    torch.testing.assert_close(sum(parts.values()), weights @ expanded)
    torch.testing.assert_close(matched_source_contribution(parts["G"], parts["D"]), parts["D"])
    torch.testing.assert_close(matched_source_contribution(torch.zeros_like(parts["G"]), parts["D"]), torch.zeros_like(parts["D"]))


@pytest.mark.parametrize("mode", ["PRE_DRAFT_MATCHED", "GENERATED_MATCHED"])
def test_source_partition_intervention_keeps_prefill_and_geometry_is_observational(mode):
    backend = tiny_backend()
    pre = backend.prefill([1, 5, 6, 7, 30, 31, 32])
    tokens, span = [33, 34, 35, 36], (1, 4)
    full = backend.teacher_force(pre, tokens, span)
    geometry = backend.teacher_force(pre, tokens, span, Intervention("FULL", ((0, 0),)), geometry_tokens=(1,))
    changed = backend.teacher_force(pre, tokens, span, Intervention(mode, ((0, 0),)))
    identity = backend.teacher_force(pre, tokens, span, Intervention(mode, ((0, 0),), strength=0))
    assert full["log_probs"] == geometry["log_probs"] == identity["log_probs"]
    assert changed["log_probs"][0] == full["log_probs"][0]
    assert pre[1].get_seq_length() == 7
    assert changed["source_match_stats"]["unmatched"] == 0
    assert all(m["token"] == 1 and m["layer"] == 0 for m in geometry["source_geometry"])
    assert geometry["source_geometry"][0]["partition_reconstruction_relative_error"] < 1e-5
    assert [e["prediction_token"] for e in geometry["target_entropy"]] == [2]


def test_gqa_contribution_and_mask_renormalization_are_different():
    weights = torch.tensor([[[[.2, .3, .5]], [[.4, .1, .5]]]])
    value = torch.tensor([[[[2., 1.], [4., 3.], [6., 5.]]]])
    contribution, expanded = draft_contribution(weights, value, (0, 2))
    full = weights @ expanded
    other = weights[..., 2:] @ expanded[..., 2:, :]
    torch.testing.assert_close(full, contribution+other)
    torch.testing.assert_close(full-contribution, other)
    assert not torch.allclose(full-contribution, other/(1-weights[..., :2].sum(-1, keepdim=True)))


def test_same_prefix_probe_does_not_compare_divergent_trajectories():
    assert first_difference([1, 2, 3, 4], [1, 2, 9, 8]) == [dict(
        index=2, preferred=3, alternative=9, semantic=False,
        label="source-conditioned token preference; not a verified reasoning decision")]
    assert first_difference([1, 2], [1, 2]) == []


def test_effects_are_paired_by_question_and_keep_missing():
    rows = [dict(id="a",condition="FULL",margin=1.),dict(id="a",condition="MASK",margin=3.),
            dict(id="b",condition="FULL",margin=None),dict(id="b",condition="MASK",margin=9.)]
    result = paired_effect(rows,"FULL","MASK",draws=100)
    assert result["n"] == 1 and result["mean"] == 2. and result["ci"] == [2.,2.]


def test_invalid_interventions_fail_before_changing_model():
    with pytest.raises(ValueError):
        Intervention("VALUE_ZERO",((0,4),)).validate(2,4)
    with pytest.raises(ValueError):
        Intervention("VALUE_ZERO",((0,1),(0,1))).validate(2,4)
    Intervention("VALUE_ZERO",()).validate(2,4)


def test_exact_arithmetic_rejects_reused_numbers_and_parses_nested_fraction():
    assert expression_measurement(r"\frac{8}{\frac{3}{1}}*9",[8,3,1,9])["exact_game24"]
    assert not expression_measurement("(8+8+8)/(1*1)",[8,8,8,1])["exact_game24"]
    assert not expression_measurement("24",[1,2,3,4])["exact_game24"]
    assert expression_measurement("__import__('os')",[1,2,3,4])["evaluation_status"] == "unparsed"


def tiny_backend():
    from selective_context.phase0.tiny_model import make_tiny_qwen, NumericTokenizer
    if not torch.cuda.is_available() or "A100" not in torch.cuda.get_device_name(0):
        pytest.skip("Model checks run on the A100 only")
    model = make_tiny_qwen().to("cuda:0")
    return DiagnosticBackend(model, NumericTokenizer())


def test_cached_branches_first_prediction_identity_and_full_mask_reference():
    backend = tiny_backend()
    pre = backend.prefill([1,5,6,7,30,31,32])
    original_length = pre[1].get_seq_length()
    tokens, span = [33,34,35], (1,4)
    full = backend.teacher_force(pre,tokens,span,collect=True,capture=True)
    mask = backend.teacher_force(pre,tokens,span,Intervention("MASK"),collect=True,capture=True)
    identity = backend.teacher_force(pre,tokens,span,Intervention("VALUE_ZERO",()),capture=True)
    repeated = backend.teacher_force(pre,tokens,span,capture=True)
    assert pre[1].get_seq_length() == original_length
    assert full["log_probs"][0] == mask["log_probs"][0]
    assert full["log_probs"] == repeated["log_probs"] == identity["log_probs"]
    assert max(max(m["applied_mass"]) for m in mask["retrieval"]) == 0
    assert max(m["reconstruction_relative_error"] for m in full["retrieval"]) < 1e-5
    # Independent reference: normal HF attention plus an explicit one-query mask.
    backend.model.config._attn_implementation = "eager"
    attention_mask = torch.zeros((1,1,1,8),device=backend.device)
    attention_mask[...,1:4] = torch.finfo(torch.float32).min
    out = backend.model(input_ids=torch.tensor([[33]],device=backend.device),
                        past_key_values=copy.deepcopy(pre[1]),attention_mask=attention_mask,use_cache=True)
    lp=float(out.logits[:,-1].detach().float().log_softmax(-1)[0,34])
    assert abs(lp-mask["log_probs"][1]) < 1e-5


def test_bidirectional_full_head_patch_matches_donor():
    backend=tiny_backend()
    pre=backend.prefill([1,5,6,7,30,31,32])
    tokens,span=[33,34,35],(1,4)
    full=backend.teacher_force(pre,tokens,span,capture=True)
    masked=backend.teacher_force(pre,tokens,span,Intervention("MASK"),capture=True)
    patched=backend.teacher_force(pre,tokens,span,Intervention("PATCH"),donor=masked["outputs"])
    reverse=backend.teacher_force(pre,tokens,span,Intervention("PATCH_MASK"),donor=full["outputs"])
    torch.testing.assert_close(torch.tensor(patched["log_probs"]),torch.tensor(masked["log_probs"]),rtol=0,atol=1e-5)
    torch.testing.assert_close(torch.tensor(reverse["log_probs"]),torch.tensor(full["log_probs"]),rtol=0,atol=1e-5)


def test_exception_restores_attention_function_and_config():
    backend=tiny_backend()
    original=backend.module.eager_attention_forward
    config=backend.model.config._attn_implementation
    with pytest.raises(RuntimeError):
        with backend.intervention(Intervention(),(1,4)):
            raise RuntimeError("abort")
    assert backend.module.eager_attention_forward is original
    assert backend.model.config._attn_implementation == config and backend.state is None


def test_budget_restarts_do_not_reset_consumed_time(tmp_path):
    import importlib.util
    path=Path(__file__).resolve().parents[2]/"scripts/run_generation_diagnostics_20261005.py"
    spec=importlib.util.spec_from_file_location("diagnostic_runner",path)
    module=importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0,str(path.parent))
    spec.loader.exec_module(module)
    budget_path=tmp_path/"budget.json"
    budget_path.write_text(json.dumps(dict(gpu_seconds=10.,active=False)))
    budget=module.Budget(budget_path,24)
    budget.close()
    assert json.loads(budget_path.read_text())["gpu_seconds"] >= 10.


def test_non_draft_direction_matches_each_head_norm():
    draft=torch.tensor([[[[3.,4.],[0.,2.]]]])
    other=torch.tensor([[[[1.,0.],[2.,0.]]]])
    delta=matched_non_draft_contribution(draft+other,draft)
    torch.testing.assert_close(delta,torch.tensor([[[[5.,0.],[2.,0.]]]]))
    torch.testing.assert_close(delta.norm(dim=-1),draft.norm(dim=-1))


def test_query_window_is_causal_and_does_not_require_donors_outside_it():
    backend=tiny_backend()
    pre=backend.prefill([1,5,6,7,30,31,32])
    tokens,span=[33,34,35,36],(1,4)
    full=backend.teacher_force(pre,tokens,span)
    inactive=backend.teacher_force(pre,tokens,span,Intervention("PATCH",query_window=(9,10)))
    assert full['log_probs']==inactive['log_probs']
    window=Intervention("VALUE_ZERO",query_window=(1,2))
    result=backend.teacher_force(pre,tokens,span,window)
    assert result['log_probs'][:2]==full['log_probs'][:2]
    control=backend.teacher_force(pre,tokens,span,Intervention("NON_DRAFT_MATCHED"),collect=True)
    assert max(m['matched_norm_relative_error_max'] for m in control['retrieval'])<1e-5
    # One-query donor, same tokens: reverse patch must equal the window FULL donor.
    donor=backend.teacher_force(pre,tokens,span,Intervention("FULL",query_window=(1,2)),capture=True)
    patched=backend.teacher_force(pre,tokens,span,Intervention("PATCH_MASK",query_window=(1,2)),donor=donor['outputs'])
    torch.testing.assert_close(torch.tensor(patched['log_probs']),torch.tensor(full['log_probs']),rtol=0,atol=1e-5)

