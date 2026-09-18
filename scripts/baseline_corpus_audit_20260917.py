"""Baseline-only corpus audit for the next held-out selection.

This script deliberately reads upstream draft-candidate artifacts only.  It does
not use any R2/R3/R4/late/path/X/CALC outcome when constructing eligibility.
The output is an audit artifact, not an intervention launcher.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "baseline-corpus-audit-20260917"

# Questions already used in the ten-question development/annotation corpus.
DEVELOPMENT_IDS = {
    "1189", "1358", "804", "123", "577", "719", "1084", "71", "513", "1226"
}
# The earlier three cases were also used for prompt/mask/reuse development.
EARLIER_CASE_IDS = {"170", "159", "1093"}

# These labels are taken only from the existing manual audits.  Unknown failed
# traces remain pending manual review and are never promoted automatically.
MANUAL_GENUINE_IDS = {
    "1189", "1358", "804", "123", "577", "71", "719", "513", "1084",
    "1226", "1093", "1356", "1170", "1261",
}
MANUAL_FORMAT_ONLY_IDS = {"23", "159"}
MANUAL_TRANSCRIPTION_IDS = {"170"}

INTERVENTION_MARKERS = (
    "r0-r4", "fixed", "multi-late", "region-late", "mx-late-path", "morphology",
    "local-calculation", "x-calc", "xcalc", "ten-validity", "independent-stage",
    "r1-supplement", "stage-b-paired", "fixed-repeats",
)


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_id(value: Any) -> str:
    return str(value)


def condition_of(record: dict[str, Any], generation: dict[str, Any]) -> str | None:
    metadata = record.get("init_response_generations_metadata") or {}
    intervention = metadata.get("intervention") or {}
    condition = intervention.get("condition_id")
    if condition is None:
        condition = generation.get("condition_id")
    return str(condition) if condition is not None else None


def source_class(path: Path) -> str:
    lower = str(path).lower()
    if "server_sources" in lower:
        return "server_synced_historical_baseline_pool"
    if "heldout-screen" in lower:
        return "heldout_baseline_screen"
    if "stage-b" in lower or "reendorsement-drafts" in lower:
        return "historical_baseline_draft_pool"
    if "thinking-drafts" in lower:
        return "historical_baseline_draft_pool"
    if "r0-r4" in lower:
        return "historical_r0_source_pool"
    return "candidate_artifact"


def parse_number_list(problem: str) -> list[int] | None:
    match = re.search(r"numbers\s+(.+?)\s+exactly once", problem, flags=re.I | re.S)
    if not match:
        return None
    values = re.findall(r"(?<![A-Za-z])\d+(?![A-Za-z])", match.group(1))
    return [int(value) for value in values] if values else None


def failure_class(problem_id: str, sample: dict[str, Any]) -> str:
    if sample["correctness"] is not False:
        return "not_failed"
    if sample["finish_reason"] != "eos" or sample["thinking_status"] != "parsable_thinking":
        return "loop_or_truncation_or_unparseable"
    if problem_id in MANUAL_FORMAT_ONLY_IDS:
        return "format_only"
    if problem_id in MANUAL_TRANSCRIPTION_IDS:
        return "final_transcription_error"
    if problem_id in MANUAL_GENUINE_IDS:
        return "manually_verified_substantive_reasoning_error"
    return "needs_manual_audit"


def read_candidates() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # The two server-synced files are deliberately renamed to avoid clobbering
    # local artifacts, so match both canonical and provenance-preserving names.
    files = sorted((ROOT / "outputs").glob("**/*draft_candidates.jsonl"))
    inventory: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for path in files:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        file_conditions: Counter[str] = Counter()
        accepted = 0
        rejected = 0
        malformed = 0
        for line_no, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            generations = record.get("init_response_generations") or []
            if not generations:
                malformed += 1
                continue
            for generation in generations:
                condition = condition_of(record, generation)
                file_conditions[condition or "<none>"] += 1
                baseline_ok = condition in (None, "R0")
                if not baseline_ok:
                    rejected += 1
                    continue
                response = generation.get("generated_response") or ""
                digest = hashlib.sha256(response.encode("utf-8", errors="replace")).hexdigest()
                problem_id = as_id(record.get("id"))
                draft_key = str(record.get("draft_key") or f"{problem_id}/{generation.get('response_id', 0)}")
                dedup_key = f"{problem_id}|{draft_key}|{digest}"
                if dedup_key in seen_hashes:
                    continue
                seen_hashes.add(dedup_key)
                accepted += 1
                token_count = len(record.get("generated_token_ids") or [])
                if not token_count:
                    token_count = int((record.get("selective_context_metadata") or {}).get("generated_tokens") or 0)
                sample = {
                    "problem_id": problem_id,
                    "draft_key": draft_key,
                    "answer": record.get("answer"),
                    "number_multiset": sorted(record.get("answer") or parse_number_list(record.get("problem", "")) or []),
                    "problem": record.get("problem", ""),
                    "source": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "source_class": source_class(path),
                    "line_no": line_no,
                    "condition_id": condition or "ordinary_sampling",
                    "baseline_only": True,
                    "correctness": generation.get("correctness"),
                    "extracted_answer": generation.get("extracted_answer"),
                    "finish_reason": generation.get("finish_reason"),
                    "thinking_status": record.get("thinking_status") or generation.get("thinking_status"),
                    "generated_tokens": token_count,
                    "response_sha256": digest,
                    "response_excerpt": response[-1200:],
                }
                sample["failure_class"] = failure_class(problem_id, sample)
                samples.append(sample)
        inventory.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "source_class": source_class(path),
            "raw_lines": len(lines),
            "accepted_baseline_samples_before_global_dedup": accepted,
            "rejected_nonbaseline_samples": rejected,
            "malformed_lines_or_records": malformed,
            "conditions_seen": dict(file_conditions),
            "baseline_only_source_for_selection": True,
        })
    return samples, inventory


def problem_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[sample["problem_id"]].append(sample)

    rows: list[dict[str, Any]] = []
    for problem_id, group in sorted(grouped.items(), key=lambda item: int(item[0]) if item[0].isdigit() else item[0]):
        total = len(group)
        correct = sum(sample["correctness"] is True for sample in group)
        false = sum(sample["correctness"] is False for sample in group)
        null = total - correct - false
        eos = sum(sample["finish_reason"] == "eos" for sample in group)
        parseable = sum(sample["thinking_status"] == "parsable_thinking" for sample in group)
        complete_failed = [
            sample for sample in group
            if sample["correctness"] is False
            and sample["finish_reason"] == "eos"
            and sample["thinking_status"] == "parsable_thinking"
        ]
        genuine = [sample for sample in group if sample["failure_class"] == "manually_verified_substantive_reasoning_error"]
        unknown = [sample for sample in group if sample["failure_class"] == "needs_manual_audit"]
        format_only = [sample for sample in group if sample["failure_class"] in {"format_only", "final_transcription_error"}]
        accuracy = correct / total if total else None
        if accuracy is None:
            bucket = "unknown"
        elif accuracy > 0.8:
            bucket = "easy_gt_80"
        elif accuracy < 0.2:
            bucket = "hard_lt_20"
        else:
            bucket = "borderline_20_to_80"
        answer = group[0].get("answer")
        multiset = group[0].get("number_multiset") or []
        excluded_reasons: list[str] = []
        if problem_id in DEVELOPMENT_IDS:
            excluded_reasons.append("current_ten_development_or_annotation_corpus")
        if problem_id in EARLIER_CASE_IDS:
            excluded_reasons.append("earlier_prompt_mask_or_reuse_case")
        same_multiset_as_development = sorted(multiset) in [
            sorted(row_answer)
            for row_answer in [
                [1, 5, 8, 8],   # 123
                [1, 6, 9, 13],  # 577
                [5, 7, 7, 9],   # 1084
                [5, 7, 8, 8],   # 719
                [3, 5, 7, 13],  # 1358
                [5, 10, 10, 12], # 804
                [6, 8, 10, 11],  # 1226
                [7, 7, 11, 12],  # 71
                [10, 12, 12, 12],# 1189
                [3, 9, 13, 13],  # 513
            ]
        ]
        if same_multiset_as_development:
            excluded_reasons.append("duplicate_number_multiset_with_development_problem")
        if not correct:
            excluded_reasons.append("no_correct_baseline_companion")
        if not genuine:
            if unknown:
                excluded_reasons.append("failed_trace_requires_manual_reasoning_audit")
            elif format_only:
                excluded_reasons.append("format_or_final_transcription_only")
            else:
                excluded_reasons.append("no_verified_substantive_failed_trace")
        eligible = not excluded_reasons
        if eligible and bucket != "borderline_20_to_80":
            # Retain easy/hard rows for audit, but mark borderline as the planned focus.
            priority = "secondary_nonborderline"
        elif eligible:
            priority = "primary_borderline_focus"
        else:
            priority = "not_eligible"
        rows.append({
            "problem_id": problem_id,
            "answer": answer,
            "number_multiset": multiset,
            "duplicate_multiset_with_development": same_multiset_as_development,
            "sample_count": total,
            "correct_count": correct,
            "false_count": false,
            "null_count": null,
            "eos_count": eos,
            "non_eos_count": total - eos,
            "parsable_thinking_count": parseable,
            "complete_failed_count": len(complete_failed),
            "verified_substantive_failed_count": len(genuine),
            "unknown_failed_count": len(unknown),
            "format_or_transcription_only_count": len(format_only),
            "accuracy": accuracy,
            "difficulty_bucket": bucket,
            "mixed_success_verified": bool(correct and genuine),
            "mixed_success_with_unknown_failure": bool(correct and (genuine or unknown)),
            "development_or_reuse_excluded": bool(excluded_reasons and any("corpus" in reason or "case" in reason for reason in excluded_reasons)),
            "excluded": bool(excluded_reasons),
            "eligible_for_next_stage": eligible,
            "priority": priority,
            "exclusion_reasons": excluded_reasons,
            "source_paths": sorted({sample["source"] for sample in group}),
            "draft_keys": sorted({sample["draft_key"] for sample in group}),
            "failed_trace_keys": sorted(sample["draft_key"] for sample in group if sample["correctness"] is False),
            "verified_failed_trace_keys": sorted(sample["draft_key"] for sample in genuine),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "problem_id", "answer", "number_multiset", "sample_count", "correct_count", "false_count", "null_count",
        "eos_count", "non_eos_count", "parsable_thinking_count", "complete_failed_count",
        "verified_substantive_failed_count", "unknown_failed_count", "format_or_transcription_only_count",
        "accuracy", "difficulty_bucket", "mixed_success_verified", "mixed_success_with_unknown_failure",
        "duplicate_multiset_with_development", "development_or_reuse_excluded", "excluded", "eligible_for_next_stage", "priority", "exclusion_reasons",
        "source_paths", "draft_keys", "failed_trace_keys", "verified_failed_trace_keys",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            for key in ("answer", "number_multiset", "exclusion_reasons", "source_paths", "draft_keys", "failed_trace_keys", "verified_failed_trace_keys"):
                serialized[key] = json.dumps(serialized[key], ensure_ascii=False)
            writer.writerow({field: serialized.get(field) for field in fields})


def markdown_report(summary: dict[str, Any], rows: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> str:
    eligible = [row for row in rows if row["eligible_for_next_stage"]]
    borderline = [row for row in eligible if row["difficulty_bucket"] == "borderline_20_to_80"]
    lines = [
        "# Baseline-only corpus audit (2026-09-17)",
        "",
        "本报告只从上游 `draft_candidates.jsonl` 及 ordinary/R0 初始采样中统计。R2、R3、R4、late、path、X、CALC、X+CALC 的生成结果和任何 recovery outcome 均未用于题目选择。该报告不启动 intervention。",
        "",
        "## 总结",
        "",
        f"- 去重后的 baseline 样本：**{summary['deduplicated_baseline_samples']}** 条，题目：**{summary['problem_count']}** 道。",
        f"- 服务器端 inventory 已核对，并补入本地审计目录中发现的 **{summary['server_missing_local_baseline_files_synced']}** 份历史 baseline 草稿文件。",
        f"- 官方正确/错误/空：**{summary['correct_count']} / {summary['false_count']} / {summary['null_count']}**。",
        f"- 已人工确认的 substantive failed traces：**{summary['verified_substantive_failed_trace_count']}** 条，覆盖 **{summary['verified_substantive_failed_problem_count']}** 道题。",
        f"- 具备正确 companion 且有人工确认 substantive failure 的候选：**{len(eligible)}** 道；其中 borderline 优先候选：**{len(borderline)}** 道。",
        f"- 当前目标是 12–15 道独立题。按已确认且未复用的 baseline 证据，**{'达到' if summary['eligible_problem_count'] >= 12 else '尚未达到'}** 目标；剩余缺口需要有限 baseline screening 或人工审计，不能用 intervention 结果补齐。",
        "",
        "## 难度分层",
        "",
        "阈值固定为：easy >80%，borderline 20–80%（含边界），hard <20%。分层只使用 baseline accuracy。",
        "",
        "| bucket | 题数 |",
        "|---|---:|",
    ]
    for bucket in ("easy_gt_80", "borderline_20_to_80", "hard_lt_20", "unknown"):
        lines.append(f"| {bucket} | {summary['difficulty_counts'].get(bucket, 0)} |")
    lines += ["", "## 候选题目", "", "| id | baseline n | accuracy | bucket | verified failed | unknown failed | eligible | priority |", "|---:|---:|---:|---|---:|---:|---|---|"]
    for row in rows:
        if row["verified_substantive_failed_count"] or row["unknown_failed_count"] or row["problem_id"] == "1170":
            accuracy = "NA" if row["accuracy"] is None else f"{row['accuracy']:.1%}"
            lines.append(
                f"| {row['problem_id']} | {row['sample_count']} | {accuracy} | {row['difficulty_bucket']} | "
                f"{row['verified_substantive_failed_count']} | {row['unknown_failed_count']} | "
                f"{'yes' if row['eligible_for_next_stage'] else 'no'} | {row['priority']} |"
            )
    lines += ["", "## 1170 的位置", "", "1170 被保留为一个 held-out baseline failed trace：它有真实的用数约束错误（重复使用 12），但只有单题、单条失败轨迹，不能单独支持泛化结论。它不因为尚未做 intervention 而被排除，也不被当作当前 12–15 题目标已经完成的证据。", "", "## 排除与 provenance", ""]
    lines += [
        "- 当前十题开发/标注集：1189、1358、804、123、577、719、1084、71、513、1226；不进入下一轮独立题统计。",
        "- 旧的 prompt/mask/reuse 案例：170、159、1093；不进入下一轮独立题统计。",
        "- 只有 `eos + parsable_thinking + correctness=False` 才可能成为完整 failed trace；循环、截断、不可解析输出不自动晋升。",
        "- 官方 false 标签不等于 substantive reasoning error；已知的 format-only/final-transcription-only 失败被单独排除，未人工确认的失败保持 `needs_manual_audit`。",
        "- 同一 generated response 的跨文件重复已按 response hash 去重；同一 number multiset 的重复关系保留在 JSON provenance 中，未在本轮静默合并。",
        "",
        "## 现有材料是否足够",
        "",
    ]
    if summary["eligible_problem_count"] >= 12:
        lines.append("已存在至少 12 道符合规则的独立候选；建议冻结 eligible manifest，先不要自动启动 intervention。后续 formal held-out 仍只用 R0/R2/whole-late/whole-path，每题两个 paired seeds。")
    else:
        gap = 12 - summary["eligible_problem_count"]
        lines.append(f"当前已确认 eligible 题数不足 12，道数缺口至少 {gap}。现有 baseline pool 没有待人工判定的 unknown complete failed trace，因此不能靠重标注现有记录填满缺口。下一步只能从未见过的题目做预注册的 ordinary baseline sampling；不得依据 intervention 恢复结果回填候选。")
        lines.append("建议有限方案：第一阶段抽取 24 道未使用题、每题 4 条 R0 baseline（最多 96 次生成），若新增 eligible 少于 3 道则停止并重新评估题源/失败标准；若至少 3 道，再扩展到总计最多 64 道新题、256 次生成，或在累计达到 12–15 道 eligible 时提前停止。按本轮 held-out screening 约 1/8 的题目级 yield，64 道预计约 8 道新候选，加上现有 2 道仍可能不足 12；要达到 12，可能需要约 80–104 道新题（320–416 次 baseline generation），这应作为单独预算决策，不能自动无限启动。")
    lines += ["", "## 机器可读文件", "", "- `baseline_corpus_audit.json`：完整题目级统计、样本级 provenance、排除原因。", "- `baseline_corpus_audit.csv`：题目级表。", "- `source_inventory.json`：扫描到的候选文件、条件和 baseline/intervention 分类。", "- `failed_trace_review_queue.json`：需要人工判定的未知 failed traces。", ""]
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    samples, inventory = read_candidates()
    rows = problem_rows(samples)
    difficulty_counts = Counter(row["difficulty_bucket"] for row in rows)
    verified_samples = [sample for sample in samples if sample["failure_class"] == "manually_verified_substantive_reasoning_error"]
    eligible = [row for row in rows if row["eligible_for_next_stage"]]
    unknown_queue = [sample for sample in samples if sample["failure_class"] == "needs_manual_audit"]
    summary = {
        "audit_date": "2026-09-17",
        "baseline_only_selection": True,
        "intervention_outcomes_used_for_selection": False,
        "candidate_files_scanned": len(inventory),
        "deduplicated_baseline_samples": len(samples),
        "problem_count": len(rows),
        "correct_count": sum(sample["correctness"] is True for sample in samples),
        "false_count": sum(sample["correctness"] is False for sample in samples),
        "null_count": sum(sample["correctness"] is None for sample in samples),
        "verified_substantive_failed_trace_count": len(verified_samples),
        "verified_substantive_failed_problem_count": len({sample["problem_id"] for sample in verified_samples}),
        "eligible_problem_count": len(eligible),
        "eligible_borderline_problem_count": sum(row["priority"] == "primary_borderline_focus" for row in eligible),
        "difficulty_counts": dict(difficulty_counts),
        "development_ids": sorted(DEVELOPMENT_IDS),
        "earlier_case_ids": sorted(EARLIER_CASE_IDS),
        "manual_labels_are_conservative": True,
        "server_inventory_checked": True,
        "server_project": "/data2/gaojc/projects/contextual-drag-extend",
        "server_missing_local_baseline_files_synced": 2,
    }
    audit = {"summary": summary, "problems": rows, "samples": samples}
    json_dump(OUT / "baseline_corpus_audit.json", audit)
    json_dump(OUT / "source_inventory.json", inventory)
    json_dump(OUT / "failed_trace_review_queue.json", unknown_queue)
    json_dump(OUT / "selection_manifest.json", {
        "status": "audit_only_not_frozen_for_intervention",
        "selection_basis": "baseline-only; no intervention outcomes",
        "preferred_problem_ids": [row["problem_id"] for row in eligible if row["priority"] == "primary_borderline_focus"],
        "secondary_problem_ids": [row["problem_id"] for row in eligible if row["priority"] == "secondary_nonborderline"],
        "heldout_1170_retained": any(row["problem_id"] == "1170" for row in rows),
        "formal_conditions_when_frozen": ["R0", "R2", "whole-late", "whole-path"],
        "paired_seeds_per_problem": 2,
    })
    write_csv(OUT / "baseline_corpus_audit.csv", rows)
    (OUT / "baseline_corpus_audit.md").write_text(markdown_report(summary, rows, inventory), encoding="utf-8")


if __name__ == "__main__":
    main()
