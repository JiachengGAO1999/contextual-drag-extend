# Qwen3-8B non-thinking engineering smoke

This run validates execution only. It is not paper replication or scientific Go/No-Go evidence.

10 paired Game24 examples; 50 condition outputs. 70 independent draft candidates were sampled to obtain 10 completed, officially parseable failed drafts. Runtime: 111.3 minutes. Temperature 0.6, top_p 0.95, no top_k, max_new_tokens 4096, non-thinking.

| Condition | Correct | Parse rate | EOS completion |
|---|---:|---:|---:|
| R0 | 6/10 | 100% | 80% |
| R1 | 1/10 | 80% | 80% |
| R2 | 0/10 | 80% | 60% |
| R3 | 4/10 | 60% | 60% |
| R4 | 2/10 | 50% | 50% |

Unparsed generations count as not correct; none are dropped from the paired denominator.

| Contrast | Effect (pp) | Paired bootstrap 95% CI | Reference not-correct→correct | Reference correct→not-correct |
|---|---:|---:|---:|---:|
| R0−R1 | +50 | [20,80] | 5 | 0 |
| R0−R2 | +60 | [30,90] | 6 | 0 |
| R3−R2 | +40 | [10,70] | 4 | 0 |
| R4−R3 | −20 | [−50,0] | 0 | 2 |
| R4−R2 | +20 | [0,50] | 2 | 0 |

Bootstrap: 10000 paired problem-level percentile resamples, seed 2027. Recovery ratios are 0.667 (R3) and 0.333 (R4). Ratio confidence intervals are omitted because some resampled residual denominators are zero.

All ten R2–R4 input/hash/span contracts and R2/R3 first-token checks passed. Actual blocking was checked across all 36 layers on the first accepted prompt: blocked attention probabilities were zero; path-block postdraft logits were unchanged after draft-token mutation. Seven examples had exact boundaries; three spilled only into one trailing newline. No semantic wrapper text was masked.

Output quality remains unresolved: 17/50 outputs hit 4096 tokens, with repeated reasoning visible in their tails. All 13 unparseable outputs were among the length-capped outputs. No completed output failed parsing. This does not establish that a longer budget alone resolves repetition. It prevents using this engineering run to judge the scientific claim.

Next runs must use Qwen3-8B Thinking, temperature 0.6, top_p 0.95, top_k 20, context size 32768, as explicitly requested. No additional non-thinking runs or fine-grained attribution were launched.
