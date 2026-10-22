"""Reproduce the CPU outcome/timing audit of manually confirmed error witnesses.

Annotations are positive witnesses, not an exhaustive classification of recognition.
No model is loaded and no additional generations are requested.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_identity_trajectories_20261011 import expression_spans
from run_identity_mvp_20261011 import audit_expression


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]


def key(record):
    return str(record["id"]), record["seed"], record["phase"], record["condition"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    args = parser.parse_args()
    source = args.output / "candidate_adoption"
    out = source / "natural_recognition_review"
    annotations = load(out / "manual_annotations.json")["annotations"]
    generations = rows(source / "generations.jsonl")
    scores = {key(r): r for r in rows(source / "behaviour.jsonl")}
    questions = {str(q["id"]): q for q in load(source / "manifest.json")["questions"]}
    cohort = [r for r in generations if r["phase"] == "NATURAL" and r["condition"] == "COUNT_HISTORY"]
    outcomes, timing = [], []
    for annotation in annotations:
        raw = generations[annotation["source_line"] - 1]
        expected = str(annotation["id"]), annotation["seed"], "NATURAL", "COUNT_HISTORY"
        if key(raw) != expected:
            raise ValueError("Annotation does not match its raw source line")
        if raw["text"][annotation["anchor_start"]:annotation["anchor_end"]] != annotation["quote"]:
            raise ValueError("Annotation quote/offset no longer matches source")
        scored = scores[key(raw)]
        outcomes.append(dict(annotation, final_correct=scored["correct"],
            final_inventory_correct=scored.get("inventory_correct"), final_old_ast_reuse=scored.get("structural_reuse"),
            finish_reason=raw["finish_reason"], final_expression=scored.get("numeric_expression"),
            score_reason=scored.get("reason")))
        text = raw["text"].split("</think>", 1)[0]
        # One-character substitutions preserve offsets into the original raw trace.
        normalized = text.translate(str.maketrans({"×": "*", "÷": "/", "−": "-", "–": "-"}))
        legal = []
        for start, end, expression in expression_spans(normalized):
            audit = audit_expression(expression, questions[str(raw["id"])]["answer"], allow_literals=True)
            if audit.get("parsed") and audit["target_correct"] and audit["inventory_correct"]:
                legal.append(dict(start=start, end=end, expression=text[start:end],
                    numeric_expression=audit["numeric_expression"], context=text[max(0, start-90):end+90]))
        first = min(legal, key=lambda r: r["start"]) if legal else None
        timing.append(dict(id=raw["id"], seed=raw["seed"], source_line=annotation["source_line"],
            witness_start=annotation["anchor_start"], first_legal_observed=first,
            observed_legal_before_witness=bool(first and first["end"] < annotation["anchor_start"])))
    counts = Counter((r["final_correct"], r["final_old_ast_reuse"], r["finish_reason"]) for r in outcomes)
    result = dict(scope="Positive witness annotations only; unmatched/unreviewed are not negatives. Emitted critique is not proof of latent belief.",
        source_cohort_requests=len(cohort), reviewed_positive_witnesses=len(outcomes),
        questions=len({str(r["id"]) for r in outcomes}),
        outcome_counts=[dict(correct=c, old_ast_reuse=reuse, stop=stop, n=n) for (c,reuse,stop),n in counts.items()],
        records=outcomes)
    temporal = dict(n=len(timing), legal_before_witness=sum(r["observed_legal_before_witness"] for r in timing),
        interpretation="Selected positive-witness subset. Expression mention is not endorsement or timing of internal knowledge. Absence means unobserved. Neither timing direction identifies a causal effect.", records=timing)
    for name, value in (("outcomes.json", result), ("timing.json", temporal)):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print(json.dumps({k:v for k,v in result.items() if k != "records"}, ensure_ascii=False, indent=2))
    print(json.dumps(dict(legal_before_witness=temporal["legal_before_witness"], timing_n=len(timing))))


if __name__ == "__main__":
    main()
