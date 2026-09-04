# Selective-context module

This directory is an additive implementation over pinned Contextual Drag upstream code. It provides same-text attention/KV-access interventions without modifying the official vLLM backend.

## Access semantics

- `full`: ordinary 2D HF causal attention for prefill and cached decoding.
- `late_block`: ordinary prefill; generated queries cannot attend draft KV positions. KV tensors remain allocated.
- `path_block`: prompt queries at/after the draft end and all generated queries cannot attend draft positions. This prevents post-draft prompt states from acting as an accessible propagation path.

Masks preserve sequence length, token IDs, absolute positions, wrapper text, and the error signal. A request bundle persists the exact IDs and hashes; R2–R4 are loaded from the same bundle.

## Local acceptance

```bash
pytest -q tests/selective_context
python -m selective_context.phase0.synthetic_smoke
python -m selective_context.phase0.evaluator_roundtrip
```

All local model checks instantiate a random tiny Qwen2 architecture. No checkpoint is fetched.

## Server-only preparation (after Stage 2 approval)

`python -m selective_context.phase0.prepare_requests` accepts only an existing local tokenizer directory (`local_files_only=True`). It emits per-example R0, R1, and shared R2–R4 request bundles. The real parseability audit is run with `python -m selective_context.parseability`; it emits JSON coverage statistics and a CSV manual-review sheet.

See `MASTER_EXPERIMENT_LOG.md` for the authoritative stage gate and `docs/phase0_portability.md` for upstream provenance.
