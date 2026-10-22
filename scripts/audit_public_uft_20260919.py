"""Read-only public-data audit; no model, no intervention outcomes, no unsafe eval."""
import ast,csv,hashlib,io,json,operator,random,re,statistics,zipfile
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/public-uft-audit-20260919'

def exact(expr):
    def visit(n):
        if isinstance(n,ast.Expression):return visit(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):return Fraction(str(n.value))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            return visit(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            return {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}[type(n.op)](visit(n.left),visit(n.right))
        raise ValueError('Unsupported arithmetic')
    if len(expr)>2000:raise ValueError('Long expression')
    return visit(ast.parse(expr.strip(),mode='eval'))

def final_check(path,structured):
    if not structured:return dict(category='unstructured',complete_shape=False)
    if len(path)!=5:return dict(category='noncanonical_length',complete_shape=False)
    expr=path[-1].removeprefix('Answer:').strip().split('=')[0].strip()
    try:
        v=exact(expr)
        nums=list(map(int,re.findall(r'\d+',expr)))
        expected=list(map(int,path[0].split()))
        wrong=Counter(nums)!=Counter(expected)
        # Decimal numerals are unusual; do not assert multiset validity from digit fragments.
        if re.search(r'\d\.\d',expr):return dict(category='decimal_needs_review',complete_shape=True)
        category='final_substantive' if wrong or v!=24 else 'final_valid_needs_step_review'
        return dict(category=category,complete_shape=True,expression=expr,value=str(v),wrong_multiset=wrong)
    except (ValueError,TypeError,KeyError,SyntaxError,ZeroDivisionError):
        return dict(category='unparseable_final',complete_shape=True,expression=expr)

def main():
    own=list(csv.DictReader((ROOT/'outputs/protocol-parity-audit-20260917/24.csv').open(encoding='utf-8-sig')))
    lookup={tuple(sorted(map(int,r['Puzzles'].split()))):str(r['Rank']) for r in own}
    assert len(lookup)==1362
    source=list(csv.DictReader((OUT/'repo/reasoners/examples/game24/metadata/24.csv').open(encoding='utf-8-sig')))
    source_lookup={str(i+1):tuple(sorted(map(int,r['Puzzles'].split()))) for i,r in enumerate(source)}
    historical=json.loads((ROOT/'outputs/baseline-corpus-audit-20260917/baseline_corpus_audit.json').read_text())
    historical_keys={tuple(sorted(r['number_multiset'])) for r in historical['problems']}
    manifests=[json.loads((ROOT/'scripts'/name).read_text()) for name in ['baseline_screen_manifest_20260917.json','baseline_screen_manifest_20260918_batch02.json']]
    screened=set(historical_keys)
    for m in manifests:screened.update(tuple(sorted(r['numbers'])) for r in m['candidate_rows'])
    dev_ids={'1189','1358','804','123','577','719','1084','71','513','1226'}
    pilot_ids={'44','914','1112','41','1057','413','509'}
    dev={k for k,v in lookup.items() if v in dev_ids};pilot={k for k,v in lookup.items() if v in pilot_ids}
    reserved={tuple(sorted(r['numbers'])) for r in json.loads((ROOT/'scripts/baseline_manifest_batch03_20260919.json').read_text())['candidate_rows']}
    groups=defaultdict(Counter);group_cases=defaultdict(set);percase=defaultdict(Counter)
    all_cases=set();mapped_cases=set();quality=Counter();candidate_counts=Counter();eligible_rows=[]
    files=[];mapping_errors=[];dedup=set();sample=[];rng=random.Random(20260919);seen=0;cot_cases=set()
    with zipfile.ZipFile(OUT/'data.zip') as z:
        names=sorted(n for n in z.namelist() if n.startswith('data/game24/corpora/') and n.endswith('/failed_train.csv'))
        for name in names:
            parts=name.split('/');group=parts[3]+'/'+parts[4].split('_')[0];c=Counter();cases=set()
            priority=group=='Qwen2.5-Math-7B/cot'
            for idx,r in enumerate(csv.DictReader(io.TextIOWrapper(z.open(name),encoding='utf-8'))):
                path=ast.literal_eval(r['text']);key=tuple(sorted(map(int,path[0].split())))
                cid=r['case_id'];structured=r['structured']=='True'
                c['rows']+=1;c['structured' if structured else 'unstructured']+=1;c['success_'+r['success']]+=1
                cases.add(key);all_cases.add(key);percase[group][key]+=1
                if key in lookup:mapped_cases.add(key)
                if source_lookup.get(cid)!=key or key not in lookup:mapping_errors.append(dict(file=name,row=idx,case_id=cid,numbers=key))
                if priority:
                    cot_cases.add(key);dedup.add(hashlib.sha256(r['text'].encode()).hexdigest())
                    check=final_check(path,structured);quality[check['category']]+=1
                    record=dict(file=name,row_index=idx,case_id=cid,our_id=lookup.get(key),numbers=key,
                                structured=structured,success=r['success'],path=path,check=check,
                                historical_overlap=key in screened)
                    seen+=1
                    if len(sample)<20:sample.append(record)
                    else:
                        j=rng.randrange(seen)
                        if j<20:sample[j]=record
                    if check['category']=='final_substantive':
                        candidate_counts[key]+=1
                        if key not in screened and key not in reserved:eligible_rows.append(record)
            groups[group].update(c);group_cases[group].update(cases)
            files.append(dict(file=name,counts=dict(c),unique_questions=len(cases)))
            print(name,c['rows'],flush=True)
    fresh=set(candidate_counts)-screened
    conservative=fresh-reserved
    summary=dict(repo_commit='5d5b56c3a12b5f96100e4418e7913cb6ee8df302',archive_sha256=hashlib.sha256((OUT/'data.zip').read_bytes()).hexdigest(),
        failed_file_count=len(files),total_failed_rows=sum(c['rows'] for c in groups.values()),unique_questions=len(all_cases),
        mapped_questions=len(mapped_cases),mapping_errors=mapping_errors,
        groups={g:dict(counts=dict(c),unique_questions=len(group_cases[g]),mean_per_question=statistics.mean(percase[g].values()),median_per_question=statistics.median(percase[g].values())) for g,c in groups.items()},
        cot7b_unique_texts=len(dedup),cot7b_quality=dict(quality),
        overlaps=dict(all_pool_development=len(all_cases&dev),all_pool_pilot=len(all_cases&pilot),all_pool_any_screen=len(all_cases&screened),
             cot7b_any_screen=len(cot_cases&screened),historical_exclusion_questions=len(screened),reserved_batch03_questions=len(reserved)),
        final_substantive_questions=len(candidate_counts),fresh_final_substantive_questions=len(fresh),fresh_excluding_reserved_questions=len(conservative),
        fresh_final_substantive_rows=sum(candidate_counts[k] for k in fresh),conservative_candidate_rows=len(eligible_rows),
        sample=dict(seed=20260919,n=20,frame='all published Qwen2.5-Math-7B CoT failed rows across 9 variants, before filtering, reservoir sample'),
        limits=['No EOS/finish_reason/token counts in CSV; structural completeness is not proof of non-truncation',
                'No target Qwen3 clean-solvability measurement', 'Automatic final-error checks do not establish full step coherence'])
    for name,obj in [('summary.json',summary),('file_inventory.json',files),('random20.json',sample)]:
        (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    with (OUT/'fresh_candidates.jsonl').open('w',encoding='utf-8') as f:
        for r in eligible_rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
