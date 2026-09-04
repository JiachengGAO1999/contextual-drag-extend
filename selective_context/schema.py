from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple


class AccessMode(str, Enum):
    FULL = "full"
    LATE_BLOCK = "late_block"
    PATH_BLOCK = "path_block"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def token_ids_sha256(input_ids: List[int]) -> str:
    # A textual, delimiter-separated encoding is stable across platforms and integer widths.
    payload = ",".join(str(int(value)) for value in input_ids).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class SelectiveContextRequest:
    condition_id: str
    input_ids: List[int]
    prompt_sha256: str
    input_ids_sha256: str
    draft_token_span: Tuple[int, int]
    access_mode: AccessMode
    sample_seed: int

    def validate(self) -> None:
        if not self.condition_id:
            raise ValueError("condition_id must be non-empty")
        if not self.input_ids:
            raise ValueError("input_ids must be non-empty")
        start, end = self.draft_token_span
        if not 0 <= start <= end <= len(self.input_ids):
            raise ValueError("draft_token_span is outside input_ids")
        if self.input_ids_sha256 != token_ids_sha256(self.input_ids):
            raise ValueError("input_ids_sha256 does not match input_ids")

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["access_mode"] = self.access_mode.value
        value["draft_token_span"] = list(self.draft_token_span)
        return value

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "SelectiveContextRequest":
        return cls(
            condition_id=value["condition_id"],
            input_ids=[int(item) for item in value["input_ids"]],
            prompt_sha256=value["prompt_sha256"],
            input_ids_sha256=value["input_ids_sha256"],
            draft_token_span=tuple(value["draft_token_span"]),
            access_mode=AccessMode(value["access_mode"]),
            sample_seed=int(value["sample_seed"]),
        )
