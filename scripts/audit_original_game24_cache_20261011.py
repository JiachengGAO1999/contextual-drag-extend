"""CPU audit of converted local TED caches; not a census of raw model failures.

Required inventories are inferred only when all exact-valid, metadata-correct
clean responses agree. Cache selection excludes missing/unparseable responses;
these numbers are not full-benchmark performance estimates. The TED converter is
potentially lossy, so cache-derived inventories and defects are provisional proxies.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_identity_mvp_20261011 import audit_expression


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def exact(expression):
    return audit_expression(expression, [], allow_literals=True)


def inventory_key(audit):
    return tuple(sorted((int(n), count) for n, count in audit["used"].items()))


def defect(expression, numbers):
    a = audit_expression(expression, numbers, allow_literals=True)
    if not a.get("parsed"):
        kind = "unparsed"
    elif a["target_correct"] and a["inventory_correct"]:
        kind = "legal"
    elif a["target_correct"]:
        kind = "inventory_only"
    elif a["inventory_correct"]:
        kind = "value_only"
    else:
        kind = "both"
    return kind, a


def tree_key(expression):
    try:
        return ast.dump(ast.parse(expression, mode="eval").body)
    except (SyntaxError, ValueError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "analysis/TED/cache/direct")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005/original_cache_audit")
    args = parser.parse_args()
    caches = {p.stem: load(p) for p in sorted(args.cache.glob("*.json"))}
    candidates = defaultdict(set)
    evidence = defaultdict(list)
    for model, data in caches.items():
        for qid, anchors in data.items():
            for anchor, entries in anchors.items():
                for expression, metadata in entries.get("init_response", []):
                    if metadata.get("correctness") is not True:
                        continue
                    a = exact(expression)
                    if a.get("parsed") and a["target_correct"] and sum(a["used"].values()) == 4:
                        inv = inventory_key(a)
                        candidates[qid].add(inv)
                        e = dict(model=model, expression=expression)
                        if e not in evidence[qid]:
                            evidence[qid].append(e)
    inventories = {qid: [n for n, count in next(iter(values)) for _ in range(count)]
        for qid, values in candidates.items() if len(values) == 1}
    all_qids = {qid for data in caches.values() for qid in data}
    source_records, response_records, models = [], [], {}
    for model, data in caches.items():
        src_counts, subset_counts = Counter(), defaultdict(Counter)
        source_total = 0
        for qid, anchors in data.items():
            for anchor, entries in anchors.items():
                source_total += 1
                try:
                    sources = ast.literal_eval(anchor)
                except (SyntaxError, ValueError):
                    src_counts["unreadable_anchor"] += 1
                    continue
                if qid not in inventories or len(sources) != 1 or sources[0] is None:
                    src_counts["inventory_or_source_unknown"] += 1
                    continue
                numbers = inventories[qid]
                old = sources[0]
                kind, a = defect(old, numbers)
                src_counts[kind] += 1
                source_records.append(dict(model=model, id=qid, anchor=anchor, expression=old,
                    inferred_numbers=numbers, defect=kind, audit=a,
                    source_cache=str(args.cache / (model + ".json"))))
                old_tree = tree_key(old)
                for index, (expression, metadata) in enumerate(entries.get("anchored_responses", [])):
                    response_kind, response_audit = defect(expression, numbers)
                    verdict = metadata.get("verdict")
                    group = "incorrect_verdict" if verdict is False else "correct_verdict" if verdict is True else "missing_verdict"
                    counts = subset_counts[group]
                    counts["n"] += 1
                    counts["metadata_correct"] += metadata.get("correctness") is True
                    counts["exact_audit_legal"] += response_kind == "legal"
                    counts["same_tree"] += old_tree is not None and tree_key(expression) == old_tree
                    counts["same_inventory_defect"] += bool(response_audit.get("parsed") and a.get("parsed")
                        and not a["inventory_correct"] and not response_audit["inventory_correct"]
                        and response_audit["used"] == a["used"])
                    counts["metadata_audit_disagreement"] += ((metadata.get("correctness") is True) != (response_kind == "legal"))
                    response_records.append(dict(model=model, id=qid, anchor=anchor, response_index=index,
                        expression=expression, verdict=verdict, metadata_correctness=metadata.get("correctness"),
                        defect=response_kind, same_tree=old_tree is not None and tree_key(expression) == old_tree,
                        audit=response_audit))
        models[model] = dict(questions=len(data), source_anchors=source_total,
            source_defects=dict(src_counts), anchored_subsets={k:dict(v) for k,v in subset_counts.items()})
    summary = dict(models=models, inventory_questions=len(inventories), cache_questions=len(all_qids),
        conflicting_inventory_questions={qid:list(values) for qid,values in candidates.items() if len(values)>1},
        unknown_inventory_questions=sorted(all_qids-inventories.keys()),
        scope="CONVERTED CACHE ONLY, not raw model failures. Inventories are provisional proxies inferred from agreeing exact-valid metadata-correct converted Direct formulas. The original TED normalization can alter formulas, so source_defects must not be reported as raw draft error types. Verdict is global metadata, not a verified diagnostic critique. No causal comparisons of verdict-selected subsets.",
        representation_stage="After original TED parse_extracted_answer/normalize_latex_to_infix; original boxed formula and critique are absent.",
        critiques_available=False, source_records=len(source_records), response_records=len(response_records))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("summary.json", summary), ("inventories.json", dict(numbers=inventories,evidence=dict(evidence))),
                        ("source_audits.json", source_records), ("response_audits.json", response_records)):
        (args.output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n",encoding="utf8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
