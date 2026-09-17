import pytest
from selective_context.phase0.thinking_pilot import generation_budget, extract_final_draft


def test_context_budget_counts_prompt_and_refuses_truncation():
    assert generation_budget(1000) == 31768
    with pytest.raises(ValueError):
        generation_budget(32768)


def test_upstream_thinking_removed_from_context_draft():
    final, status = extract_final_draft('private reasoning</think>\nFinal \\boxed{24}<|im_end|>',
        'problem\n<think>\n', '<|im_end|>')
    assert final == 'Final \\boxed{24}'
    assert status == 'parsable_thinking'
    _, status = extract_final_draft('unfinished reasoning', 'problem\n<think>\n', '<|im_end|>')
    assert status == 'malformed_thinking'
