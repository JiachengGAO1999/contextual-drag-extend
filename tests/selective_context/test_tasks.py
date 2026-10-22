import pytest
from selective_context.tasks import independent_prompt, score_record, validate_pair_task

def test_game24_legacy_prompt_exact():
    expected=('Original problem:\np\n\nThe following draft has an INCORRECT final answer.\n'
        '-- beginning of the draft --\nd\n-- end of the draft --\n\n'
        'Solve the original problem independently and provide a complete solution. '
        'You do not need to evaluate or refer to any preceding draft. '
        'Conclude with an expression using the original four numbers exactly once in \\boxed{}.')
    assert independent_prompt('p','d') == expected

def test_math500_no_game24_instruction_or_label_on_r0():
    assert 'four numbers' not in independent_prompt('p',task='math500')
    assert 'INCORRECT' not in independent_prompt('p',task='math500')
    assert '-- beginning of the draft --\nd\n-- end of the draft --' in independent_prompt('p','d','math500')

def test_mismatched_task_fails_closed():
    with pytest.raises(ValueError):validate_pair_task({'answer':'2'},'math500')
    with pytest.raises(ValueError):validate_pair_task({'task':'math500','answer':[2]},'math500')
    with pytest.raises(ValueError):independent_prompt('p',task='typo')

@pytest.mark.parametrize('answer,output,expected',[
    (r'\frac{1}{2}',r'\boxed{0.5}',True),
    ('2',r'\boxed{3}',False),
    ('2','No final expression',None),
])
def test_official_math_scoring(answer,output,expected):
    pytest.importorskip('math_verify')
    r={'answer':answer,'init_response_generations':[{'generated_response':output}]}
    assert score_record(r,'math500')['init_response_generations'][0]['correctness'] is expected

def test_scorers_are_not_interchangeable():
    pytest.importorskip('math_verify')
    r={'answer':[1,1,2,12],'init_response_generations':[{'generated_response':r'\boxed{24}'}]}
    assert score_record(r,'game24')['init_response_generations'][0]['correctness'] is False

def test_math500_bundles_preserve_text_and_block_boundaries(tmp_path):
    from selective_context.prompting import encode_prompt, make_r2_r4_requests, persist_request_bundle, load_request_bundle
    from selective_context.testing import CharacterTokenizer
    from selective_context.vllm_mask import key_block_onsets, request_metadata, NEVER
    text=independent_prompt('Solve 2x=1.', r'Therefore x=2 and \boxed{2}.', 'math500')
    enc=encode_prompt(CharacterTokenizer(),text)
    requests=make_r2_r4_requests(enc,927001)
    path=tmp_path/'bundle.json'
    persist_request_bundle(path,enc,requests)
    restored,rs=load_request_bundle(path)
    assert restored.text==text
    assert all(r.input_ids==requests[0].input_ids for r in rs)
    lo,hi=enc.draft_token_span;n=len(enc.input_ids)
    for r,onset in zip(rs,[NEVER,n,hi]):
        assert key_block_onsets(request_metadata(r))==[onset if lo<=k<hi else NEVER for k in range(n)]
