"""Apply the completed-run manuscript update; save the pre-update source."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
paper=ROOT/'texts/iclr-2027-style-files/iclr2027/contextual_drag_continued_access.tex'
rev=ROOT/'texts/revisions/iclr2027_20260925_completed'
rev.mkdir(parents=True,exist_ok=True)
t=paper.read_text(encoding='utf-8')
if (rev/'manuscript_before.tex').exists():
    raise SystemExit('Integration already applied; edit the current manuscript directly.')
(rev/'manuscript_before.tex').write_text(t,encoding='utf-8')
(rev/'abstract_before.txt').write_text(re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',t,re.S).group(1).strip()+'\n',encoding='utf-8')
replacements={
'Across 15 Game24 questions and two seeds per question, Qwen3-8B accuracy is 25/30 without a draft, 10/30 with full access to a failed draft, and 24/30 when generation-time access is blocked. The paired access effect is +46.7 percentage points (95\\% question-cluster bootstrap interval: +26.7 to +66.7). Qwen3-32B and Gemma 4 E4B show smaller positive effects on the same questions;':
'Across 23 Game24 questions and two seeds per question, Qwen3-8B accuracy is 40/46 without a draft, 18/46 with full access to a failed draft, and 36/46 when generation-time access is blocked. The paired access effect is +39.1 percentage points (95\\% question-cluster bootstrap interval: +23.9 to +54.3). Qwen3-32B and Gemma 4 E4B show positive effects on a shared 15-question subset;',
'Qwen3-8B solves 25/30 trials without a draft, 10/30 with full access to a failed draft, and 24/30 under late access blocking.':
'Qwen3-8B solves 40/46 trials without a draft, 18/46 with full access to a failed draft, and 36/46 under late access blocking.',
'Qwen3-8B has R0--R4 results;':'Qwen3-8B has R0, R2, R3, and R4 results;',
'We evaluate 15 distinct Game24 questions, each with one failed draft and two paired seeds.':'We evaluate 23 distinct Game24 questions with Qwen3-8B, each with one failed draft and two paired seeds; Qwen3-32B and Gemma 4 E4B cover a shared 15-question subset.',
'the other 14 meet the final rule.':'the other 22 meet the final rule.',
'The frozen draft for a question is shared across the three target models.':'The frozen draft for a question is shared wherever multiple target models are evaluated. Eight questions come from the completed prefix of a screening run stopped for runtime reasons: 22 of 32 candidates had complete dual-model screening, and all eight eligible completed candidates were evaluated. The ten incomplete candidates were excluded. This limits coverage and may favor shorter or faster screening trajectories.',
'covers eight of the 15 Game24 questions':'covers eight of the 23 Game24 questions',
'the failed-history prompt scores 10/30 versus 25/30 in clean context':'the failed-history prompt scores 18/46 versus 40/46 in clean context',
'The observed drag is 50.0 percentage points (95\\% interval: 33.3 to 66.7).':'The observed drag is 47.8 percentage points (95\\% interval: 34.8 to 60.9).',
'Qwen3-32B and Gemma 4 E4B also show losses, respectively':'On the shared 15-question subset, Qwen3-32B and Gemma 4 E4B also show losses, respectively',
"R3 preserves the full prompt and its prefill computation, yet raises Qwen3-8B accuracy from 10/30 to 24/30. The 46.7-point access effect [26.7, 66.7] recovers most of the 50.0-point loss observed in R2. Paired outcomes clarify the change: 16 trials move from wrong to correct, two from correct to wrong, eight remain correct, and four remain wrong. R3 is 3.3 points below R0, with an interval of $[-23.3,16.7]$ points; this is not an equivalence test or evidence of complete restoration.":
"R3 preserves the full prompt and its prefill computation, yet raises Qwen3-8B accuracy from 18/46 to 36/46. The 39.1-point access effect [23.9, 54.3] recovers 18 of the 22 net successes lost in R2 (81.8\\%, descriptively). Paired outcomes clarify the change: 21 trials move from wrong to correct, three from correct to wrong, 15 remain correct, and seven remain wrong. R3 is 8.7 points below R0, with an interval of $[-23.9,4.3]$ points; this is not an equivalence test or evidence of complete restoration. Excluding question 381, whose failed draft also contains a correct intermediate alternative, leaves a 38.6-point effect [22.7, 54.5] over 22 questions (Appendix~\\ref{app:coverage}).",
'The three Game24 target models share 15 questions, while the correct-history control uses an eight-question subset.':'Qwen3-8B covers 23 Game24 questions; the other targets cover a shared 15-question subset, and the correct-history control covers eight questions.',
'Game24 accuracy on the same 15 questions, with two seeds per condition.':'Game24 accuracy with two seeds per condition: 23 questions for Qwen3-8B and a shared 15-question subset for the other targets.',
'Qwen3-8B & 25/30 & 10/30 & 24/30 & $+46.7$ [$+26.7,+66.7$]':'Qwen3-8B & 40/46 & 18/46 & 36/46 & $+39.1$ [$+23.9,+54.3$]',
'On the same questions and source drafts, Qwen3-32B gains':'On the shared 15 questions and source drafts, Qwen3-8B gains 46.7 points [26.7, 66.7]. Qwen3-32B gains',
'rather than a comparison with the full 15-question effect.':'rather than a comparison with the full 23-question effect.',
"On Game24 with Qwen3-8B, it scores 22/30 versus R3's 24/30, giving $R4-R3=-6.7$ points [${-30.0},{+13.3}$].":
"On Game24 with Qwen3-8B, it scores 35/46 versus R3's 36/46, giving $R4-R3=-2.2$ points [${-17.4},{+13.0}$].",
'Its 15 Game24 questions are selected for mixed baseline outcomes;':'Its 23 Game24 questions are selected for mixed baseline outcomes;',
'the protocol developed across collection batches, and bootstrap intervals do not capture that selection or adaptation.':'the protocol developed across collection batches, and a runtime stop left ten screening candidates incomplete. Bootstrap intervals do not capture that selection or adaptation.',
'The 15 Game24 questions are distinct,':'The 23 Game24 questions are distinct,',
'Fourteen questions meet the final two-correct/two-failure rule;':'Twenty-two questions meet the final two-correct/two-failure rule;',
'Table~\\ref{tab:diagnostics} reports all 460 completed scientific requests used in the paper.':'Table~\\ref{tab:diagnostics} reports all 524 completed scientific requests used in the paper.',
'whereas two length-stopped outputs across the full dataset have an extracted answer scored incorrect.':'whereas four length-stopped outputs across the full dataset have an extracted answer scored incorrect.',
'Game24 & 22/30 & $+40.0$ [$+20.0,+60.0$] & $-6.7$ [$-30.0,+13.3$]':'Game24 & 35/46 & $+37.0$ [$+21.7,+52.2$] & $-2.2$ [$-17.4,+13.0$]',
'match for all 30 paired units per model. The Qwen3-8B R2/R3 transitions are 16 wrong-to-correct, two correct-to-wrong, eight both correct, and four both wrong.':'match for all 46 Qwen3-8B paired units and all 30 units per other target model. The Qwen3-8B R2/R3 transitions are 21 wrong-to-correct, three correct-to-wrong, 15 both correct, and seven both wrong.',
'../../../runs/iclr2027_evidence_20260925/game24_per_question.tex':'../../../runs/iclr2027_evidence_20260925_completed/game24_per_question.tex',
'an estimate for all 15 questions.':'an estimate for all 23 questions.',
}
for before,after in replacements.items():
    assert before in t,before
    t=t.replace(before,after)
addition=r'''
\section{Coverage and Draft-Content Sensitivity}
\label{app:coverage}

The eight questions from the completed screening prefix contribute all 64 planned outputs, using fresh R0 generations and the same seeds, decoding, and scoring as the earlier evaluation. R0/R2/R3/R4 score 15/16, 8/16, 12/16, and 13/16. Their R3--R2 effect is 25.0 points [0.0, 43.8], with five wrong-to-correct and one correct-to-wrong transition. Thus this extension agrees in direction but has a smaller and less precise effect than the shared 15-question subset. Its two length-stopped outputs are scored incorrect and remain in the denominators. All 64 extracted final expressions were checked with exact arithmetic and input-multiset verification, agreeing with their persisted scores.

Before generation, we specified a sensitivity analysis excluding question 381 because its fixed source draft contains a correct intermediate expression but explicitly selects an invalid final expression. Excluding it leaves R0/R2/R3/R4 at 38/44, 17/44, 34/44, and 33/44 over 22 questions. The access effect remains 38.6 points [22.7, 54.5]. Within the eight-question extension alone, exclusion leaves 13/14, 7/14, 10/14, and 11/14, with an access effect of 21.4 points [$-7.1$, 42.9]. This smaller subset remains uncertain; the pooled conclusion does not depend on the mixed-content draft. No draft was replaced after observing intervention outcomes.

'''
t=t.replace('\\section{Additional Behavioral Analysis}',addition+'\\section{Additional Behavioral Analysis}')
paper.write_text(t,encoding='utf-8')
print('Updated manuscript; original source and abstract preserved in',rev)
