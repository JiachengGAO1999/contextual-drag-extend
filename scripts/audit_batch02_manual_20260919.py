"""Frozen final-answer adjudication; no intervention outputs are read."""
import ast
from collections import Counter,defaultdict
from fractions import Fraction
import json
import operator
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'outputs/game24-baseline-screen-vllm-20260918-batch02'
# Manually read final prose for every scalar-boxed response.
BODY={
 '363/5':'11+11+11-9','668/1':'6*(8/(10-8))',
 '52/12':'12*(12/(3+3))','585/10':'12*(6/(9-6))',
 '754/14':'3*(10-(9/9))-3','289/1':'12+13-(13/13)',
 '289/15':'12*((13+13)/13)','674/13':'(10-2)*(6/2)',
 '754/3':'(10-9/9)*3','754/6':'(10*9-9)/3',
}

def normalize(s):
    s=s.split('=')[0].replace('\\left','').replace('\\right','').replace('\\times','*').replace('\\div','/')
    while '\\frac' in s:
        i=s.rfind('\\frac');j=i+5;parts=[]
        for _ in range(2):
            while s[j].isspace():j+=1
            assert s[j]=='{'
            start=j+1;depth=1;j+=1
            while depth:
                depth+=(s[j]=='{')-(s[j]=='}');j+=1
            parts.append(s[start:j-1])
        s=s[:i]+'(('+parts[0]+')/('+parts[1]+'))'+s[j:]
    return s.strip()

def exact(s):
    def visit(n):
        if isinstance(n,ast.Expression):return visit(n.body)
        if isinstance(n,ast.Constant) and type(n.value) is int:return Fraction(n.value)
        if isinstance(n,ast.BinOp):return {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}[type(n.op)](visit(n.left),visit(n.right))
        raise ValueError('Unsupported expression')
    return visit(ast.parse(s,mode='eval'))

def main():
    audit=[];counts=Counter();qs=defaultdict(Counter)
    for line in (RUN/'draft_candidates.jsonl').read_text().splitlines():
        r=json.loads(line);g=r['init_response_generations'][0];key=r['draft_key'];detail={}
        if g['finish_reason']!='eos':category='length_limited'
        elif r['thinking_status']!='parsable_thinking':category='unparseable_thinking'
        elif g.get('correctness') is True:category='correct'
        elif g.get('correctness') is not False:category='unscored'
        else:
            s=normalize(BODY.get(key,g['extracted_answer']))
            v=exact(s);used=Counter(map(int,re.findall(r'\d+',s)))
            wrong_numbers=used!=Counter(r['answer'])
            category='substantive_multiset' if wrong_numbers else 'substantive_wrong_value' if v!=24 else 'format_only'
            if key in ['754/3','754/6']:category='substantive_false_impossibility'
            detail=dict(expression=s,value=str(v),wrong_number_multiset=wrong_numbers,
                        final_response=r['final_response'],manual_scalar_review=key in BODY)
        counts[category]+=1;qs[str(r['id'])][category]+=1
        if category!='correct':audit.append(dict(draft_key=key,category=category,answer=r['answer'],**detail))
    eligible=[q for q,c in qs.items() if c['correct']>=2 and sum(v for k,v in c.items() if k.startswith('substantive'))>=2]
    result=dict(counts=dict(counts),questions=dict(qs),eight_b_only_eligible=eligible,
        formal_pool_frozen=False,pending='full 32B batch and pooled manual audit',audit=audit)
    (RUN/'manual_audit_20260919.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(counts=dict(counts),eligible=eligible)))

if __name__=='__main__':main()
