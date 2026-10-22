"""Confirm larger factorial denominators, source selection, and split boundaries."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec = importlib.util.spec_from_file_location("full_replication",ROOT/"scripts/game24_full_replication_20261019.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(q,s,c,correct):
    return dict(id=q,init_response_prompt="same",generated_token_ids=[10,20],
        init_response_generations=[dict(correctness=correct,finish_reason="eos")],
        init_response_generations_metadata=dict(intervention=dict(condition_id=c,sample_seed=s,
            input_ids=[1,2,3],draft_token_span=[1,2])))


class FullReplicationTests(unittest.TestCase):
    def test_spawn_imports_reference_before_minimal_checkout(self):
        from importlib.machinery import PathFinder
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            checkout=base/"checkout"
            reference=base/"reference"
            overlay=base/"overlay"
            for p in (checkout,reference):
                (p/"selective_context").mkdir(parents=True)
                (p/"selective_context/__init__.py").write_text("")
            overlay.mkdir()
            m.save(base/"runtime_profile.json",dict(reference=str(reference),overlay=str(overlay)))
            with patch.object(m,"BASE",base),patch.object(sys,"path",[str(checkout)]+sys.path):
                m.activate_worker_paths()
                spec=PathFinder.find_spec("selective_context",sys.path)
                self.assertEqual(Path(spec.origin),reference/"selective_context/__init__.py")

    def test_confirmation_denominators_include_missing(self):
        qids=[f"q{i}" for i in range(82)]
        result=m.summarize([record(qids[0],927001,"R0",True)],qids)
        self.assertEqual(result["missing"],491)
        self.assertEqual(result["conditions"]["R0"]["requested"],164)
        self.assertEqual(result["conditions"]["R0"]["accuracy_over_all_requested"],1/164)
        self.assertEqual(result["effects"],{})

    def test_pooled_coverage_and_question_units(self):
        qids=["q0","q1"]
        rows=[record(q,s,c,c!="R2") for q in qids for s in m.SEEDS for c in m.CONDITIONS]
        result=m.summarize(rows,qids)
        self.assertEqual(result["independent_questions"],2)
        self.assertEqual(result["paired_invariant_checks"],4)
        self.assertEqual(result["effects"]["R3-R2"]["question_bootstrap_95ci"],[1,1])
        self.assertEqual(result["effects"]["R3-R2"]["recovery"],4)

    def test_heldout_analysis_rejects_development_and_duplicates(self):
        a=record("dev",927001,"R0",True)
        with self.assertRaises(RuntimeError): m.summarize([a],["held"])
        with self.assertRaises(RuntimeError): m.summarize([a,a],["dev"])

    def test_new_draft_selection_replays_completed20(self):
        eligible={r["canonical_question_id"]:r for r in m.rows(m.DATA/"game24_eligible_100.jsonl")}
        trajectories={r["trajectory_id"]:r for r in m.rows(m.DATA/"game24_trajectory_pool.jsonl")}
        ids=m.read(m.DATA/"game24_split_manifest.json")["development"]
        selected,_=m.select_materials(ids,eligible,trajectories)
        previous=m.rows(m.DEV/"pairs.jsonl")
        self.assertEqual([(p["id"],p["draft_sha256"]) for p in selected],
                         [(p["id"],p["draft_sha256"]) for p in previous])


if __name__=="__main__": unittest.main()
