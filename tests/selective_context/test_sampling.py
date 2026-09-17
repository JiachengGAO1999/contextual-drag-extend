import torch
from selective_context.hf_backend import SelectiveHFBackend


def test_top_p_excludes_tail_and_keeps_highest_token():
    logits = torch.log(torch.tensor([[0.60, 0.30, 0.10]]))
    generator = torch.Generator().manual_seed(7)
    draws = [int(SelectiveHFBackend._choose(logits, 1.0, None, generator, 0.5)) for _ in range(50)]
    assert set(draws) == {0}
    draws = [int(SelectiveHFBackend._choose(logits, 1.0, None, generator, 0.8)) for _ in range(100)]
    assert set(draws) == {0, 1}


def test_top_p_one_preserves_sampling():
    logits = torch.tensor([[1., 2., 3.]])
    a, b = torch.Generator().manual_seed(42), torch.Generator().manual_seed(42)
    expected = torch.multinomial(torch.softmax(logits, -1), 1, generator=a).squeeze(-1)
    actual = SelectiveHFBackend._choose(logits, 1.0, None, b, 1.0)
    torch.testing.assert_close(actual, expected)
