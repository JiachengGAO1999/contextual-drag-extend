"""Frozen forward-only Gate 0/1; Gate 2 requires a separately frozen intervention config."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from selective_context.late_invalidation import SEED, materials, compile_requests, gate0, gate1
from run_feedback_source_binding_probe_20261012 import read, rows, save, append

OUT = ROOT / "outputs/late-invalidation-20261012"
MODEL = "/data2/huangrj/models/qwen3-8b"


def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    if (out / "manifest.json").exists():
        return read(out / "manifest.json")
    m = dict(materials(ROOT), seed=SEED, model=MODEL, dtype="bfloat16", attention="sdpa",
        max_model_len=32768, protocol="inside_thinking_fixed_neutral_stem",
        permitted_measurement_revision="Once only: same task and inputs, forced final JSON choice channel",
        gate0=dict(min_clean_preference=.60, min_option_token_mass=.10,
            min_drag=.05, min_ci95_lower=0., min_coverage=.90,
            require_both="30 historical calibration and 32 independent discovery questions"),
        gate1=dict(primary="(PRE-POST) minus (PLACEBO_PRE-PLACEBO_POST), averaged within question",
            discovery_min_mean=.03, confirmation_min_mean=.05, confirmation_ci95_lower=0.,
            require_each_wording_positive=True, min_coverage=.90),
        statistics="5000 paired question bootstrap draws; no seeds, option orders or wordings as independent units",
        gate2="Not implemented or automatically authorized by a patch result; freeze one local site using discovery only after Gate 1, with neutral donor, K/V separation, reverse transfer and correct-history controls",
        non_goals="No model training, long CoT, new model, source-binding expansion, effect-selected question replacement or automatic new mechanism direction",
        runtime_estimates_minutes=dict(gate0=[15,45], gate1=[30,120], gate2_if_justified=[60,180]),
        resource="Single A100 80GB, GPU4, serial after the existing finite source-binding task; historical 24-hour record is unchanged")
    save(out / "manifest.json", m)
    save(out / "run_state.json", dict(status="prepared", completed=0, planned_gate0=372))
    return m


def compile_inputs(out):
    from transformers import AutoTokenizer
    m = read(out / "manifest.json")
    tokenizer = AutoTokenizer.from_pretrained(m["model"], local_files_only=True)
    counts = {}
    for revision in (0,1):
        requests = compile_requests(tokenizer, m, revision)
        path = out / f"requests_r{revision}.jsonl"
        with path.open("w", encoding="utf8") as stream:
            for request in requests:
                stream.write(json.dumps(request, ensure_ascii=False)+"\n")
        counts[f"revision_{revision}"] = dict(requests=len(requests),
            max_prompt_tokens=max(len(r["input_ids"]) for r in requests),
            draft_position_and_token_alignment="exact within question, wording and option order")
    save(out / "input_check.json", counts)
    print(json.dumps(counts), flush=True)


def summarize(out):
    m, data = read(out / "manifest.json"), rows(out / "scores.jsonl")
    result = {}
    for revision in sorted({r["revision"] for r in data}):
        result[str(revision)] = dict(gate0=gate0(m,data,revision),
            discovery=gate1(m,data,revision,"discovery"), confirmation=gate1(m,data,revision,"confirmation"))
    save(out / "analysis.json", result)
    return result


def run(out):
    if os.environ.get("SC_LATE_INVALIDATION_LAUNCHER") != "1":
        raise RuntimeError("Use --launch to serialize GPU4 access")
    m = read(out / "manifest.json")
    old = rows(out / "scores.jsonl")
    done = {r["request_id"] for r in old}
    started = time.monotonic()
    prior_seconds = read(out / "run_state.json").get("elapsed_gpu_seconds",0)
    phase, revision, error = "loading_model", 0, None

    def state():
        save(out / "run_state.json", dict(status=phase, revision=revision, completed=len(done),
            elapsed_gpu_seconds=prior_seconds+time.monotonic()-started, updated_at=time.time(), pid=os.getpid(), error=error))

    try:
        state()
        import torch
        from transformers import AutoModelForCausalLM
        if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or "A100" not in torch.cuda.get_device_name(0):
            raise RuntimeError("One visible A100 required")
        model = AutoModelForCausalLM.from_pretrained(m["model"], local_files_only=True,
            torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map={"":"cuda:0"}).eval()

        def collect(todo):
            for request in todo:
                if request["request_id"] in done:
                    continue
                begin = time.monotonic()
                with torch.inference_mode():
                    output = model(input_ids=torch.tensor([request["input_ids"]],device="cuda:0"),
                                   use_cache=False, logits_to_keep=1, return_dict=True)
                    logp = output.logits[0,-1].float().log_softmax(-1)
                    choices = logp[request["option_token_ids"]]
                    log_probs = choices.tolist()
                    p_correct = float(choices.softmax(-1)[request["correct_option"]])
                    mass = float(choices.exp().sum())
                record = {k:v for k,v in request.items() if k!="input_ids"}
                record.update(option_log_probabilities=log_probs, p_correct=p_correct, option_mass=mass,
                    margin=log_probs[request["correct_option"]]-log_probs[1-request["correct_option"]],
                    input_tokens=len(request["input_ids"]), gpu_wall_seconds=time.monotonic()-begin,
                    completed_at=time.time(), model=m["model"], dtype=m["dtype"], protocol_phase=phase)
                append(out / "scores.jsonl",record)
                old.append(record); done.add(request["request_id"])
                state()
                if len(done)%20 == 0:
                    print(json.dumps(dict(phase=phase,completed=len(done),revision=revision,
                        elapsed_gpu_seconds=time.monotonic()-started)),flush=True)

        for revision in (0,1):
            requests = rows(out / f"requests_r{revision}.jsonl")
            phase = "gate0"; state()
            collect([r for r in requests if r["cohort"] in ("calibration","discovery")
                and r["wording"] == "note" and r["condition"] in ("CLEAN","NEUTRAL","POST")])
            g0 = gate0(m,old,revision)
            save(out / f"gate0_r{revision}.json",g0)
            if g0["passed"]:
                break
            if revision == 1:
                phase = "STOP_gate0_measurement_not_validated"; state()
                return
        phase = "gate1_discovery"; state()
        collect([r for r in requests if r["cohort"] == "discovery"])
        discovery = gate1(m,old,revision,"discovery")
        save(out / "gate1_discovery.json",discovery)
        e = discovery["corrected_pre_minus_post"]
        diagnostic = (e["n"] >= 29 and e["mean"] >= m["gate1"]["discovery_min_mean"]
                      and len(discovery["by_wording"]) == 2
                      and all(v["mean"] > 0 for v in discovery["by_wording"].values()))
        if not diagnostic:
            phase = "STOP_gate1_no_diagnostic_discovery_difference"; state()
            return
        phase = "gate1_confirmation"; state()
        collect([r for r in requests if r["cohort"] == "confirmation"])
        confirmation = gate1(m,old,revision,"confirmation")
        save(out / "gate1_confirmation.json",confirmation)
        phase = "gate2_design_required" if confirmation["passed"] else "STOP_gate1_not_confirmed"
    except BaseException as exc:
        phase, error = "failed",repr(exc)
        raise
    finally:
        state()
        summarize(out)


def launch(out):
    import fcntl
    from launch_generation_diagnostics_20261005 import PY, EXPECTED, gpu_apps, resident, stop_resident, log
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="4", SC_GPU="4", HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", PYTHONUNBUFFERED="1",
        PYTHONPATH=str(ROOT), TMPDIR="/data2/gaojc/tmp", SC_LATE_INVALIDATION_LAUNCHER="1")
    subprocess.run([str(PY),str(Path(__file__)),"--output",str(out),"--compile"],env=env,check=True)
    lock_path = ROOT / "outputs/generation-diagnostics-20261005/launcher.lock"
    with lock_path.open("a") as lock:
        while True:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                save(out/"run_state.json",dict(status="waiting_for_prior_project_batch",launcher_pid=os.getpid(),updated_at=time.time()))
                time.sleep(30)
        try:
            while not stop_resident(out):
                save(out/"run_state.json",dict(status="waiting_for_gpu4",launcher_pid=os.getpid(),
                    gpu4_compute_pids=sorted(gpu_apps()),updated_at=time.time()))
                time.sleep(30)
            if gpu_apps():
                raise RuntimeError("GPU4 ownership changed; not starting")
            log(out,"starting_late_invalidation_gate0_gate1")
            code = subprocess.call([str(PY),"-u",str(Path(__file__)),"--output",str(out),"--run"],env=env)
            log(out,"late_invalidation_exited",returncode=code)
        finally:
            fcntl.flock(lock,fcntl.LOCK_UN)
            if resident() is None and not gpu_apps():
                log(out,"restoring_owned_resident")
                env.update(SC_VLLM_DECODE_LAYOUT="per_request",VLLM_WORKER_MULTIPROC_METHOD="spawn")
                subprocess.call(EXPECTED,env=env)
            else:
                log(out,"resident_restoration_deferred_gpu_in_use")
        if code:
            raise SystemExit(code)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=OUT)
    group = p.add_mutually_exclusive_group(required=True)
    for flag in ("prepare","compile","analyse","status","launch","run"):
        group.add_argument("--"+flag,action="store_true")
    a = p.parse_args()
    if a.prepare:
        m=prepare(a.output)
        print(json.dumps(dict(calibration=len(m["calibration"]), independent=len(m["independent"]),
            discovery=32,confirmation=96,eligible_pool=m["eligible_pool"])))
    elif a.compile:
        compile_inputs(a.output)
    elif a.analyse:
        print(json.dumps(summarize(a.output),indent=2))
    elif a.status:
        print(json.dumps(dict(state=read(a.output/"run_state.json"),
            scores=len(rows(a.output/"scores.jsonl"))),indent=2))
    elif a.launch:
        launch(a.output)
    else:
        run(a.output)


if __name__ == "__main__":
    main()
