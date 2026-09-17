# Ten-question M_X late/path results

Finished 2026-09-13 15:25:49 CST, exit 0; elapsed 6h34m03s. 128 new + 32 unchanged reused records. GPU4 resident restored.

|Condition|Correct /40|Accuracy|Parse /40|EOS /40|
|---|---:|---:|---:|---:|
|R0|28|70%|40|39|
|R2|18|45%|40|40|
|R3|29|72.5%|39|39|
|R4|31|77.5%|39|39|
|M_X|24|60%|40|40|
|M_CX|18|45%|40|40|
|P_X|25|62.5%|38|38|
|P_CX|15|37.5%|40|40|

M_X/M_CX: target/control late. P_X/P_CX: same target/control regions, path.

|A -> B (B minus A)|Effect pp|95% CI|Wrong to correct|Correct to wrong|
|---|---:|---|---:|---:|
|R2->M_X|+15|[-7.5, 40.0]|12|6|
|R2->P_X|+17.5|[-2.5, 35.0]|13|6|
|M_X->P_X|+2.5|[-17.5, 22.5]|8|7|
|M_CX->M_X|+15|[-10.0, 37.5]|11|5|
|P_CX->P_X|+25|[12.5, 37.5]|13|3|
|M_CX->P_CX|-7.5|[-25.0, 12.5]|5|8|
|R3->M_X|-12.5|[-30.0, 5.0]|5|10|
|R4->P_X|-15|[-30.0, 0.0]|4|10|
|R2->R3|+27.5|[12.5, 42.5]|14|3|
|R2->R4|+32.5|[5.0, 57.5]|18|5|

CI: 10,000 question-cluster percentile bootstrap draws, seed2027; retain four paired seeds. Exploratory, no multiplicity correction.

|Question|R2|Whole R3|Whole R4|M_X|M_CX|P_X|P_CX|
|---|---:|---:|---:|---:|---:|---:|---:|
|1226|0|3|4|4|2|3|1|
|719|1|1|4|2|0|2|1|
|577|4|4|2|4|2|2|1|
|1358|0|1|1|0|1|1|0|
|1189|2|3|4|2|0|2|2|
|804|2|3|4|2|1|3|2|
|123|1|3|3|2|1|2|0|
|71|3|3|3|3|3|3|1|
|513|3|4|3|1|4|4|4|
|1084|2|4|3|4|4|3|3|

## Interpretation

- Old four: R2 5/16, M_X 10/16, P_X 8/16. Additional six: R2 13/24, M_X 14/24, P_X 17/24. The late advantage shrinks on expansion.
- Partial late/path remain below whole R3/R4 by 12.5/15pp. Path exceeds late by just one net success, with 8 improvements and 7 harms.
- P_X minus P_CX is +25pp, but control accuracy is below R2. This contrast may include control damage. Position, fragmentation, semantic role and path onset are unmatched; control boundaries may split a number. Do not interpret it as pure error-semantic responsibility.
- 513: M_X 1/4, P_X 4/4; late failures reuse 9 or 13, path successes give equivalent forms of 3*(9-13/13). However P_CX is also 4/4, so recovery is not exclusive to the selected error intervention.
- 577: M_X 4/4, P_X 2/4. Path failures include the original (13-6+1)*(9-6) and a different (13-1)*(6/(9-6)); both repeat 6. Blocking full expressions does not remove outside subexpressions or inherent model preferences.
- 1358: M_X 0/4, P_X 1/4, with correct (13*5+7)/3 once. Remaining outputs still misuse 7. One recovery is not stable mechanism evidence.

## Checks and decision

- P_X length/unparseable: 1226 seed32027 and 71 seed2027, both retained as failures. Other new conditions all EOS and parseable.
- 160 input/hash/seed/bundle checks;80 late first-token checks;32 exact reused records;40 actual attention checks passed. This verifies execution, not full semantic coverage.
- Continue exploratory mechanism work; do not claim partial superiority or general path-over-late advantage. Prioritize recovery/harm case review and better matched controls before interpreting an expanded mask. No new experiment launched.

Complete outputs: outputs/game24-qwen3-mx-late-path-20260913/review.html. Detailed subgroup CIs are in the companion JSON.
