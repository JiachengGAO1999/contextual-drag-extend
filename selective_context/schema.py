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
    mask_token_spans: Tuple[Tuple[int, int], ...] = ()
    # Fixed source units: retain individual path onsets even when key unions merge.
    path_block_units: Tuple[Tuple[int, int], ...] = ()

    def validate(self) -> None:
        if not self.condition_id:
            raise ValueError("condition_id must be non-empty")
        if not self.input_ids:
            raise ValueError("input_ids must be non-empty")
        start, end = self.draft_token_span
        if not 0 <= start <= end <= len(self.input_ids):
            raise ValueError("draft_token_span is outside input_ids")
        previous = -1
        for lo, hi in self.mask_token_spans:
            if not start <= lo < hi <= end or lo < previous:
                raise ValueError("mask_token_spans must be sorted, disjoint and inside draft")
            previous = hi
        if self.mask_token_spans and self.access_mode not in (AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK):
            raise ValueError("Multi-region requests require late_block or path_block")
        validate_path_units(self.path_block_units, self.mask_token_spans,
                            self.draft_token_span, self.access_mode)
        if self.input_ids_sha256 != token_ids_sha256(self.input_ids):
            raise ValueError("input_ids_sha256 does not match input_ids")

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        if not self.path_block_units:
            value.pop('path_block_units')  # Preserve legacy serialized requests.
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
            mask_token_spans=tuple(tuple(x) for x in value.get('mask_token_spans', [])),
            path_block_units=tuple(tuple(x) for x in value.get('path_block_units', [])),
        )


def validate_path_units(units, spans, draft_span, mode):
    if not units:
        return
    if mode is not AccessMode.PATH_BLOCK or not spans:
        raise ValueError('Fixed path units require path_block and explicit key spans')
    if tuple(units) != tuple(sorted(set(units))):
        raise ValueError('Fixed units must be sorted and unique')
    start,end = draft_span
    if any(not start <= lo < hi <= end for lo,hi in units):
        raise ValueError('Fixed path unit outside draft')
    keys = lambda ranges: {k for lo,hi in ranges for k in range(lo,hi)}
    if keys(units) != keys(spans):
        raise ValueError('Fixed path units must cover exactly the explicit key union')
