"""Prepare only indexed P1 cases for CPU semantic review; never calls a model.

Selected raw lines are read using Phase 1 locators and verified against its hashes.
Quoted semantic annotations live separately in annotations.json and must match
the raw prompt/text verbatim. Absence of a regex cue is never a negative label.
"""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_identity_trajectories_20261011 import expression_spans
from run_identity_mvp_20261011 import audit_expression
from run_information_followup_20261005 import same_tree

PHASE1 = ROOT / "outputs/evidence-audit-phase1-20261013"
OUT = ROOT / "outputs/p1-review-phase2a-20261013"


def save(name, x):
    (OUT / name).write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(x) for x in (PHASE1 / "trajectory_index.jsonl").read_text(encoding="utf8").splitlines()]
    support = [r for r in rows if r["dataset"] in ("cross_question_behavior", "candidate_adoption")
               and r["task"] == "solve" and r["legal_mentions"] and not r["correct"] and r["finish"] == "eos"]
    selected = {r["uid"]: ("primary_support", r) for r in support}
    labels = json.loads((PHASE1 / "early_stance_audit.json").read_text(encoding="utf8"))["labels"]
    for lab in labels:
        if lab["early_adopt"] and lab["final_route_known"] and not lab["final_reuse"]:
            uid = f"{lab['source_raw']}:{lab['source_raw_line']}"
            r = next(r for r in rows if r["uid"] == uid)
            role = "history_counterexample" if r["condition"].endswith("HISTORY") else "clean_counterexample"
            selected.setdefault(uid, (role, r))
    for r in rows:
        paired = r["dataset"] == "cross_question_behavior" and r["id"] in ("285", "1084", "651") and r["condition"] in ("CANDIDATE", "CONTROL")
        diagnostics = r["dataset"] == "candidate_adoption" and r["phase"] == "NATURAL" and r["condition"] == "COUNT_HISTORY" and (
            (r["id"], r["seed"]) in (("44", 20261015), ("339", 20261016), ("1073", 20261015)))
        if paired or diagnostics:
            selected.setdefault(r["uid"], ("paired_terminal_control" if paired else "diagnosis_boundary", r))
    records = []
    # Scan physical lines only to retrieve explicitly selected records, not to
    # inspect additional trajectories or recalculate the 3,889-record audit.
    wanted = {}
    for uid, (role, r) in selected.items():
        wanted.setdefault(r["source"], {})[r["line"]] = (role, r)
    for source, targets in wanted.items():
        with (ROOT / source).open(encoding="utf8") as handle:
            for n, line in enumerate(handle, 1):
                if n not in targets:
                    continue
                role, r = targets[n]
                raw = json.loads(line)
                assert hashlib.sha256(line.rstrip("\r\n").encode("utf8")).hexdigest() == r["raw_line_sha256_utf8_without_newline"]
                prompt = raw.get("prompt")
                if prompt is None:
                    mpath = ROOT / "outputs/generation-diagnostics-20261005/cross_question_behavior/manifest.json"
                    m = json.loads(mpath.read_text(encoding="utf8"))
                    prompt = next(q["prompt"] for q in m["questions"] if q["id"] == r["id"])
                text = raw["text"]
                draft = prompt.split("-- beginning of the draft --", 1)[-1].split("-- end of the draft --", 1)[0] if "-- beginning of the draft --" in prompt else ""
                provided_legal = []
                for a, b, expr in expression_spans(draft):
                    for piece in expr.split("="):
                        audited = audit_expression(piece.strip(), r["numbers"])
                        if audited.get("target_correct") and audited.get("inventory_correct"):
                            provided_legal.append(dict(start=a, end=b, expression=piece.strip(), audit=audited))
                cues = []
                pattern = r"twice|thrice|three times|two times|more than once|extra|reus\w*|violat\w*|incorrect|invalid|wrong|both (?:are|solutions|expressions)|more complex|simpler|choose|pick|prefer"
                for match in re.finditer(pattern, text, re.I):
                    a, b = match.span()
                    cues.append(dict(start=max(0, a-130), end=min(len(text), b+170), trigger=match.group(),
                        quote=text[max(0, a-130):min(len(text), b+170)]))
                records.append(dict(role=role, index=r, prompt=prompt, draft=draft,
                    raw=raw, provided_legal_detected=provided_legal, cues=cues,
                    cue_warning="Review candidates only; user-feedback echoes, tentative questions and other expressions are not diagnoses of the old expression."))
    records.sort(key=lambda x: (x["role"], x["index"]["dataset"], x["index"]["line"]))
    save("selected_raw.json", records)
    save("selection.json", dict(records=len(records), roles=dict(Counter(r["role"] for r in records)),
        primary_questions=len({tuple(r["index"]["numbers"]) for r in records if r["role"] == "primary_support"}),
        selection="All 20 EOS P1 supports in the two Phase 1 primary pools; seven history early-endorsement counterexamples, two clean counterexamples, six paired terminal controls, three diagnosis boundaries.",
        limits="Selected posthoc cases, not prevalence or causality; no new GPU calls. No P2 experiment and no full-corpus re-review."))
    md = ["# P1 targeted full-text packets", "", "Full selected prompts and outputs. Semantic annotations are in annotations.json; regex cues are only navigation aids.", ""]
    for r in records:
        i = r["index"]
        md += [f"## {i['dataset']} / {i['id']} / {i['condition']} / {i['seed']}", "", f"Role: {r['role']}; source `{i['source']}` physical line {i['line']}.",
            "", "### Supplied prompt", "", "```text", r["prompt"], "```", "", "### Generated text", "", "```text", r["raw"]["text"], "```", ""]
    (OUT / "full_review_packets.md").write_text("\n".join(md), encoding="utf8")
    annotations = OUT / "annotations.json"
    if annotations.exists():
        anns = json.loads(annotations.read_text(encoding="utf8"))
        ix = {r["index"]["uid"]: r for r in records}
        for ann in anns:
            r = ix[ann["uid"]]
            for e in ann["evidence"]:
                text = r["prompt"] if e.get("source") == "prompt" else r["raw"]["text"]
                start = text.find(e["quote"], e.get("search_from", 0))
                if start < 0:
                    raise ValueError((ann["uid"], e["quote"]))
                e["start"], e["end"] = start, start + len(e["quote"])
            ann["locator"] = {k: r["index"][k] for k in ("source", "line", "id", "condition", "seed", "finish", "final", "raw_line_sha256_utf8_without_newline")}
        save("annotations.json", anns)
    print(json.dumps(dict(records=len(records), roles=dict(Counter(r["role"] for r in records)),
        primary_supports=len(support), source_files=len(wanted), annotation_records=len(anns) if annotations.exists() else 0)))


if __name__ == "__main__":
    main()
