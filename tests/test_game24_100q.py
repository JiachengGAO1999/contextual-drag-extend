"""Data semantics and interrupted-run regressions; no GPU or model imports."""
import ast
import hashlib
import contextlib
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from game24_100q_audit import classify, eligible, OUT
from game24_100q_collect import read_journal, check_gpu, validate
from analyze_batch03_partial_20260924 import expression_measurement

def load_functions(path, names, globals_):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    exec(compile(module, str(path), 'exec'), globals_)
    return globals_

class DataSemantics(unittest.TestCase):
    def test_official_falsey_none_is_not_strict_failure(self):
        env = load_functions(ROOT/'data_generation/aggregate_data.py', {'preprocess_dataset', 'filter_problem'},
                             dict(tqdm=lambda x: x, combination=lambda a,b: 1))
        data = dict(id=['x']*4, init_response_generations_correctness=[True,True,False,None],
                    init_response_generations_finish_reason=['stop']*4,
                    init_response_thinking_status=['parsable_thinking']*4)
        args = SimpleNamespace(problem_id_column='id', init_response_correctness_column='init_response_generations_correctness',
            filter_init_response_completeness=True, filter_init_response_parsable_thinking=True, num_true=0, num_false=2)
        with contextlib.redirect_stdout(io.StringIO()):
            groups=env['preprocess_dataset'](data,args)
            selected=env['filter_problem'](groups,args)
        self.assertEqual(selected,['x'])
        self.assertEqual(len(groups['x']['incorrect']),2)
        rows=[dict(classification=c, official_correctness=v, finish_reason='stop', thinking_status='parsable_thinking')
              for c,v in [('correct',True),('correct',True),('substantive_error',False),('none_pending_review',None)]]
        self.assertTrue(eligible(rows,False)); self.assertFalse(eligible(rows,True))

    def test_thinking_completion_and_prompt_open_tag(self):
        fn=load_functions(ROOT/'data_generation/initial_sampling_postprocess.py', {'parse_thinking_steps'}, {})['parse_thinking_steps']
        final,status=fn('reasoning</think>answer', '<think>', 100)
        self.assertEqual((final,status),('answer','parsable_thinking'))
        self.assertEqual(fn('reasoning without end','<think>',100)[1],'malformed_thinking')

    def test_valid_alternative_does_not_rescue_wrong_final(self):
        path=ROOT/'outputs/game24-100q-20261014/snapshot/outputs/game24-batch03-dual-anchor-20260924/Qwen3_32B'
        found=[]
        for p in path.glob('chunk-*/draft_candidates.jsonl'):
            for line in p.read_text(encoding='utf-8').splitlines():
                r=json.loads(line)
                if r['id']=='381' and r['init_response_generations'][0]['response_id'] in (5,10):
                    found.append(r)
        self.assertEqual(len(found),2)
        for r in found:
            self.assertEqual(classify(r,'game24-batch03-dual-anchor-20260924')[0],'substantive_error')

    def test_value_and_operand_inventory_are_both_required(self):
        self.assertTrue(expression_measurement('(9+12)-(6-9)',[6,9,9,12])['exact_game24'])
        result=expression_measurement('6*((12-9)+(9/9))',[6,9,9,12])
        self.assertTrue(result['arithmetic_is_24']); self.assertFalse(result['exact_game24'])
        self.assertFalse(expression_measurement('13*(3)-(9+13)',[3,9,13,13])['arithmetic_is_24'])

    def test_saved_pool_deduplicates_chunks_and_aggregates(self):
        pool=[json.loads(line) for line in (OUT/'game24_trajectory_pool.jsonl').read_text(encoding='utf-8').splitlines()]
        batch=[r for r in pool if 'batch04' in r['batch']]
        self.assertEqual(len(batch),512)
        self.assertEqual(len({r['trajectory_id'] for r in pool}),len(pool))
        self.assertEqual({r['effective_sample_seed']-r['sample_index'] for r in batch},{20270925})

    def test_every_trajectory_index_resolves_to_unchanged_full_raw_text(self):
        rows=[json.loads(line) for line in (OUT/'game24_trajectory_pool.jsonl').read_text(encoding='utf-8').splitlines()]
        cache={}
        for r in rows:
            path=r['source_path']
            if path not in cache: cache[path]=(ROOT/path).read_text(encoding='utf-8').splitlines()
            line=cache[path][r['source_line']-1]
            self.assertEqual(hashlib.sha256(line.encode('utf-8')).hexdigest(),r['raw_record_sha256'])
            raw=json.loads(line)
            self.assertEqual(hashlib.sha256(raw['init_response_prompt'].encode('utf-8')).hexdigest(),r['prompt_sha256'])
            self.assertEqual(hashlib.sha256(raw['init_response_generations'][0]['generated_response'].encode('utf-8')).hexdigest(),r['generated_text_sha256'])

    def test_new_candidate_witnesses_and_historical_exclusion(self):
        rows=[json.loads(line) for line in (OUT/'game24_eligible_candidates.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual({r['tot_rank'] for r in rows},{'643','1119'})
        for r in rows:
            self.assertFalse(r['historical_development'])
            self.assertTrue(r['complete_dual_anchor_prefix8_batches'])
            self.assertEqual(len(r['witnesses']['correct']),2)
            self.assertEqual(len(r['witnesses']['substantive_error']),2)
        split=json.loads((OUT/'game24_split_manifest.json').read_text())
        self.assertEqual(split['state'],'not_frozen_target_not_met')
        self.assertEqual(split['held_out'],[])

class ResumeAndResourceGuards(unittest.TestCase):
    def test_campaign_cost_gate_handles_zero_yield_and_finite_budget(self):
        fn=load_functions(ROOT/'scripts/game24_100q_campaign.py',{'cost_forecast'},{'math':math})['cost_forecast']
        self.assertIsNone(fn(16,0,5,98)['remaining_hours'])
        self.assertGreater(fn(16,2,5,96)['remaining_hours'],240-5)
        self.assertLess(fn(16,3,5,95)['remaining_hours'],240-5)
        self.assertEqual(fn(32,5,8,0)['remaining_hours'],0)

    def test_wave_validation_does_not_relax_sample_quota(self):
        manifest=json.loads((OUT/'pilot_manifest.json').read_text())
        manifest.update(candidate_count=8,total_generations=128,phase='acquisition_wave',candidate_rows=manifest['candidate_rows'][:8])
        source=ROOT/'outputs/protocol-parity-audit-20260917/24.csv'
        validate(manifest,source)
        manifest['samples_per_problem']=4
        with self.assertRaises(ValueError):validate(manifest,source)

    def test_torn_tail_archived_before_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.jsonl'; raw=b'{"a":1}\n{"unfinished":'
            p.write_bytes(raw); read_journal(p)
            self.assertEqual(p.read_bytes(),b'{"a":1}\n')
            copies=list(p.parent.glob('records.jsonl.torn-*'))
            self.assertEqual(len(copies),1); self.assertEqual(copies[0].read_bytes(),raw)
            read_journal(p); self.assertEqual(p.read_bytes(),b'{"a":1}\n')

    def test_interior_corruption_not_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.jsonl'; raw=b'{"a":1}\nBAD\n{"a":2}\n'
            p.write_bytes(raw)
            with self.assertRaises(RuntimeError): read_journal(p)
            self.assertEqual(p.read_bytes(),raw)

    def test_gpu_guard_filters_uuid_and_rejects_foreign_owner(self):
        with patch('game24_100q_collect.subprocess.check_output', side_effect=['GPU-four, 80000','GPU-zero, 10\nGPU-four, 20']):
            with self.assertRaisesRegex(RuntimeError,'20'): check_gpu(4)
        with patch('game24_100q_collect.subprocess.check_output', side_effect=['GPU-four, 80000','GPU-zero, 10']):
            self.assertEqual(check_gpu(4)['uuid'],'GPU-four')

    def test_frozen_pilot_has_unique_fresh_multisets_and_budget(self):
        manifest=json.loads((OUT/'pilot_manifest.json').read_text())
        validate(manifest, ROOT/'outputs/protocol-parity-audit-20260917/24.csv')
        universe=[json.loads(x) for x in (OUT/'game24_question_manifest.jsonl').read_text(encoding='utf-8').splitlines()]
        by_id={r['tot_rank']:r for r in universe}
        for q in manifest['candidate_rows']:
            self.assertFalse(by_id[q['id']]['historical_development'])
            self.assertFalse(by_id[q['id']]['all_trajectory_ids'])
        self.assertEqual(manifest['max_pilot_gpu_hours'],8)

if __name__=='__main__': unittest.main()
