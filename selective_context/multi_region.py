"""Compile explicit character evidence to audited disjoint token sets."""
import string


def merge_spans(spans):
    merged=[]
    for a,b in sorted(spans):
        if not 0 <= a < b: raise ValueError('Empty/invalid span')
        if merged and a <= merged[-1][1]: merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else: merged.append((a,b))
    return tuple(merged)


def compile_regions(tokenizer, encoded, evidence):
    tok=tokenizer(encoded.text,add_special_tokens=False,return_offsets_mapping=True)
    if tok['input_ids']!=encoded.input_ids: raise ValueError('Tokenizer mismatch')
    offsets=tok['offset_mapping'];ds,de=encoded.draft_character_span;regions=[];spans=[]
    for item in evidence:
        a,b=item['character_span']
        if not ds <= a < b <= de or encoded.text[a:b]!=item['text']: raise ValueError('Evidence mismatch')
        indices=[i for i,(s,e) in enumerate(offsets) if e>s and s<b and e>a]
        lo,hi=indices[0],indices[-1]+1;left,right=offsets[lo][0],offsets[hi-1][1]
        spill=encoded.text[left:a]+encoded.text[b:right]
        if any(c not in string.whitespace+string.punctuation for c in spill):raise ValueError('Semantic boundary spillover')
        if not encoded.draft_token_span[0]<=lo<hi<=encoded.draft_token_span[1]:raise ValueError('Outside draft tokens')
        spans.append((lo,hi));regions.append(dict(item,token_span=[lo,hi],spill_before=encoded.text[left:a],spill_after=encoded.text[b:right]))
    if not spans:raise ValueError('No evidence; no automatic whole-draft fallback')
    merged=merge_spans(spans)
    return dict(spans=merged,regions=regions,token_count=sum(b-a for a,b in merged))
