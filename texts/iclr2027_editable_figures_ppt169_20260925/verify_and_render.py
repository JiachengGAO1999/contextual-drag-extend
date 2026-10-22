from pathlib import Path
import json, zipfile, xml.etree.ElementTree as ET, csv, shutil
import win32com.client

root = Path(__file__).resolve().parent
pptx = max((root/'exports').glob('*.pptx'), key=lambda p:p.stat().st_mtime)
delivery = root/'exports/iclr2027_figures_editable.pptx'
if pptx != delivery:
    shutil.copy2(pptx, delivery)
pptx = delivery
ns = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main', 'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
report = {'pptx':str(pptx), 'slides':[], 'rendered':False}
svg = ET.parse(root/'svg_output/02_access_effects.svg').getroot()
keys = ['qwen8-game24','qwen32-game24','gemma-game24','math500','math-train','correct-history']
with (root/'sources/figure2_access_effects.csv').open(encoding='utf-8') as f:
    for key, row in zip(keys, csv.DictReader(f)):
        point = svg.find(f".//*[@id='{key}-estimate']")
        ci = svg.find(f".//*[@id='{key}-ci']")
        actual = float(point.attrib.get('cx', float(point.attrib.get('x',0))+10))
        expected = lambda value: 546.48+(float(value)+45)/148*633.6
        assert abs(actual-expected(row['effect_pp']))<0.001
        assert abs(float(ci.attrib['x1'])-expected(row['low_pp']))<0.001
        assert abs(float(ci.attrib['x2'])-expected(row['high_pp']))<0.001
report['chart_coordinates_match_source_csv'] = True
report['chart_max_tolerance_source_pixels'] = 0.001
with zipfile.ZipFile(pptx) as z:
    media = [p for p in z.namelist() if p.startswith('ppt/media/')]
    assert not media, media
    for i in [1,2]:
        tree=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
        text=[e.text for e in tree.findall('.//a:t',ns)]
        shapes=len(tree.findall('.//p:sp',ns))
        pics=len(tree.findall('.//p:pic',ns))
        assert shapes>40 and pics==0
        if i==1:
            assert 'Full' in text and 'LateBlock' in text
        else:
            assert '+46.7 [+26.7, +66.7]' in text and '-18.8 [-37.5, -6.2]' in text
        report['slides'].append(dict(slide=i,native_shapes=shapes,editable_text_objects=len(tree.findall('.//p:txBody',ns)),pictures=pics,groups=len(tree.findall('.//p:grpSp',ns))))
preview=root/'previews'
preview.mkdir(exist_ok=True)
app=win32com.client.DispatchEx('PowerPoint.Application')
pres=None
try:
    pres=app.Presentations.Open(str(pptx), ReadOnly=True, Untitled=False, WithWindow=False)
    for i in [1,2]:
        pres.Slides(i).Export(str(preview/f'figure{i}_editable.png'),'PNG',1672,987)
    report['rendered']=True
finally:
    if pres is not None: pres.Close()
    app.Quit()
(root/'validation/editability_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
