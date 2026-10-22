from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
path = root / 'texts/iclr-2027-style-files/iclr2027/contextual_drag_continued_access.tex'
s = path.read_text(encoding='utf-8')
s = s.replace(r'\hypersetup{hidelinks}', r'''\definecolor{paperlink}{RGB}{0,65,125}
\hypersetup{colorlinks=true,linkcolor=paperlink,citecolor=paperlink,urlcolor=paperlink}''')
abstract = r'''Iterative LLM workflows retain previous attempts to support revision after feedback. Yet failed attempts can reduce accuracy on subsequent solutions, a phenomenon known as contextual drag. We ask whether this interference depends on continued access to the failed attempt after the model has processed it and received explicit error feedback. We introduce a same-text attention intervention that preserves the full prompt, token positions, prefill computation, and first-token logits, while blocking only later generated queries from attending to the failed draft. On 23 selected Game24 questions, Qwen3-8B accuracy falls from 87.0\% in clean context to 39.1\% with full access to a failed draft, then recovers to 78.3\% when later access is blocked, a +39.1 percentage-point effect (95\% question-cluster bootstrap interval: +23.9 to +54.3). Additional models and two MATH settings show the same direction. Blocking verified correct history instead lowers accuracy, showing that the access effect depends on the retained history and its feedback. These results identify a causal contribution of continued direct access to contextual drag after full initial exposure and explicit error feedback.'''
s = re.sub(r'(?<=\\begin\{abstract\})[\s\S]*?(?=\\end\{abstract\})', lambda m: '\n'+abstract+'\n', s)
start = s.index('Many LLM workflows')
end = s.index('These two stages', start)
s = s[:start] + r'''Iterative LLM workflows often retain previous attempts so that a model can revise its solution after feedback. Self-refinement and agents with verbal feedback use this history to guide later attempts~\citep{madaan2023selfrefine,shinn2023reflexion}. Retaining prior work can preserve useful reasoning, but also exposes the next solution to errors from earlier attempts. Understanding when this history helps or interferes is therefore important for deciding how models should use context during revision.

\citet{cheng2026contextualdrag} call the loss in subsequent reasoning performance caused by failed in-context attempts \emph{contextual drag}. They show that this interference can persist even when the failure is explicitly identified. Error feedback tells a model that the previous answer is wrong, but leaves the failed reasoning available to the computation that produces the next answer. This raises our central question: after a model has processed a failed trace, does continued direct access to that trace contribute to the loss? We distinguish initial processing of the trace from access to it during later generation.

''' + s[end:]
start = s.index(r'\section{Discussion}')
end = s.index(r'\section{Related Work}', start)
s = s[:start] + r'''\section{Analysis}
\label{sec:discussion}

\subsection{What the access contrast identifies}
The comparison between \fullaccess{} and \lateblock{} shows that processing a failed trace does not fully determine its effect on the next solution. Even after identical prefill computation and the same first sampled token, changing later direct access changes accuracy. Continued direct access therefore makes a causal contribution under the evaluated conditions. The error feedback is supplied externally, so this result concerns the model's response to known failure rather than its ability to recognize an error.

The clean baseline answers a complementary question. Comparing \clean{} with \fullaccess{} establishes a loss associated with the failed-history prompt, but changes both initial processing and later access. Comparing \lateblock{} with \fullaccess{} holds initial processing fixed and intervenes on later access. Their effect sizes are therefore not an additive decomposition of contextual drag into exposure and access components. Recovery of much of the clean-context gap does not measure the fraction of erroneous information removed from the model.

The paired outcomes also distinguish aggregate recovery from uniform improvement. Across the 46 Qwen3-8B Game24 pairs, late blocking changes 21 incorrect outputs to correct ones and three correct outputs to incorrect ones. The remaining pairs contain 15 shared successes and seven shared failures (Table~\ref{tab:game24-per-question}). The net gain thus coexists with individual losses and persistent failures. Figure~\ref{fig:question-level-recovery} shows how these outcomes are distributed across questions. This pattern supports an average benefit on the selected set without implying that access should be blocked for every request.

\subsection{History dependence of the access effect}
The correct-history comparison tests whether the benefit extends to useful prior reasoning. On the same eight questions, the failed-history access effect is $+37.5$ points, whereas the correct-history effect is $-18.75$ points. The resulting interaction is $+56.2$ points (Section~\ref{sec:specificity}). Comparing the same questions avoids attributing the reversal to a difference in question composition. The small control set nevertheless limits how precisely this dependence can be characterized.

Within each history type, \fullaccess{} and \lateblock{} receive the same feedback label. Across history types, both the draft and its truthful label change. The interaction therefore concerns the draft--feedback combination, rather than correctness as an isolated property. Matching drafts by character length does not equate their token counts, reasoning paths, or useful intermediate content. The reversal motivates selective access, but the final-answer label alone cannot locate every useful or harmful step in a draft.

An output-level audit on these eight questions provides a complementary behavioral measure. After normalization, the extracted final expression exactly repeats the frozen failed expression in 9/16 \fullaccess{} outputs, 2/16 \lateblock{} outputs, and 1/16 \pathblock{} outputs. Reduced reuse accompanies improved accuracy, connecting the access intervention to a visible change in the final answer. This measure does not classify algebraically equivalent expressions or shared reasoning routes. It therefore describes output persistence without establishing an internal copying mechanism or an estimate for all 23 questions.

\subsection{Scope of the intervention}
\lateblock{} preserves full prefill computation, so unblocked prompt states can carry draft-derived information into generation. Retaining these possible indirect routes makes the comparison informative about access after exposure. Once generation proceeds, the conditions can produce different tokens and states. The measured effect includes these downstream consequences of changing the access rule across layers and generation steps.

Blocking draft keys also changes the set of positions over which attention is normalized. The relative contribution of the problem, feedback, and generated prefix can therefore change even though their keys remain available. Improved accuracy may reflect reduced use of misleading draft information, increased use of other context, or both. These changes are consequences of the access intervention. The comparison identifies their combined effect on accuracy without separating their internal contributions. A matched irrelevant-history control could test whether the benefit depends on the draft's relationship to the current problem.

\pathblock{} additionally blocks post-draft prompt queries, changing the suffix computation during prefill as well as later access. Its comparison with \lateblock{} evaluates this earlier-starting access policy. Table~\ref{tab:r4} shows no consistent additional gain, although the intervals allow both benefits and harms. Recovery with \lateblock{} establishes that the earlier restriction is unnecessary for the observed improvement. The comparison does not establish equivalence between the policies or show that initial processing is irrelevant.

The results motivate testing selective access within histories that contain both useful and erroneous steps. Such experiments would need to control span length, position, and feedback, and select spans without consulting later outcomes. Holding a draft fixed while varying feedback would separately test how labels change the access effect. Practical use would also require evaluating span selection, runtime, memory, and task performance.

''' + s[end:]
# The behavioral evidence is now analyzed in the main text rather than duplicated.
start = s.index(r'\section{Additional Behavioral Analysis}')
end = s.index(r'\section{Data Availability}', start)
s = s[:start] + s[end:]
s = s.replace('\n\\appendix\n', '\n\\clearpage\n\\appendix\n')
# Use the existing figure label rather than introducing a new label.
labels = re.findall(r'\\label\{([^}]+)\}', s)
figure_label = next(x for x in labels if 'question' in x and x.startswith('fig:'))
s = s.replace('fig:question-level-recovery', figure_label)
path.write_text(s, encoding='utf-8')
(root / 'texts/abstract.txt').write_text(abstract.replace(r'\%', '%')+'\n', encoding='utf-8')
print('Revised main manuscript and synchronized abstract.txt')
