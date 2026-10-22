from pathlib import Path
import subprocess
import tempfile
import unicodedata
import re
import difflib

root=Path(__file__).resolve().parents[1]
paper=root/'texts/iclr-2027-style-files/iclr2027'
names=['contextual_drag_continued_access.pdf','After_Error_Feedback__Continued_Access_to_Failed_Reasoning_Contributes_to_Contextual_Drag.pdf']
texts=[]
for name in names:
    result=subprocess.run([r'C:\texlive\2024\bin\windows\pdftotext.exe','-layout',str(paper/name),'-'],capture_output=True,check=True)
    text=result.stdout.decode('utf-8')
    pages=text.split('\f')
    clean=[]
    for page in pages:
        for line in page.splitlines():
            line=re.sub(r'^\s*\d+\s+','',line)
            if re.fullmatch(r'\s*\d*\s*',line) or 'Under review as a conference paper' in line:
                continue
            clean.append(line.strip())
    text='\n'.join(clean)
    text=unicodedata.normalize('NFKD',text).lower()
    text=''.join(c for c in text if c.isalnum())
    texts.append(text)
matcher=difflib.SequenceMatcher(None,*texts,autojunk=False)
changes=[]
for tag,a,b,c,d in matcher.get_opcodes():
    if tag!='equal':
        changes.append({'kind':tag,'local':texts[0][max(0,a-45):min(len(texts[0]),b+45)],'overleaf':texts[1][max(0,c-45):min(len(texts[1]),d+45)]})
print('Normalized character lengths:',list(map(len,texts)))
print('Similarity:',matcher.ratio())
print('Differences:',len(changes))
for item in changes[:35]: print(ascii(item))
