# Stage A fixed-case reproducibility result

All five additional groups completed normally. Batch UTC2026-09-10 12:15:24–16:50:11; CST20:15:24–2026-09-11 00:50:11; elapsed4h34m47s. Initial independent-control group plus five additions:3questions x6paired seeds x4conditions=72outputs. No old critique-prompt results included. Full raw batch synced locally. Model residency restored PID1140091 in tmux qwen3-stage-a-gpu4. No Stage B launched.

| Condition | Correct | Accuracy | Parse | EOS |
|---|---:|---:|---:|---:|
|R0|10/18|55.6%|100%|100%|
|R2|5/18|27.8%|100%|100%|
|R3|10/18|55.6%|94.4%|100%|
|R4|11/18|61.1%|100%|100%|

| Question | R0 | R2 | R3 | R4 |
|---|---:|---:|---:|---:|
|1189|5/6|2/6|4/6|5/6|
|1358|0/6|0/6|1/6|1/6|
|804|5/6|3/6|5/6|5/6|

| Effect | pp | Question-cluster bootstrap95%CI pp | Right→left wrong→correct / correct→wrong |
|---|---:|---|---|
|R0−R2|27.8|[0,50]|5/0|
|R3−R2|27.8|[16.7,33.3]|6/1|
|R4−R2|33.3|[16.7,50]|7/1|
|R4−R3|5.6|[0,16.7]|2/1|

Recovery ratios: late1.0,path1.2; no ratio CI because bootstrap residual can be zero. Ratio above1 reflects R4 exceeding observed R0, not a bounded mechanistic recovery proportion. Bootstrap10000 resamples, random seed2027, question clusters retain all six paired seeds; ONLY3clusters, so positive intervals do not establish population significance or fully characterize seed uncertainty.

New five groups alone: R0/R2/R3/R4 counts9/5/9/9, denominators15 each. Thus late/path both improve overR2 by4/15 beyond the initial positive group. Overall seed-group directions vary: R3−R2 positive4groups, zero1, negative1; R4−R2 positive4,zero1,negative1. R4−R3 positive2,zero3,negative1. Do not describe universal per-seed recovery.

Audit: all18 R2–R4 bundles across6groups have matching tokens/hashes/spans/seeds within pair, unchanged prompt text/tokens across groups, zero boundary spillover. All18 R2/R3 first-token checks match. Six first-pair attention sanity files report36layers, blocked attention0 and path postdraft logits mutation difference0. Actual measured sanity is first question of each group, not each question individually.

All21 correct R3/R4 extracted expressions checked: valid12*12−12*10, (13*5+7)/3, or12*10/(10−5), up to equivalent notation. One unparsed R3 (seed52027,1189) ended normally with nested fraction; its body also uses four12s rather than three, so manual recognition does not turn it into success. Parser failure cause not diagnosed. Original null preserved and counted not correct. Full body/format audit of all failed outputs is not complete.

Decision: Stage A supports repeatable net block recovery on this fixed set; proceed to proposal/review of Stage B10–15independent questions with3–4paired seeds each. Do not add more seeds to these three or move directly to responsibility decomposition. The initial R4-only/nonrecoverable labels were not stable:1189 also responds toR3,1358 has one recovery for each block. R4's extra advantage overR3 is weak (net one output), so no robust path-specific hierarchy established. Main repeatable evidence comes from1189/804;1358 has no measured R0−R2 residual and remains difficult. Broader claim remains unverified; new prompts and HF differ from original critique/vLLM setup.

Machine report: stage_a_report_20260911.json. Aggregation script: .tmp-smoke/summarize_stage_a.py. Accuracy is primary; other diagnostics secondary.
