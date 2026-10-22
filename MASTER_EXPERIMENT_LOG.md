# Selective Context Reset — Master Experiment Log

## 2026-10-22 — Full102 replication complete; heldout82 confirms both primary directions

Completed492/492 at2026-10-22 06:37:14Asia/Shanghai in63.35hours including startup attempts; pooled612/612 across102questions. Heldout82:R0 104/164,R2 55/164,R3 95/164. Drag+29.88pp[18.90,40.85];recovery+24.39pp[13.41,35.37]. R2→R3:62paired recoveries,22damages. Pooled102:R0 131/204,R2 68/204,R3 119/204;recovery+25.00pp[14.71,35.29]. Heldout19length-limited/10scorer-null;pooled20/11,overlapping categories retained in denominators.599completed files and423frozen bindings verified;CPU analysis exactly matches server;164heldout/204pooled paired invariants pass;254new official-True formulas exact-arithmetic verified without relabeling. Launcher exit0,no automatic extension. [Full report](docs/game24_100q_8b/FULL_REPLICATION_RESULTS_20261022.md).

## 2026-10-19 — Entire102 pool authorized; frozen82 confirmation submitted

User explicitly requests the full expanded pool. Preserve completed20/120 and freeze remaining82 ×2seeds ×R0/R2/R3 =492new requests,612total. Draft policy/seeds/sampling/masks unchanged, original20 selections replay exactly. Isolated A800GPU4 deployment uses existing A100 vLLM0.11/Transformers4.55.4/xgrammar0.1.25 packages;3707hashes verified,120development prompt tokenizations agree,30CPU checks pass. Report heldout82 as confirmation and pooled102 separately, with A100/A800 strata. Runtime physical directory moved to owned system disk after4195file checks; model weights are links, no unrelated jobs changed. Initial IPC-path/spawn-import failures occurred before any scientific output and17.70s is retained. At2026-10-19 15:18Asia/Shanghai all16fixed old first4-token probes matched A100 outputs and4callback/pair probes passed; scientific first batch is running0/492,tmux game24-8b-heldout82-1019. Estimate63.13additional GPUh,96h cumulative guard. [Protocol and live-state command](docs/game24_100q_8b/FULL_REPLICATION_PLAN_20261019.md).

## 2026-10-19 — Development replication verified complete, no expansion

Completed120/120 on2026-10-18 02:16:49Asia/Shanghai,15.40hours. Frozen20questions/two seeds: R0 27/40,R2 13/40,R3 24/40. R0-R2 +35.0pp[17.5,52.5];R3-R2 +27.5pp[10.0,47.5],5000question bootstrap draws. R2→R3:15recoveries/4damages; oneR3 length-limited/scorer-null result retained in denominator. Held-out82 unused; no expansion launched. Synced117files/11,714,369bytes,all SHA256 matched; CPU analysis exactly matches saved JSON;40paired input/first-token checks passed; all64official-True final formulas exact-arithmetic verified. Runner exited0; prior idle resident restoration not confirmed, and GPU4 now serves other tasks untouched. [Full report](docs/game24_100q_8b/REPLICATION_RESULTS_20261019.md).

## 2026-10-17 — Fresh-pool Qwen3-8B development replication

User requests rerunning the old method and preparing extensions after the 102-question data freeze. Frozen development20 × seeds927001/927002 × R0/R2/R3 =120 scientific requests, plus4 engineering requests of at most4 tokens. Held-out82 remains unused. A100 GPU4 uses the actual paper snapshot with146 verified file hashes and64 old prompt-tokenization parity checks; the idle older root-checkout resident is released and restored afterward. No new weights/environment, no automatic extra conditions or held-out requests. Runtime and result status: `outputs/game24-replication-qwen3-8b-development-20261017/status.json`; tmux `game24-8b-dev-replication-1017`. Protocol and extension boundaries: [replication plan](docs/game24_100q_8b/REPLICATION_PLAN_20261017.md). No completed new effect estimate yet.

## 2026-09-20 — Same-question scope reaffirmed; public MATH final-answer audit

User confirmed existing same-question route. Parallel32B resumes frozen acquisition; no new intervention launched. Manual review of20 public R1 MATH outputs flagged by scorer finds10 substantive final errors,9 correct-answer extraction artifacts (6 nested boxes,3 multiple boxes),1 missing final. Of10 errors,7 depend on diagram relationships,1 has missing diagram,2 have sufficient text (source indices154,444). Full trace/token-budget review pending, not generation-ready. Report `docs/quick_validation/math500_public_review_20260920.md`. Original scorer results preserved; no silent scorer change.

## 2026-09-20 — UFT external20 completed, no positive residual drag

160 requests returned;157EOS/3length,7.68h. R0/R2/R3/R4 correct36/39/34/40. Question-cluster CI and paired transitions saved in outputs/game24-uft-external-20q-20260919/analysis.json. R3-R2=-12.5pp,0 recoveries/5 harms (3 length loops); R4-R2=+2.5pp,1 recovery/0 harms. No positive residual denominator; recovery ratios not interpreted. All40 same-text triples verified. No new jobs launched. See docs/quick_validation/uft_external_results_20260920.md.

## 2026-09-19 — User authorizes UFT external20 whole-trace validation

User requested draft recheck and actual generation. Frozen20 fresh UFT Qwen2.5-Math-7B CoT questions with one manually reviewed failed final expression each; no intervention-outcome or R0 selection. Source EOS unavailable and explicitly disclosed. Track B only; dual-anchor protocol unchanged. Seeds929001/929002 × R0/R2/R3/R4,160 requests, same server vLLM/Thinking sampling and prompt as seven-question pilot. Uploaded only new experiment files; original32B stays STOP at288/512. Tmux uft-external20-20260919 created20:35 CST; Real-tokenizer same-text and key-onset metadata checks160/160 passed. Model initialized and status running confirmed20:38 CST. Detailed frozen protocol: `docs/quick_validation/uft_external_plan_20260919.md`. Finish retains same engine resident; no automatic expansion.

## 2026-09-19 — Public alternatives follow-up, zero generation

Per user request, inspected additional public sources. Official ToT direct GPT-4 Game24 CoT log contains10,000 outputs/100 questions,9,597 source failures; safe final-expression checks confirm6,782 errors. After historical/reserved exclusions91 fresh questions have6,222 such rows; completion/manual review pending. Qwen3-4B MATH-traces downloaded:10,000 rows/500 questions,1,046 source False across87 questions; first False is a currency-format false negative, so labels cannot be reused as-is. Exact whitespace-normalized overlap with downloaded rasbt MATH500 is0. rasbt DeepSeek-R1 MATH500 JSON contains500 question/thinking/final-answer records, promising for second-task acquisition savings; not yet rescored. Other sources documented, no new GPU work. See `docs/quick_validation/public_failed_trace_alternatives_20260919.md`.

## 2026-09-19 — Zero-generation public UFT audit; resumable acquisition pause

User requested public failed-draft availability audit before further acquisition. Downloaded official UFT training archive (fixed repository commit and archive SHA recorded in report), read 54 Game24 failed CSVs: 1,634,093 rows across720 mapped questions. Priority Qwen2.5-Math-7B CoT:470,898 rows,361,394 exact unique text strings. Automatic canonical final-error filtering leaves625 questions after all historical and reserved exclusions; these are candidates, not manually certified or target-solvable questions. Fixed reservoir20 manually audited:12 canonical substantive failures,5 extra-step substantive failures,2 valid final expressions with inconsistent steps/RHS,1 visibly incomplete. No EOS metadata, so strict non-truncation cannot be certified. CPU wrapper checks12/12 pass with CharacterTokenizer only; no model test or new generation. Track A protocol unchanged; Track B acceptance of processed trajectories remains a decision point. See `docs/quick_validation/public_uft_audit_20260919.md` and `outputs/public-uft-audit-20260919/`.

Per user pause authorization, SIGSTOP only the exact own32B orchestration parent PID930390 while its in-flight child completed normally. Verified9 saved chunks=288/512 outputs; child exited, parent remains stopped, no next chunk. status.json256 is stale until parent resumes. Resume requires matching process creation time1789783061.78 and available GPU, then SIGCONT original parent; do not restart runner. No automatic continuation or intervention was launched.

## 2026-09-18 — Gate A passed; clean baseline acquisition queued

The seven-question dual-anchor pilot completed 56/56 with EOS and parseable outputs. R0/R2/R3/R4 were 12/14, 4/14, 12/14, and 10/14. Question-cluster bootstrap gives R3−R2 +57.1 pp and R4−R3 −14.3 pp; the strict six-question subset has the same direction. Go to independent baseline acquisition; hold any path-superiority or local-mask claim.

The earlier 24-question screen remains baseline-only history and is excluded from the formal pool because it overlaps development/intervention questions. A new fixed-order batch of 32 clean questions × 16 Qwen3-8B R0 samples (512 ordinary-vLLM generations) is queued on A100 GPU4. The queue excludes all development/intervention IDs and all previously screened IDs, waits for large non-owner GPU processes, stops only the exact own resident, and restores it after completion. No intervention or automatic Qwen3-32B launch follows this batch. Decision record: `docs/quick_validation/gate_a_decision_20260918.md`.

## 2026-09-17 — Ordinary vLLM baseline benchmarks authorized and generating

User authorizes bounded throughput work (2development questions×16samples per available anchor, max96 across3), then explicitly confirms read-only Qwen3-32B checkpoint permission. Qwen3-8B ordinary FLASH_ATTN/default worker generated from18:13:52CST onGPU4;16concurrent sequences. Qwen3-32B32generation follow-up queued after8Bsuccess;singleGPU,4concurrent sequences,32768context retained,noquantization. Both useBF16,n16,seed42,.6/.95/top_k20, eager ordinaryvLLM0.11.0; no custom mask. No formal held-out acquisition/intervention authorized. Nemotron32B not found and storage insufficient for comfortable download; no fallback. Ends restoring selective8Bresident. Full plan docs/quick_validation/ordinary_anchor_benchmark_20260917.md.

## 2026-09-17 — Protocol parity audit, preparation only (zero generation)

User explicitly pauses interventions/screening pending audit. Official HEAD8614634 unchanged in audited code directories. Pooled three-anchor2T/2F rule confirmed in extant aggregate_data.py; scripts reference missing aggregate_data_minimal.py. Default baseline16/model/question, seed42. Extant filter includes falsey None after stop/parsable-Thinking filters. 1F flatten creates two rows but published shell/path handling is inconsistent for F2; not executed.

TED caches union631questions; all631 numeric mappings match zero-based lexical ordering of our1362 ToT multisets, only2 IDs equal ToT Rank.596 retained pooled anchor cases have≥2 stop/True and≥2 stop/False, but missing raw drafts/Thinking flags and anchored parse selection prevent treating cache as full original653 or baseline-only membership. Historical401baseline records include70nonthinking,299HFThinking,32vLLMThinking; exclude development then zero meet explicit2T/2F in existing completed/parsable pool.

Read-only discovery: Qwen3-32B17/17shards (~65.5GB) under another user's directory, use not authorized; no Nemotron32B found in bounded accessible scan; own smaller model directories inspected lack weights. New machine plan selects104unseen candidates from1276 (86historical multiset exclusions), seed20270918, generate:false. Full three-anchor stages32/64/104 imply1536/3072/4992baseline generations, not approved. Old startup queue nowpaused_protocol_audit; GPU4resident unchanged. Report docs/quick_validation/protocol_parity_report_20260917.md; no new model download/load/generation.

## 2026-09-17 — Screening finished; one eligible new failed draft, no interventions

Validation exit0 at13:07:58 CST:9 EOS completions,4 correct/4 false/1 scorer-null;36529 tokens in977.59s. Null1189/path is a nested fraction with an extra12; preserve official score. vLLM resident active onGPU4. Screening13:08:49–15:11:23 CST:32 outputs,245140 tokens,30 correct,1 completed wrong,1 length-limited malformed Thinking. Only1170 mixed-success;1170/0 uses three12s where two allowed, arithmetic24 correct, explicit invalid usage endorsement.69/2 repeats until32696-token limit and is excluded. No held-out intervention generated or new budget consumed. Full result/audit: docs/quick_validation/heldout_screen_results_20260917.md. Frozen matrix remains unchanged pending discussion.

## 2026-09-17 — Bounded independent-question batch authorized and queued

User authorizes sequential handoff after current vLLM validation: at most32 draft samples and48 evaluation samples. Eight unseen question IDs frozen after excluding server historical IDs and number multisets:519,1080,69,377,45,1170,1144,197. Two fresh paired evaluation seeds927001/927002; at most6 accepted questions, R0/R2/whole_path/X_path. Resident startup queue automatically performs screening only after successful validation; then waits for agent textual/arithmetic X annotation audit. Evaluation is authorized but cannot bypass that audit. No automatic expansion or backend fallback. Plan and execution boundary: docs/quick_validation/heldout_queue_20260917.md. Freshness/overwrite tests:2 passed.

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


## 2026-09-17 夜间双anchor acquisition 已授权启动

用户批准双Qwen adaptation，固定候选前20题 × 8B/32B × n16，最多640次，约10–12小时。普通vLLM，GPU4；分批落盘，12小时上限；不自动intervention，结束恢复selective resident。原n4样本不重复合池。详见 [冻结协议与监控](docs/quick_validation/dual_anchor_overnight_20260917.md)。首启进程等待接口异常在生成前修复；原始异常日志保留。前轮人工审计修正为8实质错误/3纯格式错误，1057/1属实质错误。

## 2026-09-18 dual-anchor overnight audit
640/640 complete in 32539s. Official: 583 true, 51 false, 6 length. Final-answer audit: 40 substantive multiset failures, 11 format-only. Strict scorer eligible: 9 questions; at least one substantive draft: 7; at least two substantive failures: 6. Resident restored. No new generation. Report: outputs/game24-dual-anchor-20q-20260917/analysis_20260918.md. Raw records synchronized locally.

## 2026-09-18 seven-question intervention launched
Authorized 7 questions x 2 paired seeds (927001/927002) x R0/R2/whole-late/whole-path = 56 generations. Frozen random failed drafts, 5 from 8B and 2 from 32B. Independent-solve prompt unchanged; all conditions selective vLLM, including fresh R0. Preflight input/boundary/onset checks passed. Existing GPU4 resident reused; no extra screening. Protocol: docs/quick_validation/dual_anchor_validation_20260918.md. Output: outputs/game24-dual-anchor-validation-20260918/.


## 2026-09-19 whole-trace acquisition / Batch02 second anchor
User approved full32 Qwen3-32B x16=512 ordinary-vLLM baseline, no filtering by 8B outcomes. Frozen original candidate manifest; strict formal eligibility >=2 completed parsed True and >=2 manually substantive False, unlike pilot41. 8B manual audit35 substantive/7 format/17 length/1 unscored/452 correct; same8 preeligible. 32B chunked job launched GPU4; finish -> pooled scorer audit + manual queue -> resident; no intervention/next-batch auto-launch. See docs/quick_validation/whole_trace_acquisition_plan_20260919.md.


## 2026-09-19 submission sprint adopted and recorded
User requested plan persistence, GitHub synchronization and ongoing change tracking. Canonical plan: docs/quick_validation/iclr2027_submission_sprint_20260919.md. Acquisition time-box September21, target20–30 new strict questions, batchwise R0/R2/R3/R4, correct-draft control, bounded second task/model; major results freeze September24. Supersedes prior acquire30–50-before-evaluation schedule, not scientific thresholds. No additional generation launched by this documentation update; Batch02 queue unchanged.

## 2026-09-19 17:55 progress and CPU preparation
Batch02 Qwen32B persisted224/512 (14 questions), chunk14 running. CPU-only MATH500 read check:500 rows/500 unique IDs; official math equivalence smoke passed two checks. Existing evaluator and independent prompt are Game24-specific; explicit task routing is required before second-task generation. Preparation notes: docs/quick_validation/parallel_preparation_20260919.md. No GPU job changed or added.


## 2026-09-19 MATH500 compatibility CPU validation
Implemented explicit task routing, official math scorer, task-specific independent prompt, baseline source validation and audited-pair bundle preparation. Game24 defaults unchanged. Local31pass/4skip; isolated server37pass; real500-item dataset and Qwen tokenizer CPU integration passed. Explicit user permission obtained for isolated code upload after auto-review rejection. No active scripts overwritten/no new GPU generation. See docs/quick_validation/math500_compatibility_20260919.md.


## 2026-09-20 — Resume fixed acquisition and parallel CPU external math audit

User authorized both. Stopped exact completed own8B resident PID1868203 and its children, verified GPU4 free, SIGCONT original32B parent930390 with verified creation time. Status288/512,current chunk18;224 remaining. Isolated CUDA-disabled official MATH500 scoring completed500 public R1 outputs:480 True,12 False,8 no extracted answer. False are pending substantive manual review, not12 certified failures; no math generation launched.

Clarification: all current interventions pair a question with its own failed draft and solve that same question again. New question means newly admitted dataset item, not cross-question contamination. UFT20 selection random from625 fresh candidates; no target mixed-success filtering. Actual injected draft character mean104.7 vs pilot7 mean1391.14; these are injected strings, not full source Thinking lengths.

## 2026-09-20 Public math validation
用户批准排除图形后按实际16题运行：8 MATH500 + 8 MATH train，2 paired seeds × R0/R2/R3/R4 = 128。冻结数据与预检通过，服务器12项CPU测试通过。GPU0隔离tmux启动，GPU4的32B继续。详见 docs/quick_validation/math_external_launch_20260920.md。


## 2026-09-20 MATH external run failed before first persisted batch
运行约57分钟，服务器05:40:54 UTC（北京时间13:40:54）CUDA illegal memory access，继而EngineDeadError。128计划请求，0条持久化结果；无results.jsonl、无completion.json。GPU0已释放。故障栈经过FlexAttention create_block_mask_compiled / PyTorch Inductor cudagraph；CUDA异步报错，尚不能认定根因。不能计算accuracy或推断科学结论。原始日志已同步 outputs/math-external-16q-20260920/run.log。尚未重启。


## 2026-09-20 MATH retry1 repair
修复selective mask回调padding域读取前未保护的索引，先clamp实际读取索引，再以原物理范围门控；有效token阻断关系不变。GPU回归12组形状（batch8/5/3/1，KV127/129/32767）通过。原事故CUDA异步栈不足以认定唯一根因，长运行仍待验证。新增on_result接口按请求完成立即保存并fsync，避免整批失败丢失已完成结果。启动math-external-retry1于GPU0；短四条件接口一致性smoke通过后才运行同一128冻结请求，8条×4tokens工程检查不计科学结果。旧运行目录保留。


### retry1/retry2短验收失败，retry3静态形状修复
两次短验收均在正式生成前失败；padding保护和关闭CUDA graph分别不足。CUDA_LAUNCH_BLOCKING定位至create_block_mask编译出的triton_per_fused__to_copy_sum_7：R0_BLOCK=128、r0_mask恒True、读取x+1876*r，而buf20按动态ceil(query_length/128)分配。改create_block_mask为dynamic=False并关闭cudagraph，避免动态形状错误复用。retry3在GPU0验收，正式结果仅写retry3目录，前两次不能合并。工程短探针不计科学样本。


### retry3 partial and resume
静态形状修复后短接口一致性通过，保存24/128（3道MATH500×2seeds×4条件）。R0=6/6,R2=0/6,R3=6/6,R4=5/6，R4一次length/未解析；不可当16题总体。运行约3.36小时后达到Dynamo recompile_limit64，而非CUDA非法访问。有限上限调整1024，按id/condition/seed检查重复及manifest一致性后保留24条续104条，tmux math-external-resume，日志resume.log。首24条metadata enable_thinking默认False为记录字段遗漏，实际使用冻结Thinking prompt；后续修正字段，不修改旧结果。


## 2026-09-20 GPU4 overnight queue
Batch02 audited:8 strict eligible. User approved <=176; actual104 remaining MATH +64 Game24=168 launched GPU4. Earlier GPU0 restart failed; GPU4 preserves24 records. Finite compile limits1024/2048, static masks, immediate fsync, stop on failure and restore own resident. See docs/quick_validation/night_validation_20260920.md.


## 2026-09-20 contribution review and live snapshot
MATH34/128 persisted at check, GPU4 active; Game2464 queued. Recorded mixed evidence and deletion/reset reviewer objection in docs/quick_validation/contribution_and_controls_20260920.md. Continued access intervention differs from deletion in retained prefill exposure, but is not proof of erased information or practical superiority. Proposed controls only; no added generation budget.

## 2026-09-24 — Gemma 4E target-model validation complete
The frozen 15-question Gemma_4_E4B_it_Thinking run completed 60/60 R2/R3 requests on A100 GPU4 on Sep23 (8132s). Its R0 capability gate passed at 28/30 correct and 30/30 normally parseable. R2 was 22/30 correct; R3 was 27/30, with all 60 requests ending EOS and one R3 output unresolved by the frozen final-answer parser. Preflight same-text/mask contracts passed for all 30 paired units and all 30 persisted first-token boundary checks passed. Pooled R3-R2 is +16.7pp (6 wrong-to-correct, 1 correct-to-wrong); exact McNemar p=.125, question-cluster bootstrap 95% CI [0.0, 30.0]pp (50,000 draws). Pooled R0-R2 is +20.0pp [3.3, 33.3], p=.0703; R3-R0 is -3.3pp [-20.0, 10.0], p=1.0. The 15-question set comprises 8 dual_anchor_batch02 confirmation questions and 7 dual_anchor_initial7 pilot questions; only the former are independent confirmation data. On those 8 questions, R0/R2/R3 are 14/16, 11/16, and 15/16. R3-R2 is +25.0pp (4 recoveries, 0 harms), question-cluster bootstrap 95% CI [6.25, 43.75]pp, exact McNemar p=.125; one R3 output in this stratum is unresolved and counts incorrect. These data support bounded cross-architecture replication but not a broad significance claim. GPU4 was released after completion. Raw artifacts remain on A100 under `/data2/gaojc/tmp/math-external-16q-20260920/outputs/game24-gemma4-e4b-{r0-capability-15q,r2-r3-15q}-20260923/`. No follow-up generation was queued.

## 2026-09-24 — Independent Batch03 audit correction and prepared next experiment

Execution update22:29 Beijing: user approved64-request validation and selected wait-for-idle A100. Isolated server snapshot `/data2/gaojc/tmp/game24-batch03-validation-20260924` reuses reviewed validated code path (vLLM0.11,torch2.8,transformers4.55.4); does not deploy unrelated local backend changes. CPU preflight checks64 historical Batch02 prompt reconstructions exactly,64 new requests/16pairs, same-text and mask onsets, input97–1006tokens. Tmux `game24-batch03-idle-gpu-20260924` running queue PID261285; all GPUs occupied at registration. Three idle observations30s apart plus final recheck; max wait12h to Sep25 10:29 Beijing. One run only,8 four-token engineering probes before64 scientific requests, per-answer fsync; no termination of other jobs, no automatic retries/expansion/resident restoration. Local preflight and status snapshot saved under `runs/batch03_next_experiment_20260924/`; status is waiting, not scientific generation.

This entry supersedes the later-listed interruption report's old 57/7/4 and 7+4 eligibility counts. Verified against raw files: q122 samples4/9 reuse operands; q381 samples5/10 explicitly select invalid final answers despite an earlier valid alternative. Correct counts:61 substantive errors,3 extraction misses,4 invalid among68 raw-False. All771 raw-True extracted equations verified with Fraction and exact input multiset. Eight dual-complete and five partial questions pass; requiring original official-True>=2 yields the same sets. Added6 real-data regression tests, removed contradictory mixed-answer fallback; all14 audit/recovery tests pass. Installed vLLM0.11 confirms stable parent_seed+child_index mapping. No GPU smoke or generation performed.

Prepared deterministic failed-body pairs and a reviewable64-generation Qwen3-8B plan (8 complete new questions ×seeds927001/927002×R0/R2/R3/R4), using the existing fixed random selection rule; no intervention outcome consulted for selection. q381 sensitivity predeclared. Complete-prefix runtime selection and interrupted candidate coverage must be disclosed; Batch03 reported separately, Batch02+Batch03 secondary, pilot excluded. Reject choosing only8B-passing questions to complete32B just to reach20. Machine plan `runs/batch03_next_experiment_20260924/plan.json` has generate=false. GPU4 is now occupied by a process outside gaojc; no process changed. See `docs/quick_validation/batch03_next_experiment_20260924.md`.

## 2026-09-24 — Batch03 dual-anchor independent-question acquisition started

After the user asked to continue and keep GPU4 working, started the already frozen Batch03 manifest: 32 Game24 questions × 16 ordinary-vLLM R0 outputs × Qwen3-8B and Qwen3-32B = 1,024 generations. The new independent-question yield is the current primary evidence gap; Qwen3-32B target validation, Gemma target validation, and correct-history specificity control are already complete. Candidate order and eligibility thresholds are unchanged. Run Qwen3-8B first in four-question chunks, then Qwen3-32B in two-question chunks; every completed chunk persists before the next. Stop for pooled manual substantive-failure audit; do not select drafts or launch interventions automatically. GPU4 prelaunch was clear at 4 MiB; `/data2` had about 226 GB free. At 17:08 UTC, Qwen3-8B chunk00 had loaded and started its 64 generations; status remained 0/1,024 completed. No other GPU or user's process was touched. Protocol, runner, and live artifacts: `docs/quick_validation/batch03_dual_anchor_20260924.md`, `scripts/batch03_dual_anchor_20260924.py`, and `/data2/gaojc/projects/contextual-drag-extend/outputs/game24-batch03-dual-anchor-20260924/`.

### 2026-09-24 — Batch03 interrupted, results audited, continuation held

Per the user's stop-and-audit instruction, re-identified the Batch03 scheduler, generation frontend, and vLLM engine on A100 GPU4, stopped the scheduler before it could launch another chunk, and verified the processes ended. GPU4 was 4 MiB / 0% / no processes at 11:55:56 UTC. No other user's task was targeted. The original run is `interrupted`, not complete. Persisted data: 8B 512/512; 32B 352/512; total 864/1,024. The in-flight 32B chunk11 has config/request/log files but no saved results/summary; its unsaved responses are excluded. Chunks12–15 never began.

Recomputed from saved chunks and reviewed all 68 scorer-False answers against the full answer and input-number multiset: 57 substantive errors, seven valid answers missed by extraction/scoring, four invalid outputs excluded, zero uncertain. Two missed answers occur in Qwen3-32B question381: a valid `11+11+8−6=24` appears as an explicit alternative while the parser extracts an invalid final expression. The audited pool gives seven qualifying dual-anchor-complete questions among22 and four questions among10 with only 8B coverage; the latter are not counted as dual-anchor-complete. Prefix replay at per-anchor n=4/8/12/16 yields pooled eligible counts 2/6/7/7; n12→16 adds zero. Chunk summaries give 8B/32B generation times 8,522.619/37,157.073 seconds and reported chunk-total sums 8,891.686/37,923.732 seconds. They do not support per-prefix GPU-time allocation.


## 2026-09-25 — Batch04 fresh-question screen started

At the user's request to scale the independent-question sample before the deadline, froze a new baseline-only screen of 32 previously unseen Game24 questions, with eight R0 generations per question from each of Qwen3-8B Thinking and Qwen3-32B (512 planned generations). Preparation scanned prior manifests, screening outputs, experiment records, and question pairs; 194 question IDs and 194 corresponding number multisets were excluded. The corrected fixed-order Batch03 prefix replay is 2/7/8/8 eligible questions at per-anchor n=4/8/12/16; using n=8 is a measured-efficiency design choice, not a promised yield. Exact candidates and source hashes are in `scripts/baseline_manifest_batch04_20260925.json`; plan and timing assumptions are in `docs/quick_validation/batch04_sampling_plan_20260925.md`.

GPU4 preflight found the user's Qwen3-8B selective resident (PID 1222876 / EngineCore 1223040) as its sole compute owner, with no pending resident job. The run stopped only that owned service, verified GPU4 free, and launched in the existing `qwen3-vllm-resident` tmux session under window `batch04-screen`. Qwen3-8B chunks00–07 completed 256/512 generations. The local record-level audit found 251 EOS, five length-limited; among EOS records, 239 official-True and 12 official-False. Manual review of all 12 valid scorer-False responses classified 11 as substantive errors and one as an extraction miss with an explicitly endorsed valid equation. Question50 provisionally passes the 8B-only 2+2 threshold (3 official-True, 4 substantive errors); pooled eligibility awaits Qwen3-32B. At 12:40 UTC, Qwen3-32B chunk00 had four requests finished, four running, and eight waiting; generation throughput 72.5 token/s; GPU4 77,331 MiB / 99% with no OOM/error under the configured 0.95 memory reservation. No failed-answer labels are auto-accepted, and there is no automatic intervention, retry, or candidate expansion. The runner persists and validates each chunk and will restore the selective resident after success or failure.

At 13:23 UTC, the first Qwen3-32B chunk still has three of sixteen generations decoding; no result file has yet been persisted for this chunk. Throughput has stayed near 2.5–2.8 token/s since 13:07 while GPU4 is at full utilization and the KV-cache metric fluctuates near 75–99%. No CUDA/Xid, OOM, or Python exception is present. Batch03 chunks under the same settings measured 41–73 token/s, so this is an anomalous long-generation tail; KV-cache pressure and recomputation are plausible but unconfirmed. Keep the active chunk intact, then recalculate ETA from its measured token count/runtime before choosing whether further action is warranted. The frozen queue and candidate set have not changed.

At 14:11 UTC, chunk00 remains in flight with three sequences decoding; short-window generation throughput fluctuates around 3.0–4.0 token/s. Its KV-cache metric repeatedly cycles between roughly 90% and 100%, which is consistent with scheduling/cache pressure but is not direct proof of preemption. No results from this chunk have been persisted, and no error or thermal throttle is present. GPU5/6 show no compute process; a request for authorization to use them for disjoint tail chunks is pending. Until answered, only GPU4 runs the frozen queue. No sample count, candidate, prompt, or seed has changed.

## 2026-10-14 — Game24 100Q data audit and bounded pilot preparation

Read-only A100 snapshot exported443 files, preserving original baseline chunks/configs/full text/token IDs; all checksums verified. Unified3,538 baseline records across206 multisets, of which3,136 ordinary-vLLM records match adapted dual-Qwen decoding/context. Compatible37 and strict32 eligible historical questions; conservative local/server material exclusions leave two complete-quota new-pool candidates643/1119. Batch03 missing16032B slots remains interrupted; prefix22-question replay2/7/8/8. Batch02 full prefix7/7/8/8. Batch04 actually completed512 generations,5/32strict yield and10.683 measured whole-job hours; eligible50/353/1073 are already later materials,643/1119 unexposed. Re-read25 ambiguous full final responses with raw-hash-bound adjudications; full raw provenance of all3,538 indexed records verified by11 passing tests. ICLR frozen artifacts untouched.

Created docs/game24_100q audit/acquisition/exploration-status/decision reports,1,362-row question manifest, raw trajectory index, two candidate witness records, empty unachieved100Q freeze and explicit not-frozen split. Frozen16new questions×2anchors×8=256-generation pilot, cap8cumulative GPU-hours; asyncordinary-vLLM, per-slot seeds, fsync/heartbeat/resume, no completed-invalid resampling, no automatic expansion. A100 CPU/runtime imports and both complete checkpoints verified without loading weights, initializingengine or generating. New GPU hours/generations0. Remaining98-question cost scenario~210GPU-hours extrapolated from Batch04, not an approved budget or pilot measurement.

At user request checked A100/A800 live at17:35China time: A100 all8cards have compute processes; GPU4 includes foreignhezq process plus ownidle resident. A8000/2/4/6 are idle;1has18GBunattributed allocation;3/5/7occupied. A800 ownQwen3-8B5shards and readable sharedQwen3-32B17shards complete, with existingvLLM0.10.2/torch2.8.0 environment; no model transfer/download needed. A800data13GBfree and root1.9GBrequire storage check. No GPU occupied/stopped on either server. Await allocation window/total budget; any A800 single-card migration must freeze paths/version and validate its environment first. Current collector is A100-specific. See docs/game24_100q/GAME24_100Q_ACQUISITION_REPORT.md and resource_inventory_a100/a800.json.

## 2026-10-14 — 已授权迁移至A800单卡并启动100题数据准备

用户明确要求迁移并运行100case数据准备后，部署到A800用户独立目录
`/data/gaojc/projects/contextual-drag-extend-game24-100q`，GPU4 / UUID
`GPU-9d164491-5abf-96eb-3d3f-e08e77deb8f7`，tmux `game24-100q-a800`。
只使用这一张卡，不修改或停止A100原resident及其他用户进程。
已有8B/32B权重直接读取，无大型模型下载/搬运；独立venv补齐官方math-verify0.8.0、
datasets4.0.0及grader导入依赖，基础vLLM0.10.2未升级。
两个tokenizer文件与A100字节一致；A800本地max_position_embeddings元数据分别扩大至
409600/204800，仅通过引擎hf_overrides恢复原40960，context保持32768，共享配置不改。

16题固定pilot / 每anchor8次 / 共256次 / 累计上限8 GPU小时，审计和成本门控通过后
沿预冻结1034题序每批32题，目标至少100道strict独立题。全项目在此前210小时成本情景
上设240小时有限保护上限，失败与恢复尝试计入；若预测超额、零pilot产率、资源异常则停止。
不自动改变配额、降低门槛、根据干预结果筛选；100题达成后先冻结20/rest split再结束采集。
当前控制程序只做数据准备，不自动运行R2/R3或消费held-out。

首次18:37北京时间启动权重加载成功后因ninja未在PATH失败，0条生成。
30.01秒失败作业及原日志保留，并纳入campaign ledger和pilot attempt账目。
ninja已存在，修复基础环境/CUDA工具链PATH、将FlashInfer编译缓存置于/data后，
18:42:46恢复。首次kernel编译约74.56秒；逐条seed使vLLM自动使用PyTorch-native sampler。
随后真实响应落盘：18:53的机器进度为33/256条，8B阶段33/128条、196749已持久化tokens，
另有在途长响应。较早23条复核为20原始True/3原始False、全部EOS/parsable-thinking，
False尚不等于已通过实质错误资格；未完成双anchor配额，不提前增加正式合格题。

13项CPU测试通过，包括所有3538历史记录全文溯源、False/None、混合最终答案、恢复、
GPU UUID、wave固定配额与有限成本门控。实时状态每15秒更新。
本地刷新 `python -X utf8 scripts/game24_100q_status.py`；完整批次原文和报告同步
`python -X utf8 scripts/game24_100q_status.py --sync-data`。
执行记录在 `docs/game24_100q/A800_EXECUTION_20261014.md`，原审计memo保留为生成前快照。

## 2026-10-15 — A800 pilot达到8小时上限后停止

09:35北京时间只读核实：02:42:42停止，累计8.0048 GPU小时，controller/collector退出、GPU4已释放。
保存205/256条（8B128，32B77），剩余51条32B；32B最终summary为interrupted、errors为空。
9题完成双anchor配额，初步严格检查2道新增候选584/1053；整批未完成，不以2/9替代完整pilot合格率，不冻结100题或split。
当前/data剩余约4.6GB，低于10GiB启动阈值；未调整8小时上限或自动续跑。GUIDE、RESEARCH_STATUS与执行记录同步停止状态。

## 2026-10-15 — 用户授权暂时仅用Qwen3-8B anchor

建立独立`docs/game24_100q_8b`协议/候选/原文索引，保留原双anchor冻结配置及32B回答。
复用原pilot完整128条8B回答，16题中584/1053符合单模型固定8次严格资格；历史8B prefix8重审1024条，无额外未暴露合格题。
旧643/1119的错误来自32B，不纳入。新起点2/100；不自动启动机制实验。
仅8B的含失败实测成本0.6675小时，按2/16产率外推剩余约784道新题、32.7GPU小时；原双anchor累计8.0048小时仍计入240小时总上限。
单anchor runner用不同部署文件名，原远端dual collector hash保持不变；每新批32题×8，严格逐槽seed/缺失恢复，source/配置hash绑定，目标满足才冻结20/rest。
20项CPU测试通过，A800 tokenizer/官方grader/vLLM验证仅检查8B（engine_initialized=false、GPU generations0）。
启动前实际检查返回awaiting_disk_space：/data约4.5GiB，低于10GiB；没有新GPU进程或自动排队。新状态命令默认查询8B；旧作业加`--protocol dual`。

## 2026-10-15 09:57北京时间 — 持续8B采集正式启动

用户追问10GiB需求并明确要求一步开始100case采集。复核16题全部8B原始输出仅6,164,152bytes，pilot点估计784道新增候选约302MB，全剩余1018题约392MB；10GiB是工程默认，非模型需求。
将单8B profile及policy余量明确修订为2GiB；旧配置、collector/controller和preflight绑定在A800归档，原dual运行器未变，源文件hash/采样/资格/240小时总预算保持。运行中每15秒检查空间、每条完成回答fsync，低于余量即停止。21项CPU测试通过。
09:57:14在A800 GPU4创建持久tmux `game24-100q-8b-a800`；首批32题×8=256响应，控制器/collector已启动并报告running_baseline_acquisition。每批审计和更新成本后自动继续，目标100严格合格题后冻结20/rest并停止；无机制实验。
当前初始候选2/100、复用128条。预计剩余约32.7 GPU小时，仅为16题pilot外推；新批首完成后更新。日志：`outputs/game24-100q-8b-20261015/acquisition/a800/campaign.console.log`。

## 2026-10-16 22:37至22:38北京时间 — 授权清理HTTP缓存并恢复采集

用户明确选择直接清理四处pip HTTP下载缓存，不为缓存另做归档。先核验精确绝对路径、UID1018、常规文件/无软硬链接、无包管理进程，再仅删除四处`http-v2`内容，合计3147个文件。
数据盘实际删除18.23GiB，系统盘8.92GiB；清理后剩余约19.85GiB/9.07GiB。pip wheels（4.3MiB）/selfcheck、安装环境、模型及实验原始文件保留；删除报告同步到`docs/game24_100q_8b/pip_http_cleanup_20261016.json`。
采集此前在14:13触发低于2GiB余量保护，停于第20批243/256。恢复前核对policy/profile/order/pilot/runner/controller/audit共7项冻结绑定全部一致，8B运行时和官方True/False/None评分检查通过（无额外生成）。
22:38:53在原A800 GPU4与tmux `game24-100q-8b-a800`恢复；重新审计停机前完整保存cohort后为89/100（原整批状态86），保留5235条原回答，仅继续缺失13槽。已观察GPU加载并生成新token；后续按原预算与门控继续至目标，无新干预。

## 2026-10-17 01:26:50北京时间 — 单8B数据目标达成并冻结

第22个新批次完成后得到102道严格合格独立题；完整候选720题（复用pilot16+22批×32），全部5760条回答保存。冻结seed20261014：development20、held-out82，交集为空、完整覆盖102题。GPU进程退出、GPU4释放，无R2/R3生成。
新8B续采31.0431 GPU小时，加复用8B pilot为31.7106小时；整个数据准备过程含此前双anchor为39.0480小时。回答分类5086 correct、406 substantive_error、115 pending_review、5 none_pending_review、148 truncated_or_incomplete；120待复核不作错误见证。
终检重算102题的816条响应hash/分类/八个槽/单anchor和2+2见证、独立多重集合及历史排除，全部通过。完整254文件快照62,638,562bytes同步本地，逐文件SHA256验证通过；原始source_path在本地可直接解析。
已有测试的初始2题断言更新为按目标状态验证完整冻结划分，21项CPU检查通过。状态工具停止后读取最终worker状态，消除旧heartbeat残留running/255条显示；控制器、采样与资格规则未改。
报告`docs/game24_100q_8b/GAME24_100Q_ACQUISITION_REPORT.md`，数据`game24_eligible_100.jsonl`实际102行，split20/82；机制探索报告NOT_STARTED。

