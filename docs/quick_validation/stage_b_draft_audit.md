# Stage B first draft batch audit

Normal completion verified:32questions,128generations;109official true,15false,4null;123EOS,5length-capped. Generation time sum34527.37s (9h35m27s). All raw files and sibling log synced locally. No Stage B paired evaluation yet. GPU4 residency restored PID1919967 in qwen3-stage-b-gpu4.

Seven mixed-success questions were candidates before manual audit. Six meet the genuine body-level reasoning-failure criterion:

| Question | First eligible failed draft | Reason | Verified correct companion |
|---|---|---|---|
|123|123/1|Body uses5twice in8*(5-8/(5-1)); also boxes scalar24, but not a format-only failure.|123/0:8*(5-1)-8=24|
|577|577/0|Uses6twice in(13-6+1)*(9-6), claims each once.|577/1:6*(13-9)*1=24|
|71|71/0|Repeatedly returns12*(7-(11-7))=36 as solution; recognizes mismatch yet never supplies valid24 solution. Includes scalar boxed24 but substantive failure.|71/1:12+11+7/7=24|
|719|719/2|Uses three8s instead of two in8*(7-(5-8/8)).|719/0:8*(7-5)+8=24|
|513|513/0|Fails to find solution, repeats expressions yielding17/10 and incorrectly claims no solution; scalar boxed24 does not make this format-only.|513/1:3*(9-13/13)=24|
|1084|1084/0|Uses three7s instead of two in(9-5)*(7-7/7).|1084/1:(9-7)*(5+7)=24|

Additional failed drafts577/2,577/3 repeat6;1084/2 repeats7. First eligible per-question rule retained.

Excluded question23 (draft23/3): body contains valid12+12+11-11 and ((12+12)/11)*11, final boxed24 only. Pure final-answer formatting error, not failed reasoning. Question1356 has four substantive failed drafts but zero correct companion in the fixed4samples, so fails mixed-success selection. Length-capped/unparsed outputs are not promoted to complete drafts. Other questions have no eligible failed draft.

Target was7new questions, so first batch is one short. Six approved drafts preserved; no automatic lowering of target, promotion of1356, or extra sampling. Recommended decision: continue the fixed shuffled pool for a small bounded8-question batch (indices64–71,32generations), audit in order, and take first eligible new question. This is a proposal awaiting user decision under the existing insufficient-yield stop rule, not a launched run.
