"""Backend-independent representation of the exact selective attention edges."""
from .schema import AccessMode, SelectiveContextRequest

NEVER = 2**30
METADATA_KEY = 'selective_context_v1'


def request_metadata(request: SelectiveContextRequest):
    request.validate()
    return dict(mode=request.access_mode.value, prompt_length=len(request.input_ids),
                draft_span=list(request.draft_token_span),
                spans=[list(x) for x in request.mask_token_spans],
                units=[list(x) for x in request.path_block_units])


def key_block_onsets(metadata):
    """For each prompt key, the first query that cannot read it.

    Min over units preserves overlapping fixed-unit boundaries. Generated keys
    are never selected. This table is metadata only: no token/KV values change.
    """
    n=int(metadata['prompt_length']); mode=AccessMode(metadata['mode'])
    ds,de=metadata['draft_span']
    if not 0 <= ds <= de <= n: raise ValueError('Invalid draft span')
    result=[NEVER]*n
    if mode is AccessMode.FULL:return result
    spans=metadata['spans'] or [[ds,de]]
    units=(metadata['units'] or spans) if mode is AccessMode.PATH_BLOCK else spans
    for lo,hi in units:
        if not ds <= lo <= hi <= de:raise ValueError('Invalid selected unit')
        onset=n if mode is AccessMode.LATE_BLOCK else hi
        for k in range(lo,hi):result[k]=min(result[k],onset)
    return result
