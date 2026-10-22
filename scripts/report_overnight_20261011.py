"""CPU-only paired summary of overnight falsification and operand-identity MVP."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_generation_diagnostics_20261005 import save
from run_dependency_revision_20261011 import bootstrap, load, rows
from run_identity_mvp_20261011 import audit_expression, analyse as analyse_identity


def natural_summary(output):
    out = output / "dependency_natural"
    m = load(out / "manifest.json")
    records = rows(out / "behaviour.jsonl")
    keyed = {(r["id"], r["wiring"], r["condition"]): r for r in records}
    phases = ("CLEAN", "CORRECT_ROOT")
    fields = ("correct", "parsed", "root_correct", "dependent_correct", "independent_preserved",
              "dependent_stale", "root_correct_dependent_stale_independent_correct")
    stats = {}
    for phase in phases:
        rs = [r for r in records if r["condition"] == phase]
        stats[phase] = dict(n=len(rs), **{f: sum(bool(r.get(f)) for r in rs) for f in fields},
                           length_stops=sum(r["finish_reason"] == "length" for r in rs))
    complete = [q for q in m["questions"] if all((q["id"], v["wiring"], c) in keyed for v in q["variants"] for c in phases)]
    effects = {}
    for field in ("correct", "dependent_correct", "independent_preserved"):
        effects[field] = bootstrap([sum(int(keyed[q["id"], v["wiring"], "CORRECT_ROOT"].get(field, False))
                                       - int(keyed[q["id"], v["wiring"], "CLEAN"].get(field, False))
                                       for v in q["variants"]) / 2 for q in complete])
    return dict(conditions=stats, complete_base_groups=len(complete), paired_effects=effects,
                unresolved_fields_count_as_not_correct=True,
                interpretation="Same naturally generated answer supplies root and both terminals; exact external root correction is provided, not spontaneously discovered.")


def alias_input_groups(output, summary):
    """Predeclared input-based strata; never select on observed treatment effects."""
    manifest = load(output / "identity_alias/manifest.json")
    results = {q["id"]: q["results"] for q in summary["by_question"]}
    conditions = ("VALUE_CLEAN", "VALUE_HISTORY", "IDENTITY_CLEAN", "IDENTITY_HISTORY")
    groups = {}
    for name, duplicate in (("duplicate_input_values", True), ("all_distinct_input_values", False)):
        questions = [q for q in manifest["questions"] if (len(set(q["answer"])) < 4) == duplicate]
        complete = [results[q["id"]] for q in questions if all(c in results[q["id"]] for c in conditions)]
        simple = {h: bootstrap([int(r["IDENTITY_"+h]["correct"]) - int(r["VALUE_"+h]["correct"])
                                for r in complete]) for h in ("CLEAN", "HISTORY")}
        interaction = bootstrap([int(r["IDENTITY_HISTORY"]["correct"]) - int(r["VALUE_HISTORY"]["correct"])
                                 - int(r["IDENTITY_CLEAN"]["correct"]) + int(r["VALUE_CLEAN"]["correct"])
                                 for r in complete])
        groups[name] = dict(planned_questions=len(questions), complete_questions=len(complete),
            correct={c: sum(bool(r[c]["correct"]) for r in complete) for c in conditions},
            occurrence_minus_value=simple, history_interaction=interaction,
            note="Predeclared descriptive stratum; same reused questions, not independent confirmation. Distinct-value prompts coincide.")
    return groups


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT/"outputs/generation-diagnostics-20261005")
    a = p.parse_args()
    out = a.output / "overnight_20261011"
    natural = natural_summary(a.output)
    source_path = a.output / "cross_question/manifest.json"
    source = load(source_path)
    audit = []
    for q in source["questions"]:
        r = dict(id=q["id"], numbers=q["answer"], old_expression=q["old_expression"],
                 **audit_expression(q["old_expression"], q["answer"]))
        r["error_type"] = ("unparsed" if not r["parsed"] else "inventory_only" if r["target_correct"] and not r["inventory_correct"]
                           else "value_only" if not r["target_correct"] and r["inventory_correct"]
                           else "both" if not r["target_correct"] else "correct")
        audit.append(r)
    audit_result = dict(source=str(source_path), n=len(audit), counts=dict(Counter(r["error_type"] for r in audit)), rows=audit)
    save(out / "old_expression_audit.json", audit_result)
    identity = None
    if (a.output / "identity_mvp/manifest.json").exists():
        state = load(a.output / "identity_mvp/run_state.json") if (a.output / "identity_mvp/run_state.json").exists() else dict(status="prepared_not_launched")
        identity = (analyse_identity(load(a.output / "identity_mvp/manifest.json"), a.output / "identity_mvp", state["status"], state.get("error"))
                    if state["status"] in ("completed", "failed", "budget_exhausted", "prepared_not_launched")
                    else load(a.output / "identity_mvp/summary.json"))
    result = dict(natural=natural, original_error_types=audit_result["counts"], identity_mvp=identity)
    alias = None
    if (a.output / "identity_alias/manifest.json").exists():
        alias_state = load(a.output / "identity_alias/run_state.json") if (a.output / "identity_alias/run_state.json").exists() else dict(status="prepared_not_launched")
        alias = (analyse_identity(load(a.output / "identity_alias/manifest.json"), a.output / "identity_alias", alias_state["status"], alias_state.get("error"))
                 if alias_state["status"] in ("completed", "failed", "budget_exhausted", "prepared_not_launched")
                 else load(a.output / "identity_alias/summary.json"))
        result["identity_alias"] = alias
        result["alias_input_groups"] = alias_input_groups(a.output, alias)
        save(out / "alias_input_groups.json", result["alias_input_groups"])
    save(out / "summary.json", result)
    lines = ["# Overnight evidence and MVP", "", "This is an exploratory report, not an ICLR-level novelty or mechanism claim.", "",
             "## Natural dependency revision", "", "| Condition | Completed / 64 | All six correct | Root correct | Dependent correct | Independent preserved | Joint root-correct / dependent-stale / independent-preserved | Length stops |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, s in natural["conditions"].items():
        lines.append(f"| {c} | {s['n']} | {s['correct']} | {s['root_correct']} | {s['dependent_correct']} | {s['independent_preserved']} | {s['root_correct_dependent_stale_independent_correct']} | {s['length_stops']} |")
    lines += ["", f"Complete paired base groups: {natural['complete_base_groups']}. Effects (CORRECT_ROOT minus CLEAN):", "", "```json", json.dumps(natural["paired_effects"], indent=2), "```", "",
              "Do not use the earlier short numeric scores as evidence of natural revision failure if actual generated worksheets update normally.", "",
              "If all observed paired differences are zero, the empirical bootstrap interval degenerates to [0,0]. This describes this sample, not a guarantee of a zero population effect or absence of rare failures.", "",
              "## Original failed-expression error types", "", json.dumps(audit_result["counts"]), "",
              "Correct arithmetic with illegal operand reuse is not the same failure as propagating a wrong intermediate arithmetic value."]
    if identity:
        lines += ["", "## Resource-identity MVP", "", f"Status: {identity['status']}; {identity['completed']}/96; complete four-condition questions: {identity['complete_questions']}.", "",
                  "| Condition | Completed / 24 | Correct | Inventory correct | Value 24 | Final AST reuse | Length stops |", "|---|---:|---:|---:|---:|---:|---:|"]
        for c, s in identity["conditions"].items():
            lines.append(f"| {c} | {s['n']} | {s['correct']} | {s['inventory_correct']} | {s['target_correct']} | {s['structural_reuse']} | {s['length_stops']} |")
        lines += ["", "History-specific accuracy interaction (paired question bootstrap):", "", "```json", json.dumps(identity["history_specific_interaction"], indent=2), "```", "",
                  "Simple identity-minus-numeric effects:", "", "```json", json.dumps(identity["simple_effects"], indent=2), "```", "",
                  "All four conditions are rerun on the same backend and cap. Truncation and format failures remain in denominators. Inputs, output encoding and tokenization differ by representation. A gain alone does not establish a neural binding mechanism; a general clean gain is not specific to failed history. These 24 reused items and one fresh seed are not independent external validation."]
    if alias:
        lines += ["", "## Predeclared value-alias distinction", "",
                  f"Status: {alias['status']}; {alias['completed']}/48. Existing occurrence-identity responses are reused as references.", "",
                  "| Value-alias condition | Completed / 24 | Correct | Inventory correct | Value 24 | Final AST reuse | Length stops |", "|---|---:|---:|---:|---:|---:|---:|"]
        for c,s in alias["conditions"].items():
            lines.append(f"| {c} | {s['n']} | {s['correct']} | {s['inventory_correct']} | {s['target_correct']} | {s['structural_reuse']} | {s['length_stops']} |")
        lines += ["", "Occurrence-minus-value-alias simple effects:", "", "```json", json.dumps(alias["simple_effects"],indent=2), "```", "",
                  "History-specific interaction:", "", "```json", json.dumps(alias["history_specific_interaction"],indent=2), "```", "",
                  "Both representations use symbolic outputs and retain the original numeric failed history. Four distinct input values yield identical prompts. A similar benefit from value aliases weakens the occurrence-specific explanation; do not relabel generic surface change as a discovered neural binding mechanism. This is a conditional exploratory comparison on the same items, not independent confirmation."]
        lines += ["", "Predeclared input-value strata (descriptive; all completed four-condition pairs):", "",
                  "```json", json.dumps(result["alias_input_groups"],indent=2), "```"]
    (out / "report.md").write_text("\n".join(lines)+"\n", encoding="utf8")
    print(json.dumps(dict(natural=natural["conditions"], original_error_types=audit_result["counts"],
                         identity_status=identity["status"] if identity else None,
                         identity_completed=identity["completed"] if identity else None), indent=2))


if __name__ == "__main__":
    main()
