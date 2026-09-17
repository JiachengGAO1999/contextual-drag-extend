"""Compile fixed-unit coverage, prove edge nesting, audit structural controls. No generation."""
import argparse,json,html
from pathlib import Path
from dataclasses import replace
import torch
from transformers import AutoTokenizer,AutoModelForCausalLM
from selective_context.multi_region import compile_regions,merge_spans
from selective_context.masks import build_allowed_attention,build_additive_attention
from selective_context.phase0.multi_late import source
from selective_context.prompting import load_request_bundle
from selective_context.schema import AccessMode


def matching(targets,candidates,draft_length):
    # Prespecified engineering tolerances, not a validated definition of equivalence.
    choices=[]
    for lo,hi in targets:
        choices.append([name for name,(a,b) in candidates.items()
            if abs((b-a)-(hi-lo))/(hi-lo)<=.25 and abs(b-hi)/draft_length<=.15])
    def search(i,used):
        if i==len(choices):return list(used)
        for name in choices[i]:
            a,b=candidates[name]
            if any(max(a,candidates[k][0])<min(b,candidates[k][1]) for k in used):continue
            result=search(i+1,used+[name])
            if result is not None:return result
        return None
    selected=search(0,[])
    return dict(feasible=selected is not None,assignment=selected,
                eligible_counts=[len(c) for c in choices],
                rule='same unit count; each length within25%; each end within15% of draft length; disjoint candidates',
                reason=None if selected is not None else 'No complete assignment in audited candidate pool; no fallback')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--real-sanity',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    annotation=json.loads((root/'docs/quick_validation/fixed_coverage_annotations_v1_20260913.json').read_text(encoding='utf-8'))
    old=json.loads((root/'outputs/game24-multi-late-20260912-coverage.json').read_text())
    tok=AutoTokenizer.from_pretrained('/data2/huangrj/models/qwen3-8b',local_files_only=True,use_fast=True)
    report={};requests=[]
    page=['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{max-width:960px;margin:auto;padding:16px;font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px}</style><h1>Fixed-unit coverage preflight (no generation)</h1>']
    for pid,q in annotation['questions'].items():
        enc,refs=load_request_bundle(source(root,pid,2027)/'bundles'/f'{pid}.r2_r4.json')
        ref=next(r for r in refs if r.condition_id=='R2');ds,de=enc.draft_character_span
        assert enc.text[ds:de]==q['draft']
        compiled={}
        for u in q['units']+q['control_candidates']:
            a,b=u['draft_span']
            compiled[u['id']]=compile_regions(tok,enc,[dict(u,character_span=[ds+a,ds+b])])
        base=tuple(tuple(s) for s in old[pid]['M_X']['spans'])
        expression=merge_spans([s for name in q['levels']['C1'] for s in compiled[name]['spans']])
        assert expression==base
        levels={};previous=None
        def allowed(req):
            return build_allowed_attention(batch_size=1,query_positions=range(len(ref.input_ids)),
                key_length=len(ref.input_ids),draft_token_span=ref.draft_token_span,
                access_mode=AccessMode.PATH_BLOCK,prompt_length=len(ref.input_ids),
                mask_token_spans=req.mask_token_spans,path_block_units=req.path_block_units)
        alltarget=merge_spans([s for name in q['levels']['C4'] for s in compiled[name]['spans']])
        candidates={u['id']:compiled[u['id']]['spans'][0] for u in q['control_candidates']}
        assert all(not any(max(a,lo)<min(b,hi) for lo,hi in alltarget) for a,b in candidates.values())
        for level,names in q['levels'].items():
            units=tuple(sorted(set(base+tuple(s for name in names if not name.startswith('X') for s in compiled[name]['spans']))))
            req=replace(ref,condition_id='fixed_'+level,access_mode=AccessMode.PATH_BLOCK,
                        mask_token_spans=merge_spans(units),path_block_units=units)
            req.validate();mask=allowed(req)
            if previous is not None:assert not (mask & ~previous).any(), 'Expansion restored edges'
            if level=='C1':assert torch.equal(mask,allowed(replace(req,path_block_units=())))
            same_previous=previous is not None and torch.equal(mask,previous)
            previous=mask
            levels[level]=dict(request=req.to_dict(),unique_tokens=sum(b-a for a,b in req.mask_token_spans),
                fixed_unit_count=len(units),same_as_previous=same_previous,
                control=matching(units,candidates,ref.draft_token_span[1]-ref.draft_token_span[0]))
            if level=='C2':requests.append((pid,req))
        # Input equality across all original four seeds; no new sample_seed invented.
        for seed in (12027,22027,32027):
            other,_=load_request_bundle(source(root,pid,seed)/'bundles'/f'{pid}.r2_r4.json')
            assert other.input_ids==enc.input_ids and other.text==enc.text
        report[pid]=dict(levels=levels,compiled_units=compiled,C1_reusable_edge_identity=True,
                        nested_edges=True,notes=q['notes'])
        page.append(f'<h2>{pid}</h2><p>{html.escape(q["notes"])}</p>')
        for u in q['units']+q['control_candidates']:
            c=compiled[u['id']]
            page.append(f'<details><summary>{u["id"]}: {u["category"]}; {c["spans"]}; depends {u.get("depends_on",[])}</summary><pre>{html.escape(u["text"])}</pre><p>{html.escape(u["reason"])}</p><p>Expression family reference (not dependency edges): {u.get("refers_to_expression_family",[])}</p></details>')
        page.append('<pre>'+html.escape(json.dumps({l:{k:v for k,v in x.items() if k!='request'} for l,x in levels.items()},indent=2))+'</pre>')
    if args.real_sanity:
        model=AutoModelForCausalLM.from_pretrained('/data2/huangrj/models/qwen3-8b',local_files_only=True,
            torch_dtype=torch.bfloat16,attn_implementation='eager',device_map='cuda:0')
        with torch.inference_mode():
            for pid,req in requests:
                ids=torch.tensor([req.input_ids],device=model.device);n=ids.shape[1]
                kw=dict(batch_size=1,key_length=n,query_positions=range(n),draft_token_span=req.draft_token_span,
                    mask_token_spans=req.mask_token_spans,path_block_units=req.path_block_units,
                    access_mode=AccessMode.PATH_BLOCK,prompt_length=n,device=model.device,dtype=model.dtype)
                mask=build_additive_attention(**kw)
                a=model(input_ids=ids,attention_mask=mask,use_cache=False,output_attentions=True)
                maximum=max(float(layer[:,:,hi:,lo:hi].abs().max()) for layer in a.attentions for lo,hi in req.path_block_units)
                logits=a.logits[:,-1].clone();del a
                altered=ids.clone()
                for lo,hi in req.mask_token_spans:altered[:,lo:hi]=(altered[:,lo:hi]+17)%model.config.vocab_size
                b=model(input_ids=altered,attention_mask=mask,use_cache=False)
                delta=float((logits-b.logits[:,-1]).abs().max());del b
                assert maximum==delta==0
                report[pid]['real_C2_sanity']=dict(layers=36,blocked_max=maximum,final_logits_mutation_delta=delta)
                print('REAL_FIXED_C2_PASSED',pid,flush=True)
    dest=root/'docs/quick_validation/fixed_coverage_preflight_20260913.json'
    if not args.real_sanity and dest.exists():
        earlier=json.loads(dest.read_text(encoding='utf-8'))
        for pid in report:
            if 'real_C2_sanity' in earlier.get(pid,{}):
                assert json.loads(json.dumps(report[pid]['levels']['C2']['request']))==earlier[pid]['levels']['C2']['request']
                report[pid]['real_C2_sanity']=earlier[pid]['real_C2_sanity']
                report[pid]['sanity_reuse_note']='Identical complete C2 request; only annotation relationship metadata reviewed'
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'outputs/fixed-coverage-review-20260913.html').write_text('\n'.join(page),encoding='utf-8')
    print(json.dumps({p:{l:dict(tokens=x['unique_tokens'],units=x['fixed_unit_count'],control=x['control']['feasible'],collapsed=x['same_as_previous']) for l,x in q['levels'].items()} for p,q in report.items()},indent=2))


if __name__=='__main__':main()
