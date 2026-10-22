"""Prepare a separate, explicitly authorized single-anchor campaign; CPU only."""
import hashlib
import argparse
import json
import math
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'docs/game24_100q'
OUT = ROOT/'docs/game24_100q_8b'
RUN = ROOT/'outputs/game24-100q-8b-20261015/acquisition/a800'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--amend-disk-guard', action='store_true')
    args = ap.parse_args()
    backup = ROOT/'outputs/game24-100q-20261014/pilot_partial_backup_20261015'
    source_manifest = json.loads((backup/'source_manifest.json').read_text())
    archive = backup/'pilot_partial.tar.gz'
    if digest(archive) != source_manifest['archive_sha256']:
        raise RuntimeError('Partial pilot backup changed')
    original_run = ROOT/'outputs/game24-100q-20261014/acquisition/a800'
    with tarfile.open(archive, 'r:gz') as tar:
        for row in source_manifest['files']:
            name = row['path']
            if not name.startswith('pilot/Qwen3_8B_Thinking/') and name != 'pilot.manifest.json':
                continue
            target = (original_run/name).resolve()
            if original_run.resolve() not in target.parents:
                raise RuntimeError('Unsafe archived source path')
            member = tar.getmember(name)
            if not member.isfile():
                raise RuntimeError('Non-regular source file')
            raw = tar.extractfile(member).read()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise RuntimeError('Archived source hash mismatch')
            if target.exists() and target.read_bytes() != raw:
                raise RuntimeError('Refusing to overwrite different raw source')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    pilot_dir = original_run/'pilot/Qwen3_8B_Thinking'
    summary = json.loads((pilot_dir/'summary.json').read_text())
    if summary['generations'] != 128:
        raise RuntimeError('Only complete 16-question 8B pilot can be reused')
    old_status = json.loads((OLD/'progress.json').read_text())
    prior_hours = old_status['campaign_job_gpu_hours']
    if not math.isfinite(prior_hours) or prior_hours < 8:
        raise RuntimeError('Prior campaign accounting is missing')
    profile = json.loads((OLD/'execution_config_a800.json').read_text())
    profile['models'] = {'Qwen3_8B_Thinking': profile['models']['Qwen3_8B_Thinking']}
    profile['purpose'] = 'Authorized single Qwen3-8B anchor acquisition; dual-anchor records remain separate'
    profile['minimum_disk_free_gib'] = 2
    order = json.loads((OLD/'fresh_question_order.json').read_text())
    pilot = json.loads((OLD/'pilot_manifest.json').read_text())
    pilot.update(protocol='adapted_single_qwen8b_fixed8_v1', anchor_models=['Qwen3_8B_Thinking'],
                 total_generations=128, state='complete_8b_source_reused_after_protocol_amendment',
                 expansion='Finite single-anchor campaign; audit each32-question wave',
                 quota='Exactly8 Qwen3-8B responses per question; invalid completed responses never resampled')
    bindings = [OLD/'game24_trajectory_pool.jsonl', OLD/'historical_exclusion_frozen.json',
                pilot_dir/'draft_candidates.jsonl', pilot_dir/'config.json', pilot_dir/'summary.json']
    policy = dict(version=1, protocol=pilot['protocol'],
                  authorization='2026-10-15 user requested Qwen3-8B as the sole temporary anchor',
                  anchors=['Qwen3_8B_Thinking'], target=100, samples_per_anchor=8, wave_questions=32,
                  maximum_wave_gpu_hours=8, maximum_campaign_gpu_hours=240,
                  prior_campaign_job_gpu_hours=prior_hours,
                  reused_pilot_8b_gpu_hours=summary['total_seconds']/3600,
                  reused_pilot_root=pilot_dir.relative_to(ROOT).as_posix(),
                  historical_index=(OLD/'game24_trajectory_pool.jsonl').relative_to(ROOT).as_posix(),
                  frozen_history=(OLD/'historical_exclusion_frozen.json').relative_to(ROOT).as_posix(),
                  source_bindings=[dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p)) for p in bindings],
                  historical_dual_candidates_excluded=['643', '1119'],
                  split_seed=20261014, seed=20261014, minimum_disk_free_gib=2,
                  collector_script='scripts/game24_100q_collect_single_anchor_v1.py',
                  automatic_interventions=False,
                  scope='100 independent strict 8B-only questions; freeze20development/restheldout; no mechanism runs')
    OUT.mkdir(parents=True, exist_ok=True)
    amendments = []
    for name, value in [('execution_config_a800.json', profile), ('fresh_question_order.json', order),
                        ('pilot_manifest.json', pilot), ('acquisition_campaign.json', policy)]:
        p = OUT/name
        if p.exists() and json.loads(p.read_text()) != value:
            prior = json.loads(p.read_text())
            keys = set(prior)|set(value)
            only_reserve_changed = all(prior.get(k) == value.get(k) for k in keys if k != 'minimum_disk_free_gib')
            if not args.amend_disk_guard or not only_reserve_changed or prior.get('minimum_disk_free_gib', 10) != 10:
                raise RuntimeError('Prepared config changed; explicit revision required: '+name)
            archive = OUT/'resource_guard_10gib_before_launch'/name
            archive.parent.mkdir(parents=True, exist_ok=True)
            if archive.exists() and archive.read_bytes() != p.read_bytes():
                raise RuntimeError('Resource amendment archive already differs')
            archive.write_bytes(p.read_bytes())
            amendments.append(dict(path=name, before_sha256=digest(p), before_gib=10, after_gib=2))
        dump(p, value)
    if amendments:
        dump(OUT/'resource_guard_revision_20261015.json', dict(
            reason='10GiB was a conservative engineering default, not an8B model requirement; measured pilot raw6.16MB and projected additional raw302MB',
            changes=amendments, pilot_raw_bytes=(pilot_dir/'draft_candidates.jsonl').stat().st_size,
            expected_remaining_raw_bytes=(pilot_dir/'draft_candidates.jsonl').stat().st_size*49,
            runtime_guard='Check every15seconds and fsync every completed response; no model download or deletion',
            sampling_and_eligibility_changed=False))
    # Distinct deployment filename preserves the original dual-anchor runner on A800.
    staged = ROOT/'outputs/game24-100q-8b-20261015/deployment'/policy['collector_script']
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes((ROOT/'scripts/game24_100q_collect.py').read_bytes())
    print(json.dumps(dict(state='prepared_only', anchors=policy['anchors'], reused_pilot_responses=128,
                          source_bindings=len(bindings), gpu_calls=0)))


if __name__ == '__main__':
    main()
