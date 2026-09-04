from __future__ import annotations

from typing import Dict, List, Tuple


class CharacterTokenizer:
    """Deterministic offset tokenizer for local tests; one Unicode code point per token."""

    eos_token_id = 0
    pad_token_id = 0

    def __call__(self, text: str, **_: object) -> Dict[str, List]:
        return {
            "input_ids": [ord(character) % 251 + 1 for character in text],
            "offset_mapping": [(index, index + 1) for index in range(len(text))],
        }

    def decode(self, token_ids: List[int], **_: object) -> str:
        return " ".join(str(value) for value in token_ids)
