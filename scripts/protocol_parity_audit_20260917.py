"""Offline inventory only. No model loading, generation, or sample acceptance."""
import collections
import csv
import hashlib
import json
import re
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/protocol-parity-audit-20260917'


def main():
    rows=list(csv.DictReader((OUT/'24.csv').open(encoding='utf-8-sig')))
    number_to_rank={tuple(sorted(map(int,r['Puzzles'].split()))):r['Rank'] for r in rows}
    cache_summary={}; mapping=collections.defaultdict(set)
    retained_pool=collections.defaultdict(collections.Counter)
    cache_ids=set()
    for p in sorted((ROOT/'analysis/TED/cache/direct').glob('*.json')):
        data=json.loads(p.read_text(encoding='utf-8'));cache_ids.update(data)
        sample_counts=collections.Counter()
        for qid,groups in data.items():
            lists=[g.get('init_response',[]) for g in groups.values()]
            if any(g!=lists[0] for g in lists):
                raise ValueError('Repeated cache baseline lists differ; cannot count once')
            if p.stem in ['Qwen3_8B','Qwen3_32B','Nemotron_32B']:
                for formula,meta in lists[0]:
                    if meta.get('finish_reason')=='stop':
                        retained_pool[qid][str(meta.get('correctness'))]+=1
            # init_response lists repeat under different draft groups; do not sum them.
            for group in groups.values():
                for formula,meta in group.get('init_response',[]):
                    if meta.get('correctness') is True:
                        numbers=tuple(sorted(map(int,re.findall(r'\d+',formula))))
                        if len(numbers)==4 and numbers in number_to_rank:
                            mapping[qid].add(number_to_rank[numbers])
                sample_counts[len(group.get('init_response',[]))]+=1
        cache_summary[p.stem]={'questions':len(data),'retained_init_counts_per_draft_group':dict(sample_counts)}
    inferred={q:next(iter(v)) for q,v in mapping.items() if len(v)==1}
    conflicts={q:sorted(v) for q,v in mapping.items() if len(v)>1}
    sorted_numbers=sorted(number_to_rank)
    lexical_matches=sum(int(q)<len(sorted_numbers) and
                        number_to_rank[sorted_numbers[int(q)]]==r for q,r in inferred.items())
    (OUT/'ted_inferred_question_mapping.json').write_text(json.dumps(dict(
        warning='Inferred from retained correct formula number multisets; not original manifest or full 653 subset. Cache retention depends on parseable anchored outputs.',
        mappings=inferred,conflicts=conflicts,unmapped=sorted(cache_ids-set(inferred))),indent=2),encoding='utf-8')

    groups=collections.defaultdict(lambda:collections.Counter())
    questions=collections.defaultdict(set); seen=set(); inventory=[]; counts=collections.defaultdict(collections.Counter)
    historical_numbers=set()
    dev={'1189','1358','804','123','577','719','1084','71','513','1226','170','159','1093'}
    for p in sorted((ROOT/'outputs').rglob('*draft_candidates.jsonl')):
        cfg=p.parent/'config.json';config=json.loads(cfg.read_text(encoding='utf-8')) if cfg.exists() else {}
        n=0
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            r=json.loads(line);meta=r.get('init_response_generations_metadata',{})
            if isinstance(r.get('answer'),list) and len(r['answer'])==4:
                historical_numbers.add(tuple(sorted(map(int,r['answer']))))
            if meta.get('intervention',{}).get('condition_id') not in (None,'R0'):continue
            for g in r.get('init_response_generations',[]):
                digest=hashlib.sha256(g.get('generated_response','').encode()).hexdigest()
                key=(str(r['id']),r.get('draft_key'),digest)
                if key in seen:continue
                seen.add(key);n+=1
                thinking=meta.get('enable_thinking',config.get('enable_thinking','unknown'))
                if thinking is True and 'heldout-screen-20260917' in str(p):
                    backend='vllm_selective_flex_0.11.0'
                else:
                    backend=meta.get('backend',config.get('backend','unknown'))
                group=f'thinking={thinking}; backend={backend}'
                c=g.get('correctness');finish=g.get('finish_reason');status=r.get('thinking_status')
                groups[group]['samples']+=1;groups[group][str(c)]+=1;questions[group].add(str(r['id']))
                if finish=='eos' and status=='parsable_thinking':
                    groups[group]['complete_parsable']+=1
                    counts[str(r['id'])][str(c)]+=1
        inventory.append({'path':str(p.relative_to(ROOT)),'deduplicated_records':n})
    summary=dict(source=dict(rows=len(rows),unique_number_multisets=len(number_to_rank),
        sha256=hashlib.sha256((OUT/'24.csv').read_bytes()).hexdigest()),cache=cache_summary,
        cache_union_questions=len(cache_ids),inferred_mapping_count=len(inferred),mapping_conflicts=conflicts,
        cache_ids_matching_zero_based_lexicographic_order=lexical_matches,
        cached_anchor_stop_2true_2false_count=sum(c['True']>=2 and c['False']>=2 for c in retained_pool.values()),
        cache_ids_equal_tot_rank=sum(q==r for q,r in inferred.items()),
        baseline_groups={g:dict(c,questions=len(questions[g])) for g,c in groups.items()},
        complete_thinking_mixed_ids=sorted(q for q,c in counts.items() if c['True']>=1 and c['False']>=1),
        complete_thinking_2true_2false_ids=sorted(q for q,c in counts.items() if c['True']>=2 and c['False']>=2),
        nondevelopment_2true_2false_ids=sorted(q for q,c in counts.items() if q not in dev and c['True']>=2 and c['False']>=2),
        counts_by_question={q:dict(c) for q,c in counts.items()},source_inventory=inventory,
        note='Historical HF/vLLM and possibly sampling configurations are stratified, not declared interchangeable anchor samples. No new eligible set accepted.')
    (OUT/'inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    # Candidate order uses only source questions and historical exposure, never TED
    # retention, R2 outcomes, or any recovery statistic. It remains unapproved.
    candidates=[dict(tot_rank=r['Rank'],numbers=list(map(int,r['Puzzles'].split()))) for r in rows
                if tuple(sorted(map(int,r['Puzzles'].split()))) not in historical_numbers]
    random.Random(20270918).shuffle(candidates)
    plan=dict(status='PREPARED_NOT_AUTHORIZED_TO_GENERATE',generate=False,
        protocol_label='paper-aligned re-instantiation; not exact original-653 reproduction',
        sources_revision='8050e67d0e3a0fddc424d7fa5801538722a4c4cc',
        source_prompt_verbatim_recovered=False,order_seed=20270918,
        historical_number_multisets_excluded=len(historical_numbers),candidate_count=len(candidates),
        candidates=candidates[:104],stages=[32,64,104],
        anchors=['nvidia/OpenReasoning-Nemotron-32B','Qwen/Qwen3-32B','Qwen/Qwen3-8B'],
        samples_per_model_per_question=16,initial_sampling_seed=42,
        baseline_caps_by_stage=[1536,3072,4992],
        target_problem_count=[30,50],conditions=['R0','R2','whole_late','whole_path'],
        evaluation_paired_seeds=[927001,927002],evaluation_cap_for_50_questions=400,
        pending_decisions=['Nemotron-32B storage/compute availability',
            'authorization for discovered Qwen3-32B weights',
            'paper-faithful falsey-label pool versus explicit-False primary pool',
            'approve documented source/prompt/backend deviations or supply original data',
            'approve bounded baseline budget; prior 32+48 budget is not carried forward'],
        no_auto_anchor_substitution=True,no_auto_start=True)
    (OUT/'prepared_generation_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['counts_by_question','source_inventory','cache']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
