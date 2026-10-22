"""Finite source-binding critiques: CPU check/status or GPU4 idle launcher."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/generation-diagnostics-20261005/public_verification_preview/source_binding_probe"
MODEL = "/data2/huangrj/models/qwen3-8b"
MAX_MODEL_LEN = 32768
CONCURRENCY = 8


def read(path):
    return json.loads(path.read_text(encoding="utf8")) if path.exists() else {}


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temporary.replace(path)


def append(path, value):
    with path.open("a", encoding="utf8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def check(out, tokenize=False):
    config = read(out / "config.json")
    requests = rows(out / "requests.jsonl")
    counts = Counter(r["condition"] for r in requests)
    if len(requests) != 196 or len({r["request_id"] for r in requests}) != 196:
        raise ValueError("Expected the frozen 196 unique requests")
    if counts != Counter(NO_REFERENCE=64, REFERENCE=64, GROUNDED_REFERENCE=64,
                         REFERENCE_ORIGINAL=2, REFERENCE_RENAMED=2):
        raise ValueError("Frozen condition counts changed")
    if config["status"] != "authorized_finite_batch":
        raise ValueError("Expected the current authorized batch config")
    result = dict(requests=len(requests), conditions=dict(counts), model=MODEL)
    if tokenize:
        from transformers import AutoTokenizer, GenerationConfig
        tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
        GenerationConfig.from_pretrained(MODEL, local_files_only=True)
        lengths = [len(tokenizer.apply_chat_template([dict(role="user", content=r["prompt"])],
                       tokenize=True, add_generation_prompt=True, enable_thinking=True)) for r in requests]
        if max(lengths) + config["max_new_tokens"] > MAX_MODEL_LEN:
            raise ValueError("Frozen prompt/output limit exceeds model context")
        result.update(max_prompt_tokens=max(lengths), min_prompt_tokens=min(lengths))
        save(out / "input_check.json", result)
    return config, requests, result


def status(out):
    config = read(out / "config.json")
    completed = rows(out / "generations.jsonl")
    result = dict(state=read(out / "run_state.json"), completed=len(completed),
                  planned=config.get("total_requests"),
                  conditions=dict(Counter(r["condition"] for r in completed)),
                  finish_reasons=dict(Counter(r["finish_reason"] for r in completed)),
                  visible_feedback=sum(bool(r.get("feedback_text")) for r in completed))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run(out):
    if os.environ.get("SC_SOURCE_BINDING_LAUNCHER") != "1":
        raise RuntimeError("Start with --launch to check GPU4 ownership")
    config, requests, _ = check(out)
    if rows(out / "generations.jsonl"):
        raise RuntimeError("Existing responses retained; no automatic repeat or retry")
    started = time.monotonic()
    completed, inflight, index, tokens_total = [], {}, 0, 0
    phase, error = "loading_model", None
    last_state = 0.0

    def state(force=False):
        nonlocal last_state
        now = time.monotonic()
        if not force and now - last_state < 15:
            return
        last_state = now
        elapsed = now - started
        save(out / "run_state.json", dict(status=phase, completed=len(completed), planned=len(requests),
             submitted=index, active=[r[0]["request_id"] for r in inflight.values()],
             elapsed_gpu_seconds=elapsed, completed_output_tokens=tokens_total,
             pid=os.getpid(), updated_at=time.time(), error=error,
             runtime_note="Elapsed since model loading began; concurrent request times are not summed. Old budget.json is unchanged."))

    try:
        state(True)
        import torch
        from transformers import AutoTokenizer, GenerationConfig
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or "A100" not in torch.cuda.get_device_name(0):
            raise RuntimeError("One visible A100 required")
        os.environ.update(VLLM_WORKER_MULTIPROC_METHOD="spawn", VLLM_USE_V1="1", VLLM_ATTENTION_BACKEND="FLASH_ATTN")
        from vllm import LLM, SamplingParams
        tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
        eos = GenerationConfig.from_pretrained(MODEL, local_files_only=True).eos_token_id
        eos = [eos] if isinstance(eos, int) else eos
        llm = LLM(model=MODEL, tokenizer=MODEL, dtype="bfloat16", max_model_len=MAX_MODEL_LEN,
                  max_num_seqs=CONCURRENCY, gpu_memory_utilization=.80, enable_prefix_caching=True,
                  enable_chunked_prefill=True, max_num_batched_tokens=8192, enforce_eager=True,
                  generation_config="vllm", seed=config["seed"])
        engine = llm.llm_engine
        phase = "running"
        state(True)
        while index < len(requests) or engine.has_unfinished_requests():
            while index < len(requests) and len(inflight) < CONCURRENCY:
                item = requests[index]
                ids = tokenizer.apply_chat_template([dict(role="user", content=item["prompt"])],
                      tokenize=True, add_generation_prompt=True, enable_thinking=True)
                params = SamplingParams(temperature=config["temperature"], top_p=config["top_p"],
                         seed=config["seed"], max_tokens=config["max_new_tokens"],
                         skip_special_tokens=False, ignore_eos=False, stop_token_ids=eos)
                rid = str(next(llm.request_counter))
                engine.add_request(rid, dict(prompt_token_ids=ids), params)
                inflight[rid] = (item, time.monotonic(), len(ids))
                index += 1
            for result in engine.step():
                if not result.finished:
                    continue
                item, begin, prompt_tokens = inflight.pop(result.request_id)
                generation = result.outputs[0]
                tokens = list(generation.token_ids)
                text = tokenizer.decode(tokens, skip_special_tokens=False)
                # Thinking is enabled: absent closing tag means no visible critique, even if thoughts contain criticism.
                feedback = text.split("</think>", 1)[1].replace("<|im_end|>", "").strip() if "</think>" in text else ""
                record = dict(item, text=text, feedback_text=feedback, token_ids=tokens,
                    generated_tokens=len(tokens), prompt_tokens=prompt_tokens,
                    finish_reason="eos" if (tokens and tokens[-1] in eos) or generation.stop_reason in eos else generation.finish_reason,
                    stop_reason=generation.stop_reason, thinking_closed="</think>" in text,
                    request_wall_seconds=time.monotonic()-begin, completed_at=time.time(),
                    model=MODEL, dtype=config["dtype"], backend="vllm",
                    sampling=dict(temperature=config["temperature"], top_p=config["top_p"],
                                  seed=config["seed"], max_new_tokens=config["max_new_tokens"]),
                    source_config=str(out / "config.json"))
                append(out / "generations.jsonl", record)
                completed.append(record)
                tokens_total += len(tokens)
                print(json.dumps(dict(completed=len(completed), planned=len(requests),
                      request_id=item["request_id"], generated_tokens=len(tokens),
                      finish_reason=record["finish_reason"], visible_feedback=bool(feedback)), ensure_ascii=False), flush=True)
                state(True)
            state()
        phase = "completed"
    except BaseException as exc:
        phase, error = "failed", repr(exc)
        raise
    finally:
        state(True)
        done = {r["request_id"] for r in completed}
        save(out / "collection_summary.json", dict(status=phase, completed=len(completed), planned=len(requests),
             missing_requests=[r["request_id"] for r in requests if r["request_id"] not in done],
             conditions=dict(Counter(r["condition"] for r in completed)),
             finish_reasons=dict(Counter(r["finish_reason"] for r in completed)),
             visible_feedback=sum(bool(r["feedback_text"]) for r in completed),
             elapsed_gpu_seconds=time.monotonic()-started, error=error,
             note="Collection counts only. Source-binding errors require semantic review; no causal or novelty conclusion here."))


def launch(out):
    import fcntl
    from launch_generation_diagnostics_20261005 import PY, EXPECTED, gpu_apps, resident, stop_resident, log
    check(out)
    if rows(out / "generations.jsonl"):
        raise RuntimeError("Batch already has results; inspect rather than automatically retry")
    lock_path = ROOT / "outputs/generation-diagnostics-20261005/launcher.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="4", SC_GPU="4", HF_HUB_OFFLINE="1",
                   TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
                   PYTHONUNBUFFERED="1", TMPDIR="/data2/gaojc/tmp", PYTHONPATH=str(ROOT),
                   SC_SOURCE_BINDING_LAUNCHER="1")
        subprocess.run([str(PY), str(Path(__file__)), "--output", str(out), "--check-inputs", "--tokenize"], env=env, check=True)
        try:
            while not stop_resident(out):
                save(out / "run_state.json", dict(status="waiting_for_gpu4", completed=0, planned=196,
                     launcher_pid=os.getpid(), gpu4_compute_pids=sorted(gpu_apps()), updated_at=time.time()))
                log(out, "waiting_for_gpu4_without_touching_other_jobs")
                time.sleep(30)
            if gpu_apps():
                raise RuntimeError("GPU4 ownership changed; experiment not started")
            log(out, "starting_source_binding_probe", planned=196, runtime_estimate_minutes=[30,60])
            code = subprocess.call([str(PY), "-u", str(Path(__file__)), "--output", str(out), "--run"], env=env)
            log(out, "source_binding_process_exited", returncode=code)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            if resident() is None and not gpu_apps():
                log(out, "restoring_owned_resident")
                env.update(SC_VLLM_DECODE_LAYOUT="per_request", VLLM_WORKER_MULTIPROC_METHOD="spawn")
                # The restored resident uses this same interactive tmux pane after the batch exits.
                subprocess.call(EXPECTED, env=env)
            else:
                log(out, "resident_restoration_deferred_gpu_in_use")
        if code:
            raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--tokenize", action="store_true")
    args = parser.parse_args()
    if args.status:
        status(args.output)
    elif args.check_inputs:
        print(json.dumps(check(args.output, args.tokenize)[2]))
    elif args.launch:
        launch(args.output)
    else:
        run(args.output)


if __name__ == "__main__":
    main()
