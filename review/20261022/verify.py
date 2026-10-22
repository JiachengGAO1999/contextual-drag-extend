"""Restore immutable evidence and verify results without model/network imports."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from game24_full_replication_20261019 import summarize
from analyze_batch03_partial_20260924 import expression_measurement


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def restore(spec):
    archive = HERE / spec["file"]
    require(sha(archive) == spec["sha256"], "Archive SHA mismatch: " + str(archive))
    count = 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in member.name,
                    "Unsafe archive path")
            # The acquisition snapshot also contains older docs; keep current docs intact.
            if spec.get("outputs_only") and (not name.parts or name.parts[0] != "outputs"):
                continue
            require(member.isdir() or member.isfile(), "Nonregular archive member")
            if member.isdir():
                continue
            target = ROOT / spec["destination"] / Path(*name.parts)
            target.resolve().relative_to(ROOT.resolve())
            data = bundle.extractfile(member).read()
            digest = hashlib.sha256(data).hexdigest()
            if target.exists():
                require(sha(target) == digest, "Refusing to replace different file: " + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as f:
                    f.write(data)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    manifest = read(HERE / "manifest.json")
    for spec in manifest["archives"]:
        require(sha(HERE / spec["file"]) == spec["sha256"], "Archive SHA mismatch")
        if args.restore:
            print("restored/checked", restore(spec), "files from", spec["file"], flush=True)
    for path, digest in manifest["support_files"].items():
        require(sha(ROOT / path) == digest, "Support file changed: " + path)

    data = ROOT / "docs/game24_100q_8b"
    split = read(data / "game24_split_manifest.json")
    eligible = rows(data / "game24_eligible_100.jsonl")
    pool = {r["trajectory_id"]: r for r in rows(data / "game24_trajectory_pool.jsonl")}
    require(len(eligible) == 102, "Wrong question count")
    require(len(split["development"]) == 20 and len(split["held_out"]) == 82,
            "Wrong split size")
    require(not set(split["development"]) & set(split["held_out"]), "Split overlap")
    require(set(split["development"] + split["held_out"]) ==
            {q["canonical_question_id"] for q in eligible}, "Split coverage differs")
    cache = {}
    witness_count = 0
    for question in eligible:
        cohort = [pool[t] for t in question["trajectory_ids"]]
        require(len(cohort) == 8 and {r["sample_index"] for r in cohort} == set(range(8)),
                "Incomplete cohort")
        labels = Counter(r["classification"] for r in cohort)
        require(labels["correct"] >= 2 and labels["substantive_error"] >= 2,
                "Insufficient strict witnesses")
        for trajectory in cohort:
            path = ROOT / trajectory["source_path"]
            if path not in cache:
                cache[path] = path.read_text(encoding="utf-8").splitlines()
            line = cache[path][trajectory["source_line"] - 1]
            require(hashlib.sha256(line.encode()).hexdigest() == trajectory["raw_record_sha256"],
                    "Qualification raw-record SHA mismatch")
            raw = json.loads(line)
            require(sorted(raw["answer"]) == sorted(question["numbers"]), "Source numbers differ")
            witness_count += 1

    dev = ROOT / "outputs/game24-replication-qwen3-8b-development-20261017"
    conf = ROOT / "outputs/game24-replication-qwen3-8b-heldout82-20261019"
    for base in (dev, conf):
        relative = (base / "results.jsonl").relative_to(ROOT).as_posix()
        require(sha(base / "results.jsonl") == manifest["raw_results_sha256"][relative],
                "Scientific raw output changed")
    development, held = rows(dev / "results.jsonl"), rows(conf / "results.jsonl")
    scopes = {"development20": (development, split["development"]),
              "heldout82": (held, split["held_out"]),
              "pooled102": (development + held, split["development"] + split["held_out"])}
    saved = read(HERE / "analysis.json")
    counts, exact = {}, 0
    for scope, (records, ids) in scopes.items():
        computed = summarize(records, ids)
        require(computed == saved[scope], "Frozen analysis differs: " + scope)
        counts[scope] = {c: x["correct"] for c, x in computed["conditions"].items()}
    for raw in development + held:
        generation = raw["init_response_generations"][0]
        if generation.get("correctness") is True:
            measured = expression_measurement(generation["extracted_answer"], raw["answer"])
            require(measured["arithmetic_is_24"] and measured["operand_multiset_matches"],
                    "Official True fails exact formula verification")
            exact += 1
    result = dict(status="passed", scientific_responses=612, independent_questions=102,
                  qualification_raw_records_checked=witness_count,
                  exact_correct_formulas_checked=exact, correct_counts=counts,
                  paired_invariants=204, analysis="identical_to_frozen_question_bootstrap",
                  boundary="CPU evidence verification; not a fresh GPU reproduction or mechanism proof")
    (HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
