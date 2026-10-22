"""Prepare a reviewable next experiment from saved baseline data; never generate."""
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from analyze_batch03_partial_20260924 import is_valid, manual_classification, record_fields, sha256

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/batch03_interrupted_20260924'
RAW = RUN / 'raw'
OUT = ROOT / 'runs/batch03_next_experiment_20260924'


def main():
    manifest = json.loads((RAW / 'baseline_manifest_batch03_20260919.json').read_text(encoding='utf-8'))
    ordered = [str(row['id']) for row in manifest['candidate_rows']]
    counts = defaultdict(Counter)
    failures = defaultdict(list)
    seen = set()
    source_hashes = {}
    for path in sorted(RAW.glob('*/chunk-*/draft_candidates.jsonl')):
        digest = sha256(path)
        source_hashes[path.relative_to(ROOT).as_posix()] = digest
        for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            record = json.loads(line)
            row = record_fields(record)
            identity = (row['model'], row['id'], row['sample_index'])
            if identity in seen:
                raise RuntimeError(f'Duplicate identity: {identity}')
            seen.add(identity)
            qid = row['id']
            counts[qid][row['model']] += 1
            if not is_valid(record):
                continue
            if row['correctness'] is True:
                counts[qid]['official_true'] += 1
            elif row['correctness'] is False:
                category, reason, _ = manual_classification(dict(row, valid_for_eligibility=True))
                if category == 'uncertain_manual_confirmation':
                    raise RuntimeError(f'Unresolved audit: {identity}')
                if category == 'substantive_error':
                    counts[qid]['substantive_false'] += 1
                    failures[qid].append((row['model'], row['sample_index'], record,
                        path.relative_to(ROOT).as_posix(), line_number, digest, reason))
    if len(seen) != 864:
        raise RuntimeError('Baseline snapshot changed; review before preparing another plan')
    complete = [qid for qid in ordered if all(counts[qid][m] == 16 for m in ('Qwen3_8B_Thinking', 'Qwen3_32B'))]
    passes = [qid for qid in ordered if counts[qid]['official_true'] >= 2 and counts[qid]['substantive_false'] >= 2]
    eligible = [qid for qid in passes if qid in complete]
    partial = [qid for qid in passes if qid not in complete]
    # Enforce the original official-True criterion, rather than silently promoting manual corrections.
    if eligible != ['195', '434', '215', '144', '1281', '395', '1206', '381']:
        raise RuntimeError(f'Eligibility changed: {eligible}')
    previous_pairs = ROOT / 'outputs/game24-batch02-validation-20260920-source/pairs.jsonl'
    prior = [json.loads(line) for line in previous_pairs.read_text(encoding='utf-8').splitlines()]
    if set(eligible) & {str(row['id']) for row in prior}:
        raise RuntimeError('Batch02 question overlap')
    previous_numbers = {tuple(sorted(row['answer'])) for row in prior}
    pairs = []
    for qid in eligible:
        pool = sorted(failures[qid], key=lambda item: (item[0], item[1]))
        model, index, record, source, line, digest, reason = random.Random('20270918:' + qid).choice(pool)
        if tuple(sorted(record['answer'])) in previous_numbers:
            raise RuntimeError('Batch02 number-multiset overlap')
        if not record['final_response'].strip():
            raise RuntimeError('Empty failed final response')
        pairs.append(dict(id=qid, task='game24', problem=record['problem'], answer=record['answer'],
            traj1=record['final_response'], audit_status='substantive_failed', draft_key=record['draft_key'],
            source_model=model, stratum='dual_anchor_batch03_interrupted_complete_prefix', benchmark='Game24',
            source=source, source_line=line, source_sha256=digest, audit_reason=reason,
            draft_sha256=hashlib.sha256(record['final_response'].encode()).hexdigest(),
            eligible_failed_pool_size=len(pool)))
    OUT.mkdir(exist_ok=True)
    pairs_path = OUT / 'pairs.jsonl'
    pairs_path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in pairs), encoding='utf-8')
    plan = dict(status='prepared_not_launched', generate=False,
        scientific_generations=64, question_ids=eligible, question_count=len(eligible),
        target_model='Qwen3_8B_Thinking', seeds=[927001, 927002], conditions=['R0', 'R2', 'R3', 'R4'],
        primary_effects=['R0-R2', 'R3-R2'], secondary_effects=['R4-R2', 'R4-R3'],
        pairs_file=pairs_path.relative_to(ROOT).as_posix(), pairs_sha256=sha256(pairs_path),
        draft_selection="random.Random('20270918:'+qid).choice(pool sorted by model alias and integer sample index)",
        correctness_rule='Official True >=2; official False, valid EOS/parse and manually substantive >=2. Manual extraction corrections never supply the official-True gate.',
        candidate_coverage=dict(frozen=32, dual_complete=22, partial=10, eligible_complete=eligible, eligible_partial=partial),
        counts={qid: dict(counts[qid]) for qid in ordered},
        source_hashes=source_hashes, batch02_pairs_sha256=sha256(previous_pairs),
        sensitivity_exclude_question_ids=['381'],
        limitations=['Batch03 was stopped for runtime/cache pressure after outcomes from earlier experiments were known.',
                     'Completed-prefix coverage may correlate with answer length/difficulty; this is a documented revised cohort, not the full frozen 32-question batch.',
                     'Report Batch03 separately and Batch02+Batch03 as a secondary pooled analysis; exclude pilot/development questions.',
                     '16 eligible questions across Batch02 and this plan is below the original 20-30 target; do not claim adequate power from the count alone.'],
        execution_requirements=['Use the same validated selective backend and frozen sampling/scoring as Batch02, including fresh paired R0.',
                                'Prepare tokenizer bundles; validate same R2/R3/R4 text/tokens/positions and mask onset before generation.',
                                'Persist each response; include all requested outputs in denominators; question-cluster CI and paired transitions.',
                                'Verify GPU ownership and availability; never stop an unrelated process.',
                                'No automatic acquisition, expansion, or follow-up generation.'])
    (OUT / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(eligible=eligible, partial=partial, pairs_sha256=plan['pairs_sha256'],
                         selected=[dict(id=p['id'], model=p['source_model'], draft=p['draft_key']) for p in pairs],
                         scientific_generations=64, generate=False), indent=2))


if __name__ == '__main__':
    main()
