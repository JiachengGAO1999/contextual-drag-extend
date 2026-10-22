"""One-shot authorized continuation: finish natural revision, then one frozen MVP."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = "/data2/gaojc/envs/contextual-drag-vllm/bin/python"
OUT = ROOT / "outputs/generation-diagnostics-20261005"
sys.path.insert(0, str(ROOT / "scripts"))
from run_generation_diagnostics_20261005 import save


def load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def main():
    phase = OUT / "dependency_natural/run_state.json"
    watch = OUT / "overnight_20261011/queue_state.json"
    session = "qwen3-8b-identity-mvp-20261011"
    last = None
    while True:
        state = load(phase)
        signature = state.get("phase"), state.get("status"), state.get("completed")
        if signature != last:
            save(watch, dict(status="waiting_for_natural_revision", source_state=state,
                             next="One frozen 96-request identity MVP; no further automatic expansion"))
            print(json.dumps(dict(source_state=state)), flush=True)
            last = signature
        if state.get("phase") == "CORRECT_ROOT" and state.get("status") == "corrected_stage_completed":
            if state.get("completed") != 64:
                raise RuntimeError("Natural phase is incomplete; do not continue automatically")
            if not load(OUT / "budget.json").get("active"):
                break
        if state.get("status") in ("failed", "budget_exhausted"):
            save(watch, dict(status="stopped_source_not_completed", source_state=state))
            return
        time.sleep(30)
    subprocess.run([PY, str(ROOT / "scripts/report_overnight_20261011.py")], cwd=ROOT, check=True)
    manifest = load(OUT / "identity_mvp/manifest.json")
    budget = load(OUT / "budget.json")
    estimate = manifest["estimate"]
    needed = manifest["planned_requests"]*manifest["max_new_tokens"]/estimate["reference_tokens_per_second"] + estimate["loading_allowance_seconds"]
    if needed > budget["limit_seconds"] - budget["gpu_seconds"]:
        save(watch, dict(status="stopped_budget_estimate", needed_seconds=needed, budget=budget))
        return
    if (OUT / "identity_mvp/run_state.json").exists():
        raise RuntimeError("An MVP run state already exists; inspect instead of resubmitting")
    cmd = f"{PY} scripts/launch_generation_diagnostics_20261005.py --identity-mvp 2>&1 | tee outputs/generation-diagnostics-20261005/identity_mvp/runner.log"
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "-c", str(ROOT), "bash", "-lc", cmd], check=True)
    save(watch, dict(status="mvp_submitted", session=session, shared_budget_before=budget))
    print("MVP submitted " + session, flush=True)
    while True:
        state = load(OUT / "identity_mvp/run_state.json")
        signature = state.get("status"), state.get("completed")
        if signature != last:
            save(watch, dict(status="monitoring_mvp", session=session, mvp_state=state))
            print(json.dumps(dict(mvp_state=state)), flush=True)
            last = signature
        if state.get("status") in ("completed", "failed", "budget_exhausted"):
            subprocess.run([PY, str(ROOT / "scripts/report_overnight_20261011.py")], cwd=ROOT, check=True)
            save(watch, dict(status="finished_no_auto_followup", session=session, mvp_state=state,
                             report="outputs/generation-diagnostics-20261005/overnight_20261011/report.md"))
            return
        time.sleep(30)


if __name__ == "__main__":
    main()
