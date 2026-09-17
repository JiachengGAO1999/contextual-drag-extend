import json
import pytest
from selective_context.phase0.heldout_drafts import prepare


def test_excludes_historical_ids_and_number_permutations(tmp_path):
    history=tmp_path/'outputs'/'old';history.mkdir(parents=True)
    (history/'draft_candidates.jsonl').write_text(json.dumps({'id':'1','answer':[1,2,3,4]})+'\n')
    source=tmp_path/'pool.csv'
    source.write_text('Rank,Puzzles\n1,5 6 7 8\n2,4 3 2 1\n'+''.join(f'{i},{i} 1 2 3\n' for i in range(3,15)))
    destination=tmp_path/'plan.json'
    plan=prepare(tmp_path,source,destination)
    assert len(plan['questions'])==8
    assert not {'1','2'} & {r['id'] for r in plan['questions']}
    assert plan['screening_cap']==32 and plan['evaluation_cap']==48
    with pytest.raises(ValueError,match='frozen plan'):
        prepare(tmp_path,source,destination)


def test_missing_history_is_not_assumed_fresh(tmp_path):
    with pytest.raises(ValueError,match='historical records'):
        prepare(tmp_path,tmp_path/'unused.csv',tmp_path/'plan.json')
