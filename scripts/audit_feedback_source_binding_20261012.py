"""CPU review cues for reference-only phrases in public feedback.

Exact lexical overlap locates evidence windows; it does not classify attribution,
feedback correctness, or a causal reference effect. No model or network calls.
"""

from collections import defaultdict
import json
from pathlib import Path
import re

import pyarrow.parquet as pq


BASE = Path("outputs/generation-diagnostics-20261005/public_feedback_friction_preview")
TOKEN = re.compile(r"[a-z]+|\d+|[=<>]", re.I)


def spans(text):
    return [(m.group().lower(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def grams(tokens, size=4):
    words = [t[0] for t in tokens]
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def run():
    references = {}
    coverage = []
    for path in sorted(BASE.glob("*.parquet")):
        split = path.name.split("-00000-")[0]
        all_questions = set()
        covered = set()
        for index, row in enumerate(pq.read_table(path).to_pylist()):
            question = row["original_question"].strip()
            all_questions.add(question)
            reference = row.get("solution") or row.get("cot_content") or ""
            if not reference.strip():
                continue
            covered.add(question)
            references.setdefault((split, question), {
                "reference": reference, "file": str(path), "row": index,
            })
        coverage.append({"split": split, "questions": len(all_questions),
                         "questions_with_reference_text": len(covered)})

    histories = defaultdict(list)
    for line in (BASE / "unique_history_turns.jsonl").read_text(encoding="utf8").splitlines():
        record = json.loads(line)
        histories[(record["split"], record["original_question"])].append(record)
    candidates = []
    analyzed_turns = 0
    for key, reference in references.items():
        ref_tokens = spans(reference["reference"])
        ref_grams = grams(ref_tokens)
        ref_positions = defaultdict(set)
        for i in range(len(ref_tokens) - 3):
            ref_positions[tuple(t[0] for t in ref_tokens[i:i + 4])].add(i)
        question_grams = grams(spans(key[1]))
        previous_response_grams = set()
        previous_feedback_grams = set()
        for record in sorted(histories[key], key=lambda r: r["turn"]):
            current_response_grams = grams(spans(record["response"]))
            feedback = record["feedback"] or ""
            feedback_tokens = spans(feedback)
            feedback_words = [t[0] for t in feedback_tokens]
            analyzed_turns += 1
            eligible = ref_grams - question_grams - current_response_grams - previous_response_grams
            starts = [i for i in range(len(feedback_tokens) - 3)
                      if tuple(feedback_words[i:i + 4]) in eligible]
            # Merge consecutive matching four-grams into one review window.
            groups = []
            for start in starts:
                offsets = {p - start for p in ref_positions[tuple(feedback_words[start:start + 4])]}
                if (groups and start == groups[-1]["starts"][-1] + 1
                        and offsets & groups[-1]["offsets"]):
                    groups[-1]["starts"].append(start)
                    groups[-1]["offsets"].intersection_update(offsets)
                else:
                    groups.append({"starts": [start], "offsets": offsets})
            windows = []
            for group in groups:
                first, last = group["starts"][0], group["starts"][-1] + 3
                phrase = feedback[feedback_tokens[first][1]:feedback_tokens[last][2]]
                if len(phrase) < 18:
                    continue
                token_phrase = tuple(feedback_words[first:last + 1])
                location = first + min(group["offsets"])
                ref_start = ref_tokens[location][1]
                ref_end = ref_tokens[location + len(token_phrase) - 1][2]
                windows.append({
                    "phrase": phrase,
                    "feedback_context": feedback[max(0, feedback_tokens[first][1] - 180):
                                                 feedback_tokens[last][2] + 220],
                    "reference_context": reference["reference"][max(0, ref_start - 100):ref_end + 160],
                    "four_gram_already_in_previous_feedback": any(
                        tuple(feedback_words[i:i + 4]) in previous_feedback_grams for i in group["starts"]),
                    "token_count": len(token_phrase),
                })
            if windows:
                candidates.append({
                    "split": record["split"], "id": record["id"],
                    "local_question_index": record["local_question_index"],
                    "turn": record["turn"], "history_sources": record["sources"],
                    "reference_source": {k: v for k, v in reference.items() if k != "reference"},
                    "windows": sorted(windows, key=lambda w: -w["token_count"]),
                    "label": "reference_overlap_absent_from_question_and_current_or_earlier_responses_review_cue_only",
                })
            previous_response_grams.update(current_response_grams)
            previous_feedback_grams.update(grams(feedback_tokens))
    result = {
        "status": "cpu_lexical_triage_not_semantic_labels",
        "coverage": coverage, "analyzed_reference_available_history_turns": analyzed_turns,
        "candidate_turns": len(candidates),
        "candidate_questions": len({(c["split"], c["local_question_index"]) for c in candidates}),
        "first_turn_candidate_questions": len({(c["split"], c["local_question_index"])
                                                for c in candidates if c["turn"] == 1}),
        "candidates": candidates,
        "limitations": [
            "Reference text is released only for the 12 selected AIME questions.",
            "Reference-only overlap may be legitimate guidance rather than attribution to the solver.",
            "No model counterfactual, prevalence estimate, or causal source identification.",
            "Later turns can inherit earlier feedback; a shared phrase does not identify the unique source.",
        ],
    }
    (BASE / "source_binding_review_cues.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    # Directly inspected witnesses, kept separate from lexical candidates.
    # The first-turn octagon witness cannot have inherited earlier feedback.
    reviewed_specs = [
        ("2024-I-11", 1, "axes of symmetry",
         "Critique discusses a symmetry-axis argument and b<=4 restriction absent from this first response; both occur in the reference.",
         "No prior attempt/feedback exists at this first turn. This excludes earlier feedback as the source, but not independent hallucination."),
        ("2024-I-11", 3, "axes of symmetry",
         "Critique says 'When you say' before a 4-axes, 8/4=2 argument that occurs in the reference, not this response.",
         "Earlier critiques already mention symmetry axes, so reference and feedback-history causes are not separable here."),
        ("2024-II-15", 3, "You state results like",
         "Critique attributes equal counts for tan(30 degrees)/tan(60 degrees) and a factor of 3 to the solver. The response names generic slope counting but gives no such equal-count or multiplication calculation; the reference does.",
         "Next response retains boxed 36 with another calculation; this is not proof that the false attribution caused failure."),
        ("2024-II-9", 4, "when you say",
         "Critique attributes a remaining-four-cells, 2^4-1 count and a first-blank-row argument to the solver. These occur in the reference. The response instead imposes incorrect 25-chip equalities and does not make those arguments.",
         "Next response relaxes the 25-chip equalities and changes boxed 12 to 0. The feedback is mixed; no counterfactual identifies harm from the false attribution."),
        ("2024-I-12", 4, "locations you mention",
         "Critique attributes explicit zeros/ones of h(x) to the solver. The reference defines h and lists those locations; the response defines f,g and never defines h or lists those locations.",
         "Next response retains boxed 9 and still lacks the attributed zero/one list. No demonstrated adoption of the spurious attribution."),
    ]
    reviewed = []
    for question_id, turn, marker, observation, qualification in reviewed_specs:
        key, record = next((key, record) for key, records in histories.items()
                           for record in records if record["id"] == question_id and record["turn"] == turn)
        feedback = record["feedback"] or ""
        if marker not in feedback:
            raise ValueError(f"Reviewed feedback changed: {question_id}, {turn}")
        index = feedback.index(marker)
        reference = references[key]
        reviewed.append({
            "id": question_id, "turn": turn,
            "reviewer": "Codex direct exploratory review, not independent annotation",
            "observation": observation, "qualification": qualification,
            "history_sources": record["sources"],
            "reference_source": {k: v for k, v in reference.items() if k != "reference"},
            "response": record["response"],
            "feedback_attribution_window": feedback[max(0, index - 120):index + 700],
            "whole_feedback_incorrect": "not inferred",
            "causal_reference_effect_established": False,
            "causal_downstream_harm_established": False,
        })
    (BASE / "source_binding_reviewed_witnesses.json").write_text(
        json.dumps({"witnesses": len(reviewed),
                    "unique_questions": len({r["id"] for r in reviewed}),
                    "selection": "Targeted review of source-overlap cues plus first-turn octagon trace",
                    "records": reviewed}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    # Two illustrative input contrasts, not an execution manifest or model test.
    # Only a reference-local helper symbol changes. Source/problem/student stay
    # fixed; counting all mentions of the new symbol would be an invalid metric.
    examples = []
    for question_id, turn, old, new in [("2024-I-12", 4, "h", "u"),
                                         ("2024-II-15", 3, "k", "v")]:
        key, record = next((key, record) for key, records in histories.items()
                           for record in records if record["id"] == question_id and record["turn"] == turn)
        reference = references[key]["reference"]
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(old) + r"(?![A-Za-z])")
        new_pattern = re.compile(r"(?<![A-Za-z])" + re.escape(new) + r"(?![A-Za-z])")
        if (pattern.search(key[1]) or pattern.search(record["response"])
                or new_pattern.search(reference + key[1] + record["response"])):
            raise ValueError(f"Helper rename is not reference-local: {question_id}")
        renamed, substitutions = pattern.subn(new, reference)
        if not substitutions or new_pattern.sub(old, renamed) != reference:
            raise ValueError(f"Helper rename is not reversible: {question_id}")
        examples.append({
            "id": question_id, "turn": turn,
            "problem": key[1], "fixed_student_response": record["response"],
            "reference_original": reference, "reference_renamed": renamed,
            "renamed_reference_local_helper": {"from": old, "to": new, "occurrences": substitutions},
            "intended_semantic_invariant": "Consistently rename a reference-local mathematical helper; the student's actual claims and errors do not change",
            "diagnostic_prediction": "If reference content is misbound to the student, unsupported assertions about what the student wrote may track the reference-only helper name",
            "not_a_failure": "Legitimate guidance may introduce the renamed helper; mere mention does not establish misattribution",
            "model_test_run": False,
        })
    (BASE / "source_binding_counterfactual_examples.json").write_text(
        json.dumps({"status": "two_illustrative_cpu_examples_not_an_execution_plan",
                    "records": examples}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in result.items() if k != "candidates"}, ensure_ascii=False))


if __name__ == "__main__":
    run()
