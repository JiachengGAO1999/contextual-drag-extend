"""CPU tests for the paired branch computation, using a tiny randomly initialized Qwen3.

Run in the existing remote Transformers 4.55 environment, without loading model files.
"""
import unittest
import torch
from transformers import Qwen3Config, Qwen3ForCausalLM
from selective_context.feedback_decoding import feedback_logits, generate_batch


class Tokenizer:
    pad_token_id = 0


class FeedbackDecodingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(61)
        cls.model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=32,
            intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
            num_key_value_heads=2, head_dim=8, max_position_embeddings=128,
            attention_dropout=0.0)).eval()

    def decode(self, requests):
        result = {}
        generate_batch(self.model, Tokenizer(), requests, max_new_tokens=7,
            sampling=dict(temperature=0.0, top_k=20, top_p=.95), eos_ids={99},
            on_finish=lambda r,t,*_:result.update({r["id"]:list(t)}))
        return result

    def test_sign_and_zero(self):
        a, b = torch.tensor([2., 1.]), torch.tensor([1., 2.])
        torch.testing.assert_close(feedback_logits(a, b, 0), a)
        self.assertEqual(feedback_logits(a, b, 1).argmax().item(), 0)
        self.assertEqual(feedback_logits(b, a, 1).argmax().item(), 1)

    def test_independent_padding_and_order(self):
        requests = [dict(id="a", seed=1, strength=0., prompt_ids=[[1,2,3],[4,5,6,7,8]]),
                    dict(id="b", seed=1, strength=1., prompt_ids=[[3,5],[4,6,7]])]
        separate = {}
        for r in requests:
            separate.update(self.decode([r]))
        self.assertEqual(self.decode(requests), separate)
        self.assertEqual(self.decode(list(reversed(requests))), separate)
        # FULL must match ordinary unpadded greedy generation, irrespective of counterfactual.
        tokens = torch.tensor([[1,2,3]])
        plain = []
        for _ in range(7):
            with torch.inference_mode():
                token = int(self.model(tokens).logits[0,-1].argmax())
            plain.append(token)
            tokens = torch.cat((tokens, torch.tensor([[token]])), -1)
        self.assertEqual(separate["a"], plain)


if __name__ == "__main__":
    unittest.main()
