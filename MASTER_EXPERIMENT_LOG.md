# Selective Context Reset — Master Experiment Log

## 2026-09-17 — HF replication complete; selective vLLM engineering validation

Scope update from user: deliver a usable first version and return to the research, rather than spending more time/quota on performance perfection. Current decode-kernel retry is the final planned engineering validation; no further performance sweeps. GPU toy dense-reference/mutation checks passed before launch. Earlier per-request complete-output run was intentionally stopped for this retry and is incomplete, not a pass. Current log: vllm_decode_validation_20260917.log, tmux qwen3-vllm-decode.

Both authorized HF batches finished (48 late + 48 path). Fresh-seed X/X+CALC correct counts: late 15/24 versus 12/24; path 16/24 versus 16/24. Summary: outputs/game24-xcalc-timing-comparison-20260916/summary.json. No further scientific generation launched.

Independent vLLM 0.11.0 environment uses the read-only Qwen3-8B weights on GPU4. Custom FlexAttention worker implements unchanged logical full/late/path edges. Initial packed implementation passed 26 tests, 2112 synthetic paged-edge comparisons, real three-case mutation checks and short greedy generation. HF/vLLM are not numerically identical; future scientific comparisons must use one backend throughout.

Optimized per-request decode validation failed at Torch Dynamo's default eight-variant limit; raised explicitly to 64 on September 17 and restarted at 12:37 CST. Explicit tokenizer-EOS-only stopping now prevents vLLM from adding model-config stop IDs. This retry must pass before declaring the optimized backend usable. Logs: vllm_optimized_validation_20260917.log; prior failure retained as .failed1.log. Full engineering record: docs/quick_validation/vllm_backend_20260917.md.

## 2026-09-16 — Paired path supplement authorized and queued

User explicitly adds48 path generations beyond ongoing48 late. Same six questions,
new seed bases42027/52027/62027/72027; P_X_fixed/P_XCALC_fixed preserve independent
X and CALC unit onsets and exact late key unions. 48 preflight checks and13 tests pass.
Real12mask prefill/decode/mutation checks run after late finishes, before path generation.
tmux qwen3-xcalc-path-queue; queue waits for late exit0 and own resident, no interruption.
log xcalc_path_replication_20260916.log; output game24-qwen3-x-vs-xcalc-path-fresh-seeds-20260916.
Expected additional2–3h. Automatic96record fresh-seed four-cell summary then resident restore.
Plan docs/quick_validation/x_calc_path_plan_20260916.md. No extra generation beyond these48.

## 2026-09-16 19:29 CST — Fixed X vs XC fresh-seed replication launched

User approved one round capped48 new generations. Six unchanged dev questions,
seed bases42027/52027/62027/72027, two frozen conditions M_X/L_XCALC_v1.
All48 request preflights pass; same model/prompt/masks/scorer/sampling, only seeds
shifted+40000. Commit matches local/server7fc7245527ff81ffc2a5ee3f88db26d6e52d1540.
Own GPU4 resident2396008 terminated for run; wrapper restores afterward.
tmux qwen3-xcalc-replication; log xcalc_replication_20260916.log;
output outputs/game24-qwen3-x-vs-xcalc-fresh-seeds-20260916. ETA2–3h.
Pre-generation plan docs/quick_validation/x_calc_replication_plan_20260916.md.
No automatic expansion beyond48. Primary fresh-seed XC-X accuracy and transitions;
old/new reported separately, no semantic protective-role claim.
96-output conservative candidate audit finds valid arithmetic expressions followed
by final failure in R2/X/CALC/XC:8/3/8/4 records. Existence evidence spans6 questions;
not complete stance labeling or causal mediation. See candidate_presence_audit_20260916.md.

## 2026-09-16 — X+CALC completed and audited

Server X_CALC_FINISHED; 24/24 new generations, 3496.9s generation time.
Same-six R2/X/CALC/XC=10/18/8/14 of24. X->XC -16.7pp,3 recoveries/7 harms,
question-cluster CI[-41.7,8.3]pp. Additive accuracy interaction -8.3pp,
CI[-41.7,33.3]. All24 EOS;23 scoreable, one unparsed final actually repeats invalid
original formula. Seven extracted original candidates, two new invalid candidates,
plus that unparsed original. 24 exact input/seed/union/first-token checks and6x36layer
attention checks passed. Data synced; report docs/quick_validation/x_calc_results_20260916.md;
four-cell review outputs/game24-x-calc-late-20260916/review.html. No new run launched.

This is the live command file for the Contextual Drag reproduction and extension. Update it whenever a gate, interface, environment, commit, or experiment state changes.

## 2026-09-16 — Local-calculation results audited; no net recovery

24/24 done exit0 at12:58:29CST, elapsed56m41s; log resident2396008 restored.
Same six questions: R0/R2/E/X/CALC/R3/R4 correct18/10/6/18/8/18/20 of24.
R2->CALC−8.33pp,6recoveries/8harms, question-cluster95%CI[−37.5,+16.67]pp.
CALCparse/EOS24/24;24 paired input/seed/first-token/bundle and96 reference-source
checks passed;6x36layer attention probes verified.16 failures:15 extracted original
target expressions; remaining123/base32027 boxed24 with original invalid expression
in final body. Representative outputs regenerate blocked calculations and may find
valid answers without rejecting invalid draft. Not a general protective/harmful label.
Full results synced. Report docs/quick_validation/calculation_role_results_20260916.md/.json;
review outputs/game24-qwen3-local-calculation-late-20260916/review.html.
No new generation. Possible next fork: frozen X+CALC union to complete factorial,
or independent-question validation; neither automatically launched.

## 2026-09-16 12:01:48 CST — Role-consistent local-calculation experiment launched

User authorized proceeding through server generation. Morphology v2 requires EOS,
separates requirements/negated-validity from positive cues;19 sampled questions now
12complete/7incomplete. Manual draft-key audit distinguishes formatting failure23
and nonidentical577/1084/1358 variants. Old v1 and masks/results preserved.
Prior MASK_C12 requests/output token sequences exactly repeat oldM_X; no rerun.

New L_CALC_v1: all six fixed-ten unrejected resource-error cases1189/123/577/719/
1084/1226;27 exact numeric evaluation units, full candidate formulas/E retained.
24new requests(4original seeds), historical exact-condition audit found0reuses.
R2/R0/R3/R4 reused.24 token/pair checks,19 existing tests,5 morphology tests pass.
Only mask regions change; official Thinking and late-prefill boundary preserved.
GPU4 own resident4135183 replaced; tmux qwen3-calculation-role; output
outputs/game24-qwen3-local-calculation-late-20260916; log calculation_role_20260916.log.
Wrapper restores resident, cap24no auto expansion. ETA1.5–3h. Real model probes
passed all6 masks/all layers; first1189/base2027 generation confirmed512tokens.
Plans morphology_revision_20260916.md and
calculation_role_plan_20260916.md; annotation calculation_role_annotations_v1_20260916.json.

## 2026-09-16 — Ten-question validity results audited; no net recovery

28new/12reused completed exit0 onSep15 11:19:54CST (1h23m48s), resident restored
PID4135183 per log. E17/40 vsR2 18/40:−2.5pp,7 improvements/8 harms,
question-cluster95%CI[−27.5,20]pp. Eparse/EOS40/40.40 paired request/first-token
checks,12 original-source reuses,7x36layer checks verified locally; data synced.
Output evidence distinguishes old-candidate reuse, new resource-invalid candidates,
correct answers without recognizing draft error, and knowingly invalid final answers.
No support for general recovery by blocking false endorsement language. Broader RQ
remains exploratory; propose offline whole-cohort behavior audit before another
mechanism fork, not automatic path/seed/mask expansion. No new run launched.
Report docs/quick_validation/ten_validity_results_20260916.md/.json;
full output review in outputs/game24-qwen3-ten-validity-late-20260915/review.html.

## 2026-09-15 — vLLM selective-inference extension direction recorded

To make later sample expansion feasible, user approved recording a vLLM execution path:
vLLM V1 offline engine plus paged KV/FlexAttention with per-request interval-mask
metadata. The first target is only the current `late_block` semantics; HF eager remains
the correctness oracle. Preserve full prompt tokens/positions, ordinary full prefill,
and block selected KV spans only for generated queries. Do not approximate with token
deletion, placeholders, KV zeroing, or logits processors. `path_block` is deferred.

Before scale-up, run a fixed 3–5 case HF/vLLM parity smoke, then benchmark concurrency,
decode throughput, memory and prefix-cache behavior. Keep R2 and L_E_v1 in one vLLM
engine for future paired runs; pin vLLM/PyTorch/CUDA and defer FP8 KV/speculative
decoding until parity passes. Full direction and gates: 
`docs/quick_validation/vllm_selective_inference_extension_20260915.md`.

## 2026-09-15 09:56:06 CST — Ten-question validity-language experiment launched

User approved broadening the RQ: candidate/construction versus validity evaluation;
explicit rejection is a subtype, not mandatory inclusion. All ten fixed dev drafts
retained. Unified E annotations/audit in ten_validity_annotations_v1_20260915.json
and ten_validity_audit_20260915.md; full plan ten_validity_plan_20260915.md.
Old 513 M_V included two endorsements of another candidate; do not describe those
as fixed-F1-specific. Old results untouched. New 1358/71/513 E coverage differs.

R2 vs L_E_v1 late_block; ten questions x4paired seeds=40 records.12 exact oldM_V
reuses(577/719/1226),28 new generations. No new path/X+E/negative-statement arms.
40 token/request checks passed,19 existing tests passed,7 real new mask probes
passed all-layer blocked0/retained-positive. Full formula tokens retained.
Original Thinking sampling/prompt/scorer preserved; first token checked againstR2.
Actual first new generation1189/base2027 started. GPU4 own resident3515726 replaced;
tmux qwen3-ten-validity, log ten_validity_20260915.log, output
outputs/game24-qwen3-ten-validity-late-20260915. Wrapper restores resident.
ETA2–4h (~11:56–13:56CST); no automatic extra conditions. Main accuracy/paired
transitions; question-cluster CI exploratory; no semantic-specificity claim.

## 2026-09-15 11:19:54 CST — Ten-question validity-language experiment completed

Remote exit0; `TEN_VALIDITY_FINISHED` recorded. All28 new L_E_v1 generations ended
with EOS and all40 paired records are parsable Thinking outputs. The synced output
directory is about12MB and contains4×7 new results plus4×3 exact reused M_V records.
Preliminary primary comparison over all40 pairs: R2=18/40 (45.0%), L_E_v1=17/40
(42.5%), difference−2.5pp; transitions wrong→correct7 and correct→wrong8.
New seven-question subset is13/28 vs13/28 (0.0pp,5/5 transitions); reused three-
question subset is5/12 vs4/12 (−8.3pp,2/3 transitions). Question-cluster 10k
bootstrap over all ten gives exploratory percentile interval about[−27.5,+20.0]pp.
No mechanism or semantic-specificity claim. Preliminary report:
`docs/quick_validation/ten_validity_results_20260915.md`.

## 2026-09-15 — Bounded draft screening completed; zero new eligible episodes

Run ended00:37:47 CST, exit0, elapsed2h23m48s,32/32 records.30 correct,
1 completed incorrect (1261/0),1 length/malformed_thinking/null (33/1).
1261/0 uses three2s in11*(6-2)/2+2 but never explicitly rejects the candidate;
fails new episode criterion despite mixed-success.33/1 excluded by completion rule.
No new eligible independent question, no additional sampling or paired run launched.
Full run synced locally. Log confirms resident restoredPID3515726.
Report: docs/quick_validation/reendorsement_screen_results_20260915.md.

## 2026-09-14 22:13:59 CST — Bounded re-endorsement draft sampling launched

User requested event annotations and more independent questions, then explicitly
chose 8 new questions x4 Thinking samples (cap32) before joint paired evaluation.
Two text annotations completed:1358 N1/E4;71 N8/E18. Candidate formulas intact;
71 inline incorrect labels retained, so N is standalone rejection only. Token/model
preflight remains pending for these NEW intervention units; no intervention run yet.
Artifacts: docs/quick_validation/reendorsement_events_v1_20260914.json;
outputs/reendorsement-events-20260914.html; full plan and caveats in
docs/quick_validation/reendorsement_preparation_20260914.md.

New unique pool indices72:80, ids826/1299/1062/796/1261/33/138/54, 32 samples max.
Verified model/data/env paths, official Thinking .6/.95/20/32768, existing source
HEAD7fc7245, no old problem-id/number-set overlap, 4 sampling/Thinking tests passed.
GPU4 own resident3215274 replaced; other processes untouched. tmux
qwen3-reendorsement, log reendorsement_drafts_20260914.log, outputs
game24-qwen3-reendorsement-drafts-20260914. Wrapper restores resident on completion
or generation failure. Historical mean32-sample time2.67h; budget3–5h. No automatic
extra sampling; semantic candidate audit required before joint paired run.

## Current research direction — revised with user approval on 2026-09-14

Follow-up decision on 2026-09-14: user approved same-candidate explicit rejection
followed by re-endorsement as the first research entry. Start with 1358's later F1
episode; use 71 as a complex mixed-stance case. Cross-candidate repair and 513's
multi-candidate trace are deferred. This resolves the inventory's pending episode
choice below. See docs/quick_validation/reendorsement_entry_20260914.md.
No new generation or changes to historical annotations/results in this update.

Current RQ: after a draft explicitly rejects a candidate, how do the candidate,
its rejection, and subsequent reintroduction/endorsement affect the next solve?
Preserve failure-vs-transmission distinction without assuming a linear error-descendant
chain. Explicit textual rejection is not proven internal recognition. Primary evidence
layer is fixed final-response draft (initial Thinking stripped), separately from later
generated Thinking/final outputs. Current index: docs/RESEARCH_STATUS.md;
approved direction: docs/quick_validation/rq_revision_20260914.md.

Historical scope/primary-candidate sections below describe prior experiments and do
not override this revision. No new generation authorized by the documentation update.

## 2026-09-14 — Existing-material inventory completed; episode choice pending

Reviewed all10 fixed drafts.1358/71/513 have explicit rejection plus subsequent
candidate return or endorsement;804 has incomplete-candidate repair without explicit
rejection of its final invalid construction; remaining6 no explicit rejection found
in these fixed drafts. Old component-primary set must not transfer to newRQ.
Saved51 selected literal event/expression records with exact character spans across
the three direct cases; these are examples, not exhaustive event labels or mask units.
Source annotations verified unchanged. Candidate recurrence, endorsement, rejection
and mixed local stance kept separate; no blanket belief-state interpretation.

Files docs/quick_validation/rejection_materials_20260914.md/.json and standalone
outputs/rejection-materials-20260914.html contain full drafts, evidence and decision.
Remaining choice: same-candidate rejection->reendorsement (recommended start1358
late episode,71 complexity case) versus rejected candidate->new repaired candidate
(1358early episode). Different candidate identities/metrics; no automatic matrix.
Old outputs/reports untouched; no model generation. Local organization only; no
retry of previously rejected remote report transfer.

## 2026-09-14 18:27 CST — Marginal probe completed and analyzed

16/16 done exit0, elapsed1h25m04s; all new outputsEOS/parseable; residentPID3215274.
719 correct/4 C1=2,C1+U=1,C2-U=3,C2=2: blockingU effect-25pp in both
backgrounds, each1 improvement/2 harms.1358 C1=1,C1+U=0,C2-U=0,C2=0:
blockingU -25pp (0/1) and0pp (0/0). No supportive positive marginal signal,
no mean direction reversal establishing interaction; small dev-set sample remains.
16 request checks,48 unchanged references,8 exact edge-difference pair checks,
four36-layer actual attention checks pass. No new generation launched.
Report docs/quick_validation/marginal_results_20260914.md/.json; full review
outputs/game24-qwen3-marginal-path-20260914/review.html.

## 2026-09-14 17:02 CST — Two-question marginal probe launched

User authorized GPU execution. Frozen1358/B3 and719/B5; C1_plus_U and C2_minus_U
x4 original paired seed groups,16 new generations. C1=P_X and C2=fixed_C2 plus
R0/R2/R3/R4 copied unchanged as references. Preflight16 requests verifies same
tokens/positions/seeds, frozen units, and exact equality of added-vs-removed edge
sets across the two backgrounds. Four real conditions x36 layers prefill/decode
checks passed; removedU has positive decode attention, addedU zero.

Started17:02:36 CST, tmux qwen3-marginal, workerPID3215277, GPU4; first generation
719/base2027/C1_plus_U confirmed. Output outputs/game24-qwen3-marginal-path-20260914;
log marginal_20260914.log. ETA1–2h (~18:00–19:00 CST), may increase with sharing.
Old residentPID2013819 exited normally. GPU4 also has VLLM::EngineCore PID3201925
(37598MiB) and preexisting small processPID2947822; free42398MiB before our launch.
Other processes untouched. Wrapper restores own resident after finish/failure.
Two automatic approval-review capacity failures resolved by same-action retries;
no bypass. No further seeds/units/C4 automatically scheduled.
Frozen plan docs/quick_validation/marginal_plan_20260914.md. Probe is exploratory,
not confirmatory interaction evidence or error-specificity claim.

## 2026-09-14 — User-approved textual dependency decisions frozen

Independent decision sidecar docs/quick_validation/dependency_decisions_20260914.md/.json
records source-exact unit references.1358/B1–B2 are correct/incomplete retained
ancestors, B3 invalid repair; keep C2 membership.577/719 are explicit resource-use
construction chains, not independent arithmetic mistakes.513 candidate evaluation
is reintroduced but its downstream dependency is ambiguous: exploratory for future
strict comparisons, never removed from historical five-question results.1226 not
readjudicated in these three decisions. No harmful/protective causal labels assigned.
Future candidates1358/B3 and719/B5 need comparability review; no new matrix frozen.
Old annotations and outputs unchanged. No generation, automatic seeds or C4 launched.

## 2026-09-14 — C2-minus-C1 incremental-unit audit; awaiting semantic review

User authorized non-generative audit until a substantive obstacle, then user review.
Audited all23 added units (8/5/3/4/3 across1226/719/577/513/1358), arithmetic,
resource-use constraints, roles, context and exact additional unique attention edges.
No zero-edge units;1226 repeats semantic calculations at distinct token locations.
Prefill added edges per attention matrix:20207/20726/18467/110690/40942.
Hypothetical decode budget uses fixed1024 queries, not outcome-dependent lengths.
No error-specific harm/protection labels inferred from observed generation outcomes.

Obstacle: no explicit corrective sentence inside current23-unit delta; such text is
adjacent and unselected in1358/513. Correct arithmetic can participate in invalid
resource reuse. Unit granularity varies. Cannot manufacture a uniform reconstruction
versus correction comparison from current delta. User-facing review material covers
1358 precursor vs invalid repair,513 failed-candidate evaluation vs explicit rejection,
577/719 combined resource errors. No masks changed and no generations launched.
Files: docs/quick_validation/incremental_unit_audit_20260914.md/.json;
outputs/incremental-unit-audit-20260914.html (standalone, contexts and review questions).

## 2026-09-14 — C2 diagnostic results reviewed

20/20 completed Sep13 23:33:33 CST, exit0, elapsed1h24m38s; resident restoredPID2013819.
Five-question correct/20: R2=8, C1(P_X)=12, C2=12, wholeR4=14.
C1->C2 zero net (3 improve/3 harm), question bootstrapCI[-20,25]pp.
R2->C2 +20pp (4/0), CI[5,35]; exploratory five dev questions, no structural control.
Per-question C1->C2:1226 3->2,719 2->2,577 2->4,513 4->4,1358 1->0.
AllC2 EOS,19/20 parseable.1226/base32027 null remains failure; displayed nested fraction
also repeats8 and10, not a hidden valid solution.20 frozen request checks and100
unchanged reference records verified;five36-layer decode checks pass.
Report docs/quick_validation/fixed_c2_results_20260914.md/.json; complete review
outputs/game24-qwen3-fixed-c2-path-20260913/review.html. No automatic C4/new seeds launched.

## 2026-09-13 22:08 CST — Fixed C2 coverage diagnostic launched

User explicitly chose to compare coverage expansion now and design structural
controls separately. Thus target-only diagnostic20 generations is authorized;
no error-specificity claim or mislabeled structural placebo. Five fixed questions
1226/719/577/513/1358 x4 original paired seeds, only fixed_C2 generated.
C1=P_X and R0/R2/R3/R4 copied into references, no regeneration/rescoring.
20 request/config/identity checks passed; prior58 regression tests passed; real
fixed-C2 prefill checks reused for identical requests and allfive cached decode
checks passed across36 layers before generation.

Started22:08:55 CST, tmux qwen3-fixed-c2, workerPID2013822, GPU4.
First generation confirmed1226/base2027/fixed_C2. Output
outputs/game24-qwen3-fixed-c2-path-20260913, log fixed_c2_20260913.log.
ETA1–2h (~23:10–Sep14 00:10 CST, long Thinking may exceed). Previous idle
residentPID1059123 exited normally. Wrapper restores resident after exit;
no additional C4/seeds or retry. Frozen plan fixed_c2_run_plan_20260913.md.

## 2026-09-13 — Fixed-unit coverage preflight completed; no generation launched

Authorized annotation/implementation/preflight completed for1226/719/577/513/1358.
New optional path_block_units preserves fixed onsets under key-union expansion;
legacy behavior and serialized requests preserved when omitted. Old annotations
unchanged. C1 uses exact old merged M_X units: full mask identity confirms P_X reuse.
Each C1->C2->C3->C4 edge set checked monotone; C3 collapses toC2 for all five under
the documented text-dependency definitions. C2 token counts153/155/113/215/197.
Local targeted29 tests passed; server suite58 passed. Real Qwen3-8B five C2 cases:
36-layer blocked attention0, final-prefill mutation delta0. GPU4 resident retained.

Structural control audit fails for all five under the reviewed candidate pool and
frozen matching tolerances (same units, <=25% length gap, <=15% draft-length end gap).
This is not a global impossibility claim. No automatic relaxation or control fallback.
User decision needed before a weaker target-only20-generation C2 diagnostic
(5questions x4 existing seeds, roughly1–2h) versus further control design.
No new sampled outputs produced. Details docs/quick_validation/fixed_coverage_preflight_20260913.md,
annotations fixed_coverage_annotations_v1_20260913.json, compiled audit companionJSON,
local standalone outputs/fixed-coverage-review-20260913.html.

## 2026-09-13 — Discussion brief prepared

User requested one independent document covering completed experiments and mechanism.
Saved docs/quick_validation/discussion_brief_20260913.md: experiment lineage,
data/config deviations, exact late/path boundaries, coverage/control limitations,
five-condition and local-mask results, transitions/CIs, output cases, evidence
boundaries and discussion questions. Current partial M_X has lower observed accuracy
than whole blocking on the fixed ten-question set; this does not establish that
all fine-grained masks are inferior. No new experiments launched.

## 2026-09-13 15:25 CST — Ten-question M_X late/path completed

All128 new generations finished exit0 (6h34m03s); GPU4 resident restored PID1059123.
Combined160 records synced locally;32 reused records verified unchanged.
Correct/40: R2=18, whole R3=29, whole R4=31, M_X=24, M_CX=18, P_X=25, P_CX=15.
R2->M_X +15pp (12 improve/6 harm); R2->P_X +17.5pp (13/6);
M_X->P_X +2.5pp (8/7). P_CX->P_X +25pp CI[12.5,37.5], but control harm
and unmatched position/fragmentation/timing prevent pure semantic attribution.
Additional six: R2=13/24, M_X=14/24, P_X=17/24; late advantage shrinks on expansion.
Partial strategies remain below whole blocking. P_X length/unparseable
1226/32027 and71/2027 counted as failures; other new conditions allEOS/parseable.
160 input/hash/seed/bundle checks,80 late first-token,40 real attention checks pass.
Report docs/quick_validation/ten_question_mx_late_path_results_20260913.md/.json;
outputs outputs/game24-qwen3-mx-late-path-20260913/review.html.
Exploratory continuation warranted; no general partial-over-whole or path-over-late
claim. No new experiment launched.

## 2026-09-13 08:51 CST — Ten-question M_X late/path launched

User authorized the next experiment. Frozen 10 questions ×4 original paired seeds
×4 conditions M_X/M_CX (late), P_X/P_CX (path). Target spans identical across
timings; path uses q>=each compiled interval end. Total160, reused32 old-four late
records, new128. Six additional M_X annotations match previously compiled coverage;
equal-token pre-error-prefix controls audited and frozen; old-four annotations and
controls unchanged. ID71 control includes correctly evaluated rejected trials;
token amount is matched, position/fragmentation/semantics are not.

All160 input/seed/coverage/reuse identity checks passed. Server regression51 passed.
Before generation all40 actual question-condition checks passed across36 layers:
target attention zero, retained draft attention positive; path mutation gives zero
final-prefill logit difference. Official scorer and Qwen3 Thinking .6/.95/top_k20/
context32768, HF eager BF16/float32 sampling unchanged. No scorer fallback.

tmux `qwen3-mx-late-path`, initial worker PID1059126, GPU4, server log
`/data2/gaojc/projects/contextual-drag-extend/mx_late_path_20260913.log`.
Output `outputs/game24-qwen3-mx-late-path-20260913`, manifest includes reuse sources.
First new generation confirmed: 1226/P_X/seed_base2027. ETA8–12h (roughly17:00–21:00
CST Sep13, not guaranteed); prior comparable mean217s implies7.72h before variation.
Previous idle resident PID554943 exited normally. Wrapper restores resident after
success or visible failure, logs exit status; no retries or subsequent experiment.
Plan: docs/quick_validation/ten_question_mx_late_path_plan_20260913.md.

## 2026-09-13 — Multi-region path boundary implementation verified

User authorized directly defining/implementing/checking multi-region path. For each
frozen compiled interval [a,b), all queries q>=b are blocked from its keys, including
later draft tokens, suffix and decode. Within-interval causal access remains;
single whole-draft interval preserves legacy R4. Late first-token boundary unchanged.
Schema, masks and HF prefill routing updated; old four annotations/controls untouched.
Local targeted tests 22 passed; full local collection lacks math_verify. Server full
suite 51 passed. Real Qwen3-8B BF16/eager on fixed M_X for 1226/719/577/1358:
36-layer blocked attention exactly zero; post-last-region and cached-decode logit
mutation deltas exactly zero; retained draft attention positive. Local/server HEAD
7fc7245527ff81ffc2a5ee3f88db26d6e52d1540 plus synced overlay. No paired experiment
launched; existing GPU4 resident preserved. See
docs/quick_validation/multi_path_boundary_20260913.md and accompanying sanity JSON.

## Frozen scope

- Replication preference updated by user: prioritize settings explicitly stated in the paper. Non-thinking R0–R4 is engineering smoke only. Scientific pilot must use Qwen3-8B Thinking, temperature=0.6, top_p=0.95, top_k=20, context size=32768. No scientific No-Go from the engineering smoke.
- Exact 653-question subset may be reused if cheaply recoverable from existing files; do not regenerate a three-anchor pool. Otherwise use a small multi-sample Qwen3-8B Thinking pool and prefer problems with both correct and failed responses, targeting about 100 pairs. Descendant attribution and selective reset remain out of scope.

- Paper line: `Contextual Drag -> Same-Text Access Intervention -> Drag Transmission Attribution -> Selective Context Reset`.
- Current execution boundary (updated by user on 2026-09-06): **real Qwen3-8B smoke, then R0–R4 quick pilot only**. Infrastructure expansion, first-error/descendant attribution, and selective reset are paused.
- Upstream baseline: Princeton PLI Contextual Drag commit `8614634d3625e7d965aa30df9f99a640f4533dac`.
- Upstream code is treated as read-only; additions live under `selective_context/` plus narrow wrappers/config/tests.
- The former Stage 1-only restriction is superseded by the 2026-09-06 quick-validation authorization. Server preflight, code synchronization, failed-draft preparation, and real R0–R4 runs are in scope. Stop and ask the user at material decisions; do not silently fall back.

## Status

2026-09-13 multi-late COMPLETE96/96,06:10:03 CST,elapsed6h34m37s; restored residentPID554943 GPU4. Synced local data and full review.html. X/V/XV correct10/4/8 out16; controlsCX/CV/CXV5/5/6. X vsCX +31.25pp6improvements/1harm CI[−6.25,50]; X vsR2 +31.25pp6/1; XV vsX −12.5pp0/2. X promising exploration candidate, not generalization/causal attribution proof.1226 X4/4;7192/4;5774/4;1358 0/4. One1226/base2027 M_CV length/unscorable retained; othersEOS/scorable.96 token/hash/seed/first-token checks and24region-condition×36layer probes pass. Report docs/quick_validation/multi_late_results_20260913.md/.json. No follow-up launched; discuss frozen-source timing comparison and independent validation with user.

2026-09-12 23:35:26 CST MULTI-LATE STARTED after user authorized autonomous annotation/code review/tests/launch. tmux qwen3-multi-late PID554945 GPU4. 96 outputs:4fixed diagnostic questions1226/719/577/1358 ×4 original paired seeds ×M_X/M_V/M_XV and respective equal-token controls. All10 drafts have explicit expression/certification evidence and compiled coverage; remaining6 not queued. New optional mask_token_spans preserves full draft bounds and legacy single span; multi_region compiler merges union without masking gaps; only late supported.45 tests pass;96 input/seed preflights pass;24region-condition×36layer real probes pass (masked zero, retained draft positive). First1226/M_X generating. Docs multi_late_plan_20260912.md, multi_region_annotations_20260912.json, multi_region_annotation_audit_20260912.md; mobile outputs/multi-region-review-20260912.html. Manual audit corrected71 false same-operands formula match and missing explicit annotations. Before generation controls changed to uniform pre-error prefix to avoid masking1358 valid critique; controls match budget not position/fragmentation/semantic value. Scope is listed full-expression copies and explicit false certification, not all intermediate reconstructions or descendants. Output outputs/game24-multi-late-20260912; log multi_late_20260912.log. Estimate6–9h; success restores residency. No automatic path or new-question expansion.

2026-09-12 region late COMPLETE64/64,21:48:20 CST (3h56m18s), allEOS/scorable; resident restoredPID159959. Raw results synced locally. Same4question accuracy R2/R3/R4=5/9/11 out16;L_A/L_E/L_CA/L_CE=4/2/2/7 out16. A vs CA +12.5pp(2/0),E vs CE −31.25pp(0/5); neither targeted mask improves net overR2.64 token/hash/seed/first-token checks and16region×36layer probes pass. Report docs/quick_validation/region_late_results_20260912.md/.json; full comparative review outputs/game24-region-late-20260912/review.html. Single-occurrence late masks leave repeated erroneous content and prefill pathways accessible; no first-error responsibility claim supported. Controls match size only, not position/semantics. Next design requires user discussion; no new run launched.

2026-09-12 17:52 CST REGION LATE STARTED with explicit user authorization for annotations/code/launch. tmux qwen3-region-late PID159961 GPU4; first1226/L_A/base2027 actively generating. 4questions1226/719/577/1358 ×4paired seeds ×L_A/L_E/L_CA/L_CE=64. Frozen region annotations outputs/game24-region-late-20260912-annotations.json and mobile HTML outputs/game24-region-late-annotations.html; design docs/quick_validation/region_late_plan_20260912.md. New region_late.py reuses existing single-span late backend (no core mask changes). All64 inputs/seeds exact priorR2,16regions within draft, matched control token counts;6 mask regression tests passed; real16region×36layer blocked-attention probes passed before generation. Actual first output token checked against priorR2 per generation. Error annotation uses first uncorrected constructive resource violation;1358 earlier explicitly rejected partial expression excluded. Controls are equal-token factual intro suffixes, not position/semantics matched; limitations documented. Output outputs/game24-region-late-20260912, live log region_late_20260912.log. Estimate4–6h with long-output uncertainty. Completed idle resident3725065 released before launch; success restores residency. No automatic path/descendants follow-up.

2026-09-12 R3/R4 output mechanism review completed at user's request: docs/quick_validation/r3_r4_mechanism_review_20260912.md and outputs/r3-r4-mechanism-review-20260912/evidence.html. All120 R2/R3/R4 answer indices checked; targeted Thinking excerpts read, not exhaustive full-trace annotation. Key observations:123/12059 R2 correct Thinking candidate then incorrect draft-like Final;1226/22093 R2 recognizes reuse then falls back to wrong draft;577/2065 R4 rejects valid multiply-by1 solution for new repeated6 expression also produced by same-seed R0;1084/12083 R0/R4 share invalid repeated7 expression. Source-access/reselection and intrinsic constraint failures remain distinct hypotheses. Proposed A/E masks plus matched controls, followed by timing comparison, are discussion only; no annotation frozen, mask implementation or new experiments launched. User will review original outputs before next decision.

2026-09-12 five-condition baseline statistics COMPLETE per user request. Report docs/quick_validation/five_condition_baseline_20260912.md, machine-readable .json, and _pairs.csv (240 explicit pair transitions). All200 unique records;40 R1/R2 prompt differences exactly oracle deletion and actual seeds matched. Combined10 accuracy R0/R1/R2/R3/R4=70/37.5/45/72.5/77.5%. R0→R1 −32.5pp CI[−52.5,−12.5],2 improvements/15 harms. R1→R2 +7.5pp CI[−15,32.5],11 improvements/8 harms: error-signal benefit is not stable. R2→R3 +27.5pp CI[12.5,42.5],14/3; R2→R4 +32.5pp CI[5,57.5],18/5. Whole-question bootstrap10k seed2027; new7/old3 separately reported. Existing raw scores unchanged; no new generation or fine-mask implementation. Next step is discussion with user, not automatic launch.

2026-09-12 R1 supplement COMPLETE, verified at16:35 CST: all40/40 persisted (10 per seed group). Finished11:49:52 CST after start10:15:18, elapsed1h34m34s. R1_SUPPLEMENT_FINISHED marker present; model residency restored GPU4 PID3725065 in tmux qwen3-r1-supplement. Raw output directory and run.log synced locally to outputs/game24-r1-supplement-20260912. Full paired analysis and review-package integration remain pending; no further experiment started.

2026-09-12 10:15 CST R1 supplement STARTED, user authorized: ten frozen questions × four existing paired seeds =40 new R1 outputs. tmux qwen3-r1-supplement, PID3725067, GPU4; first generation1189/base2027 confirmed. Output outputs/game24-r1-supplement-20260912/seed-*/results.jsonl; live server log r1_supplement_20260912.log. New entry selective_context/phase0/r1_supplement.py removes only the R2 oracle sentence, retaining draft delimiters and independent-solve suffix. All40 preflight jobs reconstructed exact existing R2 input tokens and reused persisted sample_seed; frozen Thinking .6/.95/top_k20/context32768, HF eager BF16/float32 sampling and original scorer. R0/R2/R3/R4 not rerun. Local/server Git HEAD match7fc7245527ff81ffc2a5ee3f88db26d6e52d1540; overlay SCP synced. Original idle resident2969438 exited cleanly before launch; successful completion restores model residency. No automatic expansion or fine-mask work. Estimated order2–4h from prior throughput, not a deadline guarantee.

2026-09-12 user-requested combined10 review package completed: docs/quick_validation/ten_question_summary_20260912.md and outputs/ten-question-review-20260912/index.html. 160 original-schema output records (10 questions × first four frozen seed groups × R0/R2/R3/R4), fixed drafts, per-question HTML with full generated Thinking/final text, scores.csv, source-file/line manifest. Old3 contributes only first4 groups, not all6; no outcome-based selection. Combined accuracy R0/R2/R3/R4=70/45/72.5/77.5%; R2→R3 14 improvements/3 harms, R2→R4 18/5. Explicit transition directions prevent confusion with effect subtraction notation. New7 remains primary expansion evidence; no new runs.

2026-09-12 Stage B COMPLETE: all 112 outputs (7 new questions × 4 paired seeds × R0/R2/R3/R4) finished 04:30:02 CST, elapsed 6h50m45s; synced locally. New7 accuracy: R0 22/28=78.6%, R2 14/28=50.0%, R3 22/28=78.6%, R4 22/28=78.6%. R3−R2 +28.6pp (10 improvements/2 harms), R4−R2 +28.6pp (13/5), R4−R3 0pp (6/6). Residual drag +28.6pp; both recovery ratios 1.0. Question-cluster bootstrap and per-question analysis in docs/quick_validation/stage_b_result_20260912.md and stage_b_report_20260912.json. Three length outputs on question71 retained as unsuccessful; two unscorable. All28 bundle checks and four run-level 36-layer attention probes passed. Go for continued recovery investigation, not evidence of general path>late superiority; no subsequent run or attribution implementation started. Resident model restored in qwen3-stage-b-paired on GPU4. Primary analysis is new7; combined10 first4seeds supplementary only (R0/R2/R3/R4=70/45/72.5/77.5%).

2026-09-11 ~21:35 CST supplement check:11completed/32cap after~2h, slowed by22's three32K length/malformed outputs. Seventh eligible question found and manually accepted BEFORE evaluation:1226/1 repeats6 in10+11+6/(8-6); correct companions1226/0,/2 use10*(11-8)-6. Earlier22/1107not eligible. Queue tmux qwen3-stage-b-paired waits for1226/3 persistence, freezes combined source/7draft manifest, stops only verified surplus sampler PID2782459, then launches4seed groups x7new questions x4conditions=112outputs. No need to finish unused8-question acquisition cap; preserve all records and do not claim full supplement completion. Frozen seeds/prompts/scorer/masks unchanged. Output outputs/game24-stage-b-paired-20260911. Candidate audit docs/quick_validation/stage_b_final_manifest_audit.md. Stage B evaluation already authorized; queued automatically to meet sleep-time goal; status must distinguish waiting from active generation. Successful completion returns residency.

2026-09-11 19:30 CST: user approved supplement8questions/32drafts and requested timing to select last question and START paired evaluation before bedtime (~22:30CST). Launched next shuffled indices[64,72), output outputs/game24-stage-b-supplement-20260911, tmux qwen3-stage-b-supplement; same acquisition config, no quality relaxation. Based on prior128drafts9h35m,32drafts point estimate2h24m, not a guarantee; candidate yield and long sequences uncertain. Full7new-question four-seed R0/R2/R3/R4 evaluation requires112generations, roughly8–12hours using recent Stage A/control rates, not achievable within3hours. No R1 reintroduced. Manual candidate audit remains required; scripts do not automatically promote candidates or launch unaudited paired runs. Complete sampling restores model residency. Deadline does not authorize changing eligibility or accepting format-only drafts.

Stage B first draft batch completed and manually audited:128records/32questions,109true15false4null,123EOS5length; generation sum9h35m27s. Seven mixed-success candidates reduce to SIX genuine reasoning-failure questions after excluding23/3 (correct body, boxed24 only). Accepted first drafts:123/1,577/0,71/0,719/2,513/0,1084/0; correct companions verified.1356 excluded for0correct companions despite4wrong. Raw artifacts synced locally; resident PID1919967,qwen3-stage-b-gpu4. Seven-new-question target not met; no Stage B paired evaluation or extra sampling launched. Recommend bounded next8questions/32drafts to fill one vacancy, pending user decision as predeclared insufficient-yield rule. Audit: docs/quick_validation/stage_b_draft_audit.md.

2026-09-11 Stage B authorized and prepared: target10total questions (old3+new7),4paired seeds each under frozen independent-solve R0/R2/R3/R4. New7reported separately for generalization; old3reuse first4groups without outcome selection. First draft acquisition batch: next shuffled pool indices[32,64),32questions x4samples=128cap; original upstream direct draft-generation prompt/paper Thinking settings, no paired evaluation before manual draft audit/frozen manifest. Target7eligible new reasoning-failure/mixed-success questions not guaranteed by batch cap. Output outputs/game24-stage-b-drafts-20260911; tmux qwen3-stage-b-gpu4. No infrastructure/fine-grained mask changes. Full selection, evaluation seeds, reporting and stop rules: docs/quick_validation/stage_b_plan_20260911.md. Paired evaluation after audit is within Stage B authorization; material changes or insufficient-yield choices require discussion.

2026-09-11 Stage A COMPLETE: all5new groups finished at00:50:11 CST,4h34m47s. Combined new-prompt6groups/3questions/72outputs: R0=10/18,R2=5/18,R3=10/18,R4=11/18. Per-question counts R0/R2/R3/R4:1189=5/2/4/5;1358=0/0/1/1;804=5/3/5/5 (each/6). Late gain+27.8pp (6improvements/1harm),path gain+33.3pp (7/1),path−late+5.6pp (2/1); residual27.8pp. AllEOS, oneR3 null parse (nested fraction also substantively invalid), score preserved.18input bundles/first-token checks and6first-pair36layer sanity reports consistent. Recovery repeats beyond initial seed; Stage A supports proceeding to Stage B proposal, not attribution. Extra path advantage weak. Full result/cluster CIs: docs/quick_validation/stage_a_result_20260911.md and stage_a_report_20260911.json. Raw batch synced locally. Residency restored PID1140091,qwen3-stage-a-gpu4. No automatic Stage B launch.

Stage A authorized: independent-solve fixed prompt,3questions,R0/R2/R3/R4,six total paired seed groups. Initial base2027 retained; add12027/22027/32027/42027/52027 =60 new outputs. New root outputs/game24-independent-stage-a-20260910; tmux qwen3-stage-a-gpu4. No prompt/mask/scorer or generation-code changes, no optional stopping/extension, no automatic Stage B. Accuracy remains primary. Old critique-prompt seeds excluded. Plan: docs/quick_validation/stage_a_frozen_plan_20260910.md. Preflight compares current prompt templates and fixed source drafts to saved initial-control config/pairs. On success return to model residency.

User clarification: the R4 missing-draft-first review was a one-time choice for the independent-prompt diagnostic, NOT a standing preference. Future reports should lead with accuracy as the primary metric, followed by paired effects and relevant behavioral/format/completion diagnostics. This supersedes the earlier sentence prescribing a future R4-first reporting order.

User review priority updated: inspect R4 missing/unreadable-draft behavior before accuracy. New independent-control R4 full generated text (Thinking + final) searched for draft/missing/incomplete/unavailable/not-provided/cannot-see and related wording; matched contexts inspected. No draft-unavailability complaint found in any of 3 outputs. 1189/1358 start directly solving and contain no draft mentions; generic 'missing something' concerns finding a solution, not absent context. 804 mentions the incorrect original draft only to note the instruction to solve independently, with no inability-to-read complaint. All three old initial critique-prompt R4 final answers described the draft as incomplete/missing reasoning. Thus observed complaint frequency falls 3/3 to0/3 for these two small batches; this is a behavioral manipulation check, not proof of elimination of internal confusion or recovery mechanism. Full new R4 texts exported locally to outputs/game24-independent-control-20260910/readable_r4/. Future reports prioritize this check, then body/format/completion diagnostics, then accuracy.

Independent-solve control completed: 12 outputs, 66m34s generation loop. R0/R2/R3/R4 correct counts1/0/1/2 out of3, all score parse/EOS rates100%. Cases1189=[F,F,F,T],1358=[F,F,F,F],804=[T,F,T,T]. Residual+33.3pp, late recovery+33.3pp, extra path+33.3pp, net path+66.7pp; each paired bootstrap95%CI[0,100]pp. Ratios1,2 (tiny denominator, not bounded recovery fractions). No boxed-scalar-only failures in this batch; actual valid final-solution recoveries in804 R3/R4 and1189 R4. Positive exploratory R4>R3>R2, not mechanism confirmation: only3problems/one seed, R0 itself unstable, framing and format changed together. Detailed audit: docs/quick_validation/independent_control_result_20260910.md. Raw files synced locally; GPU4 residency restored PID776658 in qwen3-control-gpu4. No follow-up job launched.

2026-09-10 new authorized diagnostic: independent-solve prompt control on the same three fixed drafts, R0/R2/R3/R4 x one seed each = 12 outputs. Paper sampling and HF intervention semantics unchanged; NEW prompt setting removes critique/verdict instructions and explicitly requests boxed expression. R2–R4 input identical, R0 shares task suffix. Seed base2027, matched to initial group; no seed selection by outcome. Results kept separate from original critique pilot. Output `outputs/game24-independent-control-20260910`, tmux `qwen3-control-gpu4`. Regression suite 40 passed (3.66s), including four-condition effect indexing. Exact prompt/decision plan: `docs/quick_validation/independent_control_plan_20260910.md`. Explicit formatting change means old-vs-new improvement cannot isolate task mismatch alone. Previous repeats' full body/format audit still pending; no claim it has been completed. Successful run restores model residency, no automatic expansion.

2026-09-10 repeats completion verified: all three seed groups finished normally, batch marker ALL_THREE_REPEATS_FINISHED; UTC 02:39:57–06:47:27 (CST 10:39:57–14:47:27), elapsed 4h07m30s. New 45 outputs synced locally under `outputs/game24-fixed-repeats-20260910`. Per-group R0–R4 correct counts: seed12027 [2,0,1,0,1], seed22027 [2,0,1,0,0], seed32027 [0,0,0,1,0]. Including original group, counts [7,0,3,1,2] out of 12 per condition (three problems x four seeds, not 12 independent problems). Aggregate official R0−R2 +33.3pp; R3−R2 −16.7pp; R4−R3 +8.3pp; R4−R2 −8.3pp. Three new R3 outputs are length-capped and unparsed; other outputs completed and parsed. New body/format audit still pending; do not attribute all failures to format or claim a final mechanism conclusion. After completion, HF residency restored in tmux `qwen3-repeat-gpu4`, PID 344433, RESIDENT_READY; no more evaluations running.

2026-09-10 authorized next step: fixed HF R0–R4 repeats on the same three drafts (1189/3, 1358/0, 804/1). Three additional seed bases 12027, 22027, 32027; actual paired seeds add original pool indices 23,24,28. Each base runs 3 problems x 5 conditions = 15 outputs, total 45 new outputs. Together with original seed base 2027, four samples per problem/condition; still only three independent problems. Original prompts, paper Thinking sampling, official scoring and intervention semantics unchanged. Only CLI seed-base control added; no resampling drafts. Output root `outputs/game24-fixed-repeats-20260910`, per-seed logs and batch.log. Sequential bounded runner stops on any error and never silently falls back. On successful completion returns to HF model residency under prior user authorization, without more evaluation. Final analysis must keep official outcomes and a separate manual body-correct/final-format-failure diagnostic; analyze per-problem repeated accuracies rather than treating 12 observations as 12 independent problems. No attribution or vLLM migration in this batch.

2026-09-10: User requested GPU4 model residency while considering next experiments. Started tmux session `qwen3-gpu4` using the existing HF environment and read-only Qwen3-8B checkpoint, BF16/eager, interactive Python with `model`, `tokenizer`, and `backend`. This is not a vLLM/HTTP server and runs no automatic inference or experiments. Only model-required memory is allocated; it does not reserve/exclude other users from remaining GPU capacity. Server launch files: `qwen3_resident.py`, `start_qwen3_resident.sh`. Release the resident process before launching another full experiment model to avoid duplicate memory use.

2026-09-09 completed fixed-draft result: 3 pairs / 15 outputs, normal target-finished marker, 52m23s generation loop. R0–R4 accuracy = 100%, 0%, 33.3%, 0%, 33.3%; all parse and EOS rates 100%. R0−R1 +100pp, R0−R2 +66.7pp, R3−R2 −33.3pp, R4−R3 +33.3pp, R4−R2 0pp; recovery ratios −0.5 and 0. Critical audit: 804 R3/R4 solve correctly in body but box only 24, causing official failures. Hence observed late loss is format-only, and net path zero combines 1189 recovery with 804 format loss. Official scores preserved. All three input bundles and R2/R3 first tokens consistent; first-pair 36-layer attention sanity passes. Full output/log snapshot synced locally. Decision: hold formal expansion/attribution; recommend bounded independent-seed repeats with separate body/format diagnostic, no new job launched. Detailed CIs, transitions, audit and limitations: `docs/quick_validation/fixed_r0_r4_analysis_20260909.md`.

Fixed-draft validation launched after user authorization: PID 2096869 on GPU 4, run `outputs/game24-qwen3-8b-thinking-fixed-r0-r4-20260908`. Frozen draft keys: 1189/3, 1358/0, 804/1, first manually accepted failure in sampling order for each problem. Manifest: `docs/quick_validation/fixed_drafts_20260908.json`. Three problems x five conditions x one generation = 15 outputs; stops at three complete pairs. No new draft generation or automatic repeats/expansion. Paper Thinking settings unchanged; evaluation seeds 2050, 2051, 2055 (2027 + original shuffled pool index), shared across R0–R4 within each problem. Source records reused read-only; missing/ineligible fixed records fail rather than trigger sampling. R2–R4 input bundle checks, real attention sanity and R2/R3 first-token assertion retained. Server regression checks: 38 passed in 21.42s. This is a small direction check; no statistical Go/No-Go from three pairs alone.

Latest verification: the 2026-09-08 draft-only batch completed normally; PID 1347442 exited. All 16 problems / 64 generations and log synced locally. Official correctness: 55 true, 6 false, 3 null; EOS 60/64; parsable thinking 61/64. Generation time sum 21934.38 s (6h05m34s). Manual review accepts five completed reasoning-failure drafts across three mixed-success problems: 1189/3, 1358/0, 1358/2, 1358/3, 804/1. All violate number-use constraints in the body; correct companions verified. Four length-capped outputs excluded. Three new independent problems meet the lower end of the target; five drafts are not five independent problems. No new paired evaluations or scientific Go/No-Go. Audit: `docs/quick_validation/new_drafts_manual_audit_20260908.md`. Original artifacts unchanged.

2026-09-08 latest: user approved preserving all three initial records and collecting new genuine reasoning failures. Draft-only batch launched as PID 1347442 on GPU 4, output `outputs/game24-qwen3-8b-thinking-drafts-20260908`. It samples shuffled pool indices 16–31 (next 16 problems), four seeds per problem, and stops without paired evaluation. Official failures require manual body-level reasoning review; format-only and final-transcription-only errors do not satisfy the new selection target of 3–5 genuine reasoning-failure problems with a correct companion sample. Original artifacts remain intact. No claim that the fixed batch will yield enough accepted cases.

| Stage | State | Evidence / next gate |
|---|---|---|
| Stage 1 — local build + test | COMPLETE | 29 tests plus both executable smokes passed on 2026-09-04; local commit recorded below. |
| Stage 2 — server preflight | PASSED | Authorized model/environment/synchronization verified; user approved ToT official Game24 data. |
| Stage 3 — real smoke / quick pilot | THINKING INITIAL 3 PAIRS COMPLETE | Finished 2026-09-07 02:36 CST after 16 candidates/64 drafts and 15 paired outputs. 14/15 EOS; one R4 context-limit finish. Acc R0=3/3, R1–R4=1/3 each. Not expanded to 100; too few pairs for scientific Go/No-Go. |
| Phase 2 — attribution / selective reset | PAUSED | Explicitly out of scope for this quick validation. |

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
| 2026-09-06 | sjtu-a100 GPU 4 | 3.11.16 | 2.8.0+cu128 | 4.55.4 | `/data2/gaojc/envs/contextual-drag-smoke`; real Qwen3ForCausalLM BF16 eager forward passed; official parser checks passed. |

## Provenance and deviations

- Official vLLM backend, prompts, aggregation, output conventions, Game24 evaluator, and TED expression parser remain in place.
- Missing/nonportable official entry points are addressed through wrappers; see `docs/phase0_portability.md`.
- The local mask backend uses logical KV access blocking. It retains cache tensors and blocks their attention edges; it does not physically compact positions or evict storage.
- Real Game24 trace audit is intentionally deferred until server-generated failed drafts exist. Local tests use synthetic fixtures only.

## Historical formal Go / No-Go (superseded for quick validation)

First require `R0 - R2 >= 5 pp`. Enter Phase 2 if either R3/R4 gains at least 5 pp over R2 with clustered-bootstrap 95% CI lower bound above zero, or recovers at least 20% of a residual gap below 25 pp with the same CI condition. Parseability and finish-rate degradation must each be no more than 5 pp. If both gains are below 3 pp with CIs including zero, stop; an intermediate case receives one `n=16` R2–R4 replication only.

## Quick-validation contract — 2026-09-06

- Prioritize effect direction over statistical significance. If R0−R2 < 5 pp, assess insufficient residual drag in this setup. If R3 and R4 are approximately R2, defer transmission-responsibility experiments. R3 > R2 supports continuing; R4 > R3 > R2 prioritizes formal-scale validation and subsequent attribution, but does not authorize implementing it now.
- Report Acc(R0–R4); R0−R1, R0−R2, R3−R2, R4−R3; recovery ratios (R3−R2)/(R0−R2) and (R4−R2)/(R0−R2); paired bootstrap CIs; wrong→correct and correct→wrong counts; parse and completion rates; intervention sanity checks and anomalies.
- Use `late_block` / `path_block` terminology: logical attention blocking, not physical KV removal.
- Preserve the current late-intervention boundary: R3's first output token is sampled from full-prefill logits; blocking applies to subsequent generated queries.
- Sampling must be identical across all conditions. Minimal top_p support has now been added and tested. The prepared smoke uses temperature=0.6, top_p=0.95, no top_k, max_new_tokens=4096, enable_thinking=False for draft generation and R0–R4; independent draft/evaluation seed streams. No benchmark sampling has yet executed.
- Smoke must verify same R2–R4 text, token IDs, positions and hashes, effective attention blocking, official parser compatibility and normal completion on the real model.

### Live server preflight — 2026-09-06 15:15 CST

- Read-only SSH to `sjtu-a100` succeeded; host `rtx-node131`.
- GPU 4: 80,001 MiB free, 0% utilization; another process still holds 1,144 MiB. This is a snapshot, not a reservation.
- Free space: root 90 GB (95% used), `/data` 38 GB and `/data2` 25 GB (both display 100% used). No new model copy is proposed.
- `/data2/huangrj/models/qwen3-8b` still contains all five weight shards plus index/config/tokenizer. Prior inventory established readability and completeness. Owner-use confirmation remains pending. User-owned `/data2/gaojc/models/Qwen3-8B` still has no weight shards.
- Default Python 3.8.10; no torch/transformers reported by its pip query. `/snap/bin/uv` exists (0.12.6). No runnable user environment was located in bounded searches of `/home/gaojc` and `/data2/gaojc`; discovered pyvenv.cfg files are recovery metadata only.
- No Game24 source was located in the bounded user-directory filename search; source/provenance needs resolving before sample generation.
- Proposed synchronization: a scoped source archive via SCP to a new `/data2/gaojc/projects/contextual-drag-extend` directory, with file hashes recorded; no origin or Git push needed. Not executed.
- Pending user decision: confirm shared Qwen3-8B path use and whether to create an isolated Python >=3.10 GPU environment under `/data2/gaojc` (using the available 25 GB), or provide an existing runnable environment.
- No packages installed, code synchronized, weights loaded, or GPU inference launched. No R0–R4 measurements exist yet.

### Authorized environment setup and model load — 2026-09-06

The user confirmed read-only use of `/data2/huangrj/models/qwen3-8b`, a new isolated environment under `/data2/gaojc`, and simplified SCP synchronization without extra file-level hashes. These decisions supersede the pending items in the earlier preflight snapshot.

- Environment: `/data2/gaojc/envs/contextual-drag-smoke`; uv-managed Python 3.11.16 under `/data2/gaojc/uv-python`; cache `/data2/gaojc/uv-cache`. Core pins follow upstream: torch 2.8.0, transformers 4.55.4, accelerate 1.10.1, math-verify 0.8.0, datasets 4.0.0. Minimal install specification: `requirements/quick-smoke.txt`; resolved freeze saved on server at `/data2/gaojc/tmp/contextual-drag-smoke-freeze.txt` and locally under `docs/quick_validation/`.
- Code: Git bundle plus overlay tarball transferred with SCP and unpacked into `/data2/gaojc/projects/contextual-drag-extend`. Local and remote HEAD match `7fc7245527ff81ffc2a5ee3f88db26d6e52d1540`; smoke additions are uncommitted working-tree overlays, not falsely represented as part of that commit. No file-level integrity audit or push performed.
- Model: all five shards loaded read-only into `Qwen3ForCausalLM` on physical GPU 4. BF16, eager attention, DynamicCache, finite real forward outputs; allocated memory 15.268 GiB. No model copy or weight download. Report: `docs/quick_validation/environment_check_20260906.json`.
- Validation: local 31 tests passed (23.34 s); server 31 tests passed (72.29 s); official Game24 evaluator roundtrip passed. Initial server evaluation import failed because the official package also imports datasets; installed the pinned dependency and reran successfully. No evaluator fallback was used for server acceptance.
- Disk snapshot after setup: `/data2` has 18 GB free. Environment and uv cache report 6.8 GB and 6.7 GB respectively; uv may share hardlinked package files, so these figures should not simply be added as unique disk usage.
- Only necessary smoke changes were added: top_p sampling, its two tests, minimal dependency file, and bounded `selective_context.phase0.real_smoke` runner. No fine-grained attribution or selective-reset implementation.
- Runner is prepared for 10 paired examples, up to 100 candidate problems, one independent sampled draft per unique problem. Select the first completed officially parseable incorrect drafts, without conditioning on R0–R4 outcomes. Raw drafts retained; terminal chat control tokens omitted when embedding draft text. Any insufficient yield or failed alignment/sanity check stops the run instead of changing settings automatically.
- The real-model load check is **not** the requested Game24 R0–R4 smoke. Real intervention sanity, R0–R4 generations, and their parse/completion rates remain pending. The load-check process exited and released its GPU allocation.
- **Awaiting user input:** no shipped/local Game24 source was found. Asked whether to use version-pinned Tree of Thoughts official `src/tot/data/24/24.csv` with fixed random order, or a user-provided dataset path. No data was downloaded or benchmark sample generated while this material choice is pending.

### Game24 smoke launch — 2026-09-06

- User approved the proposed ToT official CSV source. Revision: `8050e67d0e3a0fddc424d7fa5801538722a4c4cc`; URL: `https://raw.githubusercontent.com/princeton-nlp/tree-of-thought-llm/8050e67d0e3a0fddc424d7fa5801538722a4c4cc/src/tot/data/24/24.csv`. Downloaded locally and sent via SCP to `/data2/gaojc/data/game24-tot-8050e67/24.csv`. This is quick-validation data provenance, not a claim of identical original-paper splits.
- Fixed row shuffle seed 2027; one draft attempt per unique puzzle, draft seed 102027+candidate_index, evaluation seed 2027+candidate_index shared across R0–R4. Selection uses only completed, officially parseable incorrect draft outcomes, never evaluation outcomes.
- GPU 4 prelaunch snapshot: 80,001 MiB free, 0% utilization. Environment and model paths unchanged. CPU thread limits set to 4; no weights copied.
- Run: `/data2/gaojc/projects/contextual-drag-extend/outputs/game24-qwen3-8b-r0-r4-smoke-20260906`; sibling `.log` and `.pid` files. Launched detached via nohup, PID 3025541. Logs preserve each draft and each condition's correctness/parse/completion status; requests and raw token IDs are persisted.
- Target: 10 pairs, cap 100 candidate rows, max_new_tokens=4096, temperature=0.6, top_p=0.95, BF16 eager, non-thinking. First accepted example runs real per-layer attention blocking and path-invariance checks before R0–R4 generation. ETA awaits observed throughput.

### Smoke interruption: exact token alignment — 2026-09-06

- Process 3025541 exited on the first eligible failed draft; no process remains and no R0–R4 paired outcomes were generated. This is an engineering stop, not scientific Go/No-Go evidence.
- Candidate IDs 877, 171, 702 were correct (1,241 / 228 / 362 tokens); ID 19 was officially incorrect (867 tokens). All four ended with EOS and were officially parseable. Failed draft selection occurred independently of any R0–R4 outcomes.
- `encode_prompt` raised `ValueError: draft delimiter crosses a token boundary; exact masking is unsafe` while encoding R1, before attention sanity or R0–R4 evaluation.
- Read-only tokenizer audit identifies an ending token ID 1019, decoded `**\n`: it includes the draft's final Markdown `**` and the following wrapper newline. R1 draft character span [1368,3476), token 1155 offsets [3474,3477); R2 span [1420,3528), token 1176 offsets [3526,3529). Both start boundaries are exact. The only extra character in either case is a single newline, not substantive wrapper text.
- Proposed decision for the user: allow masking the complete overlapping token only when any extra boundary characters are whitespace, record both original character span and actual masked token span/extra characters, and continue rejecting any boundary overlap with substantive wrapper text. This preserves R2–R4 text, token IDs, positions and hashes, but slightly broadens the masked region to the boundary newline. No change to this contract has been made yet; no samples were silently skipped and no prompts modified.
- Evidence retained in the original run directory: `draft_candidates.jsonl`, `config.json`, `boundary_audit.json`, and sibling `.log`. Local copies under `docs/quick_validation/smoke_20260906/`.
- Added only the requested paired-results reporting utility (`selective_context.phase0.paired_report`) while the smoke was running. Its reversal-count/denominator test passed. There are no paired results to report yet.

### Paper-parity clarification requested by user — 2026-09-06

- Boundary failure originates in our added `selective_context/prompting.py:char_span_to_token_span`, not upstream generation or evaluation. Upstream full-context inference does not require a draft-specific exact token mask. Synthetic acceptance had not covered the real Qwen3 `**\n` merged-token case.
- Checked https://arxiv.org/html/2602.04288v1, Sections 3.1 and Appendix A. The paper reports a 653/1362 Game24 hard subset selected using top-three anchor models, requiring at least two correct and two incorrect anchor responses per retained problem, with 16 evaluation generations per question. Upstream Game24 script names Nemotron-32B, Qwen3-32B, Qwen3-8B as anchors.
- Downloaded ToT CSV has 1362 rows, matching the paper's reported original pool size, but no row-level identity or equality to the selected 653-question set has been established. Our drafts are newly generated by Qwen3-8B; they are not released paper drafts. Current one-draft-per-candidate selection does not reproduce the paper's anchor-pool filtering.
- Material configuration difference newly checked against Appendix A.2 Table 4: the paper uses Qwen3-8B **Thinking**, top_k=20, with a 32768-token budget; our prepared engineering smoke uses non-thinking, no top_k, max_new_tokens=4096. Temperature=0.6 and top_p=0.95 match. The prior statement that sampling matches the existing local config must not be interpreted as paper parity.
- Therefore this smoke is an engineering check, not faithful reproduction. No scientific No-Go should be inferred from a null result in this setup. User's question is not authorization to change token boundaries, data selection, or thinking configuration; run remains stopped pending the methodological decision.

## SJTU A100 resource audit — 2026-09-04 17:28 CST

This was a user-authorized, read-only capacity inspection. It did not pull code, install packages, download weights, delete files, or launch inference.

- Host: `rtx-node131`; 8 × NVIDIA A100 80GB PCIe; driver 570.133.07; reported CUDA compatibility 12.8.
- GPU snapshot: GPUs 0–3 and 5–7 had only 5.5–36GB free. GPU 4 had 80,001MiB free and 0% utilization, but a different user's long-lived process held 1,144MiB. User `gaojc` owned none of the listed GPU processes.
- Filesystems: `/` had 145GB free at 92% use; `/data` had 38GB free and `/data2` 25GB free, both reported 100% use. Do not place model/cache data on the root filesystem merely to bypass this gate.
- User footprint: `/home/gaojc` 750MB; `/data2/gaojc` 6.8GB; default HF/Transformers/XDG cache variables unset; `/home/gaojc/.cache` only 16KB.
- Candidate checkpoint `/data2/gaojc/models/Qwen3-8B` is incomplete: 16MB metadata/tokenizer only, 0 of 5 referenced weight shards present. The index declares 16,381,470,720 bytes of weights.
- A later targeted inventory found three complete readable Qwen3-8B candidates; see below. The local `gaojc` copy remains incomplete.
- Default `python3` is 3.8.10 and lacks PyTorch. Only recovery metadata was found for former environments (`cotx`: Python 3.10.19, torch 2.9.1, transformers 4.57.1; `vllm-budget`: Python 3.11.15, torch 2.11.0, transformers 4.57.6, vLLM 0.22.0); this is not evidence that a runnable environment currently exists.
- Capacity decision: GPU memory is sufficient for a single-GPU, batch-conservative Qwen3-8B pilot when GPU 4 is available. Direct read-only reuse of a confirmed shared checkpoint removes the need for another 16.4GB copy; the remaining launch blockers are owner/path confirmation, code synchronization, and a runnable environment.

### Readable shared-model inventory — 2026-09-04

Three complete, top-level-readable Qwen3-8B candidates were found. Each has all five indexed BF16 safetensor shards (16,381,470,720 bytes total). Their config, index, and tokenizer-config SHA-256 values are identical.

| Candidate | Directory size | Status |
|---|---:|---|
| `/data/maxb/Qwen3-8B` | 31GB (includes extra cache/material) | Complete and readable; owned by `maxb` |
| `/data2/huangrj/models/qwen3-8b` | 16GB | Complete and readable; owned by `huangrj` |
| `/data2/liuxy/models/Qwen3-8B` | 16GB | Complete and readable; owned by `liuxy` |
| `/data2/gaojc/models/Qwen3-8B` | 16MB | Incomplete: 0/5 shards; do not use |

Only `/data/sharing/Llama-3.1-8B-Instruct` is in an explicitly shared namespace among the inspected 7–9B instruction models. Other readable alternatives include Qwen2.5-7B-Instruct and DeepSeek-R1-Distill-Llama-8B under other project/user directories. Read permission does not establish owner permission or path stability; obtain owner confirmation before formal experiments. Preferred storage strategy: direct read-only loading from one confirmed Qwen3-8B path, with no copy and no additional HF cache.

## Change log

- 2026-09-08: Added minimal `--drafts-only` / `--start-index` mode to the existing Thinking runner; new batch uses indices [16,32), order seed 2027, generation seeds 102027+4*index+j, unchanged paper sampling and full context budget. Every raw output is saved in `draft_candidates.jsonl`; per-problem `review_candidates/*.json` holds candidate final text and companion correct keys with manual status pending. No R1–R4, intervention bundles, or paired metrics run in this mode. Server tests: 38 passed in 21.40 s; local/server HEAD both `7fc7245527ff81ffc2a5ee3f88db26d6e52d1540` with synchronized uncommitted runner overlay. GPU 4 prelaunch free 80001 MiB. PID 1347442 verified alive while loading checkpoint. Sibling `.log` / `.pid` record progress. Bounded batch completes automatically; expansion and paired assessment await candidate audit. Existing three-draft records preserved.

- 2026-09-08: User requested independent draft review and conditionally authorized 27 R2–R4 repeats if the three drafts were all accepted. Manual review of actual `traj1` plus exact arithmetic found: ID170 body correct (24), final boxed expression wrong (19); ID159 body and valid expression correct, boxed `24` fails required expression/number-use format only; ID1093 genuinely reuses 6 twice via `6/6`. Thus official `False` labels do not establish three failed reasoning chains. Conditional agreement not met; no repeats launched, no raw data/scores changed. Review at `docs/quick_validation/three_drafts_manual_audit_20260908.md`. Existing three-case aggregate is confounded by error type; await user choice before changing sample set.

- 2026-09-07: User requested a local copy for inspection. Synced the complete finished Thinking initial-run directory and sibling log from sjtu-a100 to local `outputs/game24-qwen3-8b-thinking-r0-r4-20260906/` and `.log`. Confirmed successful extraction, 64 raw draft records and 15 R0–R4 records, with pairs, bundles, config, launch records, sanity report and paired report included. This is a manual snapshot, not automatic continuous synchronization; outputs remain Git-ignored.

- 2026-09-07 09:32 CST: Read-only status check confirms PID 3333868 exited normally with `THINKING_PILOT_TARGET_FINISHED`. Finished 02:36 CST; measured loop time 20029.95 s (5 h 34 min; excludes model load). Evaluated 16 candidate problems × 4 Thinking drafts: 61 correct, 3 failed, all accepted-pool statuses completed and parsable. Mixed-success IDs 170,159,1093 selected; 15 R0–R4 outputs recorded. No subsequent run was launched.
- 2026-09-07: Thinking initial results: ID170 R0/R1/R2 correct, R3/R4 incorrect; ID159 R0/R3/R4 correct, R1/R2 incorrect; ID1093 only R0 correct. R0 accuracy 100%; R1,R2,R3,R4 each 33.3%; parse rates all 100%; EOS completion R0–R3 100%, R4 66.7%. ID1093 R4 reached 31863 generated tokens (32768 total-context limit) and was scored incorrect. R0−R1 and R0−R2 +66.7 pp; R3−R2 and R4−R3 0 pp. R2→R3 transitions: one wrong→correct, one correct→wrong; R3→R4 no correctness transitions. Both recovery ratios 0. First-prompt sanity: 36 layers, blocked attention and path-invariance differences exactly zero. These three pairs are insufficient for scientific Go/No-Go; do not interpret equal means as no intervention effect. Report saved to `docs/quick_validation/thinking_initial_report_20260907.json`. Main scaling bottleneck is mixed-success sample yield (3/16), plus long Thinking generations; review before expansion.

- 2026-09-06: Confirmed Thinking initial batch is actually running, PID 3333868. All five checkpoint shards loaded; first candidate ID 877 started with a 70-token Thinking prompt and 32698-token generation allowance. The persisted config confirms enable_thinking=True and paper sampling settings. Initial batch stops at 3 complete mixed-success pairs (or candidate cap); it does not automatically launch the full 100-case expansion before quality/runtime review. Latest-config copy: `docs/quick_validation/thinking_initial_config_20260906.json`.

- 2026-09-06: User authorized starting the real-setting quick experiment. Added only a bounded/resumable Thinking R0–R4 runner, upstream `parse_thinking_steps` draft extraction, total-context budgeting, and generation progress callbacks. Read upstream `Qwen3_8B_Thinking` config directly: temperature=0.6, top_p=0.95, top_k=20, context=32768, thinking=True. HF sampling processors use float32 logits on a BF16 model. Server regression suite: 38 passed (24.19 s).
- 2026-09-06: Thinking initial-batch plan: same version-pinned ToT pool, shuffle seed 2027; four independent Thinking drafts/problem; accept problems with both completed parsable correct and failed responses, choose first failed final response, and strip thinking using the upstream function. Evaluation uses independent seeds and one sample per R0–R4. Exact 653/three-anchor reconstruction is not undertaken. Upstream R0/R1/R2 prompt wrappers are reused; Game24 problem wording remains the explicit four-number instruction from the prepared source normalizer because a shipped Game24 dataset/prompt could not be located.
- 2026-09-06: New run directory `outputs/game24-qwen3-8b-thinking-r0-r4-20260906`, with sibling `.log`/`.pid`; no reuse of non-thinking drafts or measurements. Initial target 3 pairs, max 40 candidates. Every generation is persisted, every 512 tokens emits progress, and explicit resume can continue the same frozen experiment. Generation cap is 32768 minus full prompt length. No physical KV removal; R3 first-token boundary and formatting-only spillover policy unchanged. GPU 4 prelaunch: 80,001 MiB free; model still read-only `/data2/huangrj/models/qwen3-8b`. ETA will be measured from Thinking throughput and mixed-success yield before expanding.

- 2026-09-06: Non-thinking engineering smoke completed 10 pairs after 70 draft candidates; measured generation-loop duration 6675.78 s (111.3 min). All 10 R2–R4 bundles and R2/R3 first-token checks pass. Actual 36-layer blocked attention probabilities and path-block postdraft logit change under draft mutation are exactly zero. Seven pairs have zero spillover; three include only a trailing newline. All 50 conditions reached a recorded finish, but only 33 ended with EOS; the remaining 17 hit 4096 tokens, often repeating expressions. This is engineering execution success with an output-quality limitation, not scientific validation.
- 2026-09-06: Smoke Acc R0–R4 = 60%, 10%, 0%, 40%, 20%; parse rates = 100%, 80%, 80%, 60%, 50%; EOS completion = 80%, 80%, 60%, 60%, 50%. Unparseable outputs count as incorrect without changing the paired denominator. R0−R1 = +50 pp [20,80], R0−R2 = +60 pp [30,90], R3−R2 = +40 pp [10,70], R4−R3 = −20 pp [−50,0], R4−R2 = +20 pp [0,50], paired percentile bootstrap 10000 resamples. In reference→comparison direction, not-correct→correct / correct→not-correct counts are 5/0, 6/0, 4/0, 0/2, 2/0 respectively. Recovery ratios 2/3 and 1/3 are descriptive only; ratio CIs omitted because some bootstrap resamples have zero residual denominator. No scientific No-Go or transmission claim is made.
- 2026-09-06: User reiterated paper-config priority after asking why this run was non-thinking. Clarified that it followed the explicit engineering-smoke-first instruction; no further non-thinking runs will be launched. Next model runs must use the approved Thinking configuration, and the repetition/completion issue must be checked before scientific expansion. Complete reports: `docs/quick_validation/smoke_boundary_paired_report_20260906.json`, `smoke_boundary_audit_20260906.json`, and `smoke_boundary_results_20260906.tar.gz`. Server process ended; GPU 4 released.

- 2026-09-06: User approved minimal covering-token spans with formatting-only spillover, and separated non-thinking engineering smoke from Thinking scientific pilot. Implemented full-prompt tokenization followed by minimum contiguous overlapping span; recorded original/masked character spans and spillover in persisted bundles and per-example boundary audits. Non-formatting spillover is rejected rather than silently skipped. R2–R4 token sequences/positions remain identical; R3 first-token boundary unchanged. Local/server suites: 36 passed (10.27 s / 3.71 s). Restarted in `outputs/game24-qwen3-8b-r0-r4-smoke-boundary-20260906`, PID 3098781, preserving earlier failure artifacts.

- 2026-09-04: Stage 1 started. Pinned official baseline checked out. Confirmed no server access and no model download.
- 2026-09-04: Stage 1 acceptance passed. Official vLLM/prompt/evaluator/TED/aggregation baseline paths have zero diff. Local Python 3.9 cannot install upstream `math-verify==0.8.0` (requires Python >=3.10), so the local evaluator smoke uses a documented Game24-only fallback; official evaluator parity remains mandatory on the server stack.
- 2026-09-04: Stage 1 snapshot committed locally; use `git log -1` for its content-addressed ID. No `origin` configured and nothing pushed.
- 2026-09-04: User requested a read-only `sjtu-a100` capacity audit. Recorded a launch No-Go due to full data filesystems, an incomplete Qwen3-8B checkpoint, and no verified runnable environment; no server state was changed.
- 2026-09-04: Targeted shared-model audit found three complete readable Qwen3-8B copies and several 7–9B alternatives. No weights were copied; owner confirmation is required before formal reuse.
