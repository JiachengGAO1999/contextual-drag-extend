from __future__ import annotations

import ast
import argparse
import csv
import json
import operator
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


NUMBER = r"-?(?:\d+(?:\.\d+)?|\d+/\d+)"
STEP_PATTERN = re.compile(
    rf"(?P<left>{NUMBER})\s*(?P<op>[+\-*/×÷])\s*(?P<right>{NUMBER})\s*=\s*(?P<result>{NUMBER})"
)


@dataclass
class ExecutableStep:
    index: int
    left: str
    operator: str
    right: str
    reported_result: str
    valid_arithmetic: bool
    consumes: List[Optional[int]]
    character_span: Tuple[int, int]
    token_span: Optional[Tuple[int, int]] = None


@dataclass
class TraceAudit:
    trace_id: str
    stepwise_parseable: bool
    first_invalid_operation: Optional[int]
    dependency_buildable: bool
    descendants: Dict[int, List[int]]
    token_span_alignable: bool
    expression_ast_parseable: bool
    error_categories: List[str] = field(default_factory=list)
    steps: List[ExecutableStep] = field(default_factory=list)
    manual_correct: Optional[bool] = None


def parse_stepwise_trace(
    trace_id: str,
    text: str,
    initial_numbers: Sequence[int],
    offsets: Optional[Sequence[Tuple[int, int]]] = None,
) -> TraceAudit:
    matches = list(STEP_PATTERN.finditer(text))
    errors: List[str] = []
    if not matches:
        errors.append("no_stepwise_operations")
    available: List[Tuple[Fraction, Optional[int]]] = [(Fraction(value), None) for value in initial_numbers]
    steps: List[ExecutableStep] = []
    dependencies: Dict[int, List[int]] = {}
    dependency_buildable = bool(matches)
    token_alignable = offsets is not None and bool(matches)
    first_invalid: Optional[int] = None

    for index, match in enumerate(matches):
        left, right, reported = (_fraction(match.group(name)) for name in ("left", "right", "result"))
        op = match.group("op").replace("×", "*").replace("÷", "/")
        consumed_indices = _consume_operands(available, left, right, op)
        if consumed_indices is None:
            dependency_buildable = False
            consumes: List[Optional[int]] = []
            errors.append(f"step_{index}_operands_unavailable")
        else:
            consumes = [available[position][1] for position in consumed_indices]
            for position in sorted(consumed_indices, reverse=True):
                available.pop(position)
        computed = _apply(left, op, right)
        valid = computed is not None and computed == reported and consumed_indices is not None
        if not valid and first_invalid is None:
            first_invalid = index
        if consumed_indices is not None:
            available.append((reported, index))
        token_span = None
        if offsets is not None:
            try:
                token_span = _align_span(offsets, match.span())
            except ValueError:
                token_alignable = False
                errors.append(f"step_{index}_token_alignment")
        dependencies[index] = [source for source in consumes if source is not None]
        steps.append(
            ExecutableStep(index, match.group("left"), op, match.group("right"), match.group("result"), valid, consumes, match.span(), token_span)
        )

    descendants = {index: _descendants(index, dependencies) for index in dependencies}
    expression_ast_parseable = parse_expression_ast(text)
    return TraceAudit(
        trace_id=trace_id,
        stepwise_parseable=bool(matches),
        first_invalid_operation=first_invalid,
        dependency_buildable=dependency_buildable,
        descendants=descendants,
        token_span_alignable=token_alignable,
        expression_ast_parseable=expression_ast_parseable,
        error_categories=sorted(set(errors)),
        steps=steps,
    )


def parse_expression_ast(text: str) -> bool:
    candidates = re.findall(r"[\d\s()+\-*/×÷.]+(?:=\s*24)?", text)
    for candidate in sorted(candidates, key=len, reverse=True):
        expression = candidate.replace("×", "*").replace("÷", "/").split("=")[0].strip()
        if not expression or not any(symbol in expression for symbol in "+-*/"):
            continue
        try:
            tree = ast.parse(expression, mode="eval")
            if _safe_eval(tree.body) == Fraction(24):
                return True
        except (SyntaxError, ValueError, ZeroDivisionError):
            continue
    return False


def summarize_audits(audits: Sequence[TraceAudit]) -> Dict[str, object]:
    count = len(audits)
    if count == 0:
        raise ValueError("cannot summarize an empty audit")
    reviewed = [audit for audit in audits if audit.manual_correct is not None]
    manual_error_rate = (
        sum(not audit.manual_correct for audit in reviewed) / len(reviewed) if reviewed else None
    )
    coverage = sum(audit.stepwise_parseable for audit in audits) / count
    use_stepwise = coverage >= 0.80 and manual_error_rate is not None and manual_error_rate <= 0.05
    categories = Counter(category for audit in audits for category in audit.error_categories)
    return {
        "n": count,
        "stepwise_coverage": coverage,
        "first_invalid_determinable_rate": sum(audit.first_invalid_operation is not None for audit in audits) / count,
        "dependency_coverage": sum(audit.dependency_buildable for audit in audits) / count,
        "token_alignment_coverage": sum(audit.token_span_alignable for audit in audits) / count,
        "expression_ast_coverage": sum(audit.expression_ast_parseable for audit in audits) / count,
        "manual_review_n": len(reviewed),
        "manual_error_rate": manual_error_rate,
        "phase2_unit": "stepwise" if use_stepwise else "expression_subtree_or_operator_path",
        "error_categories": dict(categories),
        "llm_judge_used": False,
    }


def write_audit_outputs(output_root: Path, audits: Sequence[TraceAudit]) -> None:
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with output_root.with_suffix(".json").open("w", encoding="utf-8") as handle:
        json.dump({"summary": summarize_audits(audits), "records": [asdict(audit) for audit in audits]}, handle, indent=2)
    with output_root.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trace_id", "stepwise_parseable", "first_invalid_operation", "dependency_buildable", "token_span_alignable", "expression_ast_parseable", "error_categories", "manual_correct"])
        writer.writeheader()
        for audit in audits:
            row = asdict(audit)
            row["error_categories"] = "|".join(audit.error_categories)
            writer.writerow({key: row[key] for key in writer.fieldnames})


def _fraction(value: str) -> Fraction:
    return Fraction(value)


def _apply(left: Fraction, op: str, right: Fraction) -> Optional[Fraction]:
    functions = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
    if op == "/" and right == 0:
        return None
    return functions[op](left, right)


def _consume_operands(available: Sequence[Tuple[Fraction, Optional[int]]], left: Fraction, right: Fraction, op: str) -> Optional[Tuple[int, int]]:
    for left_index, (left_value, _) in enumerate(available):
        if left_value != left:
            continue
        for right_index, (right_value, _) in enumerate(available):
            if right_index != left_index and right_value == right:
                return left_index, right_index
    return None


def _descendants(source: int, dependencies: Dict[int, List[int]]) -> List[int]:
    found = set()
    frontier = [source]
    while frontier:
        current = frontier.pop()
        for target, parents in dependencies.items():
            if current in parents and target not in found:
                found.add(target)
                frontier.append(target)
    return sorted(found)


def _align_span(offsets: Sequence[Tuple[int, int]], span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    tokens = [index for index, (left, right) in enumerate(offsets) if right > start and left < end]
    if not tokens or offsets[tokens[0]][0] != start or offsets[tokens[-1]][1] != end:
        raise ValueError("span does not align exactly")
    return tokens[0], tokens[-1] + 1


def _safe_eval(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        return _apply(left, {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(node.op)], right)  # type: ignore[return-value]
    raise ValueError("unsupported expression")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit failed Game24 traces without an LLM judge.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL containing failed traces")
    parser.add_argument("--output-root", type=Path, required=True, help="Writes .json and manual-review .csv")
    parser.add_argument("--trace-column", default="traj1")
    parser.add_argument("--numbers-column", default="answer")
    parser.add_argument("--id-column", default="id")
    parser.add_argument("--tokenizer", default=None, help="Optional local tokenizer path for executable-unit alignment")
    args = parser.parse_args()
    tokenizer = None
    if args.tokenizer:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, use_fast=True)
    audits = []
    with args.input.open("r", encoding="utf-8") as handle:
        for row_index, line in enumerate(handle):
            if not line.strip():
                continue
            row = json.loads(line)
            trace = row[args.trace_column]
            trace_offsets = None
            if tokenizer is not None:
                trace_offsets = tokenizer(trace, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
            audits.append(parse_stepwise_trace(str(row.get(args.id_column, row_index)), trace, row[args.numbers_column], trace_offsets))
    write_audit_outputs(args.output_root, audits)


if __name__ == "__main__":
    main()
