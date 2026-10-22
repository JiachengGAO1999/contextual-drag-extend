"""Auditable Game24 inventory. CPU only; never reads intervention correctness."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_batch03_partial_20260924 import (
    expression_measurement, manual_classification, record_fields, valid_response_expressions,
)
from audit_batch02_manual_20260919 import BODY

ANCHORS = ('Qwen3_8B_Thinking', 'Qwen3_32B')
SOURCE = ROOT / 'outputs/protocol-parity-audit-20260917/24.csv'
OUT = ROOT / 'docs/game24_100q'
SNAPSHOT = ROOT / 'outputs/game24-100q-20261014/snapshot'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_rows(path, rows):
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

def source_rows():
    with SOURCE.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    mapping = {tuple(sorted(map(int, r['Puzzles'].split()))): str(r['Rank']) for r in rows}
    if len(rows) != 1362 or len(mapping) != 1362:
        raise ValueError('Source universe not 1362 unique multisets')
    return rows, mapping

def collect_material(value, mapping, found):
    if isinstance(value, dict):
        nums = value.get('answer', value.get('numbers'))
        if isinstance(nums, list) and len(nums) == 4 and all(type(x) is int for x in nums):
            key = tuple(sorted(nums))
            if key in mapping:
                found.add(key)
        for v in value.values():
            collect_material(v, mapping, found)
    elif isinstance(value, list):
        for v in value:
            collect_material(v, mapping, found)

def exposure(mapping):
    evidence = defaultdict(list)
    frozen_history = OUT/'historical_exclusion_frozen.json'
    if frozen_history.exists():
        for r in json.loads(frozen_history.read_text(encoding='utf-8'))['questions']:
            key=tuple(r['numbers'])
            if key in mapping:
                evidence[key].append(dict(kind='frozen_preacquisition_historical_exclusion', **r))
    for r in json.loads((SNAPSHOT / 'exposure_inventory.json').read_text(encoding='utf-8')):
        key = tuple(r['numbers'])
        if key in mapping:
            evidence[key].append(dict(kind='persisted_experiment_or_draft_pair', **r))
    remote_inventory = SNAPSHOT.parent/'remote_material_inventory.json'
    if remote_inventory.exists():
        for r in json.loads(remote_inventory.read_text(encoding='utf-8')):
            key = tuple(r['numbers'])
            if key in mapping: evidence[key].append(r)
    # Conservative exclusion of material prepared for development or scoring, even
    # if natural generation never ran. Baseline-only source manifests are exempt.
    for base in ('outputs', 'runs'):
        for p in sorted((ROOT / base).rglob('*.json')):
            if 'game24-100q-20261014' in p.parts or 'snapshot' in p.parts:
                continue
            if p.name not in {'manifest.json', 'plan.json', 'pool_manifest.json'}:
                continue
            if any(x in p.as_posix() for x in ['baseline-screen', 'dual-anchor-20q', 'batch03_interrupted',
                                               'batch04_screen_8b', 'protocol-parity-audit']):
                continue
            try:
                value = json.loads(p.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError):
                continue
            found = set()
            collect_material(value, mapping, found)
            for key in found:
                evidence[key].append(dict(kind='historical_development_material', path=p.relative_to(ROOT).as_posix()))
    return evidence

def actual_intervention_evidence(mapping):
    found = defaultdict(list)
    for base in ('outputs', 'runs'):
        for p in (ROOT/base).rglob('results.jsonl'):
            if 'game24-100q-20261014' in p.parts:
                continue
            for n, line in enumerate(p.open(encoding='utf-8'), 1):
                try: r = json.loads(line)
                except (ValueError, UnicodeError): continue
                nums = r.get('answer')
                if not isinstance(nums, list) or len(nums) != 4 or not all(type(x) is int for x in nums):
                    continue
                key = tuple(sorted(nums))
                if key not in mapping: continue
                for g in r.get('init_response_generations', []):
                    md = g.get('selective_context_metadata', {})
                    req = md.get('request') or r.get('init_response_generations_metadata', {}).get('intervention', {})
                    condition = req.get('condition_id', md.get('condition_id'))
                    if condition and condition != 'R0':
                        found[key].append(dict(path=p.relative_to(ROOT).as_posix(), line=n, condition=condition))
    return found

def batch_name(path):
    return path.relative_to(SNAPSHOT / 'outputs').parts[0]

def classify(record, batch, old_label=None):
    g = record['init_response_generations'][0]
    complete = g.get('finish_reason') in ('eos', 'stop')
    parsed = record.get('thinking_status') == 'parsable_thinking'
    final = record.get('final_response') or ''
    if not complete:
        return 'truncated_or_incomplete', {'finish_reason': g.get('finish_reason')}
    if not parsed or not final.strip():
        return 'malformed_or_empty', {'thinking_status': record.get('thinking_status')}
    expr = g.get('extracted_answer') or ''
    measure = expression_measurement(expr, record['answer'])
    if g.get('correctness') is True:
        return ('correct' if measure['exact_game24'] else 'correct_label_pending_review'), measure
    if old_label:
        return old_label['classification'], dict(reason=old_label['reason'], measurement=measure)
    # This function's frozen scalar/mixed-answer decisions apply ONLY to Batch03.
    if batch == 'game24-batch03-dual-anchor-20260924' and g.get('correctness') is False:
        fields = record_fields(record)
        fields['valid_for_eligibility'] = True
        category, reason, _ = manual_classification(fields)
        if category == 'format_or_extraction_false_negative':
            return 'extraction_miss_correct', dict(reason=reason, measurement=measure)
        if category == 'substantive_error':
            return category, dict(reason=reason, measurement=measure)
        return 'pending_review', dict(reason=reason, measurement=measure)
    if batch == 'game24-baseline-screen-vllm-20260918-batch02' and g.get('correctness') is False:
        body_expr = BODY.get(record.get('draft_key'))
        if body_expr:
            body_measure = expression_measurement(body_expr, record['answer'])
            return ('extraction_miss_correct' if body_measure['exact_game24'] else 'substantive_error'), dict(
                reason='Frozen Batch02 full-response adjudication; exact expression rechecked',
                expression=body_expr, measurement=body_measure)
    if measure['exact_game24']:
        return 'extraction_miss_correct', measure
    # Invalid parsed FINAL boxed formula is a program-verifiable substantive error;
    # scalar-only and multiple-candidate answers remain pending full-text review.
    candidates = valid_response_expressions(final, record['answer'])
    if measure['evaluation_status'] == 'ok' and expr.strip() != '24' and not candidates and '\\boxed' in final:
        return 'substantive_error', dict(reason='Final boxed expression violates exact value or operand inventory',
                                         measurement=measure)
    return ('none_pending_review' if g.get('correctness') is None else 'pending_review'), dict(
        extracted=expr, measurement=measure, valid_alternatives=candidates)

def eligible(rows, strict=True):
    if strict:
        return sum(r['classification'] in ('correct', 'extraction_miss_correct') for r in rows) >= 2 and sum(
            r['classification'] == 'substantive_error' for r in rows) >= 2
    valid = [r for r in rows if r['finish_reason'] in ('stop', 'eos') and r['thinking_status'] == 'parsable_thinking']
    return sum(r['official_correctness'] is True for r in valid) >= 2 and sum(
        not r['official_correctness'] for r in valid) >= 2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    frozen = out/'game24_eligible_100.jsonl'
    if frozen.exists() and frozen.stat().st_size:
        raise RuntimeError('A frozen eligible dataset already exists; choose a new --output for re-audit')
    universe, mapping = source_rows()
    exposed = exposure(mapping)
    intervention_evidence = actual_intervention_evidence(mapping)
    for key, evidence in intervention_evidence.items():
        exposed[key].extend(dict(kind='actual_intervention', **r) for r in evidence)
    # Ensure the downloaded raw files remain identical to the read-only server snapshot.
    for f in json.loads((SNAPSHOT/'snapshot_file_manifest.json').read_text(encoding='utf-8')):
        if sha((SNAPSHOT/f['path']).read_bytes()) != f['sha256']:
            raise RuntimeError('Snapshot file checksum changed: '+f['path'])
    historical_labels = {}
    label_path = ROOT / 'runs/batch04_screen_8b_audit_20260925/manual_audit_decisions.json'
    for x in json.loads(label_path.read_text(encoding='utf-8'))['decisions']:
        y = dict(x)
        if y['classification'] == 'format_or_extraction_false_negative':
            y['classification'] = 'extraction_miss_correct'
        historical_labels[('game24-batch04-dual-anchor-screen-20260925', ANCHORS[0], str(x['id']), x['sample_index'])] = y
    new_reviews = out / 'manual_reviews.jsonl'
    reviews = {}
    if new_reviews.exists():
        for line in new_reviews.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            reviews[r['trajectory_id']] = r
    pool, raw_by_uid, identities, draws, files, summaries = [], {}, {}, {}, [], []
    grouped = defaultdict(list)
    acquisition = SNAPSHOT.parent/'acquisition'
    paths = list((SNAPSHOT/'outputs').rglob('draft_candidates.jsonl')) + list(acquisition.rglob('draft_candidates.jsonl'))
    for p in sorted(paths):
        # Prefer original chunks over concatenated model summaries.
        if p.parent.name in ANCHORS and list(p.parent.glob('chunk-*/draft_candidates.jsonl')):
            continue
        cfg_path = p.parent / 'config.json'
        cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}
        batch = cfg.get('acquisition_batch') or batch_name(p)
        if (p.parent / 'summary.json').exists():
            summary = json.loads((p.parent / 'summary.json').read_text(encoding='utf-8'))
            summaries.append(dict(batch=batch, model=cfg.get('model_alias'), path=str(p.parent.relative_to(ROOT)), **summary))
        raw_file = p.read_bytes()
        files.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(raw_file), bytes=len(raw_file)))
        for n, line in enumerate(raw_file.decode('utf-8').splitlines(), 1):
            if not line.strip():
                continue
            r = json.loads(line)
            nums = r.get('answer')
            if not isinstance(nums, list) or tuple(sorted(nums)) not in mapping:
                continue
            gens = r.get('init_response_generations', [])
            for g in gens:
                meta = r.get('init_response_generations_metadata', {})
                model = meta.get('model_config_alias', cfg.get('model_alias', 'unknown'))
                idx = int(str(r['draft_key']).rsplit('/', 1)[-1]) if r.get('draft_key') else int(g.get('response_id', 0))
                key = tuple(sorted(nums))
                qid = mapping[key]
                prompt = r.get('init_response_prompt', '')
                smeta = g.get('selective_context_metadata', {})
                base_seed = cfg.get('seed', smeta.get('sample_seed', meta.get('intervention', {}).get('sample_seed')))
                # n-way vLLM children use parent seed + response index. Legacy
                # metadata sometimes stores only the parent's seed.
                seed = smeta.get('sample_seed') if smeta.get('resume_seed_policy') else (
                    base_seed + idx if base_seed is not None and 'vllm' in str(smeta.get('backend', '')).lower() else base_seed)
                uid = f'{batch}/{model}/{qid}/{idx}'
                fingerprint = sha(json.dumps(dict(prompt=prompt, response=g.get('generated_response'),
                                                  correctness=g.get('correctness'), finish=g.get('finish_reason')),
                                            sort_keys=True).encode('utf-8'))
                if uid in identities:
                    if identities[uid] != fingerprint:
                        raise RuntimeError(f'Conflicting source identity {uid}')
                    continue
                identities[uid] = fingerprint
                # Deduplicate copied source draws, never by normalized formula.
                draw = (model, sha(prompt.encode('utf-8')), seed, idx, sha((g.get('generated_response') or '').encode('utf-8')))
                if draw in draws:
                    continue
                draws[draw] = uid
                category, audit = classify(r, batch, historical_labels.get((batch, model, str(r['id']), idx)))
                rawhash = sha(line.encode('utf-8'))
                if uid in reviews:
                    rev = reviews[uid]
                    if rev['raw_record_sha256'] != rawhash:
                        raise RuntimeError(f'Stale manual review {uid}')
                    category, audit = rev['classification'], rev
                ordinary = 'ordinary' in str(smeta.get('backend', '')).lower() or 'baseline-screen-vllm' in batch
                sampling = cfg.get('sampling', {})
                reuse = model in ANCHORS and ordinary and sampling.get('temperature') == 0.6 and sampling.get('top_p') == 0.95 and sampling.get('top_k') == 20 and cfg.get('context_length') == 32768
                acquisition_batch = 'batch02_dual_anchor' if batch in (
                    'game24-baseline-screen-vllm-20260918-batch02', 'game24-batch02-qwen32b-20260919') else batch
                t = dict(trajectory_id=uid, canonical_question_id='tot-rank:' + qid,
                         tot_rank=qid, original_id=str(r['id']), numbers=list(key), batch=batch,
                         acquisition_batch=acquisition_batch, source_model=model, target_model='Qwen3_8B_Thinking',
                         self_or_cross='self' if model == ANCHORS[0] else 'cross',
                         checkpoint=cfg.get('model'), sample_index=idx, base_seed=base_seed,
                         effective_sample_seed=seed, seed_verified=seed is not None,
                         prompt=prompt, sampling_parameters=sampling, generation_budget=32768-smeta.get('prompt_tokens', 0),
                         full_generated_text=g.get('generated_response'), final_answer=r.get('final_response'),
                         extracted_answer=g.get('extracted_answer'), thinking_status=r.get('thinking_status'),
                         finish_reason=g.get('finish_reason'), vllm_finish_reason=g.get('vllm_finish_reason'),
                         official_correctness=g.get('correctness'), classification=category, audit=audit,
                         generated_tokens=r.get('tokens', len(r.get('generated_token_ids', []))),
                         source_path=p.relative_to(ROOT).as_posix(), source_line=n,
                         raw_record_sha256=rawhash, reusable_adapted_protocol=reuse,
                         historical_development=key in exposed)
                pool.append(t)
                raw_by_uid[uid] = r
                grouped[key].append(t)
    # Full prompt, thinking, response, token IDs and scorer fields are already in
    # immutable raw snapshot files. Keep a compact, hash-bound per-record index.
    index = []
    for r in pool:
        item = {k:v for k,v in r.items() if k not in ('prompt', 'full_generated_text')}
        item.update(prompt_sha256=sha(r['prompt'].encode('utf-8')),
                    generated_text_sha256=sha((r['full_generated_text'] or '').encode('utf-8')),
                    full_text_storage='source_path/source_line raw JSON record; full prompt and generated_response retained',
                    raw_field_paths=dict(prompt='init_response_prompt', generated_text='init_response_generations[0].generated_response'))
        index.append(item)
    write_rows(out / 'game24_trajectory_pool.jsonl', index)
    pending = [r for r in pool if r['classification'] in ('pending_review', 'none_pending_review', 'correct_label_pending_review')]
    write_rows(out / 'pending_response_review.jsonl', pending)
    manifest, accepted = [], []
    for source in universe:
        key = tuple(sorted(map(int, source['Puzzles'].split())))
        rows = grouped[key]
        reuse = [r for r in rows if r['reusable_adapted_protocol']]
        counts = {m: dict(Counter(r['classification'] for r in reuse if r['source_model'] == m)) for m in ANCHORS}
        # A fixed-prefix8 pool must have all 8 slots for BOTH anchors from the same
        # baseline batch. Partial Batch03 data never masquerade as completed quotas.
        batches = sorted({r['acquisition_batch'] for r in reuse})
        complete_batches = [b for b in batches if all({r['sample_index'] for r in reuse if r['acquisition_batch'] == b and r['source_model'] == m} >= set(range(8)) for m in ANCHORS)]
        strict = eligible(reuse)
        strict_prefix8 = eligible([r for r in reuse if r['sample_index'] < 8])
        compatible = eligible(reuse, False)
        in_pool = strict and bool(complete_batches) and key not in exposed
        reasons = []
        if key in exposed: reasons.append('historical_development_or_experiment_material')
        if not complete_batches: reasons.append('missing_uniform_dual_anchor_prefix8')
        if not strict: reasons.append('fewer_than_two_verified_correct_or_substantive_errors')
        q = dict(canonical_question_id='tot-rank:' + str(source['Rank']), tot_rank=str(source['Rank']),
                 numbers=list(key), source_revision='8050e67d0e3a0fddc424d7fa5801538722a4c4cc',
                 source_sha256=sha(SOURCE.read_bytes()), dedup_key=','.join(map(str, key)),
                 anchor_sample_counts={m: sum(r['source_model'] == m for r in reuse) for m in ANCHORS},
                 anchor_classification_counts=counts, protocol_compatible_eligibility=compatible,
                 strict_substantive_error_eligibility=strict, complete_dual_anchor_prefix8_batches=complete_batches,
                 strict_prefix8_eligibility=strict_prefix8,
                 historical_development=key in exposed, intervention_or_material_evidence=exposed.get(key, []),
                 used_in_subsequent_intervention=True if intervention_evidence.get(key) else None if key in exposed else False,
                 intervention_usage_status='verified_from_local_raw' if intervention_evidence.get(key) else
                     'no_local_raw_evidence_conservatively_excluded_if_historical_material',
                 included_in_new_pool=in_pool, inclusion_or_exclusion_reason=reasons or ['audited_baseline_only_pool'],
                 all_trajectory_ids=[r['trajectory_id'] for r in rows])
        manifest.append(q)
        if in_pool:
            selected = {c: sorted(r['trajectory_id'] for r in reuse if r['classification'] in values)[:2]
                        for c, values in [('correct', ('correct', 'extraction_miss_correct')),
                                          ('substantive_error', ('substantive_error',))]}
            accepted.append(dict(**q, witnesses=selected,
                                 failed_draft_selection='lexicographic trajectory ID before intervention; no effect inspected'))
    write_rows(out / 'game24_question_manifest.jsonl', manifest)
    # Do not claim target achievement or freeze a split before at least 100.
    write_rows(out / 'game24_eligible_candidates.jsonl', accepted)
    target_met = len(accepted) >= 100
    if target_met:
        write_rows(out / 'game24_eligible_100.jsonl', accepted)
        ids = sorted(r['canonical_question_id'] for r in accepted)
        random.Random(20261014).shuffle(ids)
        split = dict(state='frozen', seed=20261014, development=ids[:20], held_out=ids[20:])
    else:
        (out / 'game24_eligible_100.jsonl').write_text('', encoding='utf-8')
        split = dict(state='not_frozen_target_not_met', seed=20261014, development=[], held_out=[],
                     eligible_candidates=len(accepted), required_questions=100)
    dump(out / 'game24_split_manifest.json', split)
    batch_stats, replay = [], []
    for batch in sorted({r['acquisition_batch'] for r in pool}):
        rs = [r for r in pool if r['acquisition_batch'] == batch]
        raw_batches = {r['batch'] for r in rs}
        qs = sorted({tuple(r['numbers']) for r in rs})
        ss = []
        for raw_batch in raw_batches:
            chunks = [s for s in summaries if s['batch'] == raw_batch and 'chunk-' in s['path']]
            ss.extend(chunks or [s for s in summaries if s['batch'] == raw_batch])
        # Files from the same logical batch can include aggregate copies. Chunk
        # totals take precedence; do not add aggregate time to chunk time.
        generation_seconds = sum(s.get('generation_seconds', 0) for s in ss)
        total_seconds = sum(s.get('total_seconds', 0) for s in ss)
        batch_stats.append(dict(batch=batch, questions=len(qs), records=len(rs),
                                classifications=dict(Counter(r['classification'] for r in rs)),
                                tokens=sum(r['generated_tokens'] for r in rs),
                                generation_gpu_hours=generation_seconds/3600 if ss and all('generation_seconds' in s for s in ss) else None,
                                measured_job_hours=total_seconds/3600 if ss and all('total_seconds' in s for s in ss) else None,
                                eligible_all=sum(eligible([r for r in rs if tuple(r['numbers']) == q]) for q in qs)))
        prev = 0
        prev_complete = None
        for prefix in (4, 8, 12, 16):
            complete = [q for q in qs if all({r['sample_index'] for r in rs if tuple(r['numbers']) == q and r['source_model'] == m} >= set(range(prefix)) for m in ANCHORS)]
            selected = [r for r in rs if tuple(r['numbers']) in complete and r['sample_index'] < prefix]
            hits = [q for q in complete if eligible([r for r in selected if tuple(r['numbers']) == q])]
            alone = {m: sum(eligible([r for r in selected if tuple(r['numbers']) == q and r['source_model'] == m]) for q in complete) for m in ANCHORS}
            # n16 reference is available only on dual-complete16 questions.
            complete16 = [q for q in complete if all({r['sample_index'] for r in rs if tuple(r['numbers']) == q and r['source_model'] == m} >= set(range(16)) for m in ANCHORS)]
            full_hits = [q for q in complete16 if eligible([r for r in rs if tuple(r['numbers']) == q])]
            replay.append(dict(batch=batch, prefix=prefix, complete_questions=len(complete), eligible=len(hits),
                               newly_eligible_on_same_complete_set=len(hits)-prev if prev_complete is None or set(complete) == prev_complete else None,
                               alone_eligible=alone, anchor_marginal={m: len(hits)-alone[ANCHORS[1-i]] for i,m in enumerate(ANCHORS)},
                               tokens=sum(r['generated_tokens'] for r in selected),
                               missed_full16_eligible=sum(q not in hits for q in full_hits), full16_reference=len(full_hits),
                               prefix_gpu_hours=None, reason='Concurrent chunk wall time cannot be apportioned to sample prefixes'))
            prev, prev_complete = len(hits), set(complete)
    dump(out / 'source_file_manifest.json', files)
    dump(out / 'sampling_efficiency.json', dict(batches=batch_stats, prefix_replay=replay,
         prefix_cost_identifiable=False, cost_note='Token prefixes measured; GPU hours measured for whole completed chunks only'))
    summary = dict(source_questions=1362, baseline_records=len(pool), baseline_questions=sum(bool(rs) for rs in grouped.values()),
                   historical_material_questions=len(exposed), reusable_records=sum(r['reusable_adapted_protocol'] for r in pool),
                   protocol_compatible_questions=sum(q['protocol_compatible_eligibility'] for q in manifest),
                   strict_questions_all=sum(q['strict_substantive_error_eligibility'] for q in manifest),
                   unexposed_strict_without_complete_quota=sum(q['strict_substantive_error_eligibility'] and not q['historical_development'] and not q['complete_dual_anchor_prefix8_batches'] for q in manifest),
                   admitted_independent_questions=len(accepted), admitted_ids=[q['tot_rank'] for q in accepted],
                   pending_responses=len(pending), target_met=target_met,
                   fresh_questions_available=sum(not q['historical_development'] and not q['all_trajectory_ids'] for q in manifest),
                   new_generations_this_task=sum(r['batch'].startswith('game24-100q-') for r in pool),
                   new_gpu_hours_this_task=sum(s.get('total_seconds',0)/3600 for s in summaries if s['batch'].startswith('game24-100q-')),
                   limitations=['Historical material exclusion includes prepared but potentially unrun questions; it is deliberately conservative.',
                                'Local and server baseline snapshots and material manifests checked; future or unindexed external usage cannot be ruled out.',
                                'Eligibility uses all verified baseline responses; prefix8 eligibility is reported separately for quota sensitivity.'])
    dump(out / 'audit_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    main()
