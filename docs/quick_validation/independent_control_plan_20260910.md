# Independent-solve prompt control

User approved this new diagnostic after discussing unreadable-draft/critique-task mismatch. Three fixed drafts: 1189/3, 1358/0, 804/1. One generation per R0/R2/R3/R4 per problem = 12 outputs. Original seed base 2027 (actual seeds 2050,2051,2055), enabling descriptive comparison to the initial batch without selecting seeds by outcome. Same seed does not guarantee matching random trajectories across changed prompts.

R0 input:

```text
Original problem:
{problem}

Solve the original problem independently and provide a complete solution. You do not need to evaluate or refer to any preceding draft. Conclude with an expression using the original four numbers exactly once in \boxed{}.
```

R2/R3/R4 input, identical within each problem:

```text
Original problem:
{problem}

The following draft has an INCORRECT final answer.
-- beginning of the draft --
{fixed draft}
-- end of the draft --

Solve the original problem independently and provide a complete solution. You do not need to evaluate or refer to any preceding draft. Conclude with an expression using the original four numbers exactly once in \boxed{}.
```

The same Thinking chat rendering is used in all conditions. This replaces the upstream critique wrapper; it is a new diagnostic setting, not a strict paper reproduction. Output formatting instruction is more explicit, so improvement versus old prompts cannot uniquely identify task-mismatch effects. R0 has the shared task suffix even though no draft is supplied. No R1 is run. Do not combine new and old prompt-setting scores.

Unchanged: model, BF16 HF eager backend, temperature .6, top_p .95, top_k 20, total context32768, whole-draft masks, full-prefill first token for R3, official scoring, no truncation of prompts or draft resampling. Record text/token hashes, position preservation, spillover and real attention sanity through existing runner.

Decision: first inspect new R0−R2. If residual drag disappears, this setup cannot establish block recovery. Otherwise inspect R3−R2 and R4−R2, plus parsed/EOS rates and body-correct/boxed-format failures. One sample on three selected problems is exploratory, not causal proof or a general Go/No-Go. Full manual audit of previous repeated outputs remains pending; its suspected failure categories are not established counts.

Run: outputs/game24-independent-control-20260910, sibling .log/.pid; tmux qwen3-control-gpu4. Bounded to three pairs, stops on error; after successful completion restores model residency as previously requested. No automatic expansion, vLLM migration or fine-grained masks.
