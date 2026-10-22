"""CPU evidence extraction from every completed identity trajectory; absence is unknown."""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import load,rows
from run_identity_mvp_20261011 import audit_expression
from selective_context.tasks import extract_math_box


def expression_spans(text):
    # Explicit math regions are retained with their original offsets. Plain arithmetic
    # spans are supplementary; exact validation rejects prose and partial computations.
    patterns=(r"\$\$([\s\S]*?)\$\$",r"(?<!\$)\$([^$\n]+)\$(?!\$)",
              r"\\\(([\s\S]*?)\\\)",r"\\\[([\s\S]*?)\\\]",r"`([^`\n]+)`",
              r"(?<![A-Za-z0-9_])([0-9ABCD(][0-9ABCD \t()+*/.\-]*[0-9ABCD)])(?![A-Za-z0-9_])")
    seen=set()
    for pattern in patterns:
        for match in re.finditer(pattern,text):
            a,b=match.span(1)
            expression=text[a:b].strip().strip(".,;:")
            if "\\boxed" in expression:
                expression=extract_math_box(expression) or expression
            if (a,b) not in seen:
                seen.add((a,b))
                yield a,b,expression


def inspect(text,q,condition,final_score):
    closed="</think>" in text
    thinking=text.split("</think>",1)[0] if closed else text
    legal=[]
    for a,b,expression in expression_spans(thinking):
        audit=audit_expression(expression,q["answer"],q["bindings"] if condition.startswith(("IDENTITY","VALUE")) else None,
                               q.get("binding_counts"),allow_literals=True)
        if audit.get("parsed") and audit["target_correct"] and audit["inventory_correct"]:
            legal.append(dict(start=a,end=b,expression=expression,numeric_expression=audit["numeric_expression"],
                context=thinking[max(0,a-100):min(len(thinking),b+100)],
                verbatim_in_supplied_draft=expression in q.get("draft",""),
                adoption_status="not_inferred_from_mention"))
    hints=[]
    cue=r"(?:reus(?:e|es|ed|ing)|(?:used|uses|using|appears?|occurs?)\s+(?:\w+\s+){0,4}(?:twice|thrice|three times|two times|more than once)|extra\s+(?:number|operand|[0-9]+)|(?:too many|more)\s+(?:occurrences|copies|times)|violat\w*\s+(?:\w+\s+){0,4}(?:once|constraint|number|rule))"
    for match in re.finditer(cue,thinking,re.I):
        a,b=match.span()
        hints.append(dict(start=a,end=b,context=thinking[max(0,a-160):min(len(thinking),b+200)],
                          status="needs_manual_review_of_old_expression_reference_and_negation"))
    return dict(thinking_closed=closed,legal_construct_observed=bool(legal),legal_construct_mentions=legal,
        resource_error_review_candidates=hints,
        old_illegal_final_reused=bool(final_score.get("structural_reuse")) and not final_score.get("correct",False),
        final_correct=bool(final_score.get("correct")),
        interpretation="Exact legal expression presence only; no inference of endorsement, novel discovery, specific error recognition, or absence of internal knowledge. Recognition hints require semantic review.")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"outputs/generation-diagnostics-20261005")
    a=p.parse_args()
    records=[]
    for subdir in ("identity_mvp","identity_alias"):
        m=load(a.output/subdir/"manifest.json")
        qs={q["id"]:q for q in m["questions"]}
        scored={(r["id"],r["condition"]):r for r in rows(a.output/subdir/"behaviour.jsonl")}
        for line,r in enumerate(rows(a.output/subdir/"generations.jsonl"),1):
            key=r["id"],r["condition"]
            records.append(dict(id=r["id"],condition=r["condition"],seed=r["seed"],
                source=str(a.output/subdir/"generations.jsonl"),source_line=line,
                **inspect(r["text"],qs[r["id"]],r["condition"],scored[key])))
    stats={}
    for condition in dict.fromkeys(r["condition"] for r in records):
        rs=[r for r in records if r["condition"]==condition]
        stats[condition]=dict(n=len(rs),legal_construct_observed=sum(r["legal_construct_observed"] for r in rs),
            final_wrong_despite_legal_mention=sum(r["legal_construct_observed"] and not r["final_correct"] for r in rs),
            old_illegal_final_after_legal_mention=sum(r["legal_construct_observed"] and r["old_illegal_final_reused"] for r in rs),
            with_resource_recognition_review_candidates=sum(bool(r["resource_error_review_candidates"]) for r in rs))
    result=dict(n=len(records),conditions=stats,records=records,
        semantic_review_status="candidate extraction complete; specific old-error recognition is not automatically classified",
        denominator="144 existing requests; statements across conditions are descriptive, not independent replicates")
    out=a.output/"identity_trajectory_audit"
    save(out/"audit.json",result)
    lines=["# Existing trajectory audit", "", "Exact expressions mentioned in Thinking; endorsement and recognition are not inferred.", "",
           "| Condition | Requests | Legal expression observed | Final wrong despite mention | Old illegal final after mention |",
           "|---|---:|---:|---:|---:|"]
    for c,s in stats.items():
        lines.append(f"| {c} | {s['n']} | {s['legal_construct_observed']} | {s['final_wrong_despite_legal_mention']} | {s['old_illegal_final_after_legal_mention']} |")
    lines += ["", "No extracted expression means unobserved, not that the model never found a solution.",
              "Resource-error wording is saved for semantic review; it is not counted as confirmed recognition.",
              "Offsets and quotes are in audit.json. All 144 requests are retained."]
    (out/"report.md").write_text("\n".join(lines)+"\n",encoding="utf8")
    print(__import__('json').dumps(dict(n=len(records),conditions=stats),indent=2))


if __name__=="__main__": main()
