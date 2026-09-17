import json
import pytest
from selective_context.phase0.paired_report import summarize


def test_paired_report_counts_reversals_and_keeps_unparsed_in_denominator(tmp_path):
    rows = []
    outcomes = [[True, False, False, True, True], [True, True, True, False, True],
                [False, None, False, False, True], [True, False, False, True, True]]
    for i, values in enumerate(outcomes):
        for c, value in enumerate(values):
            rows.append({"id": str(i), "init_response_generations_metadata": {
                "intervention": {"condition_id": f"R{c}"}},
                "init_response_generations": [{"correctness": value, "finish_reason": "eos"}]})
    path = tmp_path / "results.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    result = summarize(path, bootstrap_samples=1000)
    assert result["n_complete_pairs"] == 4
    assert result["conditions"]["R1"]["parse_rate"] == .75
    effect = result["effects"]["R3-R2"]
    assert effect["effect_pp"] == 25
    assert effect["reference_wrong_to_correct"] == 2
    assert effect["reference_correct_to_wrong"] == 1
    assert result["recovery_ratios"]["(R3-R2)/(R0-R2)"]["value"] == .5
    with path.open("a") as handle:
        handle.write("\n" + json.dumps(rows[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(path)
