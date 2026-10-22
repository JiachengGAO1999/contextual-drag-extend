"""Frozen analysis of the 15-question Qwen3-32B target-model experiment.

The R0 capability run and the subsequent R2/R3 intervention run were persisted
separately.  This script joins them by (question, seed), uses only the frozen
generation-time scorer decisions, and refuses incomplete or boundary-invalid
inputs.  It never regenerates or rescores an answer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CONDITIONS = ("R0", "R2", "R3")
EFFECTS = {
    "drag_R0_minus_R2": ("R0", "R2"),
    "continued_access_R3_minus_R2": ("R3", "R2"),
    "residual_R3_minus_R0": ("R3", "R0"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    weight = pos - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def exact_mcnemar_p(a0_b1: int, a1_b0: int) -> float:
    n = a0_b1 + a1_b0
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(a0_b1, a1_b0) + 1)) / 2**n
    return min(1.0, 2 * tail)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        generations = raw.get("init_response_generations") or []
        if len(generations) != 1:
            raise ValueError(f"{path}:{line_number}: expected one generation")
        generation = generations[0]
        metadata = generation.get("selective_context_metadata") or {}
        request = metadata.get("request") or {}
        correctness = generation.get("correctness")
        if correctness not in (True, False, None):
            raise ValueError(f"{path}:{line_number}: invalid correctness")
        tokens = raw.get("generated_token_ids") or []
        rows.append({
            "id": str(raw["id"]),
            "seed": int(request["sample_seed"]),
            "condition": str(request["condition_id"]),
            "stratum": str(raw["stratum"]),
            "correct": int(correctness is True),
            "score_status": "correct" if correctness is True else "incorrect" if correctness is False else "unresolved",
            "finish_reason": str(generation.get("finish_reason")),
            "thinking_status": str(raw.get("thinking_status")),
            "generated_tokens": len(tokens),
            "first_generated_token": tokens[0] if tokens else None,
            "prompt_sha256": request.get("prompt_sha256"),
            "input_ids_sha256": request.get("input_ids_sha256"),
            "draft_token_span": request.get("draft_token_span"),
            "access_mode": metadata.get("access_mode"),
            "extracted_answer": generation.get("extracted_answer"),
            "model_config_alias": metadata.get("model_config_alias"),
        })
    return rows


def clustered_ci(values: dict[str, list[float]], draws: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    ids = sorted(values)
    estimates = []
    for _ in range(draws):
        sampled = [rng.choice(ids) for _ in ids]
        estimates.append(statistics.fmean(v for qid in sampled for v in values[qid]))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def exact_question_signflip(values: dict[str, list[float]]) -> float:
    means = [statistics.fmean(values[qid]) for qid in sorted(values)]
    observed = abs(statistics.fmean(means))
    null = (
        abs(statistics.fmean(sign * value for sign, value in zip(signs, means)))
        for signs in itertools.product((-1, 1), repeat=len(means))
    )
    return sum(value >= observed - 1e-12 for value in null) / (2 ** len(means))


def analyze(rows: list[dict[str, Any]], draws: int, seed: int) -> dict[str, Any]:
    indexed = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    ids = sorted({r["id"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    conditions = {}
    for offset, condition in enumerate(CONDITIONS):
        selected = [r for r in rows if r["condition"] == condition]
        by_question: dict[str, list[float]] = defaultdict(list)
        for row in selected:
            by_question[row["id"]].append(row["correct"])
        tokens = [r["generated_tokens"] for r in selected]
        conditions[condition] = {
            "correct": sum(r["correct"] for r in selected),
            "n": len(selected),
            "accuracy": statistics.fmean(r["correct"] for r in selected),
            "accuracy_question_cluster_bootstrap_95ci": clustered_ci(by_question, draws, seed + offset),
            "finish_reasons": dict(sorted(Counter(r["finish_reason"] for r in selected).items())),
            "score_status": dict(sorted(Counter(r["score_status"] for r in selected).items())),
            "generated_tokens_mean": statistics.fmean(tokens),
            "generated_tokens_median": statistics.median(tokens),
            "generated_tokens_max": max(tokens),
        }
    effects = {}
    for offset, (name, (left, right)) in enumerate(EFFECTS.items(), 10):
        by_question: dict[str, list[float]] = defaultdict(list)
        transitions = Counter()
        for qid in ids:
            for sample_seed in seeds:
                a = indexed[qid, sample_seed, left]["correct"]
                b = indexed[qid, sample_seed, right]["correct"]
                by_question[qid].append(a - b)
                transitions[a, b] += 1
        effects[name] = {
            "definition": f"{left}_minus_{right}",
            "estimate": statistics.fmean(v for values in by_question.values() for v in values),
            "question_cluster_bootstrap_95ci": clustered_ci(by_question, draws, seed + offset),
            "exact_question_cluster_signflip_p_two_sided": exact_question_signflip(by_question),
            "exact_mcnemar_p_two_sided": exact_mcnemar_p(transitions[0, 1], transitions[1, 0]),
            "transitions": {
                f"{left}0_{right}0": transitions[0, 0],
                f"{left}0_{right}1": transitions[0, 1],
                f"{left}1_{right}0": transitions[1, 0],
                f"{left}1_{right}1": transitions[1, 1],
            },
        }
    return {"conditions": conditions, "effects": effects}


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--r0", type=Path, default=root / "runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/results.jsonl")
    parser.add_argument("--intervention", type=Path, default=root / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/results.jsonl")
    parser.add_argument("--r0-completion", type=Path, default=root / "runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/completion.json")
    parser.add_argument("--r0-gate", type=Path, default=root / "runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/gate_decision.json")
    parser.add_argument("--r0-config", type=Path, default=root / "runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/config.json")
    parser.add_argument("--intervention-completion", type=Path, default=root / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/completion.json")
    parser.add_argument("--intervention-config", type=Path, default=root / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/config.json")
    parser.add_argument("--boundary", type=Path, default=root / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/boundary_checks.json")
    parser.add_argument("--preflight", type=Path, default=root / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/preflight.json")
    parser.add_argument("--output", type=Path, default=root / "runs/game24_qwen3_32b_target_15q_20260923_analysis")
    parser.add_argument("--bootstrap-draws", type=int, default=50_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260923)
    args = parser.parse_args()

    r0 = load_rows(args.r0)
    intervention = load_rows(args.intervention)
    rows = r0 + intervention
    ids = sorted({r["id"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    keys = [(r["id"], r["seed"], r["condition"]) for r in rows]
    expected = {(qid, seed, condition) for qid in ids for seed in seeds for condition in CONDITIONS}
    indexed = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    paired = [(qid, seed) for qid in ids for seed in seeds]
    r0_completion = json.loads(args.r0_completion.read_text(encoding="utf-8"))
    gate = json.loads(args.r0_gate.read_text(encoding="utf-8"))
    r0_config = json.loads(args.r0_config.read_text(encoding="utf-8"))
    completion = json.loads(args.intervention_completion.read_text(encoding="utf-8"))
    intervention_config = json.loads(args.intervention_config.read_text(encoding="utf-8"))
    boundary = json.loads(args.boundary.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))

    same_text = {
        "prompt_hash_matches": sum(indexed[qid, seed, "R2"]["prompt_sha256"] == indexed[qid, seed, "R3"]["prompt_sha256"] for qid, seed in paired),
        "input_ids_hash_matches": sum(indexed[qid, seed, "R2"]["input_ids_sha256"] == indexed[qid, seed, "R3"]["input_ids_sha256"] for qid, seed in paired),
        "draft_span_matches": sum(indexed[qid, seed, "R2"]["draft_token_span"] == indexed[qid, seed, "R3"]["draft_token_span"] for qid, seed in paired),
        "first_generated_token_matches": sum(indexed[qid, seed, "R2"]["first_generated_token"] == indexed[qid, seed, "R3"]["first_generated_token"] for qid, seed in paired),
        "paired_units": len(paired),
    }
    duplicate_keys = [list(key) for key, count in Counter(keys).items() if count != 1]
    aligned_config_fields = (
        "model", "model_config_alias", "task", "questions", "seeds", "sampling",
        "context", "max_new_tokens", "batch_size", "gpu_memory_utilization",
        "prepared_manifest_sha256", "enable_thinking", "backend", "eos_policy",
    )
    config_alignment = {
        field: r0_config.get(field) == intervention_config.get(field)
        for field in aligned_config_fields
    }
    strata_by_question = defaultdict(set)
    for row in rows:
        strata_by_question[row["id"]].add(row["stratum"])
    inconsistent_strata = {qid: sorted(v) for qid, v in strata_by_question.items() if len(v) != 1}
    audit = {
        "complete_factorial": (
            len(rows) == 90 and len(ids) == 15 and seeds == [927001, 927002]
            and not duplicate_keys and set(keys) == expected and not inconsistent_strata
            and r0_completion.get("completed") == 30 and completion.get("completed") == 60
            and gate.get("status") == "passed" and preflight.get("passed") is True
            and len(boundary) == 30 and all(item.get("matches") is True for item in boundary)
            and all(value == len(paired) for key, value in same_text.items() if key != "paired_units")
            and all(config_alignment.values())
        ),
        "rows": len(rows),
        "questions": len(ids),
        "question_ids": ids,
        "seeds": seeds,
        "condition_counts": dict(sorted(Counter(r["condition"] for r in rows).items())),
        "duplicate_keys": duplicate_keys,
        "missing_keys": [list(key) for key in sorted(expected - set(keys))],
        "unexpected_keys": [list(key) for key in sorted(set(keys) - expected)],
        "inconsistent_question_strata": inconsistent_strata,
        "finish_reasons": dict(sorted(Counter(r["finish_reason"] for r in rows).items())),
        "thinking_status": dict(sorted(Counter(r["thinking_status"] for r in rows).items())),
        "score_status": dict(sorted(Counter(r["score_status"] for r in rows).items())),
        "access_modes": dict(sorted(Counter(f"{r['condition']}:{r['access_mode']}" for r in rows).items())),
        "same_text_and_boundary_checks": same_text,
        "persisted_boundary_checks": {"passed": sum(bool(x.get("matches")) for x in boundary), "n": len(boundary)},
        "r0_gate": gate,
        "r0_completion": r0_completion,
        "intervention_completion": completion,
        "preflight": preflight,
        "r0_vs_intervention_config_alignment": config_alignment,
    }
    if not audit["complete_factorial"]:
        raise RuntimeError(f"integrity audit failed: {audit}")

    pooled = analyze(rows, args.bootstrap_draws, args.bootstrap_seed)
    by_stratum = {
        stratum: analyze([r for r in rows if r["stratum"] == stratum], args.bootstrap_draws, args.bootstrap_seed + 100 + i)
        for i, stratum in enumerate(sorted({r["stratum"] for r in rows}))
    }
    per_question = []
    for qid in ids:
        record: dict[str, Any] = {"id": qid, "stratum": next(iter(strata_by_question[qid]))}
        for condition in CONDITIONS:
            record[condition] = sum(indexed[qid, seed, condition]["correct"] for seed in seeds)
        record["drag_R0_minus_R2"] = (record["R0"] - record["R2"]) / len(seeds)
        record["continued_access_R3_minus_R2"] = (record["R3"] - record["R2"]) / len(seeds)
        record["residual_R3_minus_R0"] = (record["R3"] - record["R0"]) / len(seeds)
        per_question.append(record)

    analysis = {
        "analysis_version": "game24_qwen32_target_v1_20260923",
        "inputs": {
            "r0_results": {"path": str(args.r0), "sha256": sha256(args.r0)},
            "intervention_results": {"path": str(args.intervention), "sha256": sha256(args.intervention)},
            "r0_gate_sha256": sha256(args.r0_gate),
            "boundary_checks_sha256": sha256(args.boundary),
            "r0_config_sha256": sha256(args.r0_config),
            "intervention_config_sha256": sha256(args.intervention_config),
        },
        "protocol": {
            "model": "Qwen3-32B (thinking)",
            "accuracy_unit": "request (two fixed seeds per question)",
            "paired_unit": "question-seed",
            "uncertainty": "percentile bootstrap over 15 question clusters",
            "bootstrap_draws": args.bootstrap_draws,
            "bootstrap_seed": args.bootstrap_seed,
            "scoring": "persisted frozen scorer output; no regeneration or rescoring",
            "primary_scope": "pooled 15-question frozen target-model set",
        },
        "audit": audit,
        "pooled": pooled,
        "by_stratum_descriptive": by_stratum,
        "per_question": per_question,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output / "per_question.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_question[0]))
        writer.writeheader(); writer.writerows(per_question)
    with (args.output / "request_level.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["id", "seed", "condition", "stratum", "correct", "score_status", "finish_reason", "thinking_status", "generated_tokens", "first_generated_token", "prompt_sha256", "input_ids_sha256", "draft_token_span", "access_mode", "extracted_answer"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)

    lines = [
        "# Qwen3-32B target-model generalization: frozen 15-question analysis", "",
        f"R0 input SHA-256: `{analysis['inputs']['r0_results']['sha256']}`  ",
        f"R2/R3 input SHA-256: `{analysis['inputs']['intervention_results']['sha256']}`", "",
        "Persisted scorer decisions are used without regeneration or rescoring.", "",
        "## Integrity", "",
        f"- Complete 15-question × 2-seed × 3-condition factorial: `{audit['complete_factorial']}`",
        f"- Rows and condition counts: {audit['rows']}; `{audit['condition_counts']}`",
        f"- Finish reasons: `{audit['finish_reasons']}`; score status: `{audit['score_status']}`",
        f"- Same-text and boundary checks: `{same_text}`",
        f"- Persisted first-token checks: `{audit['persisted_boundary_checks']}`",
        f"- R0/R2/R3 model and sampling config alignment: `{config_alignment}`",
        f"- R0 capability gate: `{gate}`", "",
        "## Pooled accuracy", "",
        "| R0 clean | R2 full failed-draft access | R3 generation-time block |",
        "|---:|---:|---:|",
    ]
    lines.append("| " + " | ".join(
        f"{pooled['conditions'][c]['correct']}/{pooled['conditions'][c]['n']} ({pct(pooled['conditions'][c]['accuracy'])})"
        for c in CONDITIONS
    ) + " |")
    lines.extend(["", "## Paired effects", "", "| Effect | Estimate [question-cluster bootstrap 95% CI] | McNemar p | Question sign-flip p |", "|---|---:|---:|---:|"])
    for name in EFFECTS:
        effect = pooled["effects"][name]
        low, high = effect["question_cluster_bootstrap_95ci"]
        lines.append(f"| {name} | {pct(effect['estimate'])} [{pct(low)}, {pct(high)}] | {effect['exact_mcnemar_p_two_sided']:.4g} | {effect['exact_question_cluster_signflip_p_two_sided']:.4g} |")
    lines.extend(["", "## Descriptive cohort check", "", "| Cohort | Questions | R0 | R2 | R3 | R0-R2 | R3-R2 |", "|---|---:|---:|---:|---:|---:|---:|"])
    for stratum, result in by_stratum.items():
        n_questions = len({r["id"] for r in rows if r["stratum"] == stratum})
        cond = result["conditions"]
        eff = result["effects"]
        lines.append(f"| {stratum} | {n_questions} | {cond['R0']['correct']}/{cond['R0']['n']} | {cond['R2']['correct']}/{cond['R2']['n']} | {cond['R3']['correct']}/{cond['R3']['n']} | {pct(eff['drag_R0_minus_R2']['estimate'])} | {pct(eff['continued_access_R3_minus_R2']['estimate'])} |")
    lines.extend(["", "## Interpretation", "", "The frozen set shows both prerequisite contextual drag (R0 > R2) and recovery when only generation-time direct access to the failed draft is blocked (R3 > R2). R3 remains below R0, so the result supports a substantial but incomplete contribution of continued direct access; it does not establish complete mediation, information erasure, or practical superiority to deletion.", ""])
    report = "\n".join(lines)
    (args.output / "summary.md").write_text(report, encoding="utf-8")

    table = [
        "% Auto-generated by scripts/analyze_game24_qwen32_target_20260923.py",
        "\\begin{tabular}{lrrr}", "\\toprule", "Model & R0 & R2 & R3 \\\\", "\\midrule",
        "Qwen3-32B & " + " & ".join(f"{pooled['conditions'][c]['correct']}/{pooled['conditions'][c]['n']}" for c in CONDITIONS) + " \\\\",
        "\\bottomrule", "\\end{tabular}", "",
    ]
    (args.output / "accuracy_table.tex").write_text("\n".join(table), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
