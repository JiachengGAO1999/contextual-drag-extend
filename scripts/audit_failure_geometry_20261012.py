"""CPU audit of grounded and goal-extendable subexpressions in saved failed drafts."""
from __future__ import annotations

import ast
import json
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from run_identity_mvp_20261011 import audit_expression
from run_information_followup_20261005 import tree

ROOT = Path(__file__).resolve().parents[1]


def canonical(values):
    return tuple(sorted(values))


@lru_cache(maxsize=None)
def completion(values):
    """Exact reachability using every supplied operand once; no additional literals."""
    if len(values) == 1:
        return values[0] == 24
    for i, a in enumerate(values):
        for j in range(i + 1, len(values)):
            b = values[j]
            rest = [x for k, x in enumerate(values) if k not in (i, j)]
            candidates = [a+b, a-b, b-a, a*b]
            if b:
                candidates.append(a/b)
            if a:
                candidates.append(b/a)
            for v in dict.fromkeys(candidates):
                if completion(canonical(rest + [v])):
                    return True
    return False


def analyse(q):
    node = tree(q["old_expression"])
    if node is None:
        return dict(id=q["id"], parsed=False)
    required = Counter(q["answer"])
    subtrees = []

    def visit(n, path):
        if not isinstance(n, (ast.BinOp, ast.UnaryOp)):
            return
        text = ast.unparse(n)
        audited = audit_expression(text, q["answer"])
        grounded = audited["parsed"] and not audited.get("excess")
        remaining = (required - Counter({int(k): v for k, v in audited.get("used", {}).items()})) if grounded else None
        reachable = bool(completion(canonical([Fraction(audited["value"])] +
                    [Fraction(x) for x in remaining.elements()]))) if grounded else None
        subtrees.append(dict(path=path, expression=text, proper=path!="root",
            parsed=audited["parsed"], value=audited.get("value"),
            grounded=bool(grounded), remaining=dict(remaining) if grounded else None,
            goal_extendable=reachable, excess=audited.get("excess")))
        if isinstance(n, ast.BinOp):
            visit(n.left, path+".L")
            visit(n.right, path+".R")
        else:
            visit(n.operand, path+".U")

    visit(node, "root")
    proper = [x for x in subtrees if x["proper"]]
    grounded = [x for x in proper if x["grounded"]]
    return dict(id=q["id"], numbers=q["answer"], old_expression=q["old_expression"], parsed=True,
        input_solvable=completion(canonical(map(Fraction,q["answer"]))),
        proper_internal_subexpressions=len(proper), grounded_proper=len(grounded),
        extendable_grounded_proper=sum(x["goal_extendable"] for x in grounded),
        grounded_dead_ends=sum(not x["goal_extendable"] for x in grounded),
        subexpressions=subtrees)


def main():
    source=ROOT/"outputs/generation-diagnostics-20261005/candidate_adoption/manifest.json"
    output=ROOT/"outputs/generation-diagnostics-20261005/error_profile_preview/failure_geometry.json"
    m=json.loads(source.read_text(encoding="utf8"))
    records=[analyse(q) for q in m["questions"]]
    summary=dict(questions=len(records), parsed=sum(r["parsed"] for r in records),
        grounded_proper=sum(r.get("grounded_proper",0) for r in records),
        extendable_grounded_proper=sum(r.get("extendable_grounded_proper",0) for r in records),
        grounded_dead_ends=sum(r.get("grounded_dead_ends",0) for r in records),
        questions_with_extendable_subexpression=[r["id"] for r in records if r.get("extendable_grounded_proper",0)],
        questions_with_grounded_dead_end=[r["id"] for r in records if r.get("grounded_dead_ends",0)])
    result=dict(source=str(source),scope="All existing 30 selected natural failed final expressions. CPU exact arithmetic; not model behavior, causal evidence, or a new selection list.",
        definition="Grounded: source occurrences do not exceed supplied inventory. Extendable: after consuming exactly those source occurrences, the subtree value and every remaining original operand can reach 24 using the four permitted binary arithmetic operations. Computed on original AST, without TED conversion.",
        limits="Counts refer to nested arithmetic subexpressions, not independent observations or explicitly emitted reasoning steps. Local arithmetic truth is automatic for a defined expression; it is not a judgment that the draft reasoning is correct. Existence of a completion is not evidence that the model can find it. This is a known planning concept, not by itself a novelty claim.",
        summary=summary,records=records)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
