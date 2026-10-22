"""Strict, prefix8 single-anchor audit with raw provenance; no GPU imports."""
import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

from game24_100q_audit import classify, eligible
from batch03_resume_core_20260924 import atomic_write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/game24_100q_8b'
RUN = ROOT/'outputs/game24-100q-8b-20261015/acquisition/a800'
MODEL = 'Qwen3_8B_Thinking'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_rows(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]


def write_rows(p, rows):
    p.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')


def select_candidates(rows, excluded):
    """A single complete fixed8 cohort must supply every eligibility witness."""
    cohorts = collections.defaultdict(dict)
    for r in rows:
        if r['source_model'] != MODEL or not r['reusable_adapted_protocol'] or r['sample_index'] not in range(8):
            continue
        key = (r['tot_rank'], r['acquisition_batch'])
        i = r['sample_index']
        if i in cohorts[key] and cohorts[key][i] != r:
            raise RuntimeError('Conflicting single-anchor sample identity')
        cohorts[key][i] = r
    accepted = {}
    for (qid, batch), slots in sorted(cohorts.items()):
        if qid in excluded or set(slots) != set(range(8)):
            continue
        cohort = [slots[i] for i in range(8)]
        if not eligible(cohort) or qid in accepted:
            continue
        counts = dict(collections.Counter(r['classification'] for r in cohort))
        accepted[qid] = dict(canonical_question_id='tot-rank:'+qid, tot_rank=qid,
            numbers=cohort[0]['numbers'], anchor_models=[MODEL], samples_per_anchor=8,
            protocol='adapted_single_qwen8b_fixed8_v1', acquisition_batch=batch,
            classification_counts=counts, historical_development=False,
            trajectory_ids=[r['trajectory_id'] for r in cohort],
            witnesses={name: sorted(r['trajectory_id'] for r in cohort if r['classification'] in values)[:2]
                       for name, values in [('correct', ('correct', 'extraction_miss_correct')),
                                            ('substantive_error', ('substantive_error',))]})
    return [accepted[q] for q in sorted(accepted, key=int)]


def audit():
    policy = json.loads((OUT/'acquisition_campaign.json').read_text())
    for r in policy['source_bindings']:
        if digest(ROOT/r['path']) != r['sha256']:
            raise RuntimeError('Bound source changed: '+r['path'])
    if policy['anchors'] != [MODEL] or policy['samples_per_anchor'] != 8:
        raise RuntimeError('Single-anchor protocol changed')
    frozen = OUT/'game24_eligible_100.jsonl'
    if frozen.exists() and frozen.stat().st_size:
        return json.loads((OUT/'audit_summary.json').read_text())
    excluded = {str(r['id']) if 'id' in r else str(r['tot_rank'])
                for r in json.loads((ROOT/policy['frozen_history']).read_text())['questions']}
    rows = []
    cache = {}
    for r in read_rows(ROOT/policy['historical_index']):
        if r['source_model'] != MODEL or not r['reusable_adapted_protocol'] or r['sample_index'] >= 8:
            continue
        p = ROOT/r['source_path']
        if p not in cache:
            cache[p] = p.read_text(encoding='utf-8').splitlines()
        raw = cache[p][r['source_line']-1]
        if hashlib.sha256(raw.encode()).hexdigest() != r['raw_record_sha256']:
            raise RuntimeError('Historical raw binding mismatch')
        rows.append(r)
    paths = [ROOT/policy['reused_pilot_root']/'draft_candidates.jsonl']
    paths += sorted(RUN.glob('wave-*/'+MODEL+'/draft_candidates.jsonl'))
    files, classifications = [], collections.Counter()
    identities = set()
    for p in paths:
        cfg = json.loads((p.parent/'config.json').read_text())
        if cfg['model_alias'] != MODEL or cfg['context_length'] != 32768 or cfg['seed'] != policy['seed']:
            raise RuntimeError('Unexpected acquisition source configuration')
        if any(cfg['sampling'].get(k) != v for k, v in [('temperature', .6), ('top_p', .95), ('top_k', 20)]):
            raise RuntimeError('Unexpected acquisition decoding parameters')
        files.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p)))
        batch = cfg['acquisition_batch']
        for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            raw = json.loads(line)
            meta = raw['init_response_generations_metadata']
            intervention = meta['intervention']
            if meta['model_config_alias'] != MODEL or intervention['condition_id'] != 'R0':
                raise RuntimeError('Non-R0 or non-8B response in single-anchor source')
            idx = intervention['sample_seed']-policy['seed']
            if idx not in range(8) or idx != raw['init_response_generations'][0]['response_id']:
                raise RuntimeError('Unexpected effective sample seed')
            uid = f"{batch}/{MODEL}/{raw['id']}/{idx}"
            if uid in identities:
                raise RuntimeError('Duplicate acquisition identity')
            identities.add(uid)
            category, measurement = classify(raw, batch)
            classifications[category] += 1
            rows.append(dict(trajectory_id=uid, tot_rank=str(raw['id']), numbers=sorted(raw['answer']),
                source_model=MODEL, acquisition_batch=batch, sample_index=idx,
                effective_sample_seed=intervention['sample_seed'], classification=category,
                audit=measurement, reusable_adapted_protocol=True, tokens=raw['tokens'],
                source_path=p.relative_to(ROOT).as_posix(), source_line=n,
                raw_record_sha256=hashlib.sha256(line.encode()).hexdigest(),
                prompt_sha256=hashlib.sha256(raw['init_response_prompt'].encode()).hexdigest(),
                generated_text_sha256=hashlib.sha256(raw['init_response_generations'][0]['generated_response'].encode()).hexdigest()))
    accepted = select_candidates(rows, excluded)
    OUT.mkdir(parents=True, exist_ok=True)
    write_rows(OUT/'game24_trajectory_pool.jsonl', rows)
    write_rows(OUT/'game24_eligible_candidates.jsonl', accepted)
    write_rows(OUT/'pending_response_review.jsonl', [r for r in rows if 'pending_review' in r['classification']])
    met = len(accepted) >= policy['target']
    write_rows(frozen, accepted if met else [])
    ids = [r['canonical_question_id'] for r in accepted]
    random.Random(policy['split_seed']).shuffle(ids)
    atomic_write_json(OUT/'game24_split_manifest.json', dict(
        state='frozen' if met else 'not_frozen_target_not_met', seed=policy['split_seed'],
        protocol=policy['protocol'], development=ids[:20] if met else [], held_out=ids[20:] if met else []))
    atomic_write_json(OUT/'source_file_manifest.json', files)
    summary = dict(protocol=policy['protocol'], anchor_models=[MODEL], admitted_independent_questions=len(accepted),
        admitted_ids=[r['tot_rank'] for r in accepted], target_met=met,
        acquisition_responses=len(identities), acquisition_classifications=dict(classifications),
        historical_index_records=len(rows)-len(identities), historical_exclusion_questions=len(excluded),
        pending_response_reviews=sum('pending_review' in r['classification'] for r in rows),
        old_dual_only_candidates_not_admitted=['643', '1119'],
        limitations=['Single 8B anchor adapted protocol; no cross-model generality claim.',
                     'All witnesses come from one complete fixed8 cohort; invalid responses are not resampled.'])
    atomic_write_json(OUT/'audit_summary.json', summary)
    return summary


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False))
