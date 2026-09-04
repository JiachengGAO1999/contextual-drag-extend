from __future__ import annotations

import json
import tempfile
from pathlib import Path

from selective_context.hf_backend import GenerationResult
from selective_context.official_compat import evaluate_game24_record, make_official_record, write_jsonl
from selective_context.schema import AccessMode, SelectiveContextRequest, text_sha256, token_ids_sha256


def main() -> None:
    input_ids = [1, 2, 3]
    request = SelectiveContextRequest("R2", input_ids, text_sha256("toy"), token_ids_sha256(input_ids), (1, 2), AccessMode.FULL, 1)
    generation = GenerationResult([], r"A valid construction is \boxed{(6-2)*(3+3)=24}.", "stop", {"backend": "fixture"})
    record = make_official_record(problem_id="toy-0", problem="Use 6 2 3 3 to make 24", answer=[6, 2, 3, 3], prompt="toy", request=request, generations=[generation], model_config_alias="fixture")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dataset.jsonl"
        write_jsonl(path, [record])
        loaded = json.loads(path.read_text(encoding="utf-8").strip())
        evaluated = evaluate_game24_record(loaded)
    response = evaluated["init_response_generations"][0]
    assert response["correctness"] is True, response
    print(json.dumps({"status": "ok", "extracted_answer": response["extracted_answer"], "correctness": True}))


if __name__ == "__main__":
    main()
