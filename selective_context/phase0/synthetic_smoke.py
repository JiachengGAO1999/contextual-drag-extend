from __future__ import annotations

import json
import tempfile
from pathlib import Path

from selective_context.hf_backend import SelectiveHFBackend, append_jsonl_resumable
from selective_context.phase0.tiny_model import NumericTokenizer, make_tiny_qwen
from selective_context.schema import AccessMode, SelectiveContextRequest, text_sha256, token_ids_sha256


def main() -> None:
    input_ids = [1, 11, 12, 13, 21, 22, 31]
    request = SelectiveContextRequest(
        condition_id="R4",
        input_ids=input_ids,
        prompt_sha256=text_sha256("synthetic-prompt"),
        input_ids_sha256=token_ids_sha256(input_ids),
        draft_token_span=(1, 4),
        access_mode=AccessMode.PATH_BLOCK,
        sample_seed=2027,
    )
    backend = SelectiveHFBackend(make_tiny_qwen(), NumericTokenizer())
    first = backend.generate(request, max_new_tokens=3, temperature=0.8, top_k=20)
    second = backend.generate(request, max_new_tokens=3, temperature=0.8, top_k=20)
    assert first.generated_token_ids == second.generated_token_ids
    assert first.metadata["logical_kv_blocking"] is True
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "resume.jsonl"
        record = {"request_key": "synthetic:R4:2027", "tokens": first.generated_token_ids}
        assert append_jsonl_resumable(path, "request_key", record)
        assert not append_jsonl_resumable(path, "request_key", record)
        assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    print(json.dumps({"status": "ok", "tokens": first.generated_token_ids, "metadata": first.metadata}))


if __name__ == "__main__":
    main()
