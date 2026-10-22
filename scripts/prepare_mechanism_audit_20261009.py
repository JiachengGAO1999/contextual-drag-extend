"""Prepare CPU-only semantic review candidates; keywords never label events."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    args = parser.parse_args()
    source = args.output / "cross_question_behavior"
    out = args.output / "mechanism_audit"
    out.mkdir(exist_ok=True)
    raw_path = source / "generations.jsonl"
    raw = read_rows(raw_path)
    scored = {(r["id"], r["seed"], r["condition"]): r for r in read_rows(source / "behaviour.jsonl")}
    config = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in config["questions"]}
    pattern = re.compile(r"reus\w*|repeat\w*|duplicat\w*|exactly once|not allowed|invalid|incorrect|draft", re.I)
    queue = []
    for line, row in enumerate(raw, 1):
        text = row["text"]
        hits = list(pattern.finditer(text))
        positions = []
        for match in hits[:4] + hits[-4:]:
            if not any(abs(match.start()-p) < 200 for p in positions):
                positions.append(match.start())
        q = questions[row["id"]]
        score = scored[row["id"], row["seed"], row["condition"]]
        queue.append(dict(id=row["id"], seed=row["seed"], condition=row["condition"],
            raw_source=str(raw_path.relative_to(ROOT)), raw_line=line,
            answer=q["answer"], old_expression=q["old_expression"],
            final_correct=score["correct"], final_expression=score["extracted_answer"],
            finish_reason=row["finish_reason"],
            keyword_candidates=[dict(start=max(0, p-180), end=min(len(text), p+420),
                text=text[max(0, p-180):min(len(text), p+420)]) for p in sorted(positions)],
            review_status="pending_semantic_review", reviewed_events=[]))
    # Keep human annotations in a separate reviews.json; regeneration cannot erase them.
    with (out / "audit_queue.jsonl").open("w", encoding="utf-8") as handle:
        for row in queue:
            handle.write(json.dumps(row, ensure_ascii=False)+"\n")
    note = dict(status="review_queue_prepared_not_reviewed", trajectories=len(queue),
        questions=len({r["id"] for r in queue}), gpu_used=False,
        event_types=["quote_or_examination", "explicit_correct_rejection", "explicit_wrong_endorsement", "constructive_use", "uncertain"],
        rule="Record exact source spans and the expression being judged; distinguish old versus new construction. Keyword matches are retrieval candidates, never semantic labels. Candidate snippets are incomplete: inspect full raw text before assigning an event sequence. Final answer correctness and expression reuse are already scored, not newly inferred.",
        provenance_rule="Under causal attention, pre-draft token values cannot depend on later draft tokens. Post-draft prompt and generated-token values can; attention weights may still depend on draft-influenced queries even for pre-draft values.",
        limitations=["Outcomes already observed; this is exploratory review, not blinded confirmation.",
            "Expressed reasoning is not proof of hidden computation or faithful causal explanation.",
            "All 72 trajectories retained; ambiguous references stay uncertain."])
    (out / "status.json").write_text(json.dumps(note, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: note[k] for k in ("status", "trajectories", "questions", "gpu_used")}))


if __name__ == "__main__":
    main()
