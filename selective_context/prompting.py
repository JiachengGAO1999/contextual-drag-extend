from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .schema import AccessMode, SelectiveContextRequest, text_sha256, token_ids_sha256


DRAFT_BEGIN = "-- beginning of the draft --\n"
DRAFT_END = "\n-- end of the draft --"


@dataclass(frozen=True)
class EncodedPrompt:
    text: str
    input_ids: List[int]
    draft_character_span: Tuple[int, int]
    draft_token_span: Tuple[int, int]


def load_official_template(repo_root: Path, condition_id: str) -> str:
    sources = {
        "R0": ("prompt_templates/init_response_prompt_templates.json", "qwen_math_prompt"),
        "R1": ("prompt_templates/1f_templates.json", "1f"),
        "R2": ("prompt_templates/prompted_error_signal_templates.json", "new_prompted_error_signal_1f"),
        "R3": ("prompt_templates/prompted_error_signal_templates.json", "new_prompted_error_signal_1f"),
        "R4": ("prompt_templates/prompted_error_signal_templates.json", "new_prompted_error_signal_1f"),
    }
    try:
        relative_path, key = sources[condition_id]
    except KeyError as exc:
        raise ValueError(f"unknown condition: {condition_id}") from exc
    with (repo_root / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)[key]


def render_official_prompt(repo_root: Path, condition_id: str, problem: str, draft: str = "") -> str:
    template = load_official_template(repo_root, condition_id)
    # Match upstream format_template_with_row: literal replacement leaves \boxed{}
    # and other non-argument braces untouched.
    return template.replace("{arg_problem}", problem).replace("{arg_traj1}", draft)


def locate_unique_draft(text: str) -> Tuple[int, int]:
    begins = _all_indices(text, DRAFT_BEGIN)
    ends = _all_indices(text, DRAFT_END)
    if len(begins) != 1 or len(ends) != 1:
        raise ValueError(f"expected one draft delimiter pair, found {len(begins)} begin/{len(ends)} end")
    start = begins[0] + len(DRAFT_BEGIN)
    end = ends[0]
    if end < start:
        raise ValueError("draft delimiters are reversed")
    if end == start:
        raise ValueError("draft span is empty")
    return start, end


def _all_indices(text: str, needle: str) -> List[int]:
    indices: List[int] = []
    offset = 0
    while True:
        found = text.find(needle, offset)
        if found < 0:
            return indices
        indices.append(found)
        offset = found + len(needle)


def char_span_to_token_span(
    offsets: Sequence[Sequence[int]], character_span: Tuple[int, int]
) -> Tuple[int, int]:
    char_start, char_end = character_span
    if char_end <= char_start:
        raise ValueError("character span must be non-empty")
    overlapping = [
        index
        for index, pair in enumerate(offsets)
        for token_start, token_end in [tuple(pair)]
        if token_end > token_start and token_start < char_end and token_end > char_start
    ]
    if not overlapping:
        raise ValueError("character span was truncated or has no token coverage")
    if overlapping != list(range(overlapping[0], overlapping[-1] + 1)):
        raise ValueError("character span maps to non-contiguous tokens")
    first_start, _ = offsets[overlapping[0]]
    _, last_end = offsets[overlapping[-1]]
    if first_start != char_start or last_end != char_end:
        raise ValueError("draft delimiter crosses a token boundary; exact masking is unsafe")
    return overlapping[0], overlapping[-1] + 1


def encode_prompt(tokenizer: Any, text: str) -> EncodedPrompt:
    character_span = locate_unique_draft(text)
    encoded: Dict[str, Any] = tokenizer(
        text, add_special_tokens=False, return_offsets_mapping=True, truncation=False
    )
    input_ids = _flatten_single(encoded["input_ids"])
    offsets = _flatten_offsets(encoded["offset_mapping"])
    if len(input_ids) != len(offsets):
        raise ValueError("tokenizer returned mismatched input_ids and offset_mapping")
    token_span = char_span_to_token_span(offsets, character_span)
    return EncodedPrompt(text, input_ids, character_span, token_span)


def encode_direct_prompt(tokenizer: Any, text: str) -> EncodedPrompt:
    encoded: Dict[str, Any] = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
    input_ids = _flatten_single(encoded["input_ids"])
    offsets = _flatten_offsets(encoded["offset_mapping"])
    if not input_ids or len(input_ids) != len(offsets):
        raise ValueError("invalid direct-prompt tokenization")
    return EncodedPrompt(text, input_ids, (0, 0), (0, 0))


def render_chat_prompt(tokenizer: Any, content: str, enable_thinking: bool = False) -> str:
    """Apply the same single-user-message chat wrapping as official inference."""
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )


def make_request(encoded: EncodedPrompt, condition_id: str, access_mode: AccessMode, seed: int) -> SelectiveContextRequest:
    request = SelectiveContextRequest(
        condition_id=condition_id,
        input_ids=list(encoded.input_ids),
        prompt_sha256=text_sha256(encoded.text),
        input_ids_sha256=token_ids_sha256(encoded.input_ids),
        draft_token_span=encoded.draft_token_span,
        access_mode=access_mode,
        sample_seed=seed,
    )
    request.validate()
    return request


def make_r2_r4_requests(encoded: EncodedPrompt, seed: int) -> List[SelectiveContextRequest]:
    return [
        make_request(encoded, "R2", AccessMode.FULL, seed),
        make_request(encoded, "R3", AccessMode.LATE_BLOCK, seed),
        make_request(encoded, "R4", AccessMode.PATH_BLOCK, seed),
    ]


def assert_same_text_contract(requests: Iterable[SelectiveContextRequest]) -> None:
    requests = list(requests)
    if not requests:
        raise ValueError("at least one request is required")
    reference = requests[0]
    fields = ("input_ids", "prompt_sha256", "input_ids_sha256", "draft_token_span")
    for request in requests:
        request.validate()
        for field in fields:
            if getattr(request, field) != getattr(reference, field):
                raise ValueError(f"same-text contract violated for {field}")


def persist_request_bundle(path: Path, encoded: EncodedPrompt, requests: Iterable[SelectiveContextRequest]) -> None:
    requests = list(requests)
    assert_same_text_contract(requests)
    payload = {
        "schema_version": 1,
        "prompt_text": encoded.text,
        "draft_character_span": list(encoded.draft_character_span),
        "requests": [request.to_dict() for request in requests],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_request_bundle(path: Path) -> Tuple[EncodedPrompt, List[SelectiveContextRequest]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported request bundle schema")
    requests = [SelectiveContextRequest.from_dict(value) for value in payload["requests"]]
    assert_same_text_contract(requests)
    reference = requests[0]
    encoded = EncodedPrompt(
        text=payload["prompt_text"],
        input_ids=list(reference.input_ids),
        draft_character_span=tuple(payload["draft_character_span"]),
        draft_token_span=reference.draft_token_span,
    )
    if text_sha256(encoded.text) != reference.prompt_sha256:
        raise ValueError("persisted prompt text hash mismatch")
    return encoded, requests


def _flatten_single(value: Any) -> List[int]:
    if value and isinstance(value[0], (list, tuple)):
        if len(value) != 1:
            raise ValueError("encode_prompt accepts one prompt at a time")
        value = value[0]
    return [int(item) for item in value]


def _flatten_offsets(value: Any) -> List[Tuple[int, int]]:
    if value and value[0] and isinstance(value[0][0], (list, tuple)):
        if len(value) != 1:
            raise ValueError("encode_prompt accepts one prompt at a time")
        value = value[0]
    return [(int(start), int(end)) for start, end in value]
