"""Freeze audited public stimuli, no model generation and no outcome selection."""
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/math-external-16q-20260920-source'
SOURCE = ROOT / 'outputs/public-alternatives-audit-20260919'
SEEDS = [930001, 930002]
TRAIN = {
    1101: (3, 'Adjacent terms before26 are18,22. Draft skips22 and returns14+18=32.'),
    2383: (1, 'Only7 boxes reach100000; draft counts13 by including low-valued left-column boxes. Minimum12 low boxes gives7/14.'),
    3000: (1, 'Midpoint arcs enclose central area4-pi, not sum of corner sectors pi; rounded100k=86.'),
    3289: (11, 'Requested upper/right sector has angle3pi/4, not pi/4; area24pi, not8pi.'),
    5293: (13, 'Drops positive starting-term constraint in divisor count. Exhaustive enumeration gives15, not4.'),
    5300: (15, 'Adds invalid column bound c<=r; actual bound1<=c<=51-r gives17, not6. Earlier trace5 is truncated and excluded.'),
    6774: (12, 'Equality of squared cosine/sine does not imply both1/2; misses4 pairs. Enumerated96/400=6/25, not92/400.'),
    6835: (0, 'Confuses collinearity of vector endpoints with common scalar multiples. Projection foot is(4/7,5/7,8/7), not zero.'),
}

def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError('Refusing overwrite of nonempty source directory')
    OUT.mkdir(exist_ok=True)
    pairs = [json.loads(l) for l in (ROOT / 'outputs/math500-cipt-audit-20260920/candidate_pairs.jsonl').read_text(encoding='utf8').splitlines()]
    for p in pairs:
        p.update(stratum='MATH500_Qwen3_1.7B', source_completion='complete_text; EOS evidence checked separately', launch_ready=False)
    rows = pq.read_table(SOURCE / 'jrosser.parquet').to_pylist()
    for i, (trace, evidence) in TRAIN.items():
        r = next(r for r in rows if int(r['problem_idx']) == i and int(r['trace_idx']) == trace)
        assert not r['is_correct'] and '</think>' in r['response'] and '[asy]' not in r['problem']
        pairs.append(dict(id=f'math-train-public-{i}', task='math500', benchmark='MATH_train',
                          stratum='MATH_train_Qwen3_4B', problem=r['problem'], answer=r['gt_answer'],
                          traj1=r['response'], audit_status='substantive_failed', audit_evidence=evidence,
                          source='jrosseruk/Qwen3-4B-MATH-traces', source_index=i, source_trace=trace,
                          source_completion='complete text; original EOS/finish_reason unavailable', launch_ready=False))
    assert len(pairs) == 16
    assert len({''.join(p['problem'].split()) for p in pairs}) == 16
    for p in pairs:
        p['source_output_sha256'] = hashlib.sha256(p['traj1'].encode()).hexdigest()
        p['benchmark'] = p.get('benchmark', 'MATH500')
        assert '[asy]' not in p['problem']
    (OUT / 'pairs.jsonl').write_text(''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in pairs), encoding='utf8')
    (OUT / 'protocol.json').write_text(json.dumps(dict(
        n_questions=16, seeds=SEEDS, conditions=['R0','R2','R3','R4'], generations=128,
        selection='Manually verified substantive failures; fixed public question/trace IDs before intervention; no target R0 filtering.',
        draft='Full original output including thinking and final; no truncation.',
        exclusions='Format-only, incomplete, ambiguous and diagram-dependent candidates excluded.',
        strata={'MATH500_Qwen3_1.7B':8,'MATH_train_Qwen3_4B':8},
        source_finish_caveat='MATH-train public source lacks original finish_reason; text completeness is not proof of EOS.',
        scoring='math_verify_balanced_last_box_v1; final last box; multiple separately boxed answers require flagged secondary adjudication.',
        analysis='Primary source-stratified accuracy and paired effects; combined16 exploratory; question-cluster bootstrap.',
        source_model_and_benchmark_confounded=True,
        first_token='R3 retains complete prefill logits; unchanged late intervention boundary.'), indent=2), encoding='utf8')
    print('Frozen16 public pairs;128 planned generations; no generation started')

if __name__ == '__main__':
    main()
