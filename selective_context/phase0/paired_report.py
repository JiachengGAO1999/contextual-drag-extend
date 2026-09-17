"""Paired descriptive and bootstrap report for a completed R0-R4 run."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(path, bootstrap_samples=10000, conditions=None):
    grouped = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        condition = record["init_response_generations_metadata"]["intervention"]["condition_id"]
        group = grouped.setdefault(record["id"], {})
        if condition in group:
            raise ValueError(f"Duplicate condition {record['id']} {condition}")
        group[condition] = record["init_response_generations"][0]
    conditions = conditions or [f"R{i}" for i in range(5)]
    partial = [key for key, rows in grouped.items() if set(rows) != set(conditions)]
    rows = [rows for rows in grouped.values() if set(rows) == set(conditions)]
    if not rows:
        raise ValueError("No complete pairs")
    correct = np.array([[r[c]["correctness"] is True for c in conditions] for r in rows], dtype=float)
    rng = np.random.default_rng(2027)
    sample_indices = rng.integers(0, len(rows), (bootstrap_samples, len(rows)))
    sampled = correct[sample_indices].mean(axis=1)
    report = {"n_complete_pairs": len(rows), "partial_problem_ids": partial,
        "bootstrap": {"unit": "problem", "resamples": bootstrap_samples, "seed": 2027,
                      "method": "paired percentile, 95% CI"}, "conditions": {}, "effects": {}}
    for i, c in enumerate(conditions):
        report["conditions"][c] = {"accuracy": float(correct[:, i].mean()),
            "correct_n": int(correct[:, i].sum()),
            "parse_rate": sum(r[c]["correctness"] is not None for r in rows)/len(rows),
            "completion_rate": sum(r[c]["finish_reason"] == "eos" for r in rows)/len(rows)}
    for better_name, reference_name in [('R0','R1'), ('R0','R2'), ('R3','R2'), ('R4','R3'), ('R4','R2')]:
        if better_name not in conditions or reference_name not in conditions:
            continue
        better, reference = conditions.index(better_name), conditions.index(reference_name)
        difference = correct[:, better] - correct[:, reference]
        ci = np.quantile(sampled[:, better] - sampled[:, reference], [0.025, 0.975])
        report["effects"][f"{better_name}-{reference_name}"] = {
            "effect_pp": float(difference.mean()*100), "ci95_pp": (ci*100).tolist(),
            "reference_wrong_to_correct": int((difference == 1).sum()),
            "reference_correct_to_wrong": int((difference == -1).sum()),
            "unparsed_scoring": "unparsed outputs count as not correct; included in paired denominator"}
    r0, r2 = conditions.index('R0'), conditions.index('R2')
    residual = correct[:, r0].mean() - correct[:, r2].mean()
    report["recovery_ratios"] = {}
    boot_residual = sampled[:, r0] - sampled[:, r2]
    for name in ('R3', 'R4'):
        i = conditions.index(name)
        ratio = (correct[:, i].mean()-correct[:, r2].mean())/residual if residual > 0 else None
        ratio_ci = None
        # Ratios with a near-zero/sign-changing denominator have unstable CIs.
        if np.all(boot_residual > 0):
            ratio_ci = np.quantile((sampled[:, i]-sampled[:, r2])/boot_residual, [.025, .975]).tolist()
        report["recovery_ratios"][f"({name}-R2)/(R0-R2)"] = {
            "value": None if ratio is None else float(ratio), "ci95": ratio_ci,
            "note": "ratio undefined for nonpositive residual; CI omitted if bootstrap denominator crosses zero"}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.results)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
