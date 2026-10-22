"""Package the current manuscript with only its local LaTeX dependencies."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'texts/iclr-2027-style-files/iclr2027'
ARCHIVE = ROOT / 'texts/iclr2027_overleaf.zip'
FILES = [
    'contextual_drag_continued_access.bib',
    'iclr2027_conference.sty', 'iclr2027_conference.bst',
    'math_commands.tex', 'natbib.sty', 'fancyhdr.sty',
    'figure1_temp.png', 'figure2_access_effects.pdf',
    'figure3_question_level_recovery.pdf',
    'generation_diagnostics_10pt.tex', 'game24_per_question_10pt.tex',
]
source = (PAPER/'contextual_drag_continued_access.tex').read_text(encoding='utf-8')
payload = {name:(PAPER/name).read_bytes() for name in FILES}
payload['main.tex'] = source.encode('utf-8')
payload['latexmkrc'] = (PAPER/'latexmkrc').read_bytes()
payload['README.md'] = b'''# Overleaf manuscript project

Upload this ZIP as a new project. All project files are at the archive root.

- Main document: main.tex
- Compiler: pdfLaTeX
- TeX Live version: 2024, to match the local manuscript build
- Bibliography: BibTeX with iclr2027_conference.bst

The latexmkrc requests pdfLaTeX. Confirm the compiler and TeX Live version in
the project settings after import. The local manuscript ends its Conclusion
on page 9. Compare that page after the first Overleaf compilation, since the
remote environment has not been executed during packaging.

This project contains the current manuscript and every local input, figure,
bibliography, and bundled style dependency. It does not need the experiment
repository or any parent-directory paths. main.tex is the upload name of
contextual_drag_continued_access.tex; its contents are unchanged.
The supplementary code artifact is a separate submission file.
'''
for name, data in payload.items():
    if name.endswith(('.tex','.sty')):
        text = data.decode('utf-8')
        if re.search(r'\\(?:input|include|includegraphics)(?:\[[^\]]*\])?\{[^}]*\.\./', text):
            raise RuntimeError('External relative dependency in '+name)
for command, path in re.findall(r'\\(input|includegraphics|bibliography|bibliographystyle)(?:\[[^\]]*\])?\{([^}]+)\}', source):
    suffix = {'bibliography':'.bib','bibliographystyle':'.bst'}.get(command,'')
    if path + suffix not in payload:
        raise RuntimeError('Missing dependency: '+path+suffix)
with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name,data in payload.items():
        archive.writestr(name,data)
print(json.dumps({'archive':str(ARCHIVE.relative_to(ROOT)), 'files':list(payload),
                  'bytes':ARCHIVE.stat().st_size,
                  'sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()},indent=2))
