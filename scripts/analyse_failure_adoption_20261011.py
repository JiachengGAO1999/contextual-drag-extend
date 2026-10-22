"""CPU-only joint judgment/choice analysis of the frozen 30-question experiment."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/generation-diagnostics-20261005/candidate_adoption"


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]


def main():
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf8"))
    records = read_rows(OUT / "behaviour.jsonl")
    keyed = {(r["id"], r["phase"], r["condition"], r["seed"]): r for r in records}
    raw = {(r["id"], r["phase"], r["condition"], r["seed"]): (line, r)
           for line, r in enumerate(read_rows(OUT / "generations.jsonl"), 1)}
    phases = {}
    for phase in manifest["phases"]:
        splits = {}
        for split in ("discovery", "replication", "all"):
            qs = [q for q in manifest["questions"] if split == "all" or q["split"] == split]
            splits[split] = {c: dict(n=len(qs) * len(manifest["seeds"]),
                correct=sum(keyed[q["id"], phase, c, seed]["correct"] for q in qs for seed in manifest["seeds"]))
                for c in manifest["conditions"]}
        directions = {}
        for prefix in ("COUNT", "IDENTITY"):
            signs, gains, losses = Counter(), 0, 0
            for q in manifest["questions"]:
                clean = [keyed[q["id"], phase, prefix + "_CLEAN", seed]["correct"] for seed in manifest["seeds"]]
                history = [keyed[q["id"], phase, prefix + "_HISTORY", seed]["correct"] for seed in manifest["seeds"]]
                delta = sum(history) - sum(clean)
                signs["improved" if delta > 0 else "worsened" if delta < 0 else "unchanged"] += 1
                gains += sum(not a and b for a, b in zip(clean, history))
                losses += sum(a and not b for a, b in zip(clean, history))
            directions[prefix] = dict(question_directions=dict(signs), paired_request_gains=gains, paired_request_losses=losses)
        phases[phase] = dict(splits=splits, history_effect_directions=directions)
    joint = {}
    for c in manifest["conditions"]:
        rs = [r for r in records if r["phase"] == "CANDIDATES" and r["condition"] == c]
        cells = Counter()
        for r in rs:
            if not r.get("judgments_parsed"): judgment = "unobserved"
            else:
                old = r["final_json"][f"option_{r['old_index']}_valid"]
                good = r["final_json"][f"option_{3-r['old_index']}_valid"]
                judgment = "both_valid" if old and good else "both_invalid" if not old and not good else "old_only" if old else "legal_only"
            choice = "old" if r.get("old_selected") else "legal" if r.get("correct") else "unobserved"
            cells[judgment, choice] += 1
        joint[c] = [dict(judgment=j, choice=k, n=n) for (j, k), n in sorted(cells.items())]
    examples = []
    for q in manifest["questions"]:
        for seed in manifest["seeds"]:
            clean = keyed[q["id"], "CANDIDATES", "COUNT_CLEAN", seed]
            history = keyed[q["id"], "CANDIDATES", "COUNT_HISTORY", seed]
            if not (clean["judgments_correct"] and history["old_selected"] and history["old_accepted"]): continue
            line, r = raw[q["id"], "CANDIDATES", "COUNT_HISTORY", seed]
            examples.append(dict(id=q["id"], split=q["split"], seed=seed, answer=q["answer"],
                old=q["old_numeric"], legal=q["legal_numeric"], clean_json=clean["final_json"], history_json=history["final_json"],
                raw_source="candidate_adoption/generations.jsonl", raw_source_line=line,
                thinking_end=r["text"].split("</think>")[0][-2400:]))
    result = dict(records=len(records), unique_requests=len(keyed), phases=phases, joint_judgment_choice=joint,
        count_correct_judgment_to_old_selection_examples=examples,
        scope="Question-level effects are in summary.json. Joint cells and selected flips are descriptive, not causal mediation or independent samples. Conditioning on emitted judgments is conditioning on a post-treatment variable. Zero observed contradictions do not prove a zero population rate.")
    (OUT / "joint_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(dict(records=len(records), unique_requests=len(keyed), joint=joint, count_flip_requests=len(examples),
        count_flip_questions=len({r["id"] for r in examples})), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
