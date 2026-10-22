"""CPU/tokenizer preflight, including prompt parity against completed Batch02."""
import hashlib
import importlib.metadata
import json
from collections import Counter, defaultdict
from pathlib import Path
from transformers import AutoTokenizer
from selective_context.prompting import load_request_bundle, render_chat_prompt, encode_prompt, encode_direct_prompt
from selective_context.tasks import independent_prompt
from selective_context.vllm_mask import NEVER, key_block_onsets, request_metadata

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('/data2/gaojc/tmp/math-external-16q-20260920')
PREP = ROOT / 'outputs/game24-batch03-8q-prepared'


def main():
    tok = AutoTokenizer.from_pretrained('/data2/huangrj/models/qwen3-8b', local_files_only=True)
    manifest = json.loads((PREP / 'manifest.json').read_text())
    plan = json.loads((ROOT / 'source/plan.json').read_text())
    assert hashlib.sha256((ROOT / 'source/pairs.jsonl').read_bytes()).hexdigest() == plan['pairs_sha256']
    assert len(manifest) == 64
    groups = defaultdict(dict)
    lengths = []
    for item in manifest:
        enc, reqs = load_request_bundle(ROOT / item['bundle'])
        req = next(r for r in reqs if r.condition_id == item['condition'])
        pair = json.loads((ROOT / item['pair']).read_text())
        req.validate()
        assert hashlib.sha256(pair['traj1'].encode()).hexdigest() == pair['draft_sha256']
        key = (pair['id'], req.sample_seed)
        assert req.condition_id not in groups[key]
        groups[key][req.condition_id] = req
        lengths.append(len(req.input_ids))
        assert 0 < len(req.input_ids) < 32768
    assert len(groups) == 16
    assert {q for q, s in groups} == set(plan['question_ids'])
    assert {s for q, s in groups} == {927001, 927002}
    for group in groups.values():
        assert set(group) == {'R0', 'R2', 'R3', 'R4'}
        r2, r3, r4 = (group[c] for c in ('R2', 'R3', 'R4'))
        assert r2.input_ids == r3.input_ids == r4.input_ids
        assert r2.prompt_sha256 == r3.prompt_sha256 == r4.prompt_sha256
        ds, de = r2.draft_token_span
        assert 0 < ds < de < len(r2.input_ids)
        for condition, onset in [('R2', NEVER), ('R3', len(r2.input_ids)), ('R4', de)]:
            onsets = key_block_onsets(request_metadata(group[condition]))
            assert all(v == (onset if ds <= k < de else NEVER) for k, v in enumerate(onsets))
        assert all(v == NEVER for v in key_block_onsets(request_metadata(group['R0'])))
    # Re-encode the prior experiment and compare against the actual frozen bundles.
    prior_manifest = json.loads((REFERENCE / 'outputs/game24-batch02-validation-20260920/manifest.json').read_text())
    for item in prior_manifest:
        enc, reqs = load_request_bundle(REFERENCE / item['bundle'])
        pair = json.loads((REFERENCE / item['pair']).read_text())
        is_r0 = item['condition'] == 'R0'
        text = independent_prompt(pair['problem'], None if is_r0 else pair['traj1'], 'game24')
        recreated = (encode_direct_prompt if is_r0 else encode_prompt)(tok, render_chat_prompt(tok, text, True))
        assert recreated.input_ids == enc.input_ids, ('reference prompt drift', pair['id'], item['condition'])
    ref_config = json.loads((REFERENCE / 'outputs/game24-batch02-validation-20260920/config.json').read_text())
    assert {k: ref_config[k] for k in ('temperature', 'top_p', 'top_k', 'context', 'batch_size')} == dict(temperature=.6, top_p=.95, top_k=20, context=32768, batch_size=8)
    assert importlib.metadata.version('vllm') == '0.11.0'
    files = [p for folder in ('selective_context', 'utils', 'data_generation', 'scripts', 'source')
             for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += list(PREP.glob('*.json'))
    report = dict(passed=True, scientific_requests=64, paired_units=16,
                  input_tokens_min=min(lengths), input_tokens_max=max(lengths),
                  batch02_prompt_parity_requests=len(prior_manifest),
                  reference_config=ref_config, versions={k: importlib.metadata.version(k) for k in ('vllm', 'torch', 'transformers')},
                  hashes={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})
    (ROOT / 'preflight.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'hashes'}, indent=2))


if __name__ == '__main__':
    main()
