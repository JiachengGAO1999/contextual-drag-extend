"""Guard physical padding before *any* paged metadata lookup."""
def make_safe_selective_mask(meta, base, table, torch):
    docs = meta.doc_ids
    width = table.shape[1]
    def mask(b, h, q, k):
        in_range = (q >= 0) & (q < docs.shape[0]) & (k >= 0) & (k < meta.total_cache_tokens)
        safe_q = torch.clamp(q, min=0, max=docs.shape[0]-1)
        safe_k = torch.clamp(k, min=0, max=meta.total_cache_tokens-1)
        valid, lq, lk = meta._convert_physical_to_logical(docs, safe_q, safe_k)
        onset = table[docs[safe_q], torch.clamp(lk, min=0, max=width-1)]
        return in_range & base(b, h, safe_q, safe_k) & valid & ((lk >= width) | (lq < onset))
    return mask
