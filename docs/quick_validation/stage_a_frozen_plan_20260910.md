# Stage A: fixed independent-solve reproducibility check

User authorized five additional paired seed groups, giving six total per problem and condition when combined with the initial independent-solve run. Fixed problems/drafts: 1189/3,1358/0,804/1. Conditions R0,R2,R3,R4; 60 additional outputs,72 total. Three independent questions, not18. Old critique-prompt data are excluded from this aggregation.

Initial seed base2027; additional bases12027,22027,32027,42027,52027, with original pool indices23,24,28 added per problem. Shared seed across all four conditions within each problem/group. No outcome-dependent stopping, seed replacement, prompt/scorer/mask changes, or expansion to eight groups. Stop at six total groups and analyze. Unexpected execution failure stops the batch; no silent fallback.

Freeze exact prompt templates/config and draft texts from outputs/game24-independent-control-20260910. Preflight checks compare current renderer and source drafts to that run. Same HF BF16 eager implementation; Thinking .6/.95/top_k20/context32768; official scoring including failures; original full-draft access masks and R3 first-token boundary. No generation code changes in this launch.

Report accuracy first, per-question and overall; then R0−R2,R3−R2,R4−R2,R4−R3 and paired transitions. Body-correct/format-only, truncation, and missing-draft wording remain secondary diagnostics. Estimate effects from per-question repeat means; resample question clusters for cross-question CIs, retaining within-question paired seeds. Only three clusters: intervals highly limited. Within-question repeatability and cross-question generality are separate questions.

Stage B gate: examine whether net recovery recurs beyond the initial draw and is not offset by correct→wrong transitions. A signal isolated to one problem is a case-specific signal, not broad support. No automatic Stage B or attribution launch: review the frozen endpoint first. If warranted, expand to10–15 questions selected by draft quality/mixed-success, never by intervention outcome.

Run outputs/game24-independent-stage-a-20260910; batch.log and seed-<base>.log track sequential groups. tmux qwen3-stage-a-gpu4. After success restore prior authorized HF residency without additional evaluations.
