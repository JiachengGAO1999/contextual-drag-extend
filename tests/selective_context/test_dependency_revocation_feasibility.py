"""Check the semantic contrast, not merely serialized implementation details."""
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[2]/"scripts/prepare_dependency_revocation_20261011.py"
spec = importlib.util.spec_from_file_location("dependency_materials", path)
materials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materials)


def test_same_cached_numbers_have_opposite_repair_targets_after_dependency_swap():
    pair = [materials.make_variant((12, 7, 8, 1, 4, 2), swapped) for swapped in (False, True)]
    assert [x["cached_value"] for x in pair[0]["oracle"]] == ["13", "13", "17", "17", "34", "34"]
    assert [x["true_value"] for x in pair[0]["oracle"]][-2:] == ["32", "34"]
    assert [x["true_value"] for x in pair[1]["oracle"]][-2:] == ["34", "32"]
    assert materials.audit_materials([dict(variants=pair)])["model_calls"] == 0


def test_dependency_does_not_by_itself_imply_a_wrong_numeric_value():
    rows = materials.evaluate([
        dict(id="A", left=19, op="-", right=7, cached=13),
        dict(id="B", left="A", op="*", right=0, cached=0),
    ])
    assert "A" in rows[1]["ancestors"]
    assert rows[1]["mathematically_correct"] and rows[1]["locally_consistent"]
    with pytest.raises(ValueError, match="Forward reference"):
        materials.evaluate([dict(id="B", left="A", op="+", right=1)])


def test_whole_cpu_feasibility_set_has_one_local_fault_and_valid_counterfactuals():
    questions = materials.build_materials()
    report = materials.audit_materials(questions)
    assert report["base_examples"] == 8 and report["wiring_variants"] == 16
