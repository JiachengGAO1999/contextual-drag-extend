import json

from selective_context.parseability import parse_expression_ast, parse_stepwise_trace, summarize_audits, write_audit_outputs


def offsets(text):
    return [(index, index + 1) for index in range(len(text))]


def test_valid_stepwise_dependencies_and_descendants():
    text = "6 - 2 = 4\n3 + 3 = 6\n4 * 6 = 24\nboxed: (6-2)*(3+3)=24"
    audit = parse_stepwise_trace("valid", text, [6, 2, 3, 3], offsets(text))
    assert audit.stepwise_parseable
    assert audit.first_invalid_operation is None
    assert audit.dependency_buildable
    assert audit.descendants[0] == [2]
    assert audit.descendants[1] == [2]
    assert audit.token_span_alignable
    assert audit.expression_ast_parseable


def test_first_invalid_operation_is_programmatic():
    text = "6 - 2 = 5\n5 * 3 = 15"
    audit = parse_stepwise_trace("bad", text, [6, 2, 3, 3], offsets(text))
    assert audit.first_invalid_operation == 0


def test_summary_rule_and_manual_table(tmp_path):
    text = "6 - 2 = 4\n3 + 3 = 6\n4 * 6 = 24"
    audits = [parse_stepwise_trace(str(i), text, [6, 2, 3, 3], offsets(text)) for i in range(5)]
    for audit in audits:
        audit.manual_correct = True
    summary = summarize_audits(audits)
    assert summary["phase2_unit"] == "stepwise"
    assert summary["llm_judge_used"] is False
    root = tmp_path / "audit"
    write_audit_outputs(root, audits)
    assert root.with_suffix(".json").exists()
    assert root.with_suffix(".csv").exists()
    assert json.loads(root.with_suffix(".json").read_text())["summary"]["n"] == 5


def test_fallback_without_manual_validation():
    audit = parse_stepwise_trace("none", "natural language only", [1, 2, 3, 4])
    assert summarize_audits([audit])["phase2_unit"] == "expression_subtree_or_operator_path"


def test_expression_parser_is_restricted_and_exact():
    assert parse_expression_ast("(6-2)*(3+3)=24")
    assert not parse_expression_ast("__import__('os').system('x')")
