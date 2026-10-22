"""A100 GPU4 launcher: stop only our verified idle resident, run, restore."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=Path("/data2/gaojc/envs/contextual-drag-vllm/bin/python")
EXPECTED=[str(PY),"-m","selective_context.phase0.vllm_resident"]


def gpu_apps():
    # Map UUID explicitly; nvidia-smi compute queries may ignore --id.
    uuid=subprocess.check_output(["nvidia-smi","--id=4","--query-gpu=uuid","--format=csv,noheader"],text=True).strip()
    text=subprocess.check_output(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],text=True)
    return {int(line.split(",")[1].strip()) for line in text.splitlines() if line.split(",")[0].strip()==uuid}


def resident():
    import psutil
    matches=[p for p in psutil.process_iter(["cmdline","uids"])
             if p.info["uids"].real==os.getuid() and p.info["cmdline"]==EXPECTED
             and p.environ().get("CUDA_VISIBLE_DEVICES")=="4"]
    if len(matches)>1:
        raise RuntimeError("Multiple project residents; inspect before stopping")
    return matches[0] if matches else None


def log(output,status,**kwargs):
    with (output/"launcher.jsonl").open("a") as f:
        f.write(json.dumps(dict(time=time.time(),status=status,**kwargs))+"\n")
    print(status,kwargs,flush=True)


def stop_resident(output):
    import psutil
    p=resident()
    apps=gpu_apps()
    if not apps:
        return True
    if p is None:
        return False
    family=[p]+p.children(recursive=True)
    if not apps.issubset({x.pid for x in family}):
        return False
    # Require an interactive idle prompt, not just the right process name.
    ancestors={p.pid}|{parent.pid for parent in p.parents()}
    pane_list=subprocess.check_output(["tmux","list-panes","-a","-F","#{pane_id} #{pane_pid}"],text=True)
    pane=next((line.split()[0] for line in pane_list.splitlines() if int(line.split()[1]) in ancestors),None)
    if pane is None:
        return False
    text=subprocess.check_output(["tmux","capture-pane","-p","-t",pane,"-S","-20"],text=True)
    if not text.rstrip().endswith(">>>"):
        return False
    startup=ROOT/"outputs/vllm-resident-startup.json"
    if startup.exists():
        state=json.loads(startup.read_text())
        if state.get("status") in ("authorized_pending","started","running"):
            return False
    log(output,"stopping_owned_idle_resident",pid=p.pid,compute_pids=sorted(apps))
    for member in family:
        try: member.terminate()
        except psutil.NoSuchProcess: pass
    # This host's pidfd_open can return EINVAL; poll the verified PID objects
    # instead of psutil.wait_procs, which depends on that kernel interface.
    deadline=time.monotonic()+45
    alive=family
    while alive and time.monotonic()<deadline:
        alive=[]
        for member in family:
            try:
                if member.is_running() and member.status()!=psutil.STATUS_ZOMBIE:
                    alive.append(member)
            except psutil.NoSuchProcess:
                pass
        if alive:
            time.sleep(.5)
    if alive:
        raise RuntimeError("Resident did not exit; no forced kill or experiment launched")
    for _ in range(45):
        if not gpu_apps():
            return True
        time.sleep(1)
    return False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    parser.add_argument("--inspect",action="store_true")
    parser.add_argument("--semantic",action="store_true",help="Run reviewed invalid-construction rejection probes")
    parser.add_argument("--localize",action="store_true",help="Continue semantic screen through gated localization and validation")
    parser.add_argument("--information-followup",action="store_true",help="Random generation control followed by gated mixed-history experiment")
    parser.add_argument("--causal-followup",action="store_true",help="Same-site source control and gated query-window localization")
    parser.add_argument("--cross-question",action="store_true",help="Frozen independent-question source verification; collect prefixes if not reviewed")
    parser.add_argument("--cross-question-behavior",action="store_true",help="Frozen 24-question natural-generation source comparison")
    parser.add_argument("--source-partition",action="store_true",help="Frozen P/D/F/G source replay; reuse original scores")
    parser.add_argument("--route-revocation",action="store_true",help="Frozen same-text early/late access scoring; no free generation")
    parser.add_argument("--dependency-revision",action="store_true",help="Exact root correction and dependency-swapped short scoring")
    parser.add_argument("--dependency-natural",action="store_true",help="Natural six-step worksheet; CLEAN competence first")
    parser.add_argument("--dependency-natural-phase",choices=("CLEAN","CORRECT_ROOT"),default="CLEAN")
    parser.add_argument("--identity-mvp",action="store_true",help="History by operand-identity 2x2 natural generation")
    parser.add_argument("--identity-alias",action="store_true",help="Predeclared value-alias versus occurrence-identity distinction")
    parser.add_argument("--identity-prospective",action="store_true",help="Frozen 64 new questions: strong count baseline versus occurrence identity")
    parser.add_argument("--failure-adoption",action="store_true",help="30 existing natural failures: free repair then fixed-candidate checking and selection")
    parser.add_argument("--check-rule-transfer",action="store_true",help="Foreign counterfactual history type by current checking dimension")
    parser.add_argument("--decision-verification",action="store_true",help="Same natural candidates: history by audit/adoption goal by checking granularity")
    parser.add_argument("--constraint-coupling",action="store_true",help="Same expression: independently intervene on target and operand inventory")
    parser.add_argument("--subject-gated-verification",action="store_true",help="Same input and two output fields: switch the subject of auxiliary arithmetic")
    parser.add_argument("--feedback-decoding",action="store_true",help="Same draft: amplify truthful or false feedback contrast during natural generation")
    args=parser.parse_args()
    os.chdir(ROOT)
    entry=ROOT/"scripts"/("run_semantic_rejection_20261005.py" if args.semantic else "run_generation_diagnostics_20261005.py")
    if args.information_followup:
        entry=ROOT/"scripts/run_information_followup_20261005.py"
    if args.causal_followup:
        entry=ROOT/"scripts/run_causal_followup_20261006.py"
    if args.cross_question:
        entry=ROOT/"scripts/run_cross_question_verification_20261007.py"
    if args.cross_question_behavior:
        entry=ROOT/"scripts/run_cross_question_behavior_20261009.py"
    if args.source_partition:
        entry=ROOT/"scripts/run_source_partition_20261009.py"
    if args.route_revocation:
        entry=ROOT/"scripts/run_route_revocation_20261010.py"
    if args.dependency_revision:
        entry=ROOT/"scripts/run_dependency_revision_20261011.py"
    if args.dependency_natural:
        entry=ROOT/"scripts/run_dependency_natural_20261011.py"
    if args.identity_mvp or args.identity_alias:
        entry=ROOT/"scripts/run_identity_mvp_20261011.py"
    if args.identity_prospective:
        entry=ROOT/"scripts/run_identity_prospective_20261011.py"
    if args.failure_adoption:
        entry=ROOT/"scripts/run_failure_adoption_20261011.py"
    if args.check_rule_transfer:
        entry=ROOT/"scripts/run_check_rule_transfer_20261011.py"
    if args.decision_verification:
        entry=ROOT/"scripts/run_decision_verification_20261011.py"
    if args.constraint_coupling:
        entry=ROOT/"scripts/run_constraint_coupling_20261011.py"
    if args.subject_gated_verification:
        entry=ROOT/"scripts/run_subject_gated_verification_20261011.py"
    if args.feedback_decoding:
        entry=ROOT/"scripts/run_feedback_decoding_20261012.py"
    args.output.mkdir(parents=True,exist_ok=True)
    if args.inspect:
        p=resident()
        print(json.dumps(dict(gpu4_compute_pids=sorted(gpu_apps()),resident_pid=p.pid if p else None)))
        return
    lock=(args.output/"launcher.lock").open("w")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES="4",SC_GPU="4",HF_HUB_OFFLINE="1",
             TRANSFORMERS_OFFLINE="1",OMP_NUM_THREADS="4",MKL_NUM_THREADS="4",PYTHONUNBUFFERED="1",
             TMPDIR="/data2/gaojc/tmp",PYTHONPATH=str(ROOT))
    if args.route_revocation:
        env["SC_ROUTE_LAUNCHER"]="1"
    if args.dependency_revision:
        env["SC_DEPENDENCY_LAUNCHER"]="1"
    if args.dependency_natural:
        env["SC_DEPENDENCY_NATURAL_LAUNCHER"]="1"
        env["SC_DEPENDENCY_NATURAL_PHASE"]=args.dependency_natural_phase
    if args.identity_mvp or args.identity_alias:
        env["SC_IDENTITY_MVP_LAUNCHER"]="1"
        env["SC_IDENTITY_MVP_MODE"]="value_alias_control" if args.identity_alias else "occurrence_mvp"
    if args.identity_prospective:
        env["SC_IDENTITY_PROSPECTIVE_LAUNCHER"]="1"
    if args.failure_adoption:
        env["SC_FAILURE_ADOPTION_LAUNCHER"]="1"
    if args.check_rule_transfer:
        env["SC_CHECK_RULE_LAUNCHER"]="1"
    if args.decision_verification:
        env["SC_DECISION_VERIFICATION_LAUNCHER"]="1"
    if args.constraint_coupling:
        env["SC_CONSTRAINT_COUPLING_LAUNCHER"]="1"
    if args.subject_gated_verification:
        env["SC_SUBJECT_GATED_LAUNCHER"]="1"
    if args.feedback_decoding:
        env["SC_FEEDBACK_DECODING_LAUNCHER"]="1"
    # Tokenizer/data readiness is checked before stopping any resident.
    subprocess.run([str(PY),str(entry),
                    "--output",str(args.output),"--prepare"],env=env,check=True)
    try:
        while not stop_resident(args.output):
            log(args.output,"waiting_for_gpu4_without_touching_other_jobs")
            time.sleep(30)
        if gpu_apps():
            raise RuntimeError("GPU4 ownership changed; no experiment launched")
        log(args.output,"starting_diagnostics")
        code=subprocess.call([str(PY),"-u",str(entry),
                              "--output",str(args.output),"--resume"]+
                             (["--localize"] if args.semantic and args.localize else []),env=env)
        log(args.output,"diagnostic_process_exited",returncode=code)
    except Exception as exc:
        import traceback
        log(args.output,"launcher_failed",error=repr(exc))
        traceback.print_exc()
        raise
    finally:
        fcntl.flock(lock,fcntl.LOCK_UN)
        lock.close()
        if resident() is None and not gpu_apps():
            log(args.output,"restoring_owned_resident")
            env["SC_VLLM_DECODE_LAYOUT"]="per_request"
            env["VLLM_WORKER_MULTIPROC_METHOD"]="spawn"
            # Interactive stdin is supplied by the launcher tmux pane.
            proc=subprocess.Popen(EXPECTED,env=env)
            proc.wait()
        else:
            log(args.output,"restoration_deferred_gpu4_occupied_or_resident_present")


if __name__=="__main__":
    main()
