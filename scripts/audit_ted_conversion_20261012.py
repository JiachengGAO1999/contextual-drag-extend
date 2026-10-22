"""CPU reproduction of original TED formula conversion on known raw formulas.

This checks the converter, not the scientific novelty of contextual drag. It
never changes original caches, generation records, scores, or model environments.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs/generation-diagnostics-20261005/original_cache_audit/parser_runtime"))
from run_identity_mvp_20261011 import audit_expression


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf8").splitlines() if s.strip()]


def original_converter():
    spec = importlib.util.spec_from_file_location("original_ted_utils", ROOT / "analysis/TED/utils.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = ROOT / "analysis/TED/sample_preprocessing.py"
    function = next(n for n in ast.parse(source.read_text(encoding="utf8")).body
        if isinstance(n, ast.FunctionDef) and n.name == "parse_extracted_answer")
    # Original _parse_expr only validates/converts arithmetic AST here. Its return
    # value is unused; the same supported expression node types are checked below.
    def validate(expression):
        root = ast.parse(expression, mode="eval").body
        def walk(node):
            if isinstance(node, ast.BinOp):
                walk(node.left)
                walk(node.right)
            elif isinstance(node, ast.UnaryOp):
                walk(node.operand)
            elif not isinstance(node, (ast.Constant, ast.Name)):
                raise ValueError("Unsupported AST node")
        walk(root)
        return root
    namespace = dict(re=module.re, contains_textual_latex=module.contains_textual_latex,
        normalize_latex_to_infix=module.normalize_latex_to_infix, _parse_expr=validate)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["parse_extracted_answer"]


def inspect(expression, numbers, convert):
    before = audit_expression(expression, numbers, allow_literals=True)
    converted = convert(expression)
    after = audit_expression(converted, numbers, allow_literals=True) if converted is not None else dict(parsed=False)
    # Production answer auditing rejects a lone numeral as a solution expression.
    # A converter can nevertheless emit one: retain its exact value and one-leaf
    # inventory for this representation audit, without changing production scores.
    if converted is not None and not after.get("parsed"):
        try:
            node = ast.parse(converted, mode="eval").body
            sign = 1
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                sign, node = -1, node.operand
            if isinstance(node, ast.Constant) and type(node.value) is int:
                used, required = Counter([node.value]), Counter(numbers)
                value = sign * node.value
                after = dict(parsed=True, correct=value==24 and used==required,
                    value=str(value), target_correct=value==24, inventory_correct=used==required,
                    used=dict(used), excess=dict(used-required), missing=dict(required-used),
                    numeric_expression=converted, literal_only_converter_output=True)
        except (SyntaxError, ValueError):
            pass
    parsed = before.get("parsed") and after.get("parsed")
    return dict(raw_expression=expression, converted_expression=converted, numbers=numbers,
        before=before, after=after, both_parsed=bool(parsed),
        value_changed=bool(parsed and before["value"] != after["value"]),
        inventory_changed=bool(parsed and before["used"] != after["used"]),
        legality_changed=bool(parsed and before["correct"] != after["correct"]),
        ordered_ast_changed=bool(parsed and ast.dump(ast.parse(before["numeric_expression"], mode="eval").body)
            != ast.dump(ast.parse(after["numeric_expression"], mode="eval").body)))


def main():
    import sympy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/generation-diagnostics-20261005")
    args = parser.parse_args()
    convert = original_converter()
    source = args.output / "candidate_adoption"
    manifest = load(source / "manifest.json")
    qs = {q["id"]:q for q in manifest["questions"]}
    records = [dict(id=q["id"], source="manifest.json", condition="SOURCE_DRAFT",
        **inspect(q["old_expression"], q["answer"], convert)) for q in qs.values()]
    for line, r in enumerate(rows(source / "behaviour.jsonl"), 1):
        if r["phase"] != "NATURAL" or not r["condition"].startswith("COUNT"):
            continue
        expression = r.get("extracted_answer")
        if expression is None:
            continue
        records.append(dict(id=r["id"], seed=r["seed"], condition=r["condition"], source="behaviour.jsonl",
            source_line=line, **inspect(expression, qs[r["id"]]["answer"], convert)))
    stats = {}
    for condition in dict.fromkeys(r["condition"] for r in records):
        rs = [r for r in records if r["condition"] == condition]
        stats[condition] = dict(n=len(rs), raw_parsed=sum(r["before"].get("parsed",False) for r in rs),
            conversion_retained=sum(r["converted_expression"] is not None for r in rs),
            both_parsed=sum(r["both_parsed"] for r in rs),
            value_changed=sum(r["value_changed"] for r in rs), inventory_changed=sum(r["inventory_changed"] for r in rs),
            legality_changed=sum(r["legality_changed"] for r in rs), ordered_ast_changed=sum(r["ordered_ast_changed"] for r in rs))
    minimal = [inspect(e, [1,1,2,12] if "12" in e else [1,1,3,6], convert)
        for e in (r"\frac{12}{1-\frac{1}{2}}", r"\frac{6}{\frac{1}{1+3}}")]
    result = dict(scope="CPU converter audit on existing raw formulas; not a re-estimate of the original paper. Conversion exclusions and transformed formula defects are not model mistakes.",
        environment=dict(python=sys.version, sympy=sympy.__version__, antlr_runtime="4.11.1 isolated output dependency"),
        original_source_files=["analysis/TED/utils.py", "analysis/TED/sample_preprocessing.py"],
        original_validation="parse_extracted_answer function loaded from its AST; unused zss tree conversion replaced with the same arithmetic AST node validation",
        conditions=stats, minimal_reproductions=minimal, records=records)
    out = args.output / "original_cache_audit/conversion_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",encoding="utf8")
    print(json.dumps(dict(conditions=stats, minimal_reproductions=minimal, environment=result["environment"]),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    import argparse
    main()
