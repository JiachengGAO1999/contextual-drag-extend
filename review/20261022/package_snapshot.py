"""Build this dated review snapshot from the existing local completed evidence."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
DEV = ROOT / "outputs/game24-replication-qwen3-8b-development-20261017"
CONF = ROOT / "outputs/game24-replication-qwen3-8b-heldout82-20261019"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


archives = []
for source, destination, outputs_only in [
    (ROOT / "outputs/game24-100q-8b-20261015/completed_snapshot_20261017.tar.gz", ".", True),
    (CONF / "game24-heldout82-completed-20261022.tar.gz", CONF.relative_to(ROOT).as_posix(), False),
]:
    target = EVIDENCE / source.name
    shutil.copyfile(source, target)
    archives.append(dict(file=target.relative_to(HERE).as_posix(), sha256=sha(target),
                         bytes=target.stat().st_size, source=source.relative_to(ROOT).as_posix(),
                         destination=destination, outputs_only=outputs_only, original_archive=True))
target = EVIDENCE / "development20-completed-20261022.tar.gz"
with tarfile.open(target, "w:gz") as bundle:
    for path in sorted(DEV.rglob("*")):
        if path.is_file():
            bundle.add(path, arcname=path.relative_to(DEV).as_posix(), recursive=False)
archives.append(dict(file=target.relative_to(HERE).as_posix(), sha256=sha(target),
                     bytes=target.stat().st_size, source=DEV.relative_to(ROOT).as_posix(),
                     destination=DEV.relative_to(ROOT).as_posix(), original_archive=False))

# Include key prior negative/control evidence, not every historical activation dump.
history = [ROOT / p for p in ["outputs/causal-specificity-audit-20261013",
           "outputs/late-invalidation-20261012",
           "outputs/generation-diagnostics-20261005/source_partition"]]
paths = [p for directory in history for p in directory.rglob("*") if p.is_file()]
paths += [ROOT / "outputs/generation-diagnostics-20261005/cross_question_behavior" / name
          for name in ["generations.jsonl", "behaviour.jsonl", "manifest.json"]]
target = EVIDENCE / "historical-controls-20261022.tar.gz"
with tarfile.open(target, "w:gz") as bundle:
    for path in sorted(paths):
        bundle.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
archives.append(dict(file=target.relative_to(HERE).as_posix(), sha256=sha(target),
                     bytes=target.stat().st_size, source="selected historical control/STOP evidence",
                     destination=".", original_archive=False, files=len(paths)))

# Preserve the source closure of the old acquisition index, used by semantic regressions.
legacy = rows(ROOT / "docs/game24_100q/game24_trajectory_pool.jsonl")
paths = {ROOT / row["source_path"] for row in legacy}
paths.add(ROOT / "outputs/protocol-parity-audit-20260917/24.csv")
target = EVIDENCE / "legacy-acquisition-sources-20261022.tar.gz"
with tarfile.open(target, "w:gz") as bundle:
    for path in sorted(paths):
        bundle.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
archives.append(dict(file=target.relative_to(HERE).as_posix(), sha256=sha(target),
                     bytes=target.stat().st_size, source="raw source closure of the historical acquisition index",
                     destination=".", original_archive=False, files=len(paths)))

shutil.copyfile(CONF / "analysis.json", HERE / "analysis.json")
split = json.loads((ROOT / "docs/game24_100q_8b/game24_split_manifest.json").read_text(encoding="utf-8"))
records = rows(DEV / "results.jsonl") + rows(CONF / "results.jsonl")
with (HERE / "response_index.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["question", "split", "seed", "condition", "correctness", "finish_reason", "extracted_answer", "raw_file", "raw_line"])
    for base in [DEV, CONF]:
        for line, raw in enumerate(rows(base / "results.jsonl"), 1):
            g = raw["init_response_generations"][0]
            m = raw["init_response_generations_metadata"]["intervention"]
            writer.writerow([raw["id"], "development20" if base == DEV else "heldout82", m["sample_seed"],
                             m["condition_id"], g.get("correctness"), g["finish_reason"], g.get("extracted_answer"),
                             (base / "results.jsonl").relative_to(ROOT).as_posix(), line])
analysis = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
with (HERE / "question_results.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["question", "split", "R0_seed_mean", "R2_seed_mean", "R3_seed_mean", "R0-R2", "R3-R2"])
    for scope in ["development20", "heldout82"]:
        for row in analysis[scope]["per_question"]:
            writer.writerow([row["id"], scope, row["R0"], row["R2"], row["R3"], row["R0"] - row["R2"], row["R3"] - row["R2"]])

support = ["scripts/game24_full_replication_20261019.py", "scripts/game24_replication_20261017.py",
           "scripts/analyze_batch03_partial_20260924.py", "docs/game24_100q_8b/game24_eligible_100.jsonl",
           "docs/game24_100q_8b/game24_trajectory_pool.jsonl", "docs/game24_100q_8b/game24_split_manifest.json"]
manifest = dict(date="2026-10-22", repository="JiachengGAO1999/contextual-drag-extend", visibility="private",
    base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    archives=archives, support_files={p: sha(ROOT / p) for p in support},
    raw_results_sha256={(base / "results.jsonl").relative_to(ROOT).as_posix(): sha(base / "results.jsonl") for base in [DEV, CONF]},
    included_scope="current research docs, scripts, tests, selective backend; complete acquisition/dev/confirmation evidence and selected old controls",
    excluded_scope=["credentials", "model weights", "installed environments", "temporary downloads", "unrelated third-party paper PDFs", "all other historical bulk outputs"],
    provenance_boundary="Original archives/raw bytes preserved; old absolute server paths remain for provenance, not portable runtime configuration.",
    license_boundary="Existing repository Apache-2.0 license retained; no new license grant for third-party models or runtime dependencies.")
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(dict(archives=archives, scientific_responses=len(records)), indent=2))
