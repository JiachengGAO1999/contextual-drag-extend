import json
from pathlib import Path
from transformers import AutoTokenizer
from selective_context.phase0.thinking_pilot import independent_prompt
from selective_context.prompting import (render_chat_prompt, encode_direct_prompt, encode_prompt,
    make_request, make_r2_r4_requests, persist_request_bundle, assert_same_text_contract)
from selective_context.schema import AccessMode
from selective_context.vllm_mask import request_metadata

root=Path(__file__).resolve().parents[1]
out=root/'outputs/game24-dual-anchor-validation-20260918-prepared'
tok=AutoTokenizer.from_pretrained('/data2/huangrj/models/qwen3-8b',local_files_only=True,use_fast=True)
rows=[json.loads(l) for l in (out/'pairs.jsonl').read_text().splitlines()]
assert len(rows)==7
manifest=[]; checks=[]
for row in rows:
    pair=out/'pairs'/f"{row['id']}.json"
    pair.parent.mkdir(exist_ok=True)
    pair.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    for seed in [927001,927002]:
        direct=encode_direct_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem']),True))
        full=encode_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem'],row['traj1']),True))
        requests=make_r2_r4_requests(full,seed)
        assert_same_text_contract(requests)
        assert full.text[slice(*full.draft_character_span)]==row['traj1']
        assert len(full.input_ids)<32768
        for suffix,enc,reqs in [('r0',direct,[make_request(direct,'R0',AccessMode.FULL,seed)]),('r2_r4',full,requests)]:
            bundle=out/'bundles'/f"{row['id']}.{seed}.{suffix}.json"
            persist_request_bundle(bundle,enc,reqs)
            for req in reqs:
                req.validate()
                checks.append(dict(id=row['id'],seed=seed,condition=req.condition_id,
                    tokens=len(req.input_ids),draft_span=req.draft_token_span,
                    spillover=enc.boundary_spillover,metadata=request_metadata(req)))
                manifest.append(dict(bundle=bundle.relative_to(root).as_posix(),
                    pair=pair.relative_to(root).as_posix(),condition=req.condition_id))
assert len(manifest)==56
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(out/'preflight.json').write_text(json.dumps(dict(passed=True,requests=56,checks=checks,
    prompt='thinking_pilot.independent_prompt, unchanged',late_first_token='full prefill logits',
    mask='whole draft logical attention blocking; positions unchanged'),indent=2),encoding='utf-8')
print('PREFLIGHT_PASSED requests=56')
