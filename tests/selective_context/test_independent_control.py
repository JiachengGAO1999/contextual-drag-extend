import json

from selective_context.phase0.paired_report import summarize
from selective_context.phase0.thinking_pilot import independent_prompt, INDEPENDENT_SUFFIX
from selective_context.prompting import locate_unique_draft


def test_independent_prompt_preserves_draft_and_common_task():
    draft = 'A wrong expression: (7 - 7) + 3 * (13 - 5).'
    text = independent_prompt('Use 3,5,7,13.', draft)
    start, end = locate_unique_draft(text)
    assert text[start:end] == draft
    assert 'INCORRECT final answer' in text
    assert text.endswith(INDEPENDENT_SUFFIX)
    assert independent_prompt('Use 3,5,7,13.').endswith(INDEPENDENT_SUFFIX)
    assert 'overall_verdict' not in text


def test_report_four_conditions_keeps_effect_labels_and_indices(tmp_path):
    path = tmp_path / 'results.jsonl'
    rows = []
    for condition, correct in [('R0', True), ('R2', False), ('R3', True), ('R4', False)]:
        rows.append(dict(id='x', init_response_generations_metadata={'intervention': {'condition_id': condition}},
                         init_response_generations=[dict(correctness=correct, finish_reason='eos')]))
    path.write_text('\n'.join(json.dumps(r) for r in rows))
    report = summarize(path, conditions=['R0','R2','R3','R4'])
    assert report['effects']['R3-R2']['effect_pp'] == 100
    assert report['effects']['R4-R3']['effect_pp'] == -100
    assert 'R0-R1' not in report['effects']
    assert report['recovery_ratios']['(R3-R2)/(R0-R2)']['value'] == 1
