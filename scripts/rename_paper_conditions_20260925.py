"""Update manuscript display names without changing experiment identifiers."""
from pathlib import Path
import re
import sys
import json
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'texts/iclr-2027-style-files/iclr2027'
DECK = ROOT / 'texts/iclr2027_editable_figures_ppt169_20260925'
PPT = DECK / 'exports/iclr2027_figures_editable.pptx'
NAMES = {'R0': 'Clean', 'R2': 'Full', 'R3': 'LateBlock', 'R4': 'PathBlock'}
MACROS = {'R0': r'\clean{}', 'R2': r'\fullaccess{}', 'R3': r'\lateblock{}', 'R4': r'\pathblock{}'}

if sys.argv[1] == 'inspect':
    with zipfile.ZipFile(PPT) as z:
        for name in z.namelist():
            if re.match(r'ppt/slides/slide\d+.xml$', name):
                tree = ET.fromstring(z.read(name))
                print(name, ascii(' | '.join(e.text or '' for e in tree.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'))))
                if name.endswith('slide1.xml'):
                    ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main', 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                    for sp in tree.findall('.//p:sp', ns):
                        tx = ''.join(e.text or '' for e in sp.findall('.//a:t', ns))
                        if sp.find('p:nvSpPr/p:cNvPr', ns).get('id') in ('45','47','117','119'):
                            print(ET.tostring(sp, encoding='unicode'))
elif sys.argv[1] == 'ppt':
    import win32com.client
    import shutil
    app = win32com.client.DispatchEx('PowerPoint.Application')
    pres = None
    try:
        pres = app.Presentations.Open(str(PPT), ReadOnly=False, Untitled=False, WithWindow=False)
        def visit(shapes):
            for i in range(shapes.Count, 0, -1):
                shape = shapes.Item(i)
                if slide.SlideIndex == 1 and shape.Name in ('Rectangle 45', 'Line 47', 'Rectangle 117', 'Line 119'):
                    shape.Delete()
                    continue
                if shape.Type == 6:
                    visit(shape.GroupItems)
                if shape.HasTextFrame and shape.TextFrame.HasText:
                    tr = shape.TextFrame.TextRange
                    old = tr.Text
                    if old in ('R2', 'R3'):
                        shape.Delete()
                    elif old == 'Full continued access':
                        tr.Text = 'Full'
                        shape.Left = 590
                    elif old == 'Late access blocking':
                        tr.Text = 'LateBlock'
                        if slide.SlideIndex == 1:
                            shape.Left = 590
                    elif 'Accuracy: blocked' in old:
                        tr.Text = 'Accuracy: LateBlock \u2212 Full (pp)'
        for slide in pres.Slides:
            visit(slide.Shapes)
        pres.Save()
        pres.Slides(1).Export(str(PAPER / 'figure1_temp.png'), 'PNG', 1672, 987)
        pres.Slides(1).Export(str(DECK / 'previews/figure1_editable.png'), 'PNG', 1672, 987)
        pres.Slides(2).Export(str(DECK / 'previews/figure2_editable.png'), 'PNG', 1672, 987)
    finally:
        if pres is not None:
            pres.Close()
        app.Quit()
    print('Updated editable PPT and exported Figure 1 directly from PowerPoint.')
elif sys.argv[1] == 'text':
    if 'Condition names and artifact IDs.' in (PAPER / 'contextual_drag_continued_access.tex').read_text(encoding='utf-8'):
        raise SystemExit('Display names already migrated; refusing to modify artifact-ID mapping.')
    for name in ['contextual_drag_continued_access.tex', 'generation_diagnostics_10pt.tex', 'generation_diagnostics.tex', 'game24_per_question_10pt.tex']:
        path = PAPER / name
        s = path.read_text(encoding='utf-8')
        s = s.replace('R2--R4', 'R2, R3, and R4')
        # Use the same readable names in prose and math mode.
        for old, macro in MACROS.items():
            s = re.sub(r'\b' + old + r'\b', lambda m: macro, s)
        if name == 'contextual_drag_continued_access.tex':
            for macro, label in [('clean', 'Clean'), ('fullaccess', 'Full'), ('lateblock', 'LateBlock'), ('pathblock', 'PathBlock')]:
                s = s.replace('\\newcommand{\\' + macro + r'}{\textsc{' + label + '}}', '\\newcommand{\\' + macro + r'}{\ifmmode\mathrm{' + label + r'}\else\textup{' + label + r'}\fi}')
            s = s.replace('ID & History & Prefill access & Later access to draft', 'Condition & History & Prefill access & Later draft access')
            s = s.replace('Blocked for generated queries', 'Blocked')
            s = s.replace(r'$\lateblock{}-\fullaccess{}$ [95\% CI]', r'$\Delta_{\mathrm{access}}$ [95\% CI]')
            s = s.replace(r'\pathblock{} correct & $\pathblock{}-\fullaccess{}$ [95\% CI] & $\pathblock{}-\lateblock{}$ [95\% CI]', r'\pathblock{} & $\Delta_{\mathrm{path}}$ [95\% CI] & $\Delta_{\mathrm{early}}$ [95\% CI]')
            marker = r'\label{app:details}'
            s = s.replace(marker, marker + '\n\n' + r'\paragraph{Condition names and artifact IDs.}' + '\n' + r'The display names \clean{}, \fullaccess{}, \lateblock{}, and \pathblock{} correspond to internal artifact IDs \texttt{R0}, \texttt{R2}, \texttt{R3}, and \texttt{R4}, respectively. These IDs are retained in code and persisted results. Unless explicitly labeled as a correct-history control, \fullaccess{}, \lateblock{}, and \pathblock{} use a failed draft with explicit error feedback.' + '\n')
            s = s.replace('width=\\textwidth,trim=18bp 72bp 18bp 72bp,clip', 'width=\\textwidth')
        path.write_text(s, encoding='utf-8')
    plot = ROOT / 'scripts/plot_iclr2027_question_recovery_20260925.py'
    s = plot.read_text(encoding='utf-8').replace('label="R2: full access"', 'label="Full"').replace('label="R3: late access blocking"', 'label="LateBlock"')
    plot.write_text(s, encoding='utf-8')
    plot = ROOT / 'scripts/plot_iclr2027_access_effects_20260925.py'
    s = plot.read_text(encoding='utf-8').replace('Accuracy: blocked − full access (pp)', 'Accuracy: LateBlock − Full (pp)')
    plot.write_text(s, encoding='utf-8')
    print('Updated manuscript, local tables, and plot display labels.')
elif sys.argv[1] == 'finish':
    path = PAPER / 'contextual_drag_continued_access.tex'
    s = path.read_text(encoding='utf-8')
    s = s.replace(r'\clean{}/\fullaccess{}/\lateblock{}/\pathblock{}', r'\clean{}, \fullaccess{}, \lateblock{}, and \pathblock{}')
    s = s.replace(r'The error label and decoding settings are also fixed, so \fullaccess{}/\lateblock{} differ', r'The error label and decoding settings are also fixed, so \fullaccess{} and \lateblock{} differ')
    s = s.replace(r'The \clean{}/\fullaccess{} comparison', r'The comparison between \clean{} and \fullaccess{}')
    s = s.replace(r'The \fullaccess{}/\lateblock{} comparison', r'The comparison between \fullaccess{} and \lateblock{}')
    s = s.replace(r'$\clean{}>\fullaccess{}$', r'$\operatorname{Acc}(\clean{})>\operatorname{Acc}(\fullaccess{})$')
    s = s.replace(r'The secondary contrast $\pathblock{}-\lateblock{}$', r'The secondary contrast between \pathblock{} and \lateblock{}')
    s = s.replace(r'$\pathblock{}-\lateblock{}=-2.2$', r'$\operatorname{Acc}(\pathblock{})-\operatorname{Acc}(\lateblock{})=-2.2$')
    path.write_text(s, encoding='utf-8')
    path = PAPER / 'game24_per_question_10pt.tex'
    s = path.read_text(encoding='utf-8')
    start = s.index(r'\caption{')
    end = s.index('\n', start)
    s = s[:start] + r'\caption{Game24 correct counts per question. Each count is out of two seeds. Counts are ordered as \clean{}, \fullaccess{}, \lateblock{}, and \pathblock{} for Qwen3-8B (23 questions). The other models cover the shared 15-question subset and report the first three conditions in the same order. A dash denotes an unevaluated model--question combination.}' + s[end:]
    path.write_text(s, encoding='utf-8')
    path = DECK / 'verify_and_render.py'
    s = path.read_text(encoding='utf-8').replace("assert 'Full continued access' in text and 'Late access blocking' in text", "assert 'Full' in text and 'LateBlock' in text")
    path.write_text(s, encoding='utf-8')
    (DECK / 'CONDITION_NAMES.md').write_text('''# Current figure source\n\nFigure 1 is edited in `exports/iclr2027_figures_editable.pptx` and exported directly by PowerPoint to the manuscript `figure1_temp.png`. Its two branches use Full and LateBlock. The older SVG reconstruction and timestamped deck are historical sources, not the current Figure 1 editing source.\n\nThe manuscript Figure 2 and Figure 3 are generated by `scripts/plot_iclr2027_access_effects_20260925.py` and `scripts/plot_iclr2027_question_recovery_20260925.py`. The second slide of this deck remains the earlier 15-question Figure 2 illustration; it is not the current manuscript Figure 2.\n\nDisplay mapping: Clean = R0, Full = R2, LateBlock = R3, PathBlock = R4. Experiment IDs and recorded outcomes are unchanged.\n''', encoding='utf-8')
    print('Finished prose, count-order caption, and editable-figure source notes.')
