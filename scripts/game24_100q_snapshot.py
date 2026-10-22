"""Read-only source snapshot; writes only its explicitly named new output folder."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

BASELINES = [
    'game24-qwen3-8b-r0-r4-smoke-20260906',
    'game24-qwen3-8b-r0-r4-smoke-boundary-20260906',
    'game24-qwen3-8b-thinking-r0-r4-20260906',
    'game24-qwen3-8b-thinking-drafts-20260908',
    'game24-stage-b-drafts-20260911', 'game24-stage-b-supplement-20260911',
    'game24-qwen3-reendorsement-drafts-20260914',
    'game24-heldout-screen-20260917',
    'game24-baseline-screen-vllm-20260917-retry1',
    'game24-baseline-screen-vllm-20260918-batch02',
    'game24-dual-anchor-20q-20260917',
    'game24-batch02-qwen32b-20260919',
    'game24-batch03-dual-anchor-20260924',
    'game24-batch04-dual-anchor-screen-20260925',
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    bundle = args.output / 'baseline_snapshot.zip'
    if bundle.exists():
        raise FileExistsError(bundle)
    files, exposure = [], []
    names = {'draft_candidates.jsonl', 'config.json', 'summary.json',
             'requests.json', 'manifest_snapshot.json', 'manifest.json',
             'frozen_source_manifest.json', 'status.json', 'launch_record.json',
             'analysis.json', 'manual_review_queue.json', 'pooled_scorer_summary.json'}
    with zipfile.ZipFile(bundle, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in BASELINES:
            folder = root / 'outputs' / name
            for p in sorted(folder.rglob('*')):
                if p.is_file() and p.name in names:
                    rel = p.relative_to(root).as_posix()
                    raw = p.read_bytes()
                    files.append(dict(path=rel, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
                    z.writestr(rel, raw)
        # Identify actual exposure without using correctness or intervention effect.
        for base in ['outputs', 'runs']:
            for p in sorted((root / base).rglob('*.jsonl')):
                if p.name not in {'results.jsonl', 'generations.jsonl', 'pairs.jsonl', 'source_pairs.jsonl'}:
                    continue
                if any(name in p.parts for name in BASELINES):
                    continue
                for n, line in enumerate(p.open(encoding='utf-8'), 1):
                    try:
                        r = json.loads(line)
                    except (ValueError, UnicodeError):
                        continue
                    nums = r.get('answer', r.get('numbers'))
                    if not (isinstance(nums, list) and len(nums) == 4 and
                            all(type(x) is int and 1 <= x <= 13 for x in nums)):
                        continue
                    exposure.append(dict(path=p.relative_to(root).as_posix(), line=n,
                                         id=str(r.get('id', r.get('question_id'))), numbers=sorted(nums)))
        z.writestr('exposure_inventory.json', json.dumps(exposure, ensure_ascii=False))
        z.writestr('snapshot_file_manifest.json', json.dumps(files, ensure_ascii=False, indent=2))
    print(json.dumps(dict(bundle=str(bundle), files=len(files), bytes=bundle.stat().st_size,
                         exposed_records=len(exposure),
                         exposed_multisets=len({tuple(r['numbers']) for r in exposure}))))

if __name__ == '__main__':
    main()
