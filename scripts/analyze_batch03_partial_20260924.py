"""Audit persisted Batch03 Game24 chunks; never treat the interrupted run as complete."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "runs/batch03_interrupted_20260924"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sample_index(record: dict[str, Any]) -> int:
    generation = record["init_response_generations"][0]
    if "response_id" in generation:
        return int(generation["response_id"])
    return int(str(record["draft_key"]).rsplit("/", 1)[1])


def is_valid(record: dict[str, Any]) -> bool:
    generation = record["init_response_generations"][0]
    return generation.get("finish_reason") == "eos" and record.get("thinking_status") == "parsable_thinking"


def record_fields(record: dict[str, Any]) -> dict[str, Any]:
    generation = record["init_response_generations"][0]
    return {
        "model": record["init_response_generations_metadata"].get("model_config_alias"),
        "id": str(record["id"]),
        "draft_key": str(record["draft_key"]),
        "sample_index": sample_index(record),
        "finish_reason": generation.get("finish_reason"),
        "thinking_status": record.get("thinking_status"),
        "correctness": generation.get("correctness"),
        "answer_numbers": record.get("answer"),
        "extracted_answer": generation.get("extracted_answer"),
        "final_response": record.get("final_response"),
        "generated_response": generation.get("generated_response"),
    }


SCALAR_FALSE_EVIDENCE = {
    ("Qwen3_8B_Thinking", "1019", 1):
        "正文未给出有效表达式；其所谓 closest expression (6×4)+(13−5) 算出 32，随后承认答案不满足约束却输出 24。",
    ("Qwen3_8B_Thinking", "1171", 4):
        "正文算式 (8×(11−7))−(4×(8÷4)) 虽得 24，但重复使用输入 8 和 4。",
    ("Qwen3_8B_Thinking", "1171", 8):
        "正文算式 (8×(11−7))−(4÷4) 得 31，且把唯一的 4 使用了两次。",
    ("Qwen3_8B_Thinking", "1171", 10):
        "正文算式 (8×(11−7))−4=28，输入虽各一次但算术结果不是 24。",
    ("Qwen3_8B_Thinking", "1171", 11):
        "正文算式 (8×(11−7))−(4×(8÷4)) 虽得 24，但重复使用输入 8 和 4。",
    ("Qwen3_8B_Thinking", "1171", 15):
        "正文算式 ((11+7)×(8−4))÷(11−8) 得 24，但重复使用输入 11 和 8。",
    ("Qwen3_8B_Thinking", "1019", 11):
        "正文算式 (13−5)×(6÷(4÷(6−4))) 得 24，但重复使用输入 6 和 4。",
}

SCALAR_EVIDENCE_EXPRESSIONS = {
    ("Qwen3_8B_Thinking", "1019", 1): "(6*4)+(13-5)",
    ("Qwen3_8B_Thinking", "1171", 4): "(8*(11-7))-(4*(8/4))",
    ("Qwen3_8B_Thinking", "1171", 8): "(8*(11-7))-(4/4)",
    ("Qwen3_8B_Thinking", "1171", 10): "(8*(11-7))-4",
    ("Qwen3_8B_Thinking", "1171", 11): "(8*(11-7))-(4*(8/4))",
    ("Qwen3_8B_Thinking", "1171", 15): "((11+7)*(8-4))/(11-8)",
    ("Qwen3_8B_Thinking", "1019", 11): "(13-5)*(6/(4/(6-4)))",
}

APPROVED_RESPONSE_EXPRESSIONS = {
    ("Qwen3_8B_Thinking", "445", 13): {
        "expression": "8 \\times (2 + 8 \\div 8)",
        "evidence": "回答将该算式作为 promising approach 展开逐步计算，并在 Final Answer 前明确宣称四个输入各用一次。",
    },
    ("Qwen3_8B_Thinking", "395", 7): {
        "expression": "10 + 7 \\times 2 \\times 1 = 24",
        "evidence": "回答将该等式明确称为 solution，并在分步核算后给出最终答案24。",
    },
    ("Qwen3_8B_Thinking", "395", 12): {
        "expression": "(7 \\times 2) + (10 \\div 1)",
        "evidence": "回答将该等式作为 better approach 展开，计算为14+10=24并作为最终答案。",
    },
}

MIXED_FINAL_ANSWER_ERRORS = {
    ("Qwen3_32B", "381", 5):
        "混合回答按明确标出的 Final Answer 评分。选中式 (8×6×11)÷(11+11) 算术值为24，但实际用数为[6,8,11,11,11]，多用了一个11。正文虽列出 11+11+8−6=24 作为替代式，最终仍把错误选中式标为答案；因此这是实质性用数错误，不是答案提取漏检。",
    ("Qwen3_32B", "381", 10):
        "混合回答按明确标出的 Final Answer 评分。选中式 (11−(8−(11÷11)))×6 算术值为24，但实际用数为[6,8,11,11,11]，多用了一个11。正文先列出合法的 11+11+8−6=24，随后明确选择错误的复杂式作为 Final Answer；因此这是实质性用数错误，不是答案提取漏检。",
}


def _braced_group(text: str, start: int) -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError("expected braced LaTeX group")
    depth = 1
    end = start + 1
    while end < len(text) and depth:
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
        end += 1
    if depth:
        raise ValueError("unclosed LaTeX group")
    return text[start + 1:end - 1], end


def evaluate_expression(expression: str) -> tuple[Fraction, Counter[int]]:
    """Evaluate the narrow arithmetic/LaTeX syntax used by extracted Game24 answers."""
    value = expression.split("=", 1)[0]
    while True:
        match = re.search(r"\\boxed\s*", value)
        if not match:
            break
        boxed, cursor = _braced_group(value, match.end())
        value = value[:match.start()] + f"({boxed})" + value[cursor:]
    while True:
        match = re.search(r"\\(?:d?frac)\s*", value)
        if not match:
            break
        numerator, cursor = _braced_group(value, match.end())
        denominator, cursor = _braced_group(value, cursor)
        value = value[:match.start()] + f"(({numerator})/({denominator}))" + value[cursor:]
    value = value.replace("\\left", "").replace("\\right", "")
    for token, replacement in (("\\times", "*"), ("\\cdot", "*"), ("\\div", "/"), ("×", "*"), ("÷", "/")):
        value = value.replace(token, replacement)
    value = value.replace("{", "(").replace("}", ")").strip()
    if "\\" in value:
        raise ValueError(f"unsupported LaTeX token in {expression!r}")
    tree = ast.parse(value, mode="eval")
    operands: Counter[int] = Counter()

    def visit(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            operands[node.value] += 1
            return Fraction(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = visit(node.operand)
            return result if isinstance(node.op, ast.UAdd) else -result
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError(f"unsupported arithmetic node {type(node).__name__}")

    return visit(tree.body), operands


def valid_response_expressions(response: str, answer_numbers: list[int]) -> list[str]:
    """Find displayed/inline equations in the final response that solve this exact number multiset."""
    pattern = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)|(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
    expected = Counter(int(number) for number in answer_numbers)
    found = []
    for match in pattern.finditer(response or ""):
        expression = next((group for group in match.groups() if group is not None), "").strip()
        try:
            value, operands = evaluate_expression(expression)
        except (SyntaxError, ValueError, ZeroDivisionError):
            continue
        if value == 24 and operands == expected and expression not in found:
            found.append(expression)
    return found


def format_multiset(values: Counter[int]) -> str:
    return ",".join(f"{number}x{values[number]}" for number in sorted(values))


def expression_measurement(expression: str, answer_numbers: list[int]) -> dict[str, Any]:
    expected = Counter(int(number) for number in answer_numbers)
    try:
        value, operands = evaluate_expression(expression)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return {
            "evaluation_status": f"error:{type(exc).__name__}",
            "evaluated_value": "",
            "actual_operand_multiset": "",
            "expected_operand_multiset": format_multiset(expected),
            "arithmetic_is_24": False,
            "operand_multiset_matches": False,
            "exact_game24": False,
        }
    value_text = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    matches = operands == expected
    return {
        "evaluation_status": "ok",
        "evaluated_value": value_text,
        "actual_operand_multiset": format_multiset(operands),
        "expected_operand_multiset": format_multiset(expected),
        "arithmetic_is_24": value == 24,
        "operand_multiset_matches": matches,
        "exact_game24": value == 24 and matches,
    }


def manual_classification(row: dict[str, Any]) -> tuple[str, str, str | None]:
    if not row["valid_for_eligibility"]:
        return "excluded_invalid", "未同时满足完整 EOS 结束与可解析回答条件；不进入错误样本门槛。", None
    response_candidates = valid_response_expressions(row.get("final_response") or "", row["answer_numbers"])
    identity = (row["model"], row["id"], row["sample_index"])
    mixed_final_error = MIXED_FINAL_ANSWER_ERRORS.get(identity)
    approved_response = APPROVED_RESPONSE_EXPRESSIONS.get(identity)
    approved_candidate = (
        approved_response["expression"]
        if approved_response and approved_response["expression"] in response_candidates
        else None
    )
    expression = row.get("extracted_answer") or ""
    if expression.strip() == "24":
        if approved_candidate:
            examples = approved_candidate
            return "format_or_extraction_false_negative", (
                "提取器只返回标量24；人工核对正文中明确提出并认可的答案，程序验证算术值和输入多重集均正确："
                + examples + "。" + approved_response["evidence"]
            ), "24"
        if response_candidates:
            return "uncertain_manual_confirmation", (
                "正文中出现程序可验证的正确算式，但尚无明确证据判断其是否作为答案被提出/认可："
                + "；".join(response_candidates[:2])
            ), None
        reason = SCALAR_FALSE_EVIDENCE.get(identity)
        if reason is None:
            return "uncertain_manual_confirmation", "只提取到标量 24，正文证据未完成核定。", None
        return "substantive_error", reason, None
    try:
        value, operands = evaluate_expression(expression)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return "uncertain_manual_confirmation", f"提取式无法安全求值：{type(exc).__name__}: {exc}", None
    expected = Counter(int(number) for number in row["answer_numbers"])
    got = ",".join(str(number) for number in sorted(operands.elements()))
    wanted = ",".join(str(number) for number in sorted(expected.elements()))
    value_text = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    if value == 24 and operands == expected:
        return "format_or_extraction_false_negative", "提取表达式本身满足 24 与四个输入数字各用一次；评分器误判。", value_text
    if mixed_final_error:
        return "substantive_error", mixed_final_error, value_text
    if response_candidates:
        return "uncertain_manual_confirmation", (
            "提取式错误且正文含合法备选；需核对提取式是否为明确最终选式，不能自动用备选改判正确："
            + "；".join(response_candidates[:2])
        ), value_text
    details = []
    if value != 24:
        details.append(f"提取表达式精确值为 {value_text}，不是 24")
    if operands != expected:
        details.append(f"提取表达式数字为 [{got}]，题目输入为 [{wanted}]，多重集不一致")
    return "substantive_error", "；".join(details), value_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_RUN / "raw")
    parser.add_argument("--inspect-failures", type=int, default=0, help="Print the first N scorer-false cases for format inspection")
    parser.add_argument("--failure-offset", type=int, default=0)
    parser.add_argument("--list-failures", action="store_true", help="Print compact indexed failure rows for manual audit")
    parser.add_argument("--response-tail-chars", type=int, default=1200)
    args = parser.parse_args()
    run_dir, data_dir = args.run_dir, args.data_dir
    manifest = read_json(data_dir / "baseline_manifest_batch03_20260919.json")
    ordered_ids = [str(row["id"]) for row in manifest["candidate_rows"]]
    if len(ordered_ids) != 32 or len(set(ordered_ids)) != 32:
        raise RuntimeError("Frozen manifest must contain 32 unique questions")

    model_chunks = {"Qwen3_8B_Thinking": list(range(8)), "Qwen3_32B": list(range(11))}
    all_records: list[dict[str, Any]] = []
    file_manifest = []
    identity_manifest = []
    chunk_summaries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    observed = Counter()
    identities: set[tuple[str, str, int]] = set()
    source_lines: dict[tuple[str, str, int], tuple[str, int, str]] = {}

    for model, chunks in model_chunks.items():
        for chunk_number in chunks:
            chunk = f"chunk-{chunk_number:02d}"
            base = data_dir / model / chunk
            result_path = base / "draft_candidates.jsonl"
            summary_path = base / "summary.json"
            if not result_path.is_file() or not summary_path.is_file():
                raise FileNotFoundError(f"Missing completed chunk artifacts: {model}/{chunk}")
            summary = read_json(summary_path)
            records = read_jsonl(result_path)
            expected = 64 if model == "Qwen3_8B_Thinking" else 32
            if summary.get("generations") != expected or len(records) != expected:
                raise RuntimeError(f"Unexpected persisted count in {model}/{chunk}: {len(records)}")
            relative_path = result_path.relative_to(data_dir).as_posix()
            digest = sha256(result_path)
            file_manifest.append({"path": relative_path, "records": len(records), "sha256": digest})
            chunk_summaries[model].append({"chunk": chunk, **summary})
            for line_number, record in enumerate(records, start=1):
                fields = record_fields(record)
                if fields["model"] != model:
                    raise RuntimeError(f"Model alias mismatch in {relative_path}:{line_number}")
                identity = (model, fields["id"], fields["sample_index"])
                if identity in identities:
                    raise RuntimeError(f"Duplicate model/question/sample identity: {identity}")
                identities.add(identity)
                observed[model, fields["id"]] += 1
                source_lines[identity] = (relative_path, line_number, digest)
                identity_manifest.append({
                    "model": model,
                    "question_id": fields["id"],
                    "sample_index": fields["sample_index"],
                    "finish_reason": fields["finish_reason"],
                    "thinking_status": fields["thinking_status"],
                    "raw_scorer_correctness": fields["correctness"],
                    "source_path": relative_path,
                    "source_line": line_number,
                    "source_sha256": digest,
                })
                all_records.append(record)

    complete_8b = {qid for qid in ordered_ids if observed["Qwen3_8B_Thinking", qid] == 16}
    complete_32b = {qid for qid in ordered_ids if observed["Qwen3_32B", qid] == 16}
    dual_complete = complete_8b & complete_32b
    partial_only = (complete_8b | complete_32b) - dual_complete
    if len(complete_8b) != 32 or len(complete_32b) != 22 or len(dual_complete) != 22 or len(partial_only) != 10:
        raise RuntimeError(f"Unexpected coverage: 8B={len(complete_8b)}, 32B={len(complete_32b)}, dual={len(dual_complete)}")
    for model in model_chunks:
        for qid in ordered_ids:
            expected = 16 if (model, qid) in observed else 0
            if observed[model, qid] not in (0, 16):
                raise RuntimeError(f"Partial saved sample group: {model}/{qid}={observed[model, qid]}")
            if observed[model, qid] != expected:
                raise RuntimeError(f"Invalid group count: {model}/{qid}={observed[model, qid]}")

    scorer_counts = Counter()
    strict_counts = Counter()
    per_question: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    failure_queue = []
    for record in all_records:
        fields = record_fields(record)
        model, qid = fields["model"], fields["id"]
        correct = fields["correctness"]
        scorer_counts[str(correct)] += 1
        per_question[qid][model]["samples"] += 1
        if not is_valid(record):
            strict_counts["invalid"] += 1
            per_question[qid][model]["invalid"] += 1
        elif correct is True:
            strict_counts["correct"] += 1
            per_question[qid][model]["correct"] += 1
        elif correct is False:
            strict_counts["incorrect_pending_manual_review"] += 1
            per_question[qid][model]["incorrect_pending_manual_review"] += 1
        else:
            strict_counts["invalid"] += 1
            per_question[qid][model]["invalid"] += 1
        if correct is False:
            identity = (model, qid, fields["sample_index"])
            path, line_number, digest = source_lines[identity]
            response_candidates = valid_response_expressions(fields["final_response"] or "", fields["answer_numbers"] or [])
            failure_queue.append(
                {
                    **fields,
                    "valid_exact_expressions_in_response": response_candidates,
                    "valid_for_eligibility": is_valid(record),
                    "source_path": path,
                    "source_line": line_number,
                    "source_sha256": digest,
                    "manual_category": "pending",
                    "manual_reason": "",
                }
            )

    preaudit_eligible = {
        qid
        for qid, by_model in per_question.items()
        if sum(counts["correct"] for counts in by_model.values()) >= 2
        and sum(counts["incorrect_pending_manual_review"] for counts in by_model.values()) >= 2
    }

    audited_failures = []
    review_by_identity = {}
    for row in failure_queue:
        category, reason, value = manual_classification(row)
        reviewed = {**row, "manual_category": category, "manual_reason": reason,
                    "audited_expression_value": value}
        audited_failures.append(reviewed)
        review_by_identity[(row["model"], row["id"], row["sample_index"])] = reviewed
    audited_counts = Counter(row["manual_category"] for row in audited_failures)

    failure_by_identity = {
        (row["model"], row["id"], row["sample_index"]): row
        for row in audited_failures
    }
    expression_verifications = []
    scorer_true_unverified = []

    def add_expression_verification(
        fields: dict[str, Any], expression: str, expression_source: str,
        source_path: str, source_line: int, category: str,
    ) -> dict[str, Any]:
        measurement = expression_measurement(expression, fields["answer_numbers"] or [])
        expression_verifications.append({
            "model": fields["model"], "question_id": fields["id"],
            "sample_index": fields["sample_index"], "raw_scorer_correctness": fields["correctness"],
            "manual_category": category, "expression_source": expression_source,
            "expression": expression, **measurement,
            "answer_numbers": json.dumps(fields["answer_numbers"], ensure_ascii=False),
            "source_path": source_path, "source_line": source_line,
        })
        return measurement

    for record in all_records:
        fields = record_fields(record)
        identity = (fields["model"], fields["id"], fields["sample_index"])
        source_path, source_line, _ = source_lines[identity]
        manual = failure_by_identity.get(identity)
        category = manual["manual_category"] if manual else "not_manually_reviewed"
        expression = (fields["extracted_answer"] or "").strip()
        if expression and expression != "24":
            selected_measurement = add_expression_verification(
                fields, expression, "extracted_answer", source_path, source_line, category
            )
        else:
            selected_measurement = None
            if expression == "24":
                add_expression_verification(
                    fields, expression, "scalar_only_no_formula", source_path, source_line, category
                )

        needs_response_scan = (
            fields["correctness"] is False
            or (fields["correctness"] is True and
                (selected_measurement is None or not selected_measurement["exact_game24"]))
        )
        response_candidates = valid_response_expressions(
            fields["final_response"] or "", fields["answer_numbers"] or []
        ) if needs_response_scan else []
        for candidate in response_candidates:
            add_expression_verification(
                fields, candidate, "full_response_exact_candidate", source_path, source_line, category
            )

        scalar_evidence = SCALAR_EVIDENCE_EXPRESSIONS.get(identity)
        if scalar_evidence:
            evidence_measurement = add_expression_verification(
                fields, scalar_evidence, "manual_scalar_error_evidence",
                source_path, source_line, category,
            )
            if identity[0:2] == ("Qwen3_8B_Thinking", "1019") and identity[2] == 1:
                evidence_is_consistent = evidence_measurement["evaluated_value"] == "32"
            else:
                evidence_is_consistent = not evidence_measurement["exact_game24"]
            if not evidence_is_consistent:
                raise RuntimeError(f"Manual scalar evidence failed arithmetic/operand check: {identity}")

        if is_valid(record) and fields["correctness"] is True:
            verified = bool(selected_measurement and selected_measurement["exact_game24"])
            if not verified:
                verified = any(
                    expression_measurement(candidate, fields["answer_numbers"] or [])["exact_game24"]
                    for candidate in response_candidates
                )
            if not verified:
                scorer_true_unverified.append({
                    "model": fields["model"], "question_id": fields["id"],
                    "sample_index": fields["sample_index"],
                    "extracted_answer": fields["extracted_answer"],
                    "source_path": source_path, "source_line": source_line,
                })

    expression_verifications.sort(key=lambda row: (
        row["model"], int(row["question_id"]), row["sample_index"], row["expression_source"]
    ))

    def counts_for_question(question_id: str, max_sample_index: int | None = None) -> dict[str, Counter]:
        counts = {model: Counter() for model in model_chunks}
        for record in all_records:
            fields = record_fields(record)
            if fields["id"] != question_id:
                continue
            if max_sample_index is not None and fields["sample_index"] >= max_sample_index:
                continue
            if not is_valid(record):
                counts[fields["model"]]["invalid"] += 1
                continue
            correctness = fields["correctness"]
            if correctness is True:
                counts[fields["model"]]["correct"] += 1
            elif correctness is False:
                audit = review_by_identity[(fields["model"], fields["id"], fields["sample_index"])]
                if audit["manual_category"] == "format_or_extraction_false_negative":
                    counts[fields["model"]]["correct"] += 1
                elif audit["manual_category"] == "substantive_error":
                    counts[fields["model"]]["substantive_wrong"] += 1
                else:
                    counts[fields["model"]]["unresolved"] += 1
            else:
                counts[fields["model"]]["unresolved"] += 1
        return counts

    final_coverage = {}
    for cohort, question_ids in (("dual_complete", dual_complete), ("8b_only_partial", partial_only)):
        qualifying = []
        for qid in ordered_ids:
            if qid not in question_ids:
                continue
            model_counts = counts_for_question(qid)
            correct_n = sum(value["correct"] for value in model_counts.values())
            substantive_n = sum(value["substantive_wrong"] for value in model_counts.values())
            if correct_n >= 2 and substantive_n >= 2:
                qualifying.append(qid)
            final_coverage[cohort] = {"candidate_n": len(question_ids), "qualifying_n": len(qualifying),
                                  "qualifying_question_ids": qualifying}

    boundary_rows = []
    for qid in ordered_ids:
        model_counts = counts_for_question(qid)
        correct_samples = []
        substantive_wrong_samples = []
        unresolved_samples = []
        invalid_samples = []
        for record in all_records:
            fields = record_fields(record)
            if fields["id"] != qid:
                continue
            identity = (fields["model"], fields["id"], fields["sample_index"])
            path, line_number, digest = source_lines[identity]
            sample_ref = {
                "model": fields["model"], "sample_index": fields["sample_index"],
                "raw_scorer_correctness": fields["correctness"],
                "extracted_answer": fields["extracted_answer"],
                "source_path": path, "source_line": line_number, "source_sha256": digest,
            }
            if not is_valid(record):
                sample_ref["audit_class"] = "excluded_invalid"
                invalid_samples.append(sample_ref)
            elif fields["correctness"] is True:
                sample_ref["audit_class"] = "raw_scorer_correct"
                correct_samples.append(sample_ref)
            elif fields["correctness"] is False:
                category = review_by_identity[identity]["manual_category"]
                if category == "format_or_extraction_false_negative":
                    sample_ref["audit_class"] = category
                    correct_samples.append(sample_ref)
                elif category == "substantive_error":
                    sample_ref["audit_class"] = category
                    substantive_wrong_samples.append(sample_ref)
                else:
                    sample_ref["audit_class"] = category
                    unresolved_samples.append(sample_ref)
            else:
                sample_ref["audit_class"] = "unscored_unresolved"
                unresolved_samples.append(sample_ref)
        correct_n = sum(counts["correct"] for counts in model_counts.values())
        wrong_n = sum(counts["substantive_wrong"] for counts in model_counts.values())
        correct_gap, wrong_gap = max(0, 2 - correct_n), max(0, 2 - wrong_n)
        if qid in dual_complete:
            cohort = "dual_complete"
        elif qid in partial_only:
            cohort = "8b_only_partial"
        else:
            cohort = "uncovered"
        boundary_rows.append({
            "question_id": qid, "cohort": cohort,
            "pooled_valid_correct_n": correct_n,
            "pooled_confirmed_substantive_wrong_n": wrong_n,
            "counts_by_model": {
                model: {
                    "valid_correct": model_counts[model]["correct"],
                    "confirmed_substantive_wrong": model_counts[model]["substantive_wrong"],
                    "unresolved": model_counts[model]["unresolved"],
                    "invalid": model_counts[model]["invalid"],
                }
                for model in model_chunks
            },
            "unresolved_n": len(unresolved_samples), "invalid_n": len(invalid_samples),
            "qualifies_on_saved_data": correct_n >= 2 and wrong_n >= 2,
            "additional_correct_needed": correct_gap,
            "additional_substantive_errors_needed": wrong_gap,
            "boundary_class": (
                "qualifies" if correct_n >= 2 and wrong_n >= 2
                else "one_error_short" if correct_n >= 2 and wrong_n == 1
                else "one_correct_short" if correct_n == 1 and wrong_n >= 2
                else "other"
            ),
            "correct_sample_identities": correct_samples,
            "substantive_wrong_sample_identities": substantive_wrong_samples,
            "invalid_sample_identities": invalid_samples,
            "unresolved_sample_identities": unresolved_samples,
        })
    near_boundary_rows = [row for row in boundary_rows if row["boundary_class"] != "other"]
    near_boundary_summary = [{
        "question_id": row["question_id"], "cohort": row["cohort"],
        "boundary_class": row["boundary_class"],
        "pooled_valid_correct_n": row["pooled_valid_correct_n"],
        "pooled_confirmed_substantive_wrong_n": row["pooled_confirmed_substantive_wrong_n"],
        "counts_by_model": row["counts_by_model"],
        "substantive_wrong_sample_identities": [
            {key: sample[key] for key in ("model", "sample_index", "extracted_answer", "source_path", "source_line")}
            for sample in row["substantive_wrong_sample_identities"]
        ],
        "extraction_miss_sample_identities": [
            {key: sample[key] for key in ("model", "sample_index", "extracted_answer", "source_path", "source_line")}
            for sample in row["correct_sample_identities"]
            if sample.get("audit_class") == "format_or_extraction_false_negative"
        ],
    } for row in near_boundary_rows]

    prefix_replay = []
    previous_qualified: set[str] = set()
    for k in (4, 8, 12, 16):
        qualified = set()
        q8_standalone = set()
        q32_standalone = set()
        both_standalone = set()
        q8_rescue = set()
        q32_rescue = set()
        question_rows = []
        for qid in ordered_ids:
            if qid not in dual_complete:
                continue
            model_counts = counts_for_question(qid, max_sample_index=k)
            c8, c32 = model_counts["Qwen3_8B_Thinking"], model_counts["Qwen3_32B"]
            e8 = c8["correct"] >= 2 and c8["substantive_wrong"] >= 2
            e32 = c32["correct"] >= 2 and c32["substantive_wrong"] >= 2
            pooled = (c8["correct"] + c32["correct"] >= 2 and
                      c8["substantive_wrong"] + c32["substantive_wrong"] >= 2)
            if e8:
                q8_standalone.add(qid)
            if e32:
                q32_standalone.add(qid)
            if e8 and e32:
                both_standalone.add(qid)
            if pooled:
                qualified.add(qid)
                if not e32:
                    q8_rescue.add(qid)
                if not e8:
                    q32_rescue.add(qid)
            question_rows.append({
                "id": qid,
                "8b_correct": c8["correct"], "8b_substantive_wrong": c8["substantive_wrong"],
                "32b_correct": c32["correct"], "32b_substantive_wrong": c32["substantive_wrong"],
                "pooled_correct": c8["correct"] + c32["correct"],
                "pooled_substantive_wrong": c8["substantive_wrong"] + c32["substantive_wrong"],
                "qualifies_8b_alone": e8, "qualifies_32b_alone": e32, "qualifies_pooled": pooled,
            })
        new_questions = qualified - previous_qualified
        prefix_replay.append({
            "samples_per_model_prefix": k,
            "dual_complete_questions": len(dual_complete),
            "qwen3_8b_alone_qualifying_n": len(q8_standalone),
            "qwen3_8b_alone_qualifying_ids": [qid for qid in ordered_ids if qid in q8_standalone],
            "qwen3_32b_alone_qualifying_n": len(q32_standalone),
            "qwen3_32b_alone_qualifying_ids": [qid for qid in ordered_ids if qid in q32_standalone],
            "both_models_alone_qualifying_n": len(both_standalone),
            "both_models_alone_qualifying_ids": [qid for qid in ordered_ids if qid in both_standalone],
            "pooled_qualifying_n": len(qualified),
            "new_since_previous_prefix_n": len(new_questions),
            "new_since_previous_prefix_ids": [qid for qid in ordered_ids if qid in new_questions],
            "pooled_questions_rescued_by_8b": [qid for qid in ordered_ids if qid in q8_rescue],
            "pooled_questions_rescued_by_32b": [qid for qid in ordered_ids if qid in q32_rescue],
            "qualified_question_ids": [qid for qid in ordered_ids if qid in qualified],
            "per_question": question_rows,
            "timing_note": "Chunk summaries record aggregate duration only; no per-sample timestamps support a prefix-specific GPU-time estimate.",
        })
        previous_qualified = qualified

    gpu_time = {}
    for model, summaries in chunk_summaries.items():
        gpu_time[model] = {
            "chunks": len(summaries),
            "generation_seconds_sum": round(sum(row.get("generation_seconds", 0) for row in summaries), 3),
            "model_load_seconds_sum": round(sum(row.get("load_seconds", 0) for row in summaries), 3),
            "reported_total_seconds_sum": round(sum(row.get("total_seconds", 0) for row in summaries), 3),
            "generated_tokens_sum": sum(row.get("tokens", 0) for row in summaries),
            "tokens_per_second_weighted": round(
                sum(row.get("tokens", 0) for row in summaries) /
                max(1e-9, sum(row.get("generation_seconds", 0) for row in summaries)), 3
            ),
        }

    summary = {
        "run_state": "interrupted",
        "planned_generations": 1024,
        "persisted_generations": len(all_records),
        "persisted_per_model": {model: len(chunks) * (64 if model == "Qwen3_8B_Thinking" else 32) for model, chunks in model_chunks.items()},
        "coverage": {
            "candidate_questions": len(ordered_ids),
            "dual_model_complete_question_ids": [qid for qid in ordered_ids if qid in dual_complete],
            "dual_model_complete_n": len(dual_complete),
            "8b_only_question_ids": [qid for qid in ordered_ids if qid in partial_only],
            "8b_only_n": len(partial_only),
            "32b_only_n": len(complete_32b - complete_8b),
            "no_persisted_32b_question_ids": [qid for qid in ordered_ids if qid not in complete_32b],
        },
        "raw_scorer_correctness_counts": dict(scorer_counts),
        "strict_eos_parseable_counts": dict(strict_counts),
        "prefilter_automatic_threshold_n_correct_ge_2_and_raw_false_ge_2": {
            "dual_complete": sum(qid in preaudit_eligible for qid in dual_complete),
            "partial_only": sum(qid in preaudit_eligible for qid in partial_only),
            "ids": [qid for qid in ordered_ids if qid in preaudit_eligible],
        },
        "manual_error_audit_counts": dict(audited_counts),
        "adjudicated_valid_answer_counts": {
            "raw_scorer_true": scorer_counts["True"],
            "confirmed_extraction_false_negatives": audited_counts["format_or_extraction_false_negative"],
            "total_adjudicated_correct": scorer_counts["True"] + audited_counts["format_or_extraction_false_negative"],
            "formal_correct_gate": "Use original valid official-True responses only; extraction corrections are descriptive and excluded from the failed pool. Independently checked in runs/batch03_next_experiment_20260924/plan.json.",
            "confirmed_substantive_errors": audited_counts["substantive_error"],
            "invalid_false_rows_excluded": audited_counts["excluded_invalid"],
            "uncertain_rows": audited_counts["uncertain_manual_confirmation"],
            "correctness_policy": "A response counts correct if the extracted/designated final expression is exact Game24, or if the final answer is only a scalar/format extraction miss and the body clearly supplies an endorsed exact Game24 expression. When an explicit final expression is wrong, an earlier valid alternative does not rescue the response; it is a mixed substantive error.",
        },
        "question_381_mixed_answer_rule": {
            "primary_policy": "Score the explicitly designated Final Answer. A valid earlier alternative does not override an explicit, selected final expression that misuses inputs.",
            "sample_5_final_expression": expression_measurement(
                "(8*6*11)/(11+11)", [6, 8, 11, 11]
            ),
            "sample_10_final_expression": expression_measurement(
                "(11-(8-(11/11)))*6", [6, 8, 11, 11]
            ),
            "body_alternative": expression_measurement("11+11+8-6", [6, 8, 11, 11]),
            "sensitivity_if_any_explicitly_endorsed_valid_alternative_counts": {
                "question_381_qualifies": False,
                "dual_complete_qualifying_n": max(0, final_coverage["dual_complete"]["qualifying_n"] - 1),
                "batch02_plus_batch03_count_if_batch02_has_8": max(0, final_coverage["dual_complete"]["qualifying_n"] - 1) + 8,
                "shortfall_to_target_floor_20": max(0, 20 - (max(0, final_coverage["dual_complete"]["qualifying_n"] - 1) + 8)),
            },
        },
        "manual_eligibility_after_review": final_coverage,
        "arithmetic_and_operand_validation": {
            "expression_rows_checked": len(expression_verifications),
            "exact_game24_rows": sum(bool(row["exact_game24"]) for row in expression_verifications),
            "scorer_true_unverified_rows": scorer_true_unverified,
            "all_valid_scorer_true_have_verified_equation": not scorer_true_unverified,
            "verification_file": "expression_verification.csv",
        },
        "eligibility_boundary_audit": {
            "all_question_rows": len(boundary_rows),
            "near_boundary_rows": len(near_boundary_rows),
            "file": "eligibility_boundary_audit.json",
        },
        "prefix_replay": prefix_replay,
        "summed_chunk_timing_from_persisted_summaries_only": gpu_time,
        "chunk_summary_records": chunk_summaries,
        "source_files": file_manifest,
        "question_counts": {
            qid: {model: dict(per_question[qid][model]) for model in model_chunks}
            for qid in ordered_ids
        },
        "note": "The interrupted Qwen3_32B/chunk-11 has no result records and is excluded. No result is inferred from the incomplete batch.",
    }
    (run_dir / "partial_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    model_order = {model: index for index, model in enumerate(model_chunks)}
    question_order = {question_id: index for index, question_id in enumerate(ordered_ids)}
    identity_manifest.sort(key=lambda row: (
        model_order[row["model"]], question_order[row["question_id"]], row["sample_index"]
    ))
    partial_manifest = {
        "files": file_manifest,
        "record_count": len(identity_manifest),
        "unique_identity_count": len(identities),
        "duplicate_identity_count": len(identity_manifest) - len(identities),
        "coverage": {
            "candidate_question_count": len(ordered_ids),
            "dual_model_complete_question_count": len(dual_complete),
            "8b_only_question_count": len(partial_only),
            "saved_generation_count_by_model": {
                model: sum(1 for row in identity_manifest if row["model"] == model)
                for model in model_chunks
            },
        },
        "identities": identity_manifest,
        "identity_check": "Every persisted record has one unique (model, question_id, sample_index); duplicate identities fail analysis.",
    }
    (run_dir / "partial_results_manifest.json").write_text(json.dumps(partial_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "failure_review_queue.json").write_text(json.dumps(audited_failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "prefix_yield_analysis.json").write_text(json.dumps(prefix_replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_fields = ["model", "id", "draft_key", "sample_index", "valid_for_eligibility", "manual_category",
                    "manual_reason", "answer_numbers", "extracted_answer", "audited_expression_value",
                    "source_path", "source_line", "source_sha256"]
    with (run_dir / "error_review.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        for row in audited_failures:
            csv_row = {field: row.get(field) for field in audit_fields}
            csv_row["answer_numbers"] = json.dumps(row["answer_numbers"], ensure_ascii=False)
            writer.writerow(csv_row)
    verification_fields = [
        "model", "question_id", "sample_index", "raw_scorer_correctness", "manual_category",
        "expression_source", "expression", "evaluation_status", "evaluated_value",
        "actual_operand_multiset", "expected_operand_multiset", "arithmetic_is_24",
        "operand_multiset_matches", "exact_game24", "answer_numbers", "source_path", "source_line",
    ]
    with (run_dir / "expression_verification.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=verification_fields)
        writer.writeheader()
        for row in expression_verifications:
            writer.writerow({field: row.get(field) for field in verification_fields})
    boundary_payload = {
        "rule": "At least two complete, parseable correct answers and at least two manually confirmed substantive errors, pooled across available anchors.",
        "cohorts": {
            "dual_complete": [row for row in boundary_rows if row["cohort"] == "dual_complete"],
            "8b_only_partial": [row for row in boundary_rows if row["cohort"] == "8b_only_partial"],
        },
        "near_boundary": near_boundary_rows,
    }
    (run_dir / "eligibility_boundary_audit.json").write_text(
        json.dumps(boundary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    boundary_fields = [
        "question_id", "cohort", "pooled_valid_correct_n", "pooled_confirmed_substantive_wrong_n",
        "unresolved_n", "invalid_n", "qualifies_on_saved_data", "additional_correct_needed",
        "additional_substantive_errors_needed", "boundary_class", "counts_by_model",
        "correct_sample_identities", "substantive_wrong_sample_identities",
        "invalid_sample_identities", "unresolved_sample_identities",
    ]
    with (run_dir / "eligibility_boundary_audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=boundary_fields)
        writer.writeheader()
        for row in boundary_rows:
            csv_row = dict(row)
            csv_row["counts_by_model"] = json.dumps(row["counts_by_model"], ensure_ascii=False)
            for field in boundary_fields[11:]:
                if field in csv_row:
                    csv_row[field] = json.dumps(csv_row[field], ensure_ascii=False)
            writer.writerow({field: csv_row.get(field) for field in boundary_fields})
    extraction_rows = [row for row in audited_failures
                       if row["manual_category"] == "format_or_extraction_false_negative"]
    extraction_fields = [
        "model", "id", "sample_index", "answer_numbers", "extracted_answer",
        "audited_expression_value", "valid_exact_expressions_in_response", "manual_reason",
        "source_path", "source_line", "source_sha256",
    ]
    with (run_dir / "extraction_miss_audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=extraction_fields)
        writer.writeheader()
        for row in extraction_rows:
            csv_row = {field: row.get(field) for field in extraction_fields}
            csv_row["answer_numbers"] = json.dumps(row["answer_numbers"], ensure_ascii=False)
            csv_row["valid_exact_expressions_in_response"] = json.dumps(
                row["valid_exact_expressions_in_response"], ensure_ascii=False
            )
            writer.writerow(csv_row)
    print(json.dumps({
        "persisted_generations": len(all_records),
        "raw_scorer_correctness_counts": dict(scorer_counts),
        "strict_eos_parseable_counts": dict(strict_counts),
        "dual_complete_n": len(dual_complete),
        "partial_only_n": len(partial_only),
        "automatic_threshold_dual": summary["prefilter_automatic_threshold_n_correct_ge_2_and_raw_false_ge_2"]["dual_complete"],
        "automatic_threshold_partial": summary["prefilter_automatic_threshold_n_correct_ge_2_and_raw_false_ge_2"]["partial_only"],
        "failure_review_rows": len(failure_queue),
        "manual_error_audit_counts": dict(audited_counts),
        "adjudicated_valid_answer_counts": summary["adjudicated_valid_answer_counts"],
        "question_381_mixed_answer_rule": summary["question_381_mixed_answer_rule"],
        "manual_eligibility_after_review": final_coverage,
        "arithmetic_and_operand_validation": summary["arithmetic_and_operand_validation"],
        "near_boundary_questions": near_boundary_summary,
        "prefix_replay_summary": [
            {key: row[key] for key in ("samples_per_model_prefix", "qwen3_8b_alone_qualifying_n",
                                       "qwen3_8b_alone_qualifying_ids", "qwen3_32b_alone_qualifying_n",
                                       "qwen3_32b_alone_qualifying_ids", "both_models_alone_qualifying_n",
                                       "both_models_alone_qualifying_ids",
                                       "pooled_qualifying_n", "new_since_previous_prefix_n",
                                       "new_since_previous_prefix_ids", "pooled_questions_rescued_by_8b",
                                       "pooled_questions_rescued_by_32b")}
            for row in prefix_replay
        ],
        "gpu_time": gpu_time,
    }, ensure_ascii=False, indent=2))
    if args.inspect_failures:
        for row in failure_queue[args.failure_offset : args.failure_offset + args.inspect_failures]:
            print("\n--- FAILURE CASE ---")
            compact = {key: row.get(key) for key in (
                "model", "id", "draft_key", "sample_index", "valid_for_eligibility",
                "finish_reason", "thinking_status", "answer_numbers", "extracted_answer",
                "source_path", "source_line",
            )}
            final = row.get("final_response") or ""
            compact["final_response_chars"] = len(final)
            compact["final_response_tail"] = final[-args.response_tail_chars:]
            print(json.dumps(compact, ensure_ascii=True, indent=2))
    if args.list_failures:
        for index, row in enumerate(failure_queue):
            print(json.dumps({
                "index": index,
                "model": row["model"],
                "id": row["id"],
                "sample_index": row["sample_index"],
                "valid": row["valid_for_eligibility"],
                "answer": row["extracted_answer"],
            }, ensure_ascii=False))


if __name__ == "__main__":
    main()
