"""Launch the frozen confirmation on exactly one idle A800 GPU; leave other jobs alone."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"outputs/game24-replication-qwen3-8b-heldout82-20261019"


def main():
    os.chdir(ROOT)
    profile = json.loads((BASE/"runtime_profile.json").read_text())
    pre = json.loads((BASE/"preflight.json").read_text())
    assert pre["passed"]
    for name,digest in pre["hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    uuid = subprocess.check_output(["nvidia-smi","--id=4","--query-gpu=uuid","--format=csv,noheader"],text=True).strip()
    assert uuid==profile["gpu_uuid"]
    gpu_rows = subprocess.check_output(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],text=True)
    assert not any(line.split(",")[0].strip()==uuid for line in gpu_rows.splitlines()),"GPU4 occupied; no process stopped"
    assert shutil.disk_usage(BASE).free>=2*1024**3
    lock = (BASE/"launcher.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    cache = BASE/"runtime/cache"
    cache.mkdir(parents=True,exist_ok=True)
    # ZMQ Unix sockets include a36-character UUID and have a107-byte path limit.
    tmp = Path.home()/".cache/cd82-1019"
    tmp.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert len(str(tmp).encode())+37<107 and tmp.stat().st_uid==os.getuid()
    env = dict(os.environ,CUDA_VISIBLE_DEVICES="4",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
        PYTHONPATH=profile["overlay"]+":"+profile["reference"]+":"+str(ROOT),
        SC_HELDOUT_LAUNCHER="1",SC_VLLM_DECODE_LAYOUT="per_request",SC_FLEX_NO_CUDAGRAPHS="1",
        SC_FLEX_COMPILE_LIMIT="1024",VLLM_WORKER_MULTIPROC_METHOD="spawn",VLLM_NO_USAGE_STATS="1",
        VLLM_USE_FLASHINFER_SAMPLER="0",CUDA_LAUNCH_BLOCKING="1",OMP_NUM_THREADS="4",MKL_NUM_THREADS="4",
        MAX_JOBS="4",PYTHONUNBUFFERED="1",TMPDIR=str(tmp),VLLM_RPC_BASE_PATH=str(tmp),XDG_CACHE_HOME=str(cache),
        TRITON_CACHE_DIR=str(cache/"triton"),VLLM_CACHE_ROOT=str(cache/"vllm"))
    env["PATH"] = str(ROOT/".venv/bin")+":/data/gaojc/mamba/envs/vllm-gptoss/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
    resume = "--resume" in sys.argv
    args = [profile["python"],"-u",str(ROOT/"scripts/game24_full_replication_20261019.py"),"run"]
    if resume: args.append("--resume")
    with (BASE/("resume_console.log" if resume else "console.log")).open("a" if resume else "x") as output:
        result = subprocess.run(args,env=env,stdout=output,stderr=subprocess.STDOUT)
    (BASE/"launcher_exit.json").write_text(json.dumps(dict(returncode=result.returncode,gpu_uuid=uuid)) + "\n")
    raise SystemExit(result.returncode)


if __name__=="__main__": main()
