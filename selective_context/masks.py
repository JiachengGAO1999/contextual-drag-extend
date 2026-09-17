from __future__ import annotations

from typing import Optional, Sequence, Tuple

import torch

from .schema import AccessMode, validate_path_units


def build_allowed_attention(
    *,
    batch_size: int,
    query_positions: Sequence[int],
    key_length: int,
    draft_token_span: Tuple[int, int],
    access_mode: AccessMode,
    prompt_length: int,
    device: Optional[torch.device] = None,
    mask_token_spans: Sequence[Tuple[int, int]] = (),
    path_block_units: Sequence[Tuple[int, int]] = (),
) -> torch.Tensor:
    """Return [batch, 1, query, key] causal access edges.

    `late_block` blocks draft keys only for generated queries (absolute position >=
    prompt_length). For each selected interval [lo, hi), `path_block` blocks its
    keys for every query at or after hi, including subsequent draft queries.
    Without explicit intervals, the whole draft is one interval (legacy R4).
    Fixed path_block_units preserve each source unit's end, without merging onsets.
    """
    if batch_size <= 0 or key_length <= 0:
        raise ValueError("batch_size and key_length must be positive")
    start, end = draft_token_span
    if not 0 <= start <= end <= prompt_length <= key_length:
        raise ValueError("invalid draft span, prompt length, or key length")
    if mask_token_spans and access_mode not in (AccessMode.LATE_BLOCK, AccessMode.PATH_BLOCK):
        raise ValueError('Multi-region mask requires late_block or path_block')
    previous = -1
    for lo, hi in mask_token_spans:
        if not start <= lo < hi <= end or lo < previous:
            raise ValueError('Invalid multi-region spans')
        previous = hi
    validate_path_units(path_block_units, mask_token_spans, draft_token_span, access_mode)
    query_positions_tensor = torch.as_tensor(query_positions, dtype=torch.long, device=device)
    if query_positions_tensor.ndim != 1 or query_positions_tensor.numel() == 0:
        raise ValueError("query_positions must be a non-empty one-dimensional sequence")
    if torch.any(query_positions_tensor < 0) or torch.any(query_positions_tensor >= key_length):
        raise ValueError("query position outside key range")

    key_positions = torch.arange(key_length, device=device)
    allowed = key_positions.view(1, -1) <= query_positions_tensor.view(-1, 1)
    if end > start and access_mode is not AccessMode.FULL:
        for lo, hi in path_block_units or mask_token_spans or ((start, end),):
            selected_keys = (key_positions >= lo) & (key_positions < hi)
            if access_mode is AccessMode.LATE_BLOCK:
                affected_queries = query_positions_tensor >= prompt_length
            elif access_mode is AccessMode.PATH_BLOCK:
                affected_queries = query_positions_tensor >= hi
            else:  # defensive against non-enum callers
                raise ValueError(f"unsupported access mode: {access_mode}")
            allowed &= ~(affected_queries.view(-1, 1) & selected_keys.view(1, -1))
    return allowed.view(1, 1, len(query_positions), key_length).expand(batch_size, -1, -1, -1).clone()


def allowed_to_additive(allowed: torch.Tensor, dtype: torch.dtype) -> torch.Tensor:
    if allowed.dtype is not torch.bool or allowed.ndim != 4:
        raise ValueError("allowed must be a rank-4 boolean tensor")
    if not torch.empty((), dtype=dtype).is_floating_point():
        raise ValueError("attention-mask dtype must be floating point")
    result = torch.zeros(allowed.shape, dtype=dtype, device=allowed.device)
    return result.masked_fill(~allowed, torch.finfo(dtype).min)


def build_additive_attention(**kwargs: object) -> torch.Tensor:
    dtype = kwargs.pop("dtype")
    if not isinstance(dtype, torch.dtype):
        raise TypeError("dtype must be a torch.dtype")
    return allowed_to_additive(build_allowed_attention(**kwargs), dtype)
