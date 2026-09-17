"""Characterize shipped aggregation semantics without loading models/datasets."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace


def functions():
    root=Path(__file__).resolve().parents[2]
    module=ast.parse((root/'data_generation/aggregate_data.py').read_text())
    names={'preprocess_dataset','filter_problem','combination'}
    nodes=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace={'math':math,'tqdm':lambda x:x}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<upstream>','exec'),namespace)
    return namespace


def test_shipped_aggregation_counts_null_and_requires_both_classes():
    ns=functions()
    args=SimpleNamespace(problem_id_column='id',init_response_correctness_column='correctness',
        filter_init_response_completeness=True,filter_init_response_parsable_thinking=True,
        num_true=0,num_false=2)
    ds={'id':['a']*6,'correctness':[True,True,False,None,False,False],
        'init_response_generations_finish_reason':['stop']*4+['length','stop'],
        'init_response_thinking_status':['parsable_thinking']*5+['malformed_thinking']}
    entries=ns['preprocess_dataset'](ds,args)
    assert entries['a']['correct']==[0,1]
    assert entries['a']['incorrect']==[2,3]
    assert ns['filter_problem'](entries,args)==['a']
    entries['a']['correct']=[0]
    assert ns['filter_problem'](entries,args)==[]


def test_1f_is_two_rows_without_changing_question_identity():
    # Characterize actual flattening loop; do not call its broken F2 output path.
    import copy
    root=Path(__file__).resolve().parents[2]
    module=ast.parse((root/'data_generation/minimal_aggregate_flatten.py').read_text())
    main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    loop=next(n for n in main.body if isinstance(n,ast.For))
    row={'id':'p','traj1':'a','traj2':'b','traj1_correctness':False,
         'traj2_correctness':False,'traj1_metadata':{'source':'A'},'traj2_metadata':{'source':'B'}}
    ns={'copy':copy,'tqdm':lambda x:x,'dataset':[row],'new_ds':[]}
    exec(compile(ast.Module(body=[loop],type_ignores=[]),'<upstream flatten>','exec'),ns)
    assert [r['id'] for r in ns['new_ds']]==['p','p']
    assert [r['traj1'] for r in ns['new_ds']]==['a','b']
    assert row['traj2']=='b'
