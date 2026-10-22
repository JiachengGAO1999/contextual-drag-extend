"""Run the frozen development replication on only the project's A100 GPU4."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from launch_generation_diagnostics_20261005 import PY, EXPECTED, resident, gpu_apps, stop_resident, log

BASE = ROOT / "outputs/game24-replication-qwen3-8b-development-20261017"
REFERENCE = Path("/data2/gaojc/tmp/game24-batch03-validation-20260924")


def main():
    os.chdir(ROOT)
    if (BASE / "launch.json").exists():
        raise RuntimeError("No duplicate launch/retry")
    import hashlib
    pre = json.loads((BASE/"preflight.json").read_text())
    assert pre["passed"] and pre["reference_files_verified"] == 146
    for name, digest in pre["hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    assert hashlib.sha256((REFERENCE/"preflight.json").read_bytes()).hexdigest() == pre["reference_preflight_sha256"]
    for name, digest in json.loads((REFERENCE/"preflight.json").read_text())["hashes"].items():
        assert hashlib.sha256((REFERENCE/name).read_bytes()).hexdigest() == digest, name
    uuid = subprocess.check_output(["nvidia-smi", "--id=4", "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    assert uuid == "GPU-bb740995-3c17-c363-1553-ef7ac3907eca"
    assert shutil.disk_usage(ROOT).free >= 2*1024**3
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="4", SC_GPU="4", HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", MAX_JOBS="4",
        PYTHONUNBUFFERED="1", TMPDIR="/data2/gaojc/tmp", PYTHONPATH=str(REFERENCE)+":"+str(ROOT),
        SC_REPLICATION_LAUNCHER="1", SC_VLLM_DECODE_LAYOUT="per_request", SC_FLEX_NO_CUDAGRAPHS="1",
        SC_FLEX_COMPILE_LIMIT="1024", VLLM_WORKER_MULTIPROC_METHOD="spawn", VLLM_NO_USAGE_STATS="1",
        CUDA_LAUNCH_BLOCKING="1")
    # Share the existing project's exclusion lock; preserve all previous artifacts.
    lock = (ROOT / "outputs/generation-diagnostics-20261005/launcher.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    restore = False
    try:
        p = resident()
        if p is not None:
            assert gpu_apps() <= {p.pid} | {c.pid for c in p.children(recursive=True)}, "Foreign GPU job; do not stop/launch"
            restore = True
        assert stop_resident(BASE), "GPU4 is not available; no queued expansion/retry"
        assert not gpu_apps(), "GPU acquired by another job"
        log(BASE, "start_frozen_120_request_replication", gpu_uuid=uuid, reference_root=str(REFERENCE))
        with (BASE / "console.log").open("x") as output:
            code = subprocess.run([str(PY), "-u", str(ROOT/"scripts/game24_replication_20261017.py"), "run"],
                                  env=env, stdout=output, stderr=subprocess.STDOUT).returncode
        log(BASE, "replication_exited_no_retry", returncode=code)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        if restore and resident() is None and not gpu_apps():
            # Original service restored with original code, no automatic requests.
            original = dict(env, PYTHONPATH=str(ROOT))
            original.pop("SC_REPLICATION_LAUNCHER", None)
            original.pop("SC_FLEX_NO_CUDAGRAPHS", None)
            original.pop("SC_FLEX_COMPILE_LIMIT", None)
            log(BASE, "restore_previous_idle_resident_no_experiment")
            subprocess.run(EXPECTED, env=original)


if __name__ == "__main__": main()
