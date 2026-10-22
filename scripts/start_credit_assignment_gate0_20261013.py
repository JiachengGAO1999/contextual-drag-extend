"""Run only the frozen Gate 0; release/restore only our verified idle resident."""
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from launch_generation_diagnostics_20261005 import PY, EXPECTED, gpu_apps, resident, log

out = ROOT / "outputs/credit-assignment-gate0-20261013"
entry = ROOT / "scripts/gate0_credit_assignment_20261013.py"
os.chdir(ROOT)
env = dict(os.environ, CUDA_VISIBLE_DEVICES="4", SC_GPU="4", HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
    PYTHONUNBUFFERED="1", PYTHONPATH=str(ROOT), TMPDIR="/data2/gaojc/tmp")
subprocess.run([str(PY), str(entry), "--prepare", "--compile"], env=env, check=True)
lock = (ROOT / "outputs/generation-diagnostics-20261005/launcher.lock").open("a")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
restore = False
try:
    p = resident()
    if p is not None:
        ancestors = {p.pid} | {a.pid for a in p.parents()}
        panes = subprocess.check_output(["tmux", "list-panes", "-a", "-F", "#{pane_id} #{pane_pid}"], text=True)
        pane = next((s.split()[0] for s in panes.splitlines() if int(s.split()[1]) in ancestors), None)
        if pane is None:
            raise RuntimeError("No verified resident pane")
        content = subprocess.check_output(["tmux", "capture-pane", "-p", "-t", pane, "-S", "-20"], text=True)
        assert content.rstrip().endswith(">>>"), "Resident is not idle"
        startup = ROOT / "outputs/vllm-resident-startup.json"
        if startup.exists():
            assert json.loads(startup.read_text()).get("status") not in ("authorized_pending", "started", "running")
        family = [p] + p.children(recursive=True)
        owned = {a.pid for a in family}
        foreign = gpu_apps()-owned
        log(out, "release_only_verified_idle_resident", resident_pid=p.pid,
            owned_pids=sorted(owned), foreign_gpu_pids_untouched=sorted(foreign))
        restore = True
        for a in family:
            try:
                a.terminate()
            except Exception:
                pass
        deadline = time.monotonic()+45
        while gpu_apps() & owned and time.monotonic() < deadline:
            time.sleep(.5)
        assert not (gpu_apps() & owned), "Resident still holds GPU; no forced kill"
    free_mib = int(subprocess.check_output(["nvidia-smi", "--id=4", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], text=True).strip())
    assert free_mib >= 24000, "Insufficient memory for bounded HF check"
    log(out, "start_HF_Gate0_only", free_mib=free_mib, foreign_gpu_pids_untouched=sorted(gpu_apps()))
    result = subprocess.run([str(PY), "-u", str(entry), "--run"], env=env)
    log(out, "HF_Gate0_exited", returncode=result.returncode)
finally:
    fcntl.flock(lock, fcntl.LOCK_UN)
    lock.close()
    if restore and resident() is None:
        env.update(SC_VLLM_DECODE_LAYOUT="per_request", VLLM_WORKER_MULTIPROC_METHOD="spawn")
        log(out, "restore_owned_idle_resident_no_experiment")
        # Foreground in the new tmux pane preserves the resident's interactive stdin.
        subprocess.run(EXPECTED, env=env)
