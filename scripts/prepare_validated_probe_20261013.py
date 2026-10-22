"""Goal 2 Gate 0 assets and blinded early-trajectory review; no model forward."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_feedback_source_binding_probe_20261012 import read, rows, save, append
from run_identity_mvp_20261011 import audit_expression
from selective_context.diagnostic_data import SOURCES, request_of

BASE = ROOT / 'outputs/generation-diagnostics-20261005'
OUT = ROOT / 'outputs/validated-probe-20261013'
SEED = 20261013
TEMPLATE_CHECK = dict(
    replace='In your final boxed expression, use numerical literals with exactly the required occurrence counts.',
    with_text='Conclude with a boxed numerical expression that obeys every required occurrence count.',
    development_questions=6,confirmation_questions=12,seed=20261013,max_new_tokens=16384,
    min_prefix_stance_agreement=.75,max_balanced_accuracy_drop=.10,
    require_same_history_effect_direction=True,
    interpretation='Finite same-seed prompt paraphrase check, not universal template invariance. No answer candidates or forced readout in either template.')


def boxed(text):
    start = text.rfind('\\boxed{')
    if start < 0:
        raise ValueError('No original boxed history expression')
    start += len('\\boxed{')
    depth, end = 1, start
    while end < len(text) and depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    if depth:
        raise ValueError('Unclosed original expression')
    return text[start:end-1]


def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    if (out/'manifest.json').exists():
        return read(out/'manifest.json')
    natural = read(BASE/'candidate_adoption/manifest.json')
    # Original frozen order, before viewing this probe's clipped trajectories.
    development = natural['questions'][:20]
    dev_sets = {tuple(sorted(q['answer'])) for q in development}
    choices, qualification_skips = {}, []
    for name, file in [('failure_pool','candidate_adoption/failure_pool.json'),
                       ('cross_question','cross_question/manifest.json'),
                       ('original_r0_r4','manifest.json')]:
        for original in read(BASE/file)['questions']:
            ns = tuple(sorted(original['answer']))
            if ns in choices:
                continue
            q = dict(original)
            if 'draft' not in q:
                q['draft'] = q['prompt'].split('-- beginning of the draft --\n',1)[1].split('\n-- end of the draft --',1)[0]
                q['old_expression'] = boxed(q['draft'])
            audited = audit_expression(q['old_expression'],q['answer'])
            if not audited.get('parsed') or audited['correct']:
                qualification_skips.append(dict(id=q['id'],pool=name,
                    reason='No parseable invalid full construction',expression=q['old_expression']))
                continue
            choices[ns] = dict(id=q['id'], answer=list(ns), problem=q['problem'],
                draft=q['draft'], old_expression=q['old_expression'], old_numeric=audited['numeric_expression'],
                source=q['source'], source_line=q['source_line'], pool=name)
    confirmation = [q for ns,q in sorted(choices.items()) if ns not in dev_sets]
    random.Random(SEED).shuffle(confirmation)
    if len(development)!=20 or len(confirmation)!=36:
        raise ValueError('Record an asset change before freezing a different split')
    qs = {q['id']:q for q in development}
    raw_source = BASE/'candidate_adoption/generations.jsonl'
    score_source = BASE/'candidate_adoption/behaviour.jsonl'
    raw = [dict(r,source_raw=str(raw_source.relative_to(ROOT)),source_raw_line=i)
           for i,r in enumerate(rows(raw_source),1)
           if r['id'] in qs and r['phase']=='NATURAL' and r['condition'] in ('COUNT_CLEAN','COUNT_HISTORY')]
    scored = [r for r in rows(score_source) if r['id'] in qs and r['phase']=='NATURAL'
              and r['condition'] in ('COUNT_CLEAN','COUNT_HISTORY')]
    if len(raw)!=80 or len(scored)!=80:
        raise ValueError('Expected 20 questions x 2 conditions x 2 existing seeds')
    audit = {}
    for source in SOURCES:
        source_rows = rows(ROOT/source)
        audit[source] = dict(rows=len(source_rows),conditions=dict(Counter(request_of(r)['condition_id'] for r in source_rows)))
    m = dict(goal='Goal 2 Validated Low-Cost Mechanism Probe',seed=SEED,
        model='/data2/huangrj/models/qwen3-8b',dtype='bfloat16',primary='B: bounded natural continuation, last unambiguous old-route stance',
        prefix_token_limit=2048,development=development,confirmation=confirmation,
        development_selection='First 20 in candidate_adoption frozen order; no selection by new probe outcome',
        confirmation_selection='All remaining 36 qualified unique number multisets in the audited union; metadata only, no probe or final-outcome debugging',
        confirmation_precision='36 questions: worst-case independent Bernoulli SE about 0.083 (95% half-width about 0.163); cluster bootstrap may be wider. No GO from imprecise intervals.',
        primary_endpoint='Old-route adoption = last explicit stance by token 2048 accepts or chooses the original invalid construction. Quotation/checking alone excluded. No event is distinct from rejection and predicts no early adoption, not successful revocation.',
        behavior_reference='Same original prompt, seed and condition, complete natural final expression AST reuse. Truncated/unparseable final route is unknown, never a negative.',
        gate1=dict(min_questions_with_complete_paired_seed=14,min_clean_success_questions=12,
            min_complete_history_positive=8,min_complete_history_negative=8,
            min_balanced_accuracy=.75,min_balanced_accuracy_ci95_lower=.50,
            min_adoption_precision=.80,require_positive_paired_history_effect=True,
            max_mean_prefix_to_full_token_ratio=.50,
            fresh_template_check_questions=6,max_new_full_development_requests=24),
        gate2=dict(questions=36,min_questions_with_complete_pair=30,min_balanced_accuracy=.75,
            min_balanced_accuracy_ci95_lower=.50,min_adoption_precision=.80,
            require_positive_history_effect_ci95_lower=True,max_mean_prefix_to_full_token_ratio=.50,
            max_new_full_primary_requests=72,max_new_full_template_requests=24,
            template_subset='First 12 in frozen confirmation order; selected before outcomes'),
        bootstrap=dict(draws=5000,unit='question',seed=SEED),
        no_options_or_forced_output=True,
        limits='One primary method. No window extension, candidate/prefix search, PRE/POST, KV transplant, source-binding expansion or automatic second method. Goal 1 96-question set untouched.',
        prior_exposure='Question-independent within this goal, not pristine external data: some histories/results have been used in older experiments.',
        audit_sources=audit,qualification_skips=qualification_skips,
        template_check=TEMPLATE_CHECK,freeze_status='gate0_finalized_before_clipped_prefix_review')
    save(out/'manifest.json',m)
    save(out/'asset_audit.json',dict(unique_failed_history_questions=len(choices),development_questions=20,
        confirmation_questions=36,development_natural_trajectories=len(raw),qualification_skips=qualification_skips,
        prospective_64_note='61 correct histories, 2 incorrect, 1 undetermined; not a 64-question failed-history confirmation set',
        existing_reviewed_events=23,existing_reviewed_event_missing=1,
        original_r0_r4=audit,goal1_forwards=744,goal1_gate='STOP_measurement_not_validated'))
    # Kept separate so annotation never needs the final label or full future text.
    save(out/'development_raw.json',raw)
    save(out/'development_reference.json',scored)
    save(out/'run_state.json',dict(status='gate0_frozen_awaiting_cpu_tokenizer_decode',gpu_seconds=0,development_questions=20,confirmation_questions=36))
    return m


def decode(out):
    from transformers import AutoTokenizer
    m=read(out/'manifest.json')
    tokenizer=AutoTokenizer.from_pretrained(m['model'],local_files_only=True)
    samples=[]
    for r in read(out/'development_raw.json'):
        ids=r['token_ids'][:m['prefix_token_limit']]
        text=tokenizer.decode(ids,skip_special_tokens=False)
        # Source text can prepend a thinking marker; tokens are authoritative.
        q=next(q for q in m['development'] if q['id']==r['id'])
        samples.append(dict(key=f"{r['id']}:{r['condition']}:{r['seed']}",id=r['id'],condition=r['condition'],
            seed=r['seed'],text=text,tokens=ids,problem=q['problem'],old_expression=q['old_numeric'],
            source_raw=r['source_raw'],source_raw_line=r['source_raw_line'],
            source_prefix_note='Exact native token prefix; no appended reasoning, candidates or fabricated decision stem'))
    random.Random(SEED).shuffle(samples)
    save(out/'development_prefixes.json',samples)
    save(out/'development_labels_template.json',{
        r['key']:dict(stance=None,anchor=None,reason=None) for r in samples})
    save(out/'run_state.json',dict(status='gate1_awaiting_blind_prefix_annotation',gpu_seconds=0,prefixes=len(samples),prefix_limit=m['prefix_token_limit']))
    print(json.dumps(dict(prefixes=len(samples),max_prefix_tokens=max(len(r['tokens']) for r in samples),model_forward_calls=0)))


def review(out,keys):
    # This command cannot expose the reference file or tokens after the cutoff.
    data=read(out/'development_prefixes.json')
    for index in keys:
        r=data[index]
        print(json.dumps(dict(index=index,key=r['key'],problem=r['problem'],old_expression=r['old_expression']),ensure_ascii=False))
        print(r['text'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=OUT)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',action='store_true')
    g.add_argument('--decode',action='store_true')
    g.add_argument('--review',nargs='+',type=int)
    a=p.parse_args()
    if a.prepare:
        m=prepare(a.output)
        print(json.dumps(dict(development=len(m['development']),confirmation=len(m['confirmation']))))
    elif a.decode:decode(a.output)
    else:review(a.output,a.review)


if __name__=='__main__':main()
