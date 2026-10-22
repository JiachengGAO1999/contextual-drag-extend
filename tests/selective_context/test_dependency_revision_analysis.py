import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
spec = importlib.util.spec_from_file_location("dependency_revision", ROOT/"scripts/run_dependency_revision_20261011.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_analysis_keeps_root_success_separate_from_stale_dependent_and_preserved_independent(tmp_path):
    questions = runner.build_materials(2)
    manifest = dict(questions=questions,planned_score_units=36)
    records = []
    for question in questions:
        for variant in question["variants"]:
            for condition in runner.CONDITIONS:
                for readout in variant["readouts"]:
                    margin = 2. if readout["depends_on_error"] else -2.
                    if condition=="CORRECT_ROOT" and readout["node"]!="S1" and readout["depends_on_error"]:
                        margin=-1.
                    records.append(dict(id=question["id"],wiring=variant["wiring"],condition=condition,
                                        node=readout["node"],margin=margin,mean_margin=margin/2))
    path=tmp_path/"scores.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records)+"\n",encoding="utf8")
    result=runner.analyse(manifest,tmp_path)
    assert result["complete_base_graphs"]==2
    assert result["primary"]["mean"]==-3.
    assert result["conditions"]["CORRECT_ROOT"]["counts"]["root_correct"]==4
    assert result["conditions"]["CORRECT_ROOT"]["counts"]["independent_preserved"]==4
    assert result["conditions"]["CORRECT_ROOT"]["counts"]["root_correct_dependent_stale_independent_correct"]==4
    # An incomplete wiring is missing data, not another independent successful case.
    path.write_text("\n".join(json.dumps(r) for r in records[:-1])+"\n",encoding="utf8")
    result=runner.analyse(manifest,tmp_path)
    assert result["complete_base_graphs"]==1 and len(result["missing"])==1
