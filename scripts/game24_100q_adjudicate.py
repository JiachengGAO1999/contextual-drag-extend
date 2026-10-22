"""Full-final-answer review decisions made on 2026-10-14, bound to raw hashes."""
import json
from pathlib import Path
from analyze_batch03_partial_20260924 import expression_measurement

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/game24_100q'
# Read the complete final prose before recording these expressions. A valid
# abandoned alternative never rescues an explicitly selected invalid final.
EXPRESSIONS = {
 'game24-baseline-screen-vllm-20260917-retry1/Qwen3_8B_Thinking/753/0': '8*(3+1)-8',
 'game24-baseline-screen-vllm-20260917-retry1/Qwen3_8B_Thinking/753/1': '(1+3)*8-8',
 'game24-baseline-screen-vllm-20260917-retry1/Qwen3_8B_Thinking/1057/1': '6*((12-9)+(9/9))',
 'game24-baseline-screen-vllm-20260917-retry1/Qwen3_8B_Thinking/125/2': '4*6*(4-3)',
 'game24-baseline-screen-vllm-20260918-batch02/Qwen3_8B_Thinking/1305/4': '(10*(13-(10/10)))/5',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/6/6': '12*2*(1/1)',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/6/13': '12*2+1-1',
 'game24-dual-anchor-20q-20260917/Qwen3_32B/44/8': '(12+12)*(10/10)',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/44/4': '12*((12/12)+(10/10))',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/137/4': '6*4*(7-6)',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/1293/13': '8*5-11-5',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/655/5': '12*(8/(7-3))',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/753/9': '8*(1+3)-8',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/753/11': '8*(3+1)-8',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/41/5': '12*1+11+1',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/41/8': '(12*(1+1))/(11/11)',
 'game24-dual-anchor-20q-20260917/Qwen3_32B/1057/5': '12*((9-6)/(9/6))',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/1033/3': '(9/(4-1))*8',
 'game24-dual-anchor-20q-20260917/Qwen3_8B_Thinking/152/14': '(13+11)*(10/10)',
 'game24-qwen3-8b-thinking-r0-r4-20260906/Qwen3_8B_Thinking/170/3': '6*(6/2)+1',
 'game24-qwen3-8b-thinking-r0-r4-20260906/Qwen3_8B_Thinking/159/2': '12*((13-5)/4)',
 'game24-stage-b-drafts-20260911/Qwen3_8B_Thinking/123/1': '8*(5-(8/(5-1)))',
 'game24-stage-b-drafts-20260911/Qwen3_8B_Thinking/71/0': '12*(7-(11-7))',
 'game24-stage-b-drafts-20260911/Qwen3_8B_Thinking/23/3': '12+12+11-11',
 'game24-stage-b-drafts-20260911/Qwen3_8B_Thinking/513/0': '13*3-(9+13)',
}

def main():
    rows = [json.loads(x) for x in (OUT/'game24_trajectory_pool.jsonl').read_text(encoding='utf-8').splitlines()]
    decisions = []
    for r in rows:
        expr = EXPRESSIONS.get(r['trajectory_id'])
        if expr is None:
            continue
        m = expression_measurement(expr, r['numbers'])
        assert m['evaluation_status'] == 'ok'
        category = 'extraction_miss_correct' if m['exact_game24'] else 'substantive_error'
        reason = 'Read full final response; explicitly endorsed final expression verified with rational arithmetic and exact input multiset.'
        if r['trajectory_id'].endswith('/44/4') or r['trajectory_id'].endswith('/1057/5') or r['trajectory_id'].endswith('/170/3'):
            reason += ' Valid earlier alternative does not override the explicitly selected wrong final formula.'
        if r['trajectory_id'].endswith('/71/0'):
            reason += ' Complete response repeatedly asserts a 36-valued expression as its solution and ends with scalar 24; substantive contradiction, not just missing box.'
        if r['trajectory_id'].endswith('/513/0'):
            # Conservatively do not count contradictory impossibility prose until
            # an exact solvability witness is recorded.
            category = 'excluded_ambiguous_failure'
            reason = 'Contradictory no-solution conclusion and scalar 24; exclude from strict failure witnesses.'
        decisions.append(dict(trajectory_id=r['trajectory_id'], raw_record_sha256=r['raw_record_sha256'],
                              classification=category, expression=expr, measurement=m, reason=reason,
                              reviewer='Codex full-final-text review 2026-10-14; no intervention outcome read'))
    with (OUT/'manual_reviews.jsonl').open('w', encoding='utf-8') as f:
        for r in decisions:
            f.write(json.dumps(r, ensure_ascii=False)+'\n')
    print(json.dumps(dict(reviewed=len(decisions))))

if __name__ == '__main__': main()
