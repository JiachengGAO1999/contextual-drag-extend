from __future__ import annotations

from typing import Optional, Sequence, Tuple

import torch

from .schema import AccessMode


def build_allowed_attention(
    *,
    batch_size: int,
    query_positions: Sequence[int],
    key_length: int,
    draft_token_span: Tuple[int, int],
    access_mode: AccessMode,
    prompt_length: int,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Return [batch, 1, query, key] causal access edges.

    `late_block` blocks draft keys only for generated queries (absolute position >=
    prompt_length). `path_block` additionally blocks those keys for every prompt
    query at or after the end of the draft.
    """
    if batch_size <= 0 or key_length <= 0:
        raise ValueError("batch_size and key_length must be positive")
    start, end = draft_token_span
    if not 0 <= start <= end <= prompt_length <= key_length:
        raise ValueError("invalid draft span, prompt length, or key length")
    query_positions_tensor = torch.as_tensor(query_positions, dtype=torch.long, device=device)
    if query_positions_tensor.ndim != 1 or query_positions_tensor.numel() == 0:
        raise ValueError("query_positions must be a non-empty one-dimensional sequence")
    if torch.any(query_positions_tensor < 0) or torch.any(query_positions_tensor >= key_length):
        raise ValueError("query position outside key range")

    key_positions = torch.arange(key_length, device=device)
    allowed = key_positions.view(1, -1) <= query_positions_tensor.view(-1, 1)
    if end > start and access_mode is not AccessMode.FULL:
        draft_keys = (key_positions >= start) & (key_positions < end)
        if access_mode is AccessMode.LATE_BLOCK:
            affected_queries = query_positions_tensor >= prompt_length
        elif access_mode is AccessMode.PATH_BLOCK:
            affected_queries = query_positions_tensor >= end
        else:  # defensive against non-enum callers
            raise ValueError(f"unsupported access mode: {access_mode}")
        allowed &= ~(affected_queries.view(-1, 1) & draft_keys.view(1, -1))
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
