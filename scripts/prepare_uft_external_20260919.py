"""Freeze reviewed UFT stimuli locally; tokenize on the server without generation."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/game24-uft-external-20q-20260919-prepared'
NOTES={
'510':'Final value9, claimed24; steps end21 and differ from final expression.',
'724':'Final value0, claimed24; introduces9 and omits8; steps end12.',
'507':'Consistent arithmetic ends20 rather than target24.',
'176':'Final value144, claimed24; steps also end144.',
'792':'Final value32, claimed24; steps end12 on another route.',
'856':'Consistent arithmetic ends30 rather than target24.',
'476':'Final value20, claimed24; introduces10; steps end10.',
'322':'Final equals24 but duplicates1 and omits one12; remaining-number state invalid.',
'414':'Consistent arithmetic ends6.5 rather than target24.',
'121':'Final value36, claimed24; intermediate remaining-number states invalid.',
'752':'Final value20, claimed24; steps end20.',
'235':'Final value25, claimed24; introduces26 and omits1,5; step2 reuses5.',
'147':'Final value5, claimed24; repeats12 and omits8; steps end2.',
'827':'Final value32, claimed24; final step reuses consumed6 instead of remaining8.',
'721':'Final value15, claimed24; steps end15.',
'529':'Final value21, claimed24; introduces14 and omits5; steps end14.',
'330':'Final value42 rather than target24; preceding steps use a different decomposition.',
'412':'Consistent arithmetic ends13 rather than target24.',
'366':'Final value16, claimed24; steps end16.',
'495':'Final value14, claimed24; steps end14.'}

def freeze():
    rows=json.loads((OUT/'selected_raw.json').read_text(encoding='utf8'))
    assert len(rows)==20 and {r['our_id'] for r in rows}==set(NOTES)
    pairs=[];review=['# UFT external 20-question frozen draft review','',
       'All20 read in full before generation. Three published steps + final expression; no visible unfinished text. EOS unknown, not certified.',
       'Some trajectories correctly calculate a non-24 result: failed task solution, not necessarily an arithmetic error. Retained without rewriting.','']
    for r in rows:
        draft='\n'.join(r['path']);nums=r['numbers'];qid=r['our_id']
        pair=dict(id=qid,problem=f"Use the numbers {', '.join(map(str,nums))} exactly once each, with addition, subtraction, multiplication, division and parentheses, to make 24. Provide an expression using the original four numbers.",
          answer=nums,traj1=draft,audit_status='substantive_failed',source_model='Qwen2.5-Math-7B',
          source_file=r['file'],source_row_index=r['row_index'],source_case_id=r['case_id'],
          draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),manual_evidence=NOTES[qid],
          track='B_external_uft',source_finish_reason='unknown',completeness='published_three_steps_and_final_expression',
          automatic_check=r['check'])
        pairs.append(pair);review += [f'## {qid}',NOTES[qid],'','```text',draft,'```','']
    (OUT/'pairs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in pairs),encoding='utf8')
    (OUT/'draft_review.md').write_text('\n'.join(review),encoding='utf8')
    protocol=dict(track='B_external_uft',questions=20,seeds=[929001,929002],conditions=['R0','R2','R3','R4'],generation_cap=160,
      source='UFT Qwen2.5-Math-7B CoT',selection_seed=20260919,
      question_selection='sorted625 fresh IDs shuffled by Python Random(20260919), first20',
      draft_selection='minimum SHA256 of 20260919:json(path) among canonical final-substantive candidate texts per question',
      primary=['R0-R2','R3-R2'],secondary=['R4-R2','R4-R3'],
      r0_selection=False,intervention_outcome_selection=False,cluster='question',
      no_r1=True,unknown_source_eos=True,allow_processed_complete_looking_external_trace=True,
      temperature=.6,top_p=.95,top_k=20,context_size=32768,thinking=True,
      late_first_token='full prefill logits; unchanged',automatic_expansion=False)
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf8')
    print('FROZEN20 drafts,160 requested generations')

def tokenize():
    from transformers import AutoTokenizer
    from selective_context.phase0.thinking_pilot import independent_prompt
    from selective_context.prompting import render_chat_prompt,encode_direct_prompt,encode_prompt,make_request,make_r2_r4_requests,persist_request_bundle,assert_same_text_contract
    from selective_context.schema import AccessMode
    from selective_context.vllm_mask import request_metadata
    tok=AutoTokenizer.from_pretrained('/data2/huangrj/models/qwen3-8b',local_files_only=True,use_fast=True)
    manifest=[];checks=[]
    for row in map(json.loads,(OUT/'pairs.jsonl').read_text(encoding='utf8').splitlines()):
        pair=OUT/'pairs'/f"{row['id']}.json";pair.parent.mkdir(exist_ok=True)
        pair.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf8')
        for seed in [929001,929002]:
            direct=encode_direct_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem']),True))
            full=encode_prompt(tok,render_chat_prompt(tok,independent_prompt(row['problem'],row['traj1']),True))
            reqs=make_r2_r4_requests(full,seed);assert_same_text_contract(reqs)
            assert full.text[slice(*full.draft_character_span)]==row['traj1']
            assert len(full.input_ids)<32768
            for suffix,enc,requests in [('r0',direct,[make_request(direct,'R0',AccessMode.FULL,seed)]),('r2_r4',full,reqs)]:
                p=OUT/'bundles'/f"{row['id']}.{seed}.{suffix}.json";persist_request_bundle(p,enc,requests)
                for req in requests:
                    checks.append(dict(id=row['id'],seed=seed,condition=req.condition_id,tokens=len(req.input_ids),draft_span=req.draft_token_span,spillover=enc.boundary_spillover,metadata=request_metadata(req)))
                    manifest.append(dict(bundle=p.relative_to(ROOT).as_posix(),pair=pair.relative_to(ROOT).as_posix(),condition=req.condition_id))
    assert len(manifest)==160
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    (OUT/'preflight.json').write_text(json.dumps(dict(passed=True,requests=160,real_tokenizer=True,checks=checks),indent=2),encoding='utf8')
    print('PREFLIGHT_PASSED160 same-text requests')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tokenize',action='store_true');args=ap.parse_args()
    tokenize() if args.tokenize else freeze()
