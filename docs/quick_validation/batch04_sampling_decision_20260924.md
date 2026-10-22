# Next Game24 acquisition: widen independent questions

**Superseded by the 2026-09-25 user-authorized fresh Batch04 plan:** see [`batch04_sampling_plan_20260925.md`](batch04_sampling_plan_20260925.md). The new run screens 32 unseen questions at eight samples per anchor; it does not resume or alter Batch03's frozen manifest.

Decision recorded 2026-09-24 after discussion with the user. This is a plan for the batch **after** the running Batch03 dual-anchor acquisition; it does not change Batch03's frozen 32 questions, two models, or 16 generations per model per question.

## Why reconsider 16 generations

The [Contextual Drag paper](https://arxiv.org/html/2602.04288v2) uses three Game24 anchor models (Nemotron-32B, Qwen3-8B, Qwen3-32B) and requires at least two correct and two incorrect anchor responses per selected question. Its [public initial-sampling script](https://github.com/princeton-pli/Contextual-Drag/blob/main/data_generation/initial_sampling.sh) defaults to 16 generations per model-question pair (`N_SAMPLES=16`, passed as `--n`). Thus three anchors at the public default imply up to 48 screening generations per candidate question. The paper separately says it samples 16 generations per question for **evaluation**; that is a different stage. The authors' actual initial-sampling launch settings are not confirmed by the public default alone.

Batch03 uses two Qwen anchors, so its fixed budget is 32 questions x 2 models x 16 generations = 1,024 screening generations. Each question is still one independent question. Prior strict screening yielded 14 eligible questions among 52 candidates across the pilot and Batch02, but the pilot is excluded from the independent confirmation denominator. The original paper's 653/1,362 selected Game24 questions are not a directly comparable yield because its anchors and acceptance procedure differ from ours.

## Decision for the next batch

After Batch03 finishes and its incorrect responses receive manual substantive-error review, favor **more fresh independent questions with fewer initial generations per question**, provided a retrospective analysis shows acceptable loss of eligible questions per GPU hour. Do not choose a reduced count solely from intuition or from scorer-only labels.

For each Batch03 candidate, replay the frozen output order at 4, 8, 12, and 16 generations **per anchor**. At each prefix, apply the same pooled two-correct/two-substantive-wrong eligibility rule using completed, parseable responses and the manual labels. Report (1) eligible independent questions, (2) questions first reaching eligibility at each prefix, (3) incremental eligible questions per additional generation and measured GPU hour, and (4) each anchor's marginal contribution. Keep every already generated response in the audit; the replay is a planning analysis, not a replacement for the preregistered full-batch result.

Choose the next batch's question count and initial per-anchor generation count from those measured tradeoffs before seeing its outcomes. A practical design to evaluate is a broad initial screen followed by extra generations only for questions close to the two-and-two threshold. Freeze any such continuation rule and total budget before the next batch starts. Do not report adaptive-screen estimates as an unbiased independent evaluation; final intervention comparisons must use a separately frozen eligible set and preserve independent-question counts.

The selection and exact budget for Batch04 remain pending Batch03 completion, manual audit, and prefix-yield analysis. No Batch04 job is launched by this decision record.
