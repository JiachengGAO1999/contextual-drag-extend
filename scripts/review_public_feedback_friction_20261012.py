"""Download optional public artifacts and reconstruct stored history snapshots.

CPU only; no model calls. Content/answer flags are review cues, not automated
judgments of reasoning quality, causal feedback effects, or population rates.
"""

import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import re
import urllib.request

import pyarrow.parquet as pq


BASE = Path("outputs/generation-diagnostics-20261005/public_feedback_friction_preview")
REPO = "https://huggingface.co/datasets/Dongwei/Feedback_Friction_Dataset"
HEADER = re.compile(
    r"Attempt at \(iteration (\d+)\) and the corresponding feedback:\s*\nAnswer:\s*\n"
)
SEPARATOR = "\nYour answer was incorrect.\nHere is the feedback:\n"
BOX = re.compile(r"\\boxed\{([^{}]*)\}")
ENDING = "Please answer the question again."


def parse_history(text):
    markers = list(HEADER.finditer(text))
    turns = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end():end].strip()
        if body.endswith(ENDING):
            body = body[:-len(ENDING)].rstrip()
        parts = body.split(SEPARATOR, 1)
        turns.append({
            "turn": int(marker.group(1)), "response": parts[0].strip(),
            "feedback": parts[1].strip() if len(parts) == 2 else None,
            "stored_verdict": "incorrect" if len(parts) == 2 else None,
        })
    return turns


def octagon_check():
    counts = Counter()
    for blue in range(256):
        valid = any(
            ((((blue << shift) | (blue >> (8 - shift))) & 255) & blue) == 0
            for shift in range(8)
        )
        if valid:
            counts[bin(blue).count("1")] += 1
    probability = Fraction(sum(counts.values()), 256)
    if dict(sorted(counts.items())) != {0: 1, 1: 8, 2: 28, 3: 56, 4: 22}:
        raise AssertionError("Octagon enumeration changed")
    return {
        "algorithm": "Enumerate all 256 blue masks and all 8 cyclic rotations; require disjoint masks",
        "valid_by_blue_count": dict(sorted(counts.items())),
        "total_valid": sum(counts.values()), "probability": str(probability),
        "requested_m_plus_n": probability.numerator + probability.denominator,
        "independent_reason_for_at_most_three": (
            "For k<=3 blue vertices, their difference set has at most "
            "1+k*(k-1)<=7 elements. One of 8 shifts is absent, hence disjoint."
        ),
    }


def run(download=False):
    BASE.mkdir(parents=True, exist_ok=True)
    if download:
        index = json.loads((BASE / "file_index.json").read_text(encoding="utf-8"))
        for item in index["files"]:
            remote = item.get("path", "")
            if not remote.endswith(".parquet"):
                continue
            local = BASE / Path(remote).name
            if local.exists():
                continue
            url = f"{REPO}/resolve/main/{remote}"
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read()
            local.write_bytes(raw)
            print(f"downloaded {local.name}: {len(raw)} bytes", flush=True)

    unique = {}
    conflicts = []
    unaligned = []
    current_records = []
    split_stats = []
    for path in sorted(BASE.glob("*.parquet")):
        split = path.name.split("-00000-")[0]
        rows = pq.read_table(path).to_pylist()
        question_indices = {}
        matched = 0
        for row_index, row in enumerate(rows):
            original_question = (row.get("original_question") or "").strip()
            if not original_question:
                raise ValueError(f"Missing original_question in {path.name} row {row_index}")
            if original_question not in question_indices:
                question_indices[original_question] = len(question_indices) + 1
            local_index = question_indices[original_question]
            source = {"file": str(path), "row": row_index,
                      "snapshot_iteration": row["iteration"]}
            turns = parse_history(row["question"])
            expected_turn = row["iteration"] + 1
            responses = row.get("full_response") or []
            current = responses[0].strip() if len(responses) == 1 else None
            aligned = (current is not None and any(
                t["turn"] == expected_turn and t["response"] == current for t in turns))
            matched += aligned
            if not aligned:
                unaligned.append({"split": split, "id": row["question_id"],
                                  "local_question_index": local_index,
                                  **source, "expected_current_turn": expected_turn,
                                  "parsed_history_turns": [t["turn"] for t in turns],
                                  "current_field_count": len(responses),
                                  "author_is_correct": row["is_correct"],
                                  "reason": "Current response not identical to expected stored history turn"})
            for turn in turns:
                # GPQA and MMLU have empty source question_id fields. Group
                # by actual original question text rather than merging them.
                key = (split, local_index, turn["turn"])
                if key in unique:
                    earlier = unique[key]
                    if (earlier["response"], earlier["feedback"]) != (
                            turn["response"], turn["feedback"]):
                        conflicts.append({"split": split, "id": row["question_id"],
                                          "local_question_index": local_index,
                                          "turn": turn["turn"], "source": source,
                                          "earlier_source": earlier["sources"][0]})
                    earlier["sources"].append(source)
                else:
                    unique[key] = {"split": split, "id": row["question_id"],
                                   "local_question_index": local_index,
                                   "original_question": original_question,
                                   **turn, "sources": [source],
                                   "normalized_answer": row["normalized_answer"]}
            if current is not None:
                boxes = list(BOX.finditer(current))
                last_box = boxes[-1].group(1).strip() if boxes else None
                before_box = current[:boxes[-1].start()] if boxes else current
                gold = str(row["normalized_answer"])
                mention = bool(re.search(r"(?<!\w)" + re.escape(gold) + r"(?!\w)", before_box))
                prior_boxes = [b.group(1).strip() for t in turns
                               if t["turn"] < expected_turn for b in BOX.finditer(t["response"])]
                current_records.append({
                    "split": split, "id": row["question_id"], **source,
                    "local_question_index": local_index,
                    "current_turn_alignment_verified": aligned,
                    "expected_current_turn": expected_turn,
                    "author_is_correct": row["is_correct"],
                    "normalized_answer": gold,
                    "normalized_prediction": row["normalized_prediction"],
                    "last_simple_box": last_box,
                    "gold_mentioned_before_final_box_review_cue_only": mention,
                    "final_box_repeats_prior_box_review_cue_only": bool(
                        last_box is not None and last_box in prior_boxes),
                })
        split_stats.append({
            "split": split, "snapshot_rows": len(rows),
            "unique_questions_by_original_text": len(question_indices),
            "empty_source_question_id_rows": sum(not r.get("question_id") for r in rows),
            "snapshot_iterations": sorted({r["iteration"] for r in rows}),
            "current_response_in_expected_stored_history_turn": matched,
        })

    ordered = [unique[key] for key in sorted(unique)]
    with (BASE / "unique_history_turns.jsonl").open("w", encoding="utf-8") as output:
        for record in ordered:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    (BASE / "current_snapshot_review_cues.json").write_text(
        json.dumps(current_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "public_data_cpu_reconstruction_only_no_model_calls",
        "source": REPO, "model_as_described_by_source": "LLaMA-4 Maverick",
        "splits": split_stats, "unique_history_turns": len(ordered),
        "conflicting_history_records": conflicts,
        "unaligned_current_snapshot_records": unaligned,
        "unaligned_author_correct_count": sum(bool(r["author_is_correct"]) for r in unaligned),
        "limitations": [
            "Source releases late-stage snapshots (iteration>=7), not an unselected benchmark population.",
            "Rows, turns and repeated snapshots are not independent questions.",
            "Some question fields contain the current answer and its later feedback; they are not pre-generation prompts.",
            "Review cues do not prove correct reasoning, faithful computation, or causal copying.",
            "Conflicts and current fields outside parsed history require review, not silent timeline inference.",
            "Data cannot re-estimate the paper's Claude-only error-category table or original Contextual Drag results.",
        ],
    }
    (BASE / "reconstruction_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (BASE / "octagon_verification.json").write_text(
        json.dumps(octagon_check(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Six snapshot responses inspected directly. This is an exploratory review
    # of explicit terminal contradictions, not an automated CoT-validity label.
    aime_path = next(BASE.glob("*aime_2024*.parquet"))
    aime_rows = pq.read_table(aime_path).to_pylist()
    reviewed = []
    for index, question_id, value, box in [
        (6, "2024-II-10", "468", "312"),
        (9, "2024-I-9", "480", "96"),
        (11, "2024-I-5", "104", "106"),
        (13, "2024-I-11", "371", "73"),
        (20, "2024-I-9", "480", "96"),
        (28, "2024-II-10", "468", "312"),
    ]:
        row = aime_rows[index]
        response = row["full_response"][0].strip()
        boxes = list(BOX.finditer(response))
        if (row["question_id"] != question_id or str(row["normalized_answer"]) != value
                or not boxes or boxes[-1].group(1).strip() != box):
            raise ValueError(f"Reviewed snapshot changed: AIME row {index}")
        turn = row["iteration"] + 1
        history = parse_history(row["question"])
        prior = [b.group(1).strip() for t in history if t["turn"] < turn
                 for b in BOX.finditer(t["response"])]
        feedback = next(t["feedback"] for t in history if t["turn"] == turn)
        reviewed.append({
            "file": str(aime_path), "row": index, "id": question_id,
            "snapshot_iteration": row["iteration"], "attempt_number": turn,
            "reviewer": "Codex exploratory text review",
            "finding": "Requested quantity explicitly ends at gold numeral before a contradictory final box",
            "body_terminal_value": value, "final_simple_box": box,
            "final_box_present_in_prior_history": box in prior,
            "response_ending": response[-900:], "subsequent_feedback": feedback,
            "whole_reasoning_chain_verified": False,
            "independent_full_answer_verification": question_id == "2024-I-11",
            "causal_history_or_feedback_effect_established": False,
        })
    (BASE / "reviewed_terminal_contradictions.json").write_text(
        json.dumps({
            "snapshot_witnesses": len(reviewed),
            "unique_questions": len({r["id"] for r in reviewed}),
            "selection": "AIME current responses whose gold numeral occurs before a different final box, followed by direct text inspection",
            "records": reviewed,
            "limitations": "Selected late-stage corpus; neither a population prevalence estimate nor a novel mechanism result",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**summary,
        "conflicting_history_records": len(conflicts),
        "unaligned_current_snapshot_records": len(unaligned)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true",
                        help="Download missing public Parquet shards listed in the saved source index")
    run(parser.parse_args().download)
