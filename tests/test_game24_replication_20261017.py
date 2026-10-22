"""Critical audit boundaries: pairing, frozen denominator, and independent units."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("replication", Path(__file__).resolve().parents[1]/"scripts/game24_replication_20261017.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(q="q", s=927001, c="R2", correct=False):
    return dict(id=q, init_response_prompt="same", generated_token_ids=[10, 20],
        init_response_generations=[dict(correctness=correct, finish_reason="eos")],
        init_response_generations_metadata=dict(intervention=dict(condition_id=c,
            sample_seed=s, input_ids=[1, 2, 3], draft_token_span=[1, 2])))


class AuditTests(unittest.TestCase):
    def test_first_token_mismatch_stops_pair(self):
        a, b = record(), record(c="R3")
        self.assertEqual(m.verify_first_tokens([a, b]), 1)
        b["generated_token_ids"][0] = 11
        with self.assertRaises(RuntimeError): m.verify_first_tokens([a, b])

    def test_input_changes_and_unpaired_outputs_fail(self):
        a, b = record(), record(c="R3")
        b["init_response_generations_metadata"]["intervention"]["input_ids"][0] = 9
        with self.assertRaises(RuntimeError): m.verify_first_tokens([a, b])
        with self.assertRaises(RuntimeError): m.verify_first_tokens([a])

    def test_partial_data_keeps_all_requested_denominator(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, "BASE", Path(tmp)):
            m.save(m.BASE/"plan.json", dict(questions=[f"q{i}" for i in range(20)]))
            m.write_rows(m.BASE/"results.jsonl", [record(q="q0", c="R0", correct=True)])
            result = m.analyse()
            self.assertEqual(result["missing"], 119)
            self.assertEqual(result["conditions"]["R0"]["accuracy_over_all_requested"], 1/40)
            self.assertEqual(result["effects"], {})

    def test_question_bootstrap_and_duplicate_rejection(self):
        self.assertEqual(m.bootstrap([.5]*20, draws=50), [.5, .5])
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, "BASE", Path(tmp)):
            m.save(m.BASE/"plan.json", dict(questions=[f"q{i}" for i in range(20)]))
            a = record(q="q0")
            m.write_rows(m.BASE/"results.jsonl", [a, copy.deepcopy(a)])
            with self.assertRaises(RuntimeError): m.analyse()


if __name__ == "__main__": unittest.main()
