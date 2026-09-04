import json

from selective_context.hf_backend import GenerationResult, append_jsonl_resumable
from selective_context.official_compat import evaluate_game24_record, make_official_record, write_jsonl
from selective_context.schema import AccessMode, SelectiveContextRequest, text_sha256, token_ids_sha256


def request():
    ids = [1, 2, 3]
    return SelectiveContextRequest("R2", ids, text_sha256("p"), token_ids_sha256(ids), (1, 2), AccessMode.FULL, 5)


def test_jsonl_roundtrip_through_official_game24_verifier(tmp_path):
    result = GenerationResult([], r"\boxed{(6-2)*(3+3)=24}", "stop", {"kv": "recorded"})
    record = make_official_record(problem_id="x", problem="game", answer=[6, 2, 3, 3], prompt="p", request=request(), generations=[result], model_config_alias="tiny")
    path = tmp_path / "dataset.jsonl"
    write_jsonl(path, [record])
    loaded = json.loads(path.read_text())
    evaluated = evaluate_game24_record(loaded)
    assert evaluated["init_response_generations"][0]["correctness"] is True
    assert evaluated["init_response_generations_metadata"]["intervention"]["condition_id"] == "R2"


def test_resume_deduplicates(tmp_path):
    path = tmp_path / "resume.jsonl"
    record = {"id": "x", "value": 1}
    assert append_jsonl_resumable(path, "id", record)
    assert not append_jsonl_resumable(path, "id", record)
    assert len(path.read_text().splitlines()) == 1
