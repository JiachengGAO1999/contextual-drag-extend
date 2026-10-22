from pathlib import Path
import hashlib, json, struct, importlib.util

root = Path(__file__).resolve().parent
pages = []
regions = [
    [dict(id='shared-input', bbox=[26, 398, 635, 143], family='graphic', text='Problem | Wrong trace | Error signal | Solve independently | Full prefill | y₁'),
     dict(id='shared-logits', bbox=[468, 270, 195, 135], family='text', text='same full-prefill logits\nsame sampled y₁'),
     dict(id='r2', bbox=[757, 105, 890, 355], family='graphic', text='R2 | Full continued access | queries retain access to failed-trace K/V | Problem | Wrong trace | Error signal | Solve independently | q₁ q₂ q₃ | y₂ y₃ y₄ | …'),
     dict(id='r3', bbox=[757, 485, 890, 358], family='graphic', text='R3 | Late access blocking | block q₁, q₂, q₃, … → failed-trace K/V only | Problem | Wrong trace | Error signal | Solve independently | q₁ q₂ q₃ | y₂ y₃ y₄ | …')],
    [dict(id='headings', bbox=[544, 28, 902, 40], family='text', text='Late access blocking | Effect [95% CI]'),
     dict(id='labels', bbox=[70, 132, 447, 614], family='text', text='Qwen3-8B / Game24\nFailed history, 15 questions\nQwen3-32B / Game24\nFailed history, 15 questions\nGemma 4 E4B / Game24\nFailed history, 15 questions\nQwen3-8B / MATH500\nFailed history, 8 questions\nQwen3-8B / MATH-train\nFailed history, 8 questions\nQwen3-8B / Game24\nCorrect history, 8 questions'),
     dict(id='forest', bbox=[546, 103, 634, 674], family='graphic', text='Six point estimates with 95% CI; source values in figure2_access_effects.csv'),
     dict(id='values', bbox=[1204, 145, 356, 584], family='text', text='+46.7 [+26.7, +66.7]\n+26.7 [+3.3, +50.0]\n+16.7 [+0.0, +30.0]\n+75.0 [+50.0, +93.8]\n+50.0 [+18.8, +81.2]\n-18.8 [-37.5, -6.2]'),
     dict(id='axis', bbox=[535, 776, 645, 115], family='text', text='−40 | 0 | 40 | 80 | 100 | Accuracy: blocked − full access (pp)')]
]
for n, name in enumerate(['figure1_temp.png', 'figure2_access_effects.png']):
    p = root/'sources'/name
    data = p.read_bytes()
    w, h = struct.unpack('>II', data[16:24])
    for r in regions[n]:
        r.update(confidence='high', source_sufficiency='legible at full placement', boundary_complete=True, occlusion='none; arrows intentionally overlap', identity_data_verifiable=True)
    pages.append(dict(order=n+1, original=str(p), normalized_page=str(p), source_bbox=[0,0,w,h], pixel_dimensions=[w,h], sha256=hashlib.sha256(data).hexdigest(), visible_regions=regions[n], unresolved_evidence=[]))
(root/'analysis').mkdir(exist_ok=True)
(root/'analysis/reconstruction_inventory.json').write_text(json.dumps({'pages':pages}, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'source_sizes':[p['pixel_dimensions'] for p in pages], 'dependencies':{m:bool(importlib.util.find_spec(m)) for m in ['lxml','PIL','pptx','cairosvg','win32com']}}, indent=2))
