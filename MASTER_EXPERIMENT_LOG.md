# Selective Context Reset — Master Experiment Log

This is the live command file for the Contextual Drag reproduction and extension. Update it whenever a gate, interface, environment, commit, or experiment state changes.

## Frozen scope

- Paper line: `Contextual Drag -> Same-Text Access Intervention -> Drag Transmission Attribution -> Selective Context Reset`.
- Current execution boundary: **Stage 1 local engineering only**.
- Upstream baseline: Princeton PLI Contextual Drag commit `8614634d3625e7d965aa30df9f99a640f4533dac`.
- Upstream code is treated as read-only; additions live under `selective_context/` plus narrow wrappers/config/tests.
- No SJTU SSH, model-weight download, formal reproduction, anchor-pool generation, or real R0–R4 run in Stage 1.

## Status

| Stage | State | Evidence / next gate |
|---|---|---|
| Stage 1 — local build + test | COMPLETE | 29 tests plus both executable smokes passed on 2026-09-04; local commit recorded below. |
| Stage 2 — server preflight | BLOCKED BY POLICY GATE | Requires an `origin`, push, and server-side pull before any SSH audit. |
| Stage 3 — A100 pilot | NOT STARTED | Requires Stage 2 space/environment approval. |
| Phase 2 — attribution | NOT STARTED | Requires R0–R4 Go decision. |

## Frozen R0–R4 contract

| ID | Prompt | Access mode |
|---|---|---|
| R0 | Direct | `full` |
| R1 | 1F, no oracle error signal | `full` |
| R2 | 1F + oracle error signal | `full` |
| R3 | Exact persisted R2 token IDs | `late_block` |
| R4 | Exact persisted R2 token IDs | `path_block` |

Every request records `condition_id`, `input_ids`, `prompt_sha256`, `input_ids_sha256`, `draft_token_span`, `access_mode`, and `sample_seed`. R2–R4 must have identical text, token IDs, length, positions, and hashes.

Operational contrasts only:

- `R3 - R2`: direct-access recovery.
- `R4 - R3`: additional recovery under propagation-safe blocking.
- Do not call these a mediation decomposition; Whole Draft Blocked is not Direct.

## Stage 1 checklist

- [x] Initialize git at the pinned upstream commit and configure read-only `upstream` provenance.
- [x] Add lightweight local/server dependency layers without changing official `requirements.txt`.
- [x] Freeze prompt/span/request/output contracts.
- [x] Implement full, late-block, and path-block HF inference paths.
- [x] Implement token/span alignment and persistent prompt artifacts.
- [x] Add evaluator-compatible JSONL output and portability wrappers.
- [x] Add Game24 parseability audit and synthetic fixtures.
- [x] Pass `pytest -q tests/selective_context` — 29 passed in 8.49 s.
- [x] Pass `python -m selective_context.phase0.synthetic_smoke` — deterministic tokens, DynamicCache metadata, resume check.
- [x] Pass `python -m selective_context.phase0.evaluator_roundtrip` — boxed Game24 answer parsed correct.
- [x] Audit git status, large files, caches, outputs, and likely secrets — only ignored bytecode/pytest cache found; no new file above 10 MB; no credential-pattern hit.
- [x] Create local Stage 1 commit. Do not push without `origin` supplied by the user.

## Environment ledger

| Date | Location | Python | Torch | Transformers | Notes |
|---|---|---:|---:|---:|---|
| 2026-09-04 | local Windows CPU | 3.9.1 | 2.6.0+cpu | 4.49.0 | No pytest initially; no checkpoint downloaded. Tiny random Qwen2 is the local Qwen-compatible test model. |

## Provenance and deviations

- Official vLLM backend, prompts, aggregation, output conventions, Game24 evaluator, and TED expression parser remain in place.
- Missing/nonportable official entry points are addressed through wrappers; see `docs/phase0_portability.md`.
- The local mask backend uses logical KV access blocking. It retains cache tensors and blocks their attention edges; it does not physically compact positions or evict storage.
- Real Game24 trace audit is intentionally deferred until server-generated failed drafts exist. Local tests use synthetic fixtures only.

## Go / No-Go (not evaluated in Stage 1)

First require `R0 - R2 >= 5 pp`. Enter Phase 2 if either R3/R4 gains at least 5 pp over R2 with clustered-bootstrap 95% CI lower bound above zero, or recovers at least 20% of a residual gap below 25 pp with the same CI condition. Parseability and finish-rate degradation must each be no more than 5 pp. If both gains are below 3 pp with CIs including zero, stop; an intermediate case receives one `n=16` R2–R4 replication only.

## Change log

- 2026-09-04: Stage 1 started. Pinned official baseline checked out. Confirmed no server access and no model download.
- 2026-09-04: Stage 1 acceptance passed. Official vLLM/prompt/evaluator/TED/aggregation baseline paths have zero diff. Local Python 3.9 cannot install upstream `math-verify==0.8.0` (requires Python >=3.10), so the local evaluator smoke uses a documented Game24-only fallback; official evaluator parity remains mandatory on the server stack.
- 2026-09-04: Stage 1 snapshot committed locally; use `git log -1` for its content-addressed ID. No `origin` configured and nothing pushed.
