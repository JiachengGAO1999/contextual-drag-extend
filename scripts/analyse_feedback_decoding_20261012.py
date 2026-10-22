"""CPU analysis of completed paired-feedback requests; no model loading or resampling."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import load, rows, bootstrap
from run_feedback_decoding_20261012 import CONDITIONS, summarize
from run_information_followup_20261005 import same_tree
from run_identity_mvp_20261011 import audit_expression
from audit_identity_trajectories_20261011 import expression_spans
from selective_context.tasks import extract_math_box


def frozen_cohort_bounds(manifest, scores):
    """Finite-cohort bounds for missing binary outcomes, not confidence intervals."""
    metrics = {
        "true_gain": {"GUIDED_TRUE": 1, "FULL_TRUE": -1},
        "false_gain": {"GUIDED_FALSE": 1, "FULL_FALSE": -1},
        "polarity_interaction": {"GUIDED_TRUE": 1, "FULL_TRUE": -1,
                                 "GUIDED_FALSE": -1, "FULL_FALSE": 1},
    }
    result = {}
    for history in ("BAD", "GOOD"):
        questions = [q for q in manifest["questions"] if history in q["histories"]]
        result[history] = {}
        for metric, coefficients in metrics.items():
            per_question = []
            for q in questions:
                known = {c: int(scores[q["id"], history, c]["correct"])
                         for c in coefficients if (q["id"], history, c) in scores}
                missing = [c for c in coefficients if c not in known]
                observed = sum(coefficients[c]*value for c, value in known.items())
                lower = observed + sum(min(0, coefficients[c]) for c in missing)
                upper = observed + sum(max(0, coefficients[c]) for c in missing)
                per_question.append(dict(id=q["id"], known=known, missing=missing,
                                         score_difference_bounds=[lower, upper]))
            n = len(questions)
            result[history][metric] = dict(planned_questions=n,
                fully_observed_questions=sum(not r["missing"] for r in per_question),
                mean_bounds=[sum(r["score_difference_bounds"][i] for r in per_question)/n
                             for i in (0, 1)] if n else None,
                per_question=per_question)
    return dict(histories=result,
        interpretation="Sharp worst/best-case bounds for the frozen finite cohort and one seed when each unfinished correctness score can be 0 or 1. Not confidence intervals, population effects, or proof of equivalence. Completed length stops keep their observed score 0; missing GOOD histories are outside the eligible GOOD cohort. Added as a posthoc missingness analysis; not a new primary metric or an early-stop rule.")


def analyse(output):
    m = load(output / "manifest.json")
    raw = {(r["id"],r["history"],r["condition"]):(line,r)
           for line,r in enumerate(rows(output / "generations.jsonl"),1)}
    scores = {(r["id"],r["history"],r["condition"]):r for r in rows(output / "behaviour.jsonl")}
    state = load(output / "run_state.json")
    result = summarize(m, output, state["status"], state.get("error"))
    bounds = frozen_cohort_bounds(m, scores)
    save(output/"missing_outcome_bounds.json", bounds)
    planned_keys = [(q["id"], h, c) for q in m["questions"] for h in q["histories"] for c in CONDITIONS]
    save(output/"completion_audit.json", dict(status=state["status"], planned=len(planned_keys),
        raw_completed=len(raw), scored_completed=len(scores),
        missing_requests=[dict(id=k[0], history=k[1], condition=k[2]) for k in planned_keys if k not in scores],
        raw_without_score=[dict(id=k[0], history=k[1], condition=k[2]) for k in raw if k not in scores],
        score_without_raw=[dict(id=k[0], history=k[1], condition=k[2]) for k in scores if k not in raw]))
    transitions, cases, source_copy, token_lengths = {}, [], {}, {}
    for history in ("BAD","GOOD"):
        token_lengths[history] = {}
        for c in CONDITIONS:
            lengths = [r["generated_tokens"] for key,(_,r) in raw.items()
                       if key in scores and r["history"] == history and r["condition"] == c]
            token_lengths[history][c] = dict(n=len(lengths),
                mean=mean(lengths) if lengths else None, median=median(lengths) if lengths else None,
                total=sum(lengths), note="Generated-token counts, including length stops; not GPU time or evidence of overthinking as a cause.")
        transitions[history] = {}
        for feedback in ("TRUE","FALSE"):
            full, guided = "FULL_"+feedback, "GUIDED_"+feedback
            paired = [q for q in m["questions"] if all((q["id"],history,c) in scores for c in (full,guided))]
            recovered, harmed, both_correct, both_wrong = [], [], [], []
            for q in paired:
                f,g = scores[q["id"],history,full],scores[q["id"],history,guided]
                target = both_correct if f["correct"] and g["correct"] else recovered if g["correct"] else harmed if f["correct"] else both_wrong
                target.append(q["id"])
                if f["correct"] != g["correct"]:
                    case = dict(id=q["id"],numbers=q["answer"],history=history,feedback=feedback,
                        change="recovery" if g["correct"] else "harm",source=q["histories"][history],conditions={})
                    for c in (full,guided):
                        line,r = raw[q["id"],history,c]
                        s = scores[q["id"],history,c]
                        case["conditions"][c] = dict(raw_line=line,correct=s["correct"],
                            finish_reason=r["finish_reason"],tokens=r["generated_tokens"],
                            final=r["text"].rsplit("</think>",1)[-1] if "</think>" in r["text"] else None,
                            old_reuse=s.get("structural_reuse"))
                    cases.append(case)
            transitions[history][feedback] = dict(paired_questions=len(paired),recovery=recovered,harm=harmed,
                both_correct=both_correct,both_wrong=both_wrong,
                accuracy_gain=bootstrap([int(scores[q["id"],history,guided]["correct"])-int(scores[q["id"],history,full]["correct"]) for q in paired]) if paired else None)
        source_copy[history] = {}
        for c in CONDITIONS:
            available = [q for q in m["questions"] if (q["id"],history,c) in scores]
            observed,copied = [],[]
            for q in available:
                s = scores[q["id"],history,c]
                if not s.get("parsed"):
                    continue
                expression = q["old_expression"] if history=="BAD" else extract_math_box(q["histories"][history]["draft"])
                observed.append(q["id"])
                if same_tree(expression,s.get("numeric_expression")):
                    copied.append(q["id"])
            source_copy[history][c] = dict(completed=len(available),parsed=len(observed),same_tree_ids=copied,
                note="AST matching to the history final expression; not semantic equivalence, internal reuse or proof of utilization. Unparsed/truncated outputs are missing for this metric.")
    audit = dict(status=state["status"],completed=result["completed"],planned=m["planned_requests"],
        transitions=transitions,source_expression_match=source_copy,generated_token_lengths=token_lengths,
        frozen_cohort_missing_outcome_bounds=bounds,
        case_selection="All observed FULL/GUIDED outcome changes, in frozen question order; no selected winner narrative.",
        limits="Partial pairs are explicitly counted. GOOD availability selected on prior clean success; no same-backend CLEAN baseline. One reused-question exploratory seed; not independent confirmation.")
    save(output/"paired_analysis.json",audit)
    save(output/"outcome_change_cases.json",cases)
    mentions=[]
    qs={q["id"]:q for q in m["questions"]}
    for key,(line,r) in raw.items():
        if key not in scores:
            continue
        thinking=r["text"].split("</think>",1)[0]
        normalized=thinking.translate(str.maketrans({"×":"*","÷":"/","−":"-","–":"-"}))
        legal=[]
        for start,end,expression in expression_spans(normalized):
            checked=audit_expression(expression,qs[r["id"]]["answer"])
            if checked.get("correct"):
                legal.append(dict(start=start,end=end,expression=thinking[start:end],
                    numeric_expression=checked["numeric_expression"],context=thinking[max(0,start-90):end+90]))
        mentions.append(dict(id=r["id"],history=r["history"],condition=r["condition"],raw_line=line,
            final_correct=scores[key]["correct"],finish_reason=r["finish_reason"],
            legal_mentions=legal,first_legal_mention=min(legal,key=lambda x:x["start"]) if legal else None))
    save(output/"expression_mentions.json",dict(records=mentions,
        scope="Completed raw/scored intersection, explicit arithmetic spans in Thinking only; exact value and multiset. Mention does not imply endorsement or new discovery; absence is unobserved. GOOD histories already supply a legal expression. Primary final-answer scores are unchanged."))
    lines = ["# Feedback direction MVP: CPU result snapshot","",f"Status: {state['status']}; completed {result['completed']}/{m['planned_requests']}","",
        "Partial snapshots are for execution review. They are not a decision to stop early or evidence for the hypothesis.","",
        "| History | Condition | Completed/planned | Correct | Length stops | Old wrong AST reuse | Mean new tokens |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for h in ("BAD","GOOD"):
        for c in CONDITIONS:
            v=result["counts"][h][c]
            avg = token_lengths[h][c]["mean"]
            token_display = f"{avg:.0f}" if avg is not None else "NA"
            lines.append(f"| {h} | {c} | {v['completed']}/{v['planned']} | {v['correct']} | {v['length_stops']} | {v['old_reuse']} | {token_display} |")
    lines += ["","Missing GOOD histories: "+", ".join(result["good_missing"]),"",
        "Question-level confidence intervals and per-question four-condition outcomes: summary.json.",
        "All paired recoveries/harms and counts of parsed source-expression matches: paired_analysis.json.",
        "Every observed outcome-change case, with raw line and final answer: outcome_change_cases.json.","",
        "Unfinished requests are listed in completion_audit.json. Frozen-cohort best/worst-case score bounds are in missing_outcome_bounds.json; these are not confidence intervals or population statements.","",
        "Exact legal expressions mentioned in Thinking, with offsets and context: expression_mentions.json. Presence is not endorsement; absence is not failure to search.","",
        "A zero-width empirical bootstrap interval from identical observed differences does not establish population equivalence, especially in a partial snapshot.","",
        "The ID/CFG formula is established prior work. A gain alone does not establish feedback-specific control, neural reset, actual correct-history utilization, a new algorithm or ICLR readiness."]
    (output/"analysis.md").write_text("\n".join(lines)+"\n",encoding="utf8")
    return audit


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"outputs/generation-diagnostics-20261005/feedback_decoding")
    a=p.parse_args()
    r=analyse(a.output)
    print(json.dumps(dict(status=r["status"],completed=r["completed"],planned=r["planned"],transitions=r["transitions"]),ensure_ascii=False))
