"""CPU inventory of prior development materials, including remote-only manifests."""
import csv
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/data2/gaojc/data/game24-tot-8050e67/24.csv')

def collect(v, found, mapping):
    if isinstance(v, dict):
        nums = v.get('answer', v.get('numbers'))
        if isinstance(nums, list) and len(nums) == 4 and all(type(x) is int for x in nums):
            key = tuple(sorted(nums))
            if key in mapping: found.add(key)
        for x in v.values(): collect(x, found, mapping)
    elif isinstance(v, list):
        for x in v: collect(x, found, mapping)

def main():
    with SOURCE.open() as f:
        mapping = {tuple(sorted(map(int,r['Puzzles'].split()))): r['Rank'] for r in csv.DictReader(f)}
    rows = []
    for base in ('outputs', 'runs'):
        for p in sorted((ROOT/base).rglob('*.json')):
            if p.name not in {'manifest.json','plan.json','pool_manifest.json'}: continue
            if any(x in p.as_posix() for x in ['baseline-screen','dual-anchor-20q','batch03_interrupted',
                      'batch04_screen_8b','protocol-parity-audit','game24-100q-20261014']): continue
            try: value = json.loads(p.read_text())
            except (ValueError, UnicodeError): continue
            found = set(); collect(value, found, mapping)
            for nums in sorted(found): rows.append(dict(kind='historical_development_material_remote',
                 path=p.relative_to(ROOT).as_posix(), id=mapping[nums], numbers=list(nums)))
    output = ROOT/'outputs/game24-100q-20261014/remote_material_inventory.json'
    output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(records=len(rows), multisets=len({tuple(r['numbers']) for r in rows}))))

if __name__ == '__main__': main()
