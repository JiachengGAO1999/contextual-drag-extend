"""Protect the statistical units and censoring semantics of Goal 2 analysis."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validated_probe", ROOT / "scripts/analyse_validated_probe_20261013.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def row(qid, early, final, known=True):
    return dict(id=qid, early_adopt=early, final_reuse=final, final_route_known=known)


def test_unknown_route_is_not_a_negative():
    sample = [row("a", True, True), row("b", False, False)]
    assert probe.confusion_metrics(sample + [row("c", True, None, False)]) == probe.confusion_metrics(sample)
    assert not probe.reference_known(dict(final_available=False, parsed=False))
    assert not probe.reference_known(dict(final_available=True, parsed=True, structural_reuse=False, finish_reason="length"))


def test_question_weight_does_not_turn_seeds_into_independent_questions():
    sample = [row("a", True, True), row("a", True, True), row("b", True, False), row("c", False, False)]
    assert probe.confusion_metrics(sample)["adoption_precision"] == .5
    assert probe.confusion_metrics(sample, equal_question=False)["adoption_precision"] == pytest.approx(2 / 3)
    assert probe.confusion_metrics(sample)["balanced_accuracy"] == .75
    assert probe.confusion_metrics(sample, ["a", "a", "b", "c"])["adoption_precision"] == pytest.approx(2 / 3)


def test_absent_reference_class_does_not_produce_valid_accuracy():
    assert probe.confusion_metrics([row("a", True, True)])["balanced_accuracy"] is None
    assert probe.confusion_metrics([row("b", False, False)])["adoption_precision"] is None


def test_incomplete_annotations_stop_before_reading_future_files(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "development_prefixes.json").write_text(json.dumps([dict(id="a", condition="CLEAN", seed=1)]), encoding="utf-8")
    (tmp_path / "development_labels.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="Freeze all 80"):
        probe.evaluate(tmp_path)
