"""Evaluate frozen early-stance labels against natural final behavior (CPU only).

Primary metrics give each question equal weight among its observed references;
bootstrap resamples whole questions, keeping seeds and conditions together.
Unknown final routes never enter the confusion matrix as negatives.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "outputs/validated-probe-20261013"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def key(row):
    return f"{row['id']}:{row['condition']}:{row['seed']}"


def reference_known(row):
    return (row.get("finish_reason") != "length" and row.get("final_available") is True
            and row.get("parsed") is True and isinstance(row.get("structural_reuse"), bool))


def confusion_metrics(rows, question_order=None, equal_question=True):
    groups = defaultdict(list)
    for r in rows:
        if r["final_route_known"]:
            groups[r["id"]].append(r)
    ids = list(groups) if question_order is None else question_order
    cells = dict(tp=0., fp=0., tn=0., fn=0.)
    for qid in ids:
        observed = groups.get(qid, [])
        for r in observed:
            weight = 1. / len(observed) if equal_question else 1.
            cell = ("tp" if r["early_adopt"] else "fn") if r["final_reuse"] else ("fp" if r["early_adopt"] else "tn")
            cells[cell] += weight
    tp, fp, tn, fn = (cells[k] for k in ("tp", "fp", "tn", "fn"))
    sensitivity = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    return dict(confusion=cells, sensitivity=sensitivity, specificity=specificity,
                balanced_accuracy=(sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None,
                adoption_precision=tp / (tp + fp) if tp + fp else None)


def interval(values):
    finite = [v for v in values if v is not None and np.isfinite(v)]
    return dict(ci95=np.quantile(finite, [.025, .975]).tolist() if finite else None,
                valid_bootstrap_draws=len(finite))


def evaluate(out):
    start = time.perf_counter()
    manifest = read(out / "manifest.json")
    prefixes = read(out / "development_prefixes.json")
    labels = read(out / "development_labels.json")
    # Guard precedes reading either future-bearing file.
    if set(labels) != {key(r) for r in prefixes} or len(labels) != 80:
        raise ValueError("Freeze all 80 prefix annotations before opening final references")
    for r in prefixes:
        label = labels[key(r)]
        if label["stance"] not in ("adopt", "reject", "none") or label.get("reference_file_or_post_cutoff_seen") is not False:
            raise ValueError(f"Invalid blind annotation: {key(r)}")
        if label["anchor"] is not None and label["anchor"] not in r["text"]:
            raise ValueError(f"Annotation anchor is outside prefix: {key(r)}")
    references = {key(r): r for r in read(out / "development_reference.json")}
    raw = {key(r): r for r in read(out / "development_raw.json")}
    if set(references) != set(labels) or set(raw) != set(labels):
        raise ValueError("References must match the frozen prompt/seed/condition records")
    joined = []
    for p in prefixes:
        k = key(p); r = references[k]; g = raw[k]; label = labels[k]
        known = reference_known(r)
        joined.append(dict(key=k, id=p["id"], condition=p["condition"], seed=p["seed"],
            stance=label["stance"], early_adopt=label["stance"] == "adopt", anchor=label["anchor"],
            final_route_known=known, final_reuse=r["structural_reuse"] if known else None,
            final_correct=r.get("correct") is True, final_expression=r.get("extracted_answer"),
            finish_reason=g["finish_reason"], full_tokens=len(g["token_ids"]), prefix_tokens=len(p["tokens"]),
            completed_within_prefix=g["finish_reason"] == "eos" and len(g["token_ids"]) <= manifest["prefix_token_limit"],
            prefix_to_full_token_ratio=len(p["tokens"]) / len(g["token_ids"]),
            source_raw=p["source_raw"], source_raw_line=p["source_raw_line"]))
    qids = [q["id"] for q in manifest["development"]]
    groups = {qid: [r for r in joined if r["id"] == qid] for qid in qids}
    history = [r for r in joined if r["condition"] == "COUNT_HISTORY"]
    primary = confusion_metrics(history)
    paired = []
    competence_subset = []
    for qid in qids:
        rs = groups[qid]; pairs = []
        for seed in sorted({r["seed"] for r in rs}):
            c = next(r for r in rs if r["condition"] == "COUNT_CLEAN" and r["seed"] == seed)
            h = next(r for r in rs if r["condition"] == "COUNT_HISTORY" and r["seed"] == seed)
            complete = c["final_route_known"] and h["final_route_known"]
            item = dict(id=qid, seed=seed, complete_pair=complete, clean_correct=c["final_correct"],
                        early_difference=int(h["early_adopt"]) - int(c["early_adopt"]),
                        final_difference=int(h["final_reuse"]) - int(c["final_reuse"]) if complete else None)
            pairs.append(item)
            if c["final_correct"]:
                competence_subset.append(item)
        observed = [r["final_difference"] for r in pairs if r["complete_pair"]]
        paired.append(dict(id=qid, complete_paired_seeds=len(observed),
            clean_success_any=any(r["clean_correct"] for r in pairs),
            early_difference=float(np.mean([r["early_difference"] for r in pairs])),
            final_difference=float(np.mean(observed)) if observed else None,
            prefix_to_full_token_ratio=float(np.mean([r["prefix_to_full_token_ratio"] for r in rs])), pairs=pairs))
    pby = {r["id"]: r for r in paired}
    effect = lambda ids, field: float(np.mean([pby[q][field] for q in ids if pby[q][field] is not None])) if any(pby[q][field] is not None for q in ids) else None
    rng = random.Random(manifest["bootstrap"]["seed"])
    draws = dict(balanced_accuracy=[], adoption_precision=[], early_difference=[], final_difference=[])
    for _ in range(manifest["bootstrap"]["draws"]):
        ids = rng.choices(qids, k=len(qids)); metrics = confusion_metrics(history, ids)
        for field in ("balanced_accuracy", "adoption_precision"):
            draws[field].append(metrics[field])
        for field in ("early_difference", "final_difference"):
            draws[field].append(effect(ids, field))
    for field in ("balanced_accuracy", "adoption_precision"):
        primary[field + "_uncertainty"] = interval(draws[field])
    effects = {field: dict(mean=effect(qids, field), **interval(draws[field])) for field in ("early_difference", "final_difference")}
    valid_h = [r for r in history if r["final_route_known"]]
    coverage = dict(questions=len(qids), trajectories=len(joined), history_references_known=len(valid_h),
        history_positive=sum(r["final_reuse"] for r in valid_h), history_negative=sum(not r["final_reuse"] for r in valid_h),
        history_positive_questions=len({r["id"] for r in valid_h if r["final_reuse"]}),
        history_negative_questions=len({r["id"] for r in valid_h if not r["final_reuse"]}),
        complete_pair_questions=sum(r["complete_paired_seeds"] > 0 for r in paired),
        complete_paired_seeds=sum(r["complete_paired_seeds"] for r in paired),
        clean_success_questions=sum(r["clean_success_any"] for r in paired))
    conditions = {}
    for condition in ("COUNT_CLEAN", "COUNT_HISTORY"):
        rs = [r for r in joined if r["condition"] == condition]
        conditions[condition] = dict(n=len(rs), stances=dict(Counter(r["stance"] for r in rs)),
            observed_correct=sum(r["final_correct"] for r in rs), complete=sum(r["final_route_known"] for r in rs),
            final_reuse=sum(r["final_reuse"] is True for r in rs), unknown=sum(not r["final_route_known"] for r in rs),
            completed_within_prefix=sum(r["completed_within_prefix"] for r in rs),
            mean_full_tokens=float(np.mean([r["full_tokens"] for r in rs])))
    ratio = float(np.mean([r["prefix_to_full_token_ratio"] for r in paired]))
    gate = manifest["gate1"]
    checks = dict(
        sufficient_complete_paired_questions=coverage["complete_pair_questions"] >= gate["min_questions_with_complete_paired_seed"],
        sufficient_clean_competence=coverage["clean_success_questions"] >= gate["min_clean_success_questions"],
        sufficient_history_positives=coverage["history_positive"] >= gate["min_complete_history_positive"],
        sufficient_history_negatives=coverage["history_negative"] >= gate["min_complete_history_negative"],
        balanced_accuracy=primary["balanced_accuracy"] is not None and primary["balanced_accuracy"] >= gate["min_balanced_accuracy"],
        balanced_accuracy_ci=primary["balanced_accuracy_uncertainty"]["ci95"] is not None and primary["balanced_accuracy_uncertainty"]["ci95"][0] > gate["min_balanced_accuracy_ci95_lower"],
        adoption_precision=primary["adoption_precision"] is not None and primary["adoption_precision"] >= gate["min_adoption_precision"],
        positive_early_history_effect=effects["early_difference"]["mean"] > 0,
        positive_final_history_effect=effects["final_difference"]["mean"] is not None and effects["final_difference"]["mean"] > 0,
        token_saving=ratio <= gate["max_mean_prefix_to_full_token_ratio"])
    passed = all(checks.values())
    failures = [name for name, ok in checks.items() if not ok]
    result = dict(goal=manifest["goal"], stage="gate1_cached_behavior_validation", gate1_cached_pass=passed,
        allowed_next_action="fresh_template_and_timing_check_max24" if passed else "stop_current_proxy_no_new_generation",
        coverage=coverage, conditions=conditions, primary_history_metrics=primary,
        raw_history_metrics=confusion_metrics(history, equal_question=False), paired_effects=effects,
        unfinished_history_metrics=confusion_metrics([r for r in history if not r["completed_within_prefix"]]),
        clean_success_pairs=dict(n=len(competence_subset), complete=sum(r["complete_pair"] for r in competence_subset),
            early_difference=float(np.mean([r["early_difference"] for r in competence_subset])) if competence_subset else None,
            final_difference=float(np.mean([r["final_difference"] for r in competence_subset if r["complete_pair"]])) if any(r["complete_pair"] for r in competence_subset) else None,
            interpretation="Descriptive conditioning on observed CLEAN success, not a population causal estimate"),
        token_cost=dict(mean_prefix_to_full_ratio=ratio, cached_full_tokens=sum(r["full_tokens"] for r in joined),
            bounded_prefix_tokens=sum(r["prefix_tokens"] for r in joined), new_gpu_seconds=0, new_model_forward_calls=0,
            interpretation="Token estimate on censored historical references, not measured GPU speedup. CPU clipping is not model inference."),
        checks=checks, failed_checks=failures, bootstrap=manifest["bootstrap"],
        specificity_boundary="Local expressed endorsement is the predictor. Final AST reuse is the reference; neither alone proves an internal mechanism.",
        template_check="not_started" if not passed else "pending", independent_confirmation="not_started",
        annotation_method="One assistant reviewed shuffled exact natural prefixes before final references; no inter-rater reliability estimate.",
        final_reference_censoring="Incomplete/unparseable/length-limited outputs are unknown. Complete-case association may have informative censoring.",
        per_question=paired,
        mismatches=[r for r in history if r["final_route_known"] and r["early_adopt"] != r["final_reuse"]])
    result["cpu_analysis_seconds"] = time.perf_counter() - start
    save(out / "development_joined.json", joined)
    save(out / "development_statistics.json", result)
    state = dict(status="gate1_cached_pass_awaiting_template_check" if passed else "gate1_stopped_proxy_validation_failed",
        annotated=len(labels), planned_annotations=80, gpu_seconds=0, new_model_forward_calls=0,
        gate1_cached_pass=passed, failed_checks=failures, independent_confirmation_requests=0)
    if (out / "decision.json").exists() and not passed:
        decision = read(out / "decision.json")
        if decision["decision"] == "STOP" and decision["reason"] == failures:
            state.update(status="complete_STOP", decision="STOP", gate0="COMPLETE", gate1="FAILED",
                         gate2="NOT_STARTED", gate3="COMPLETE", report=decision["report"])
    save(out / "run_state.json", state)
    print(json.dumps({k: v for k, v in result.items() if k not in ("per_question", "mismatches")}, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    evaluate(parser.parse_args().output)
