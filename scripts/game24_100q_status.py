"""Refresh A800 campaign progress without loading a model or sending messages."""
import argparse
import json
import subprocess
import shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REMOTE='/data/gaojc/projects/contextual-drag-extend-game24-100q'
OUT=ROOT/'docs/game24_100q'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--protocol', choices=['dual', '8b'],
                    default='8b' if (ROOT/'docs/game24_100q_8b/acquisition_campaign.json').exists() else 'dual')
    ap.add_argument('--sync-reports',action='store_true')
    ap.add_argument('--sync-data',action='store_true',help='Copy raw assets only from fully completed dual-anchor batches')
    args=ap.parse_args()
    out=ROOT/('docs/game24_100q_8b' if args.protocol=='8b' else 'docs/game24_100q')
    acquisition='outputs/game24-100q-8b-20261015/acquisition/a800' if args.protocol=='8b' else 'outputs/game24-100q-20261014/acquisition/a800'
    command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','sjtu-a800',
             'cat '+REMOTE+'/'+acquisition+'/status.json']
    status=json.loads(subprocess.check_output(command,text=True,encoding='utf-8',timeout=30))
    # The controller's last heartbeat may precede the final worker summary.
    # Read the actual journal status after stopping instead of displaying stale
    # "running" state and an incomplete count for a finished batch.
    if status.get('state') in ('target_frozen_complete','stopped_at_checkpoint') and status.get('current_batch'):
        batch_path=REMOTE+'/'+acquisition+'/'+status['current_batch']
        script='import json,pathlib; p=pathlib.Path('+repr(batch_path)+'); '
        script+='print(json.dumps([dict(model=s.parent.name,**json.loads(s.read_text())) for s in p.glob("*/status.json")]))'
        refreshed=json.loads(subprocess.check_output(['ssh','sjtu-a800',shlex.join(['python3','-c',script])],
                            text=True,encoding='utf-8',timeout=30))
        if refreshed: status['models']=refreshed
    if status.get('models'):
        status['current_batch_completed_generations']=sum(m.get('completed_generations',0) for m in status['models'])
    (out/'progress.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.sync_reports or args.sync_data:
        for name in ['audit_summary.json','sampling_efficiency.json','GAME24_100Q_ACQUISITION_LIVE.md',
                     'game24_eligible_candidates.jsonl','game24_split_manifest.json',
                     'game24_question_manifest.jsonl','game24_trajectory_pool.jsonl','source_file_manifest.json',
                     'pending_response_review.jsonl','game24_eligible_100.jsonl']:
            # A report may not exist until the first full batch is audited.
            remote=REMOTE+'/'+out.relative_to(ROOT).as_posix()+'/'+name
            exists=subprocess.run(['ssh','sjtu-a800','test -f '+remote],capture_output=True,timeout=30)
            if exists.returncode==0:
                subprocess.run(['scp','sjtu-a800:'+remote,str(out/name)],check=True,timeout=60)
    if args.sync_data:
        script="import json,pathlib,hashlib; root=pathlib.Path("+repr(REMOTE)+"); base=root/"+repr(acquisition)+"; files=[]; "
        script+="exec(\"for p in base.glob('*/status.json'):\\n if json.loads(p.read_text()).get('state')=='pilot_complete_pending_audit':\\n  for f in p.parent.rglob('*'):\\n   if f.is_file() and f.suffix in ('.json','.jsonl'):\\n    files.append(dict(path=f.relative_to(root).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))\"); print(json.dumps(files))"
        remote_command=shlex.join(['python3','-c',script])
        files=json.loads(subprocess.check_output(['ssh','sjtu-a800',remote_command],text=True,encoding='utf-8',timeout=60))
        for f in files:
            target=(ROOT/f['path']).resolve()
            if ROOT.resolve() not in target.parents:raise RuntimeError('Unsafe relative asset path')
            import hashlib
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==f['sha256']:continue
            target.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['scp','sjtu-a800:'+REMOTE+'/'+f['path'],str(target)],check=True,timeout=120)
            if hashlib.sha256(target.read_bytes()).hexdigest()!=f['sha256']:raise RuntimeError('Asset changed during transfer')
        status['completed_batch_raw_assets_checked']=len(files)
    print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
