"""Prepare small A800 deployment archive; never includes checkpoint weights."""
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/game24_100q'

def main():
    qs=[json.loads(l) for l in (OUT/'game24_question_manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    history=[dict(tot_rank=q['tot_rank'],numbers=q['numbers'],
                  evidence_paths=sorted({r['path'] for r in q['intervention_or_material_evidence'] if 'path' in r}))
             for q in qs if q['historical_development']]
    frozen=OUT/'historical_exclusion_frozen.json'
    if not frozen.exists():
        frozen.write_text(json.dumps(dict(state='frozen_before_a800_acquisition',questions=history),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=[
        'scripts/game24_100q_collect.py','scripts/game24_100q_campaign.py','scripts/game24_100q_audit.py',
        'scripts/batch03_resume_core_20260924.py','scripts/baseline_screen_vllm_20260917.py',
        'scripts/analyze_batch03_partial_20260924.py','scripts/audit_batch02_manual_20260919.py',
        'selective_context/__init__.py','selective_context/prompting.py','selective_context/schema.py',
        'data_generation/initial_sampling_postprocess.py',
        'prompt_templates/init_response_prompt_templates.json',
        'outputs/protocol-parity-audit-20260917/24.csv',
        'outputs/game24-100q-20261014/baseline_snapshot.zip',
        'outputs/game24-100q-20261014/remote_material_inventory.json',
        'runs/batch04_screen_8b_audit_20260925/manual_audit_decisions.json',
        'docs/game24_100q/manual_reviews.jsonl','docs/game24_100q/historical_exclusion_frozen.json',
        'docs/game24_100q/pilot_manifest.json','docs/game24_100q/fresh_question_order.json',
        'docs/game24_100q/execution_config_a800.json','docs/game24_100q/acquisition_campaign.json']
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'utils/verifiable_evaluation/math_eval/utils').glob('*.py')]
    archive=ROOT/'outputs/game24-100q-20261014/a800_deployment.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(ROOT/name,name)
    print(json.dumps(dict(archive=str(archive),files=len(files),bytes=archive.stat().st_size,history_questions=len(history))))

if __name__=='__main__':main()
