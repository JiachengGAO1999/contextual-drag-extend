import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import run_failure_adoption_20261011 as adoption


def test_symbolic_conversion_preserves_value_and_resource_violation():
    bindings=dict(A=5,B=7,C=8,D=8)
    bad=adoption.symbolise('8*(7-(5-8/8))',bindings)
    audited=adoption.audit_expression(bad,[5,7,8,8],bindings)
    assert audited['target_correct'] and not audited['inventory_correct']
    assert not audited['identity_correct']
    good=adoption.symbolise('8*(7-5)+8',bindings)
    assert adoption.audit_expression(good,[5,7,8,8],bindings)['correct']


def test_candidate_checking_and_adoption_are_separate_observations():
    q=dict(first_seed_old_index=1)
    r=adoption.score_candidate('</think>{"option_1_valid":false,"option_2_valid":true,"choice":1}',q,adoption.SEEDS[0])
    assert r['judgments_correct'] and r['old_selected'] and not r['correct']
    assert r['recognized_but_selected_old'] and not r['old_accepted']
    # In the second seed the old candidate moves to option 2.
    r=adoption.score_candidate('</think>{"option_1_valid":true,"option_2_valid":false,"choice":1}',q,adoption.SEEDS[1])
    assert r['judgments_correct'] and r['correct'] and not r['old_selected']


def test_unclosed_thinking_incomplete_json_and_boolean_choice_do_not_pass():
    q=dict(first_seed_old_index=1)
    valid='{"option_1_valid":false,"option_2_valid":true,"choice":2}'
    assert not adoption.score_candidate(valid,q,adoption.SEEDS[0])['correct']
    assert not adoption.score_candidate('</think>'+valid+'\n{"choice":',q,adoption.SEEDS[0])['correct']
    r=adoption.score_candidate('</think>{"option_1_valid":false,"option_2_valid":true,"choice":true}',q,adoption.SEEDS[0])
    assert not r['correct'] and not r['choice_parsed'] and not r['recognized_but_selected_old']


def test_candidates_match_between_history_conditions_and_keep_draft_verbatim():
    q=dict(problem='Use 1,5,9,12.',answer=[1,5,9,12],bindings=dict(A=1,B=5,C=9,D=12),
           draft='The original draft\ncontains 1 twice.',old_numeric='(9-1)*12/(5-1)',legal_numeric='12*(9+1)/5',
           first_seed_old_index=1)
    q['old_symbolic']=adoption.symbolise(q['old_numeric'],q['bindings'])
    q['legal_symbolic']=adoption.symbolise(q['legal_numeric'],q['bindings'])
    for prefix in ('COUNT','IDENTITY'):
        clean=adoption.prompt_for(q,prefix+'_CLEAN','CANDIDATES',adoption.SEEDS[0])
        history=adoption.prompt_for(q,prefix+'_HISTORY','CANDIDATES',adoption.SEEDS[0])
        assert clean[clean.index('Option 1:'):]==history[history.index('Option 1:'):]
        assert q['draft'] in history and q['draft'] not in clean


def test_missing_judgments_are_not_counted_as_rejecting_the_old_candidate():
    q=dict(first_seed_old_index=1)
    missing=adoption.score_candidate('unfinished thinking',q,adoption.SEEDS[0])
    rejection=adoption.score_candidate('</think>{"option_1_valid":false,"option_2_valid":true,"choice":2}',q,adoption.SEEDS[0])
    accepted=adoption.score_candidate('</think>{"option_1_valid":true,"option_2_valid":false,"choice":1}',q,adoption.SEEDS[0])
    observations=adoption.candidate_observations([missing,rejection,accepted])
    assert observations['total']==3 and observations['judgments_missing']==1
    assert observations['old_rejected_observed']==observations['old_accepted_observed']==1
    assert observations['choices_missing']==1


def test_cross_phase_pairs_require_the_same_question_condition_and_seed():
    manifest=dict(questions=[dict(id='q',split='discovery')])
    records={
        ('q','NATURAL','COUNT_HISTORY',adoption.SEEDS[0]):dict(correct=False,structural_reuse=True),
        ('q','CANDIDATES','COUNT_HISTORY',adoption.SEEDS[0]):dict(correct=True,judgments_correct=True,choice_parsed=True),
        ('q','NATURAL','COUNT_HISTORY',adoption.SEEDS[1]):dict(correct=False),
        ('q','CANDIDATES','IDENTITY_HISTORY',adoption.SEEDS[1]):dict(correct=True),
    }
    result=adoption.cross_phase_observations(manifest,records)
    assert result['conditions']['COUNT_HISTORY']['paired_requests']==1
    assert result['conditions']['COUNT_HISTORY']['natural_old_reuse_candidate_right']==1
    assert result['conditions']['IDENTITY_HISTORY']['paired_requests']==0
