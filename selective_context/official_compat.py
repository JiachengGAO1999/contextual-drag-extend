from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .hf_backend import GenerationResult
from .schema import SelectiveContextRequest


def make_official_record(
    *,
    problem_id: str,
    problem: str,
    answer: List[int],
    prompt: str,
    request: SelectiveContextRequest,
    generations: Iterable[GenerationResult],
    model_config_alias: str,
) -> Dict[str, Any]:
    """Mirror official general-inference fields and append intervention metadata."""
    responses = []
    for response_id, generation in enumerate(generations):
        responses.append(
            {
                "response_id": response_id,
                "generated_response": generation.text,
                "finish_reason": generation.finish_reason,
                "selective_context_metadata": generation.metadata,
            }
        )
    return {
        "id": problem_id,
        "problem": problem,
        "answer": answer,
        "init_response_generations": responses,
        "init_response_prompt": prompt,
        "init_response_generations_metadata": {
            "num_responses": len(responses),
            "template_path": None,
            "template_key": None,
            "enable_thinking": False,
            "partition_id": 0,
            "num_partitions": 1,
            "model_config_alias": model_config_alias,
            "intervention": request.to_dict(),
        },
    }


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def evaluate_game24_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Use the official evaluator when installable, with a Python-3.9 smoke fallback.

    Upstream pins math-verify 0.8, which requires Python >=3.10. The fallback is
    intentionally Game24-only and preserves the official boxed-answer/schema
    semantics so local Windows tests need not replace the official environment.
    """
    try:
        from utils.verifiable_evaluation.math_eval.utils.evaluation_utils import evaluate_single_entry
        from utils.verifiable_evaluation.math_eval.utils.verification_utils import is_correct_game_of_24

        return evaluate_single_entry(record, "answer", "init_response_generations", is_correct_game_of_24)
    except ModuleNotFoundError as exc:
        if exc.name != "math_verify":
            raise
        return _evaluate_game24_smoke_fallback(record)


def _evaluate_game24_smoke_fallback(record: Dict[str, Any]) -> Dict[str, Any]:
    import ast
    import re
    from fractions import Fraction

    copied = dict(record)
    evaluated = []
    for response in record.get("init_response_generations", []):
        item = dict(response)
        matches = re.findall(r"\\boxed\{([^{}]+)\}", item.get("generated_response", ""))
        answer = matches[-1].strip() if matches else None
        correct = None
        if answer is not None:
            expression = answer.replace("×", "*").replace("÷", "/").replace(" ", "").split("=")[0]
            numbers = [int(value) for value in re.findall(r"\d+", expression)]
            try:
                value = _eval_arithmetic_ast(ast.parse(expression, mode="eval").body)
                correct = value == 24 and sorted(numbers) == sorted(record["answer"])
            except (SyntaxError, ValueError, ZeroDivisionError):
                correct = None
        item["correctness"] = correct
        item["extracted_answer"] = answer
        evaluated.append(item)
    copied["init_response_generations"] = evaluated
    return copied


def _eval_arithmetic_ast(node: Any):
    import ast
    import operator
    from fractions import Fraction

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_arithmetic_ast(node.operand)
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    if isinstance(node, ast.BinOp) and type(node.op) in operations:
        return operations[type(node.op)](_eval_arithmetic_ast(node.left), _eval_arithmetic_ast(node.right))
    raise ValueError("unsupported arithmetic expression")
