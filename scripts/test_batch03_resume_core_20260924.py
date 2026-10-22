"""No-model tests for Batch03 checkpoint, deduplication, and safe-stop behavior."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from batch03_resume_core_20260924 import (
    append_jsonl_once,
    contiguous_sample_runs,
    consume_request_stream,
    load_completed,
    missing_sample_indices,
    sample_seed,
)


def record(sample_index: int, text: str) -> dict:
    return {
        "id": "q1",
        "draft_key": f"q1/{sample_index}",
        "init_response_generations_metadata": {"model_config_alias": "Qwen3_32B"},
        "init_response_generations": [{"response_id": sample_index, "generated_response": text}],
    }


class FakeEngine:
    def __init__(self, updates):
        self.updates = updates
        self.aborted = []

    async def generate(self, prompt, sampling_params, request_id):
        for update in self.updates:
            yield update

    async def abort(self, request_id):
        self.aborted.append(request_id)


class ResumeCoreTests(unittest.TestCase):
    def test_per_sample_seeds_are_stable_and_unique_across_resume_gaps(self):
        expected = {index: 42 + index for index in range(16)}
        seeds = {index: sample_seed(42, index) for index in range(16)}
        self.assertEqual(seeds, expected)
        self.assertEqual(len(set(seeds.values())), 16)
        # If 0-2 were saved, missing indices keep seeds45+ rather than restarting at42.
        missing = [index for index in range(8) if index not in {0, 1, 2}]
        self.assertEqual([sample_seed(42, index) for index in missing], [45, 46, 47, 48, 49])
        self.assertEqual(len(set(sample_seed(42, index) for index in missing)), len(missing))
        resumed_runs = contiguous_sample_runs([3, 4, 5, 7, 8, 12])
        self.assertEqual(resumed_runs, [[3, 4, 5], [7, 8], [12]])
        child_seeds = [
            sample_seed(42, run[0]) + local_index
            for run in resumed_runs for local_index, _sample_index in enumerate(run)
        ]
        self.assertEqual(child_seeds, [sample_seed(42, index) for index in [3, 4, 5, 7, 8, 12]])
        self.assertEqual(len(set(child_seeds)), 6)

    def test_negative_sample_index_has_no_seed(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            sample_seed(42, -1)

    def test_contiguous_seed_runs_reject_unsorted_or_duplicate_indices(self):
        with self.assertRaisesRegex(ValueError, "unique and sorted"):
            contiguous_sample_runs([3, 2])
        with self.assertRaisesRegex(ValueError, "unique and sorted"):
            contiguous_sample_runs([3, 3])

    def test_catalog_deduplicates_identical_identity_and_skips_saved_indices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, duplicate = root / "first.jsonl", root / "duplicate.jsonl"
            row = record(0, "same")
            first.write_text(json.dumps(row) + "\n", encoding="utf-8")
            duplicate.write_text(json.dumps(row) + "\n", encoding="utf-8")
            completed, _ = load_completed([first, duplicate])
            self.assertEqual(len(completed), 1)
            self.assertEqual(missing_sample_indices(completed, "Qwen3_32B", "q1", 4), [1, 2, 3])

    def test_conflicting_duplicate_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first.jsonl", root / "second.jsonl"
            first.write_text(json.dumps(record(0, "a")) + "\n", encoding="utf-8")
            second.write_text(json.dumps(record(0, "b")) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Conflicting persisted records"):
                load_completed([first, second])

    def test_duplicate_identity_within_one_output_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicated.jsonl"
            row = json.dumps(record(0, "same"))
            path.write_text(row + "\n" + row + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Duplicate persisted identity inside"):
                load_completed([path])

    def test_append_is_idempotent_and_flushes_one_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft_candidates.jsonl"
            completed, canonical = set(), {}
            row = record(3, "durable")
            self.assertTrue(append_jsonl_once(path, row, completed, canonical))
            self.assertFalse(append_jsonl_once(path, row, completed, canonical))
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def test_safe_stop_persists_finished_output_then_resume_skips_it(self):
        async def scenario():
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "draft_candidates.jsonl"
                completed, canonical = set(), {}
                stop = asyncio.Event()
                engine = FakeEngine([SimpleNamespace(outputs=[
                    SimpleNamespace(index=0, finish_reason="stop", text="first"),
                    SimpleNamespace(index=1, finish_reason=None, text="partial"),
                ])])

                def persist(sample_index, output):
                    append_jsonl_once(path, record(sample_index, output.text), completed, canonical)
                    stop.set()

                done, finished = await consume_request_stream(
                    engine, {"prompt_token_ids": [1]}, object(), "request-1", [0, 1], persist, stop
                )
                self.assertEqual(done, {0})
                self.assertFalse(finished)
                self.assertEqual(engine.aborted, ["request-1"])
                missing = missing_sample_indices(completed, "Qwen3_32B", "q1", 2)
                self.assertEqual(missing, [1])

                engine2 = FakeEngine([SimpleNamespace(outputs=[
                    SimpleNamespace(index=0, finish_reason="stop", text="second"),
                ])])
                stop.clear()
                done2, finished2 = await consume_request_stream(
                    engine2, {"prompt_token_ids": [1]}, object(), "request-2", missing,
                    lambda sample_index, output: append_jsonl_once(
                        path, record(sample_index, output.text), completed, canonical
                    ), stop,
                )
                self.assertEqual(done2, {1})
                self.assertTrue(finished2)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                self.assertEqual([row["draft_key"] for row in rows], ["q1/0", "q1/1"])

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
