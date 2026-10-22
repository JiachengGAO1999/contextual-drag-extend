"""Regression checks against real saved answers; no model or network required."""
import json
import unittest
from pathlib import Path
from analyze_batch03_partial_20260924 import (
    expression_measurement, manual_classification, record_fields, is_valid,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'runs/batch03_interrupted_20260924/raw'


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {}
        for path in RAW.glob('*/chunk-*/draft_candidates.jsonl'):
            for line in path.read_text(encoding='utf-8').splitlines():
                record = json.loads(line)
                row = record_fields(record)
                row['valid_for_eligibility'] = is_valid(record)
                cls.rows[row['model'], row['id'], row['sample_index']] = row

    def test_122_repeated_operands_are_errors_despite_value_24(self):
        for index, multiset in [(4, '8x2,9x1,12x2'), (9, '8x1,9x1,12x3')]:
            row = self.rows['Qwen3_8B_Thinking', '122', index]
            measured = expression_measurement(row['extracted_answer'], row['answer_numbers'])
            self.assertTrue(measured['arithmetic_is_24'])
            self.assertEqual(measured['actual_operand_multiset'], multiset)
            self.assertFalse(measured['exact_game24'])
            self.assertEqual(manual_classification(row)[0], 'substantive_error')

    def test_381_final_choice_is_not_rescued_by_earlier_alternative(self):
        for index in (5, 10):
            row = self.rows['Qwen3_32B', '381', index]
            self.assertFalse(expression_measurement(row['extracted_answer'], row['answer_numbers'])['exact_game24'])
            self.assertTrue(expression_measurement('11+11+8-6', row['answer_numbers'])['exact_game24'])
            self.assertEqual(manual_classification(row)[0], 'substantive_error')

    def test_three_scalar_extraction_misses_are_supported(self):
        for question, index in [('445', 13), ('395', 7), ('395', 12)]:
            row = self.rows['Qwen3_8B_Thinking', question, index]
            self.assertEqual(row['extracted_answer'], '24')
            self.assertEqual(manual_classification(row)[0], 'format_or_extraction_false_negative')

    def test_invalid_answers_cannot_supply_error_threshold(self):
        row = dict(self.rows['Qwen3_8B_Thinking', '122', 4], valid_for_eligibility=False)
        self.assertEqual(manual_classification(row)[0], 'excluded_invalid')

    def test_wrong_selected_expression_never_uses_scalar_override(self):
        row = dict(self.rows['Qwen3_8B_Thinking', '445', 13], extracted_answer='8+8+8+2')
        self.assertEqual(manual_classification(row)[0], 'uncertain_manual_confirmation')

    def test_all_scorer_true_extracted_expressions_are_exact(self):
        checked = 0
        for row in self.rows.values():
            if row['valid_for_eligibility'] and row['correctness'] is True:
                self.assertTrue(expression_measurement(row['extracted_answer'], row['answer_numbers'])['exact_game24'],
                                (row['model'], row['id'], row['sample_index']))
                checked += 1
        self.assertEqual(checked, 771)


if __name__ == '__main__':
    unittest.main(verbosity=2)
