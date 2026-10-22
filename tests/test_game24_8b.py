"""Protocol-amendment regressions: single-anchor eligibility and fixed quotas."""
import ast
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from game24_100q_collect import validate, minimum_disk_free_bytes
from game24_8b_audit import MODEL, select_candidates


def cohort(q='1', batch='a', categories=None, model=MODEL):
    categories = categories or ['correct']*6+['substantive_error']*2
    return [dict(trajectory_id=f'{batch}/{model}/{q}/{i}', tot_rank=q, acquisition_batch=batch,
                 numbers=[1, 2, 3, 4], source_model=model, reusable_adapted_protocol=True,
                 sample_index=i, classification=c) for i, c in enumerate(categories)]


class SingleAnchorProtocol(unittest.TestCase):
    def test_disk_reserve_is_explicit_and_preserves_legacy_default(self):
        self.assertEqual(minimum_disk_free_bytes(), 10*1024**3)
        self.assertEqual(minimum_disk_free_bytes({'minimum_disk_free_gib': 2}), 2*1024**3)
        for bad in (0, 1, float('nan'), float('inf'), '2'):
            with self.assertRaises(ValueError):
                minimum_disk_free_bytes({'minimum_disk_free_gib': bad})

    def test_single_and_dual_quota_validation_are_distinct(self):
        m = json.loads((ROOT/'docs/game24_100q_8b/pilot_manifest.json').read_text())
        src = ROOT/'outputs/protocol-parity-audit-20260917/24.csv'
        validate(m, src)
        m['total_generations'] = 256
        with self.assertRaisesRegex(ValueError, 'budget'):
            validate(m, src)
        m['total_generations'] = 128
        m['anchor_models'] = ['Qwen3_32B']
        with self.assertRaises(ValueError):
            validate(m, src)

    def test_32b_errors_do_not_qualify_all_correct_8b(self):
        rows = cohort(categories=['correct']*8)+cohort(model='Qwen3_32B')
        self.assertEqual(select_candidates(rows, set()), [])

    def test_partial_or_different_cohorts_cannot_supply_errors(self):
        rows = cohort(categories=['correct']*8)+cohort(batch='b')[-2:]
        self.assertEqual(select_candidates(rows, set()), [])
        self.assertEqual(select_candidates(cohort()[:-1], set()), [])

    def test_only_prefix8_and_strict_errors_qualify(self):
        rows = cohort(categories=['correct']*7+['none_pending_review'])
        rows += [dict(cohort()[-1], sample_index=i, trajectory_id=f'extra/{i}') for i in (8, 9)]
        self.assertEqual(select_candidates(rows, set()), [])
        self.assertEqual(len(select_candidates(cohort(), set())), 1)
        self.assertEqual(select_candidates(cohort(), {'1'}), [])

    def test_saved_candidates_are_8b_only_and_freeze_matches_target(self):
        out = ROOT/'docs/game24_100q_8b'
        accepted = [json.loads(s) for s in (out/'game24_eligible_candidates.jsonl').read_text().splitlines()]
        candidate_ids = {r['tot_rank'] for r in accepted}
        self.assertTrue({'584', '1053'} <= candidate_ids)
        self.assertTrue(candidate_ids.isdisjoint({'643', '1119'}))
        self.assertEqual(len(candidate_ids), len(accepted))
        self.assertEqual(len({tuple(sorted(r['numbers'])) for r in accepted}), len(accepted))
        for r in accepted:
            self.assertEqual(r['anchor_models'], [MODEL])
            self.assertEqual(len(r['trajectory_ids']), 8)
            for ids in r['witnesses'].values():
                self.assertEqual(len(ids), 2)
                self.assertTrue(all('/'+MODEL+'/' in s for s in ids))
        frozen = [json.loads(s) for s in (out/'game24_eligible_100.jsonl').read_text().splitlines()]
        split = json.loads((out/'game24_split_manifest.json').read_text())
        if len(accepted) >= 100:
            self.assertEqual(frozen, accepted)
            self.assertEqual(split['state'], 'frozen')
            self.assertEqual(len(split['development']), 20)
            self.assertTrue(set(split['development']).isdisjoint(split['held_out']))
            self.assertEqual(set(split['development']) | set(split['held_out']),
                             {r['canonical_question_id'] for r in accepted})
        else:
            self.assertEqual(frozen, [])
            self.assertEqual(split['state'], 'not_frozen_target_not_met')

    def test_prior_32b_cost_is_retained_but_not_used_as_8b_sampling_rate(self):
        policy = json.loads((ROOT/'docs/game24_100q_8b/acquisition_campaign.json').read_text())
        self.assertGreater(policy['prior_campaign_job_gpu_hours'], 8)
        self.assertLess(policy['reused_pilot_8b_gpu_hours'], 1)
        tree = ast.parse((ROOT/'scripts/game24_8b_campaign.py').read_text())
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'forecast'], type_ignores=[])
        env = dict(math=math)
        exec(compile(module, 'forecast', 'exec'), env)
        result = env['forecast'](16, 2, policy['reused_pilot_8b_gpu_hours'], 98)
        self.assertGreater(result['remaining_gpu_hours'], 30)
        self.assertLess(result['remaining_gpu_hours'], 35)
        self.assertIsNone(env['forecast'](16, 0, 1, 100)['remaining_gpu_hours'])

    def test_resume_denominator_uses_completed_wave_prefix(self):
        tree = ast.parse((ROOT/'scripts/game24_8b_campaign.py').read_text())
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                                 and n.name in ('load', 'completed_prefix')], type_ignores=[])
        env = dict(json=json)
        exec(compile(module, 'completed_prefix', 'exec'), env)
        order = [dict(id=str(i), numbers=[i, 1, 2, 3]) for i in range(80)]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            self.assertEqual(env['completed_prefix'](order, run, 32), 16)
            (run/'wave-001').mkdir()
            (run/'wave-001/status.json').write_text(json.dumps(dict(state='pilot_complete_pending_audit')))
            mp = run/'wave-001.manifest.json'
            mp.write_text(json.dumps(dict(candidate_rows=order[16:48])))
            self.assertEqual(env['completed_prefix'](order, run, 32), 48)
            mp.write_text(json.dumps(dict(candidate_rows=order[17:49])))
            with self.assertRaises(RuntimeError):
                env['completed_prefix'](order, run, 32)


if __name__ == '__main__':
    unittest.main()
