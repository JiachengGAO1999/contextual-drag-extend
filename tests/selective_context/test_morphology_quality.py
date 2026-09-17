from selective_context.phase0.morphology_pilot import features,stance_proxies

def row(finish='eos',text='This expression is valid.'):
    return dict(id='x',answer=[1,2,3,4],thinking_status='parsable_thinking',final_response=text,
        init_response_generations=[dict(finish_reason=finish,correctness=False)])

def test_truncated_final_is_not_normal_even_when_thinking_parses():
    assert features(row('length'),'test')['trace_quality']=='malformed_or_truncated'

def test_negative_validity_not_positive():
    assert stance_proxies('This expression is not valid.')['endorsement_count']==0

def test_requirements_and_neutral_heading_not_endorsements():
    p=stance_proxies('Use each number exactly once.\n### Final Answer\nWe must find a valid expression.')
    assert p['endorsement_count']==0

def test_positive_negative_evidence_both_retained():
    p=stance_proxies('This expression is valid. This is incorrect.')
    assert p['endorsement_count']==p['rejection_count']==1

def test_failure_semantics_not_inferred_from_score():
    assert features(row(text='A valid calculation but final output 24'),'test')['semantic_failure_label']=='not_assigned_from_scorer_or_keywords'
