"""Freeze a question-balanced failed-draft morphology pilot from existing pools.

This pass is intentionally outcome-blind after pool inclusion: it keeps one
deterministically sampled failed response per question, extracts auditable
surface/structural proxies, and writes a reviewable sample manifest.  It does
not infer causal effects and does not use downstream R0/R2/L_E outcomes.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


POOL_PATHS = [
    "outputs/game24-stage-b-drafts-20260911/draft_candidates.jsonl",
    "outputs/game24-qwen3-8b-thinking-drafts-20260908/draft_candidates.jsonl",
    "outputs/game24-qwen3-reendorsement-drafts-20260914/draft_candidates.jsonl",
]
FIXED_IDS = {"71", "123", "513", "577", "719", "804", "1084", "1189", "1226", "1358"}
SEED = 20270915

REJECTION_PATTERNS = (
    r"\bnot valid\b", r"\binvalid\b", r"\bincorrect\b", r"\bwrong\b",
    r"\bdoes not\b", r"\bdo not\b", r"\bcannot\b", r"\bcan't\b",
    r"\bno valid\b", r"\bnot equal\b", r"\bnot allowed\b",
)
ENDORSEMENT_PATTERNS = (
    r"\bvalid\b", r"\bcorrect\b", r"\bworks\b", r"\bsatisf(?:y|ies)\b",
    r"\bexactly once\b", r"\ball numbers\b", r"\bfinal answer\b",
    r"\btherefore\b", r"\bthis expression\b",
)
UNCERTAINTY_PATTERNS = (
    r"\bmaybe\b", r"\bperhaps\b", r"\bhmm\b", r"\bwait\b",
    r"\blet me\b", r"\bnot sure\b", r"\bthink again\b",
)
REPAIR_PATTERNS = (
    r"\bremaining\b", r"\bleft\b", r"\bincorporat\w*\b", r"\binclude\w*\b",
    r"\bwithout changing\b", r"\buse all\b", r"\badd and subtract\b",
    r"\bsubstitut\w*\b", r"\bcombine\w*\b",
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def count_patterns(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def stance_proxies(text: str) -> dict:
    """Conservative sentence evidence, NOT candidate identity or belief labels."""
    evidence = []
    for line in text.splitlines():
        plain = re.sub(r'[*#]', '', line).strip()
        if not plain or re.search(r'\b(goal|aim|must|need to|we are given|we want|if we)\b', plain, re.I):
            continue
        for sentence in re.split(r'(?<=[.!?])\s+', plain):
            negative = bool(re.search(r'\b(not (?:valid|correct|equal|24)|invalid|incorrect|wrong|violates?|no valid)\b', sentence, re.I))
            cleaned = re.sub(r'\b(?:not|never)\s+(?:a\s+)?(?:valid|correct)\b', '', sentence, flags=re.I)
            positive = bool(re.search(r'\b(?:this expression (?:is valid|is correct|uses|satisfies)|all (?:four )?numbers (?:are )?used (?:exactly )?once|(?:correct|valid)(?: and (?:correct|valid))? (?:final )?(?:expression|answer)|expression that satisfies)\b', cleaned, re.I))
            if negative or positive:
                evidence.append(dict(text=sentence,negative=negative,positive=positive,mixed=negative and positive))
    return dict(rejection_count=sum(x['negative'] for x in evidence),
                endorsement_count=sum(x['positive'] for x in evidence),evidence=evidence)


def extract_boxed(text: str) -> list[str]:
    return re.findall(r"\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", text)


def number_signature(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"(?<![A-Za-z])\d+(?![A-Za-z])", text)]


def features(record: dict, source: str) -> dict:
    generation = record.get("init_response_generations", [{}])[0]
    text = record.get("final_response") or generation.get("generated_response", "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    boxes = extract_boxed(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    line_counts = Counter(lines)
    max_line_repetition = max(line_counts.values(), default=0)
    trace_quality = "normal" if generation.get('finish_reason') == 'eos' and record.get("thinking_status") == "parsable_thinking" and "<think>" not in text.lower() and text else "malformed_or_truncated"
    stance = stance_proxies(text)
    rejection, endorsement = stance['rejection_count'], stance['endorsement_count']
    uncertainty = count_patterns(text, UNCERTAINTY_PATTERNS)
    repair = count_patterns(text, REPAIR_PATTERNS)
    equations = len(re.findall(r"=", text))
    displays = text.count("$$") // 2
    numbered_steps = len(re.findall(r"(?m)^\s*(?:Step\s+\d+|\d+[.)])", text, flags=re.IGNORECASE))
    question_id = str(record["id"])
    answer = record.get("answer", [])
    final_numbers = number_signature(boxes[-1] if boxes else text[-500:])
    answer_counter = Counter(int(x) for x in answer)
    final_counter = Counter(final_numbers)
    extra_final_numbers = sum((final_counter - answer_counter).values())
    missing_final_numbers = sum((answer_counter - final_counter).values())
    # These are proxies for review/stratification only, not semantic labels.
    oscillation = rejection * max(endorsement, 0)
    commitment = (
        2 * len(boxes)
        + min(endorsement, 8)
        + min(equations, 8)
        + min(numbered_steps, 8)
        - min(rejection, 8)
    )
    if trace_quality != "normal":
        bucket = "malformed_or_truncated"
    elif len(text) >= 10000 and (max_line_repetition >= 4 or len(set(lines)) / max(len(lines), 1) < 0.6):
        bucket = "repetitive_or_looping"
    elif oscillation >= 8 and rejection >= 2:
        bucket = "negative_positive_cues_manual_review_required"
    elif repair >= 4 and equations >= 4:
        bucket = "repair_lexical_cues_manual_review_required"
    elif commitment >= 10 and rejection <= 1:
        bucket = "structured_positive_cues_manual_review_required"
    elif uncertainty >= 8 or equations >= 12:
        bucket = "search_or_uncertain"
    else:
        bucket = "mixed_or_other"
    return {
        "source": source,
        "id": question_id,
        "draft_key": record.get("draft_key"),
        "response_id": generation.get("response_id"),
        "correctness": generation.get("correctness"),
        "thinking_status": record.get("thinking_status"),
        "finish_reason": generation.get('finish_reason'),
        "stance_evidence": stance['evidence'],
        "semantic_failure_label": "not_assigned_from_scorer_or_keywords",
        "trace_quality": trace_quality,
        "fixed_ten_overlap": question_id in FIXED_IDS,
        "problem": record.get("problem"),
        "answer": answer,
        "text": text,
        "char_len": len(text),
        "line_count": len(text.splitlines()),
        "unique_line_ratio": round(len(set(lines)) / max(len(lines), 1), 4),
        "max_line_repetition": max_line_repetition,
        "boxed_count": len(boxes),
        "equation_count": equations,
        "display_math_count": displays,
        "numbered_step_count": numbered_steps,
        "rejection_count": rejection,
        "endorsement_count": endorsement,
        "uncertainty_count": uncertainty,
        "repair_count": repair,
        "final_boxed_numbers": final_numbers,
        "final_extra_number_count": extra_final_numbers,
        "final_missing_number_count": missing_final_numbers,
        "oscillation_proxy": oscillation,
        "commitment_proxy": commitment,
        "provisional_bucket": bucket,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-seed", type=int, default=SEED)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    rng = random.Random(args.sample_seed)
    pool: list[dict] = []
    for rel in POOL_PATHS:
        path = root / rel
        for row in read_jsonl(path):
            generation = row.get("init_response_generations", [{}])[0]
            if generation.get("correctness") is True:
                continue
            pool.append(features(row, rel))

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in pool:
        grouped[row["id"]].append(row)
    sampled = []
    for question_id in sorted(grouped, key=int):
        candidates = list(grouped[question_id])
        rng.shuffle(candidates)
        # Keep malformed/truncated outputs visible, but prefer a normal trace
        # when the same question has both kinds of failed response.
        candidates.sort(key=lambda row: row["trace_quality"] != "normal")
        sampled.append(candidates[0])
    sampled.sort(key=lambda row: int(row["id"]))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "morphology_pilot_v2",
        "sample_seed": args.sample_seed,
        "pool_paths": POOL_PATHS,
        "inclusion": "init_response_generations[0].correctness is not True",
        "question_balancing": "one seeded random failed response per unique question id",
        "fixed_ten_overlap_is_flagged_not_excluded": True,
        "pool_record_count": len(pool),
        "unique_question_count": len(sampled),
        "sample": sampled,
    }
    (args.output_dir / "sample_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output_dir / "sample.jsonl").open("w", encoding="utf-8") as handle:
        for row in sampled:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    buckets = Counter(row["provisional_bucket"] for row in sampled)
    qualities = Counter(row["trace_quality"] for row in sampled)
    overlap = sum(row["fixed_ten_overlap"] for row in sampled)
    lines = [
        "# Morphology pilot v2",
        "",
        f"Pool records: {len(pool)} failed/unparsable records from {len(POOL_PATHS)} existing pools.",
        f"Sample: one seeded-random record per question, {len(sampled)} questions; sample seed `{args.sample_seed}`.",
        f"Overlap with current ten-question development set: {overlap} questions; flagged, not silently removed.",
        f"Trace quality: {dict(qualities)}. Malformed/truncated outputs are retained as a separate class and excluded from normal morphology strata.",
        "",
        "## Provisional buckets",
        "",
        "These buckets are deterministic surface proxies for review/stratification, not causal labels.",
        "",
    ]
    for bucket, count in sorted(buckets.items()):
        lines.append(f"- `{bucket}`: {count}")
    lines.extend(["", "## Sample summary", "", "| id | source | fixed overlap | quality | bucket | len | reject | endorse | repair | oscillation | commitment |", "|---:|---|:---:|---|---|---:|---:|---:|---:|---:|---:|"])
    for row in sampled:
        lines.append("| {id} | {source} | {fixed_ten_overlap} | {trace_quality} | {provisional_bucket} | {char_len} | {rejection_count} | {endorsement_count} | {repair_count} | {oscillation_proxy} | {commitment_proxy} |".format(**row))
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "No downstream R0/R2/masked outcome is used in inclusion, feature extraction, or bucket assignment. Manual review is required before causal mask conditions are frozen.",
    ])
    (args.output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"pool_records": len(pool), "sampled_questions": len(sampled), "buckets": dict(buckets), "fixed_overlap": overlap}, ensure_ascii=False))


if __name__ == "__main__":
    main()
