"""Persist manual adjudications and CPU-only wrapper checks; never generate."""
import csv
import io
import json
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from selective_context.tasks import independent_prompt
from selective_context.testing import CharacterTokenizer
from selective_context.prompting import encode_prompt, make_r2_r4_requests, assert_same_text_contract

OUT = ROOT / 'outputs/public-uft-audit-20260919'
# Manual review of the already frozen reservoir; no intervention results consulted.
NOTES = {
    '450': '最终式等于27，不是24；三步算术本身正确。',
    '731': '最终式实际等于4且重复使用2、4；中间凭空多出一个2；四步。',
    '421': '最终式和三步结果均为18，不是24。',
    '561': '最终式((12/3)*9)-12合法且等于24；前文六步路线不一致并引入新数。不能用当前“最终答案错误”提示词。',
    '231': '最终式和三步结果均为72，不是24。',
    '263': '最终式实际为21，却写24；第四步重复使用6。',
    '273': '最终式实际为-3，并以11替代原始3；三步结果为11。',
    '280': '最终式实际为42，重复使用2；三步结果为30。',
    '838': '最终式实际为20，重复使用3；第四步凭空加入6。',
    '14': '最终式实际为22/3，重复使用6；三步结果为27.5。',
    '619': '最终式实际为-12，重复使用10；left状态重复保留已消耗的10；四步。',
    '423': '最终式实际为-50，重复使用13、3；left状态凭空增加5；四步。',
    '519': '最终式实际为13，却写24；三步结果也为13。',
    '646': '反复减1并引入新数，末尾停在“-10 - 1”，无Answer；明显不完整，排除。',
    '453': '步骤声称4*8=24，实际32；最终式实际为-32。',
    '67': '最终表达式3*(9-(9-8))合法且等于24，但等号右侧写27；不是纯格式问题，主池排除以免oracle歧义。',
    '130': '最终式实际为11，却写24。',
    '437': '最终式实际为12，却写24。',
    '869': '最终式实际为74且重复使用10；三步结果为20。',
    '53': '最终式实际为6且重复使用4；三步结果为2。',
}

def main():
    sample = json.loads((OUT / 'random20.json').read_text(encoding='utf-8'))
    reviewed = []
    examples = []
    lines = ['# 公开 UFT：固定随机20条人工审计', '',
             '抽样种子20260919；从全部470898条7B CoT failed行进行reservoir抽样，先抽后审；不是按题均匀抽样。',
             '保留源文件、零基数据行号和完整已发布path。未使用任何intervention outcome。',
             '所有记录均缺少EOS/finish_reason；“完整外观”不等于已证明正常终止。', '']
    for i, row in enumerate(sample, 1):
        cid = row['case_id']
        if cid == '646':
            verdict = 'visibly_incomplete'
        elif cid in ('561', '67'):
            verdict = 'valid_final_expression_with_inconsistent_trace_or_rhs'
        elif len(row['path']) == 5:
            verdict = 'substantive_canonical_candidate'
        else:
            verdict = 'substantive_extra_steps_candidate'
        row = dict(row, manual_verdict=verdict, manual_evidence=NOTES[cid],
                   original_finish_reason='unavailable',
                   primary_shape_candidate=verdict == 'substantive_canonical_candidate')
        reviewed.append(row)
        lines += [f'## {i}. 题{cid}：{verdict}', '', NOTES[cid], '',
                  f"来源：`{row['file']}`；数据行索引`{row['row_index']}`；历史重叠`{row['historical_overlap']}`。", '',
                  '```text', '\n'.join(row['path']), '```', '']
        if row['primary_shape_candidate']:
            # Preserve every published path string; no repairs or invented reasoning.
            draft = '\n'.join(row['path'])
            prompt = independent_prompt('Use each of ' + row['path'][0] + ' exactly once to make 24.', draft)
            encoded = encode_prompt(CharacterTokenizer(), prompt)
            requests = make_r2_r4_requests(encoded, 0)
            assert_same_text_contract(requests)
            start, end = encoded.draft_character_span
            assert prompt[start:end] == draft
            assert all(r.input_ids == requests[0].input_ids for r in requests)
            examples.append(dict(case_id=cid, source_file=row['file'], source_row=row['row_index'],
                                 draft=draft, prompt_text=prompt, draft_character_span=[start,end],
                                 prompt_sha256=requests[0].prompt_sha256,
                                 same_text_contract=True, tokenizer='CharacterTokenizer CPU fixture only',
                                 generate=False, real_qwen_tokenizer_checked=False))
    counts = Counter(r['manual_verdict'] for r in reviewed)
    (OUT / 'random20_reviewed.json').write_text(json.dumps(reviewed, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'random20_review.md').write_text('\n'.join(lines), encoding='utf-8')
    (OUT / 'wrapper_audit_examples.json').write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding='utf-8')
    per_question = Counter()
    with zipfile.ZipFile(OUT / 'data.zip') as z:
        for name in sorted(z.namelist()):
            if name.startswith('data/game24/corpora/') and name.endswith('/failed_train.csv'):
                for row in csv.DictReader(io.TextIOWrapper(z.open(name), encoding='utf-8')):
                    per_question[row['case_id']] += 1
    result = dict(manual_sample_counts=dict(counts), sample_size=len(reviewed),
                  pure_format_only_in_sample=0, cpu_wrapper_checks_passed=len(examples),
                  real_model_checks=0, new_generations=0,
                  all_failed_mean_per_question=statistics.mean(per_question.values()),
                  all_failed_median_per_question=statistics.median(per_question.values()))
    (OUT / 'manual_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
