from pathlib import Path

import pytest

from selective_context.prompting import DRAFT_BEGIN, DRAFT_END, assert_same_text_contract, char_span_to_token_span, encode_direct_prompt, encode_prompt, load_request_bundle, make_r2_r4_requests, persist_request_bundle, render_official_prompt
from selective_context.testing import CharacterTokenizer


ROOT = Path(__file__).resolve().parents[2]


def test_official_r2_r4_same_text_contract():
    text = render_official_prompt(ROOT, "R2", "Use 1 2 3 4 to make 24", "1 + 2 = 9")
    encoded = encode_prompt(CharacterTokenizer(), text)
    requests = make_r2_r4_requests(encoded, 2027)
    assert_same_text_contract(requests)
    assert [request.access_mode.value for request in requests] == ["full", "late_block", "path_block"]
    assert len({tuple(request.input_ids) for request in requests}) == 1
    assert len({request.prompt_sha256 for request in requests}) == 1
    assert len({request.input_ids_sha256 for request in requests}) == 1


@pytest.mark.parametrize("text", ["no delimiters", DRAFT_BEGIN + "x", "x" + DRAFT_END, DRAFT_BEGIN + DRAFT_END])
def test_missing_or_empty_delimiters_fail(text):
    with pytest.raises(ValueError):
        encode_prompt(CharacterTokenizer(), text)


def test_duplicate_delimiters_fail():
    text = DRAFT_BEGIN + "x" + DRAFT_END + DRAFT_BEGIN + "y" + DRAFT_END
    with pytest.raises(ValueError):
        encode_prompt(CharacterTokenizer(), text)


def test_truncated_span_fails():
    with pytest.raises(ValueError, match="truncated"):
        char_span_to_token_span([(0, 2)], (3, 4))


def test_cross_token_boundary_fails():
    with pytest.raises(ValueError, match="boundary"):
        char_span_to_token_span([(0, 2), (2, 4)], (1, 4))


def test_qwen_markdown_newline_boundary_uses_minimal_covering_span():
    text = "We**\nNext"
    assert char_span_to_token_span([(0, 2), (2, 5), (5, 9)], (0, 4), text) == (0, 2)


def test_formatting_spillover_on_both_boundaries_allowed():
    text = "\n**draft**\n"
    assert char_span_to_token_span([(0, 4), (4, 8), (8, 11)], (3, 8), text) == (0, 2)


def test_semantic_boundary_spillover_rejected():
    with pytest.raises(ValueError, match="semantic"):
        char_span_to_token_span([(0, 2), (2, 7)], (0, 4), "We**Now")


def test_partial_token_coverage_rejected():
    with pytest.raises(ValueError, match="truncated"):
        char_span_to_token_span([(0, 2)], (0, 4), "abcd")


def test_request_bundle_roundtrip_and_hash_validation(tmp_path):
    text = render_official_prompt(ROOT, "R2", "game", "6 - 2 = 5")
    encoded = encode_prompt(CharacterTokenizer(), text)
    requests = make_r2_r4_requests(encoded, 4)
    path = tmp_path / "requests.json"
    persist_request_bundle(path, encoded, requests)
    loaded_encoded, loaded_requests = load_request_bundle(path)
    assert loaded_encoded == encoded
    assert loaded_requests == requests


def test_direct_prompt_has_empty_noop_span():
    encoded = encode_direct_prompt(CharacterTokenizer(), "direct problem")
    assert encoded.draft_token_span == (0, 0)
    assert encoded.draft_character_span == (0, 0)
