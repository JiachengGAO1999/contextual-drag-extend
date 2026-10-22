"""Prepare a finite source-binding probe. CPU only; does not queue model work."""

from collections import Counter
import json
from pathlib import Path
import random


ROOT = Path("outputs/generation-diagnostics-20261005")
SOURCE = ROOT / "public_verification_preview/dataset.json"
OUT = ROOT / "public_verification_preview/source_binding_probe"
SEED = 20261005
TASK = (
    "Give brief feedback on the student's attempted solution below. Identify up to "
    "three concrete errors in the student's reasoning and explain them in at most "
    "six sentences. Do not provide the full corrected solution or reveal the "
    "correct final answer. Focus on what the student actually wrote."
)
GROUNDING = (
    " Before attributing an erroneous claim to the student, check that the claim "
    "occurs in the student's attempt. Quote the relevant student words exactly. "
    "Keep suggestions from the reference distinct from claims the student made."
)


def prompt(problem, student, reference=None, grounded=False):
    pieces = [TASK + (GROUNDING if grounded else ""), "Question:\n" + problem]
    if reference is not None:
        pieces.append("Reference solution (for checking correctness):\n" + reference)
    pieces.append("Student attempt to critique:\n" + student)
    return "\n\n".join(pieces)


def run():
    rows = json.loads(SOURCE.read_text(encoding="utf8"))
    unique = {}
    for index, row in enumerate(rows):
        unique.setdefault(row["problem"].strip(), (index, row))
    ordered = list(unique.values())
    random.Random(SEED).shuffle(ordered)
    selected = ordered[:64]
    requests = []
    questions = []
    for position, (index, row) in enumerate(selected, 1):
        steps = row["student_incorrect_solution"]
        error_index = row["incorrect_index"]
        if steps[error_index].strip() != row["incorrect_step"].strip():
            raise ValueError(f"First-error annotation does not align at row {index}")
        student = "\n".join(f"[S{i + 1}] {step}" for i, step in enumerate(steps))
        question = {
            "question_number": position, "source_file": str(SOURCE), "source_row": index,
            "problem": row["problem"], "student_step_count": len(steps),
            "teacher_first_error_step": f"S{error_index + 1}",
            "teacher_first_error_text": row["incorrect_step"],
            "teacher_error_category": row["error_category"],
            "teacher_error_description": row["error_description"],
        }
        questions.append(question)
        for condition in ["NO_REFERENCE", "REFERENCE", "GROUNDED_REFERENCE"]:
            requests.append({
                "request_id": f"independent_{position:03d}_{condition.lower()}",
                "role": "independent_material_replication", "question_number": position,
                "source_file": str(SOURCE), "source_row": index, "condition": condition,
                "prompt": prompt(row["problem"], student,
                                 row["reference_solution"] if condition != "NO_REFERENCE" else None,
                                 condition == "GROUNDED_REFERENCE"),
            })

    example_file = ROOT / "public_feedback_friction_preview/source_binding_counterfactual_examples.json"
    examples = json.loads(example_file.read_text(encoding="utf8"))["records"]
    for example in examples:
        for condition, field in [("REFERENCE_ORIGINAL", "reference_original"),
                                 ("REFERENCE_RENAMED", "reference_renamed")]:
            requests.append({
                "request_id": f"transport_{example['id']}_{condition.lower()}",
                "role": "exploratory_reference_only_symbol_transport",
                "source_file": str(example_file), "source_question_id": example["id"],
                "condition": condition, "rename": example["renamed_reference_local_helper"],
                "prompt": prompt(example["problem"], example["fixed_student_response"], example[field]),
            })
    random.Random(SEED).shuffle(requests)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    with (OUT / "requests.jsonl").open("w", encoding="utf8") as output:
        for request in requests:
            output.write(json.dumps(request, ensure_ascii=False) + "\n")
    config = {
        "status": "authorized_finite_batch",
        "source_url": "https://github.com/eth-lre/verify-then-generate/blob/main/dataset/dataset.json",
        "source_rows": len(rows), "unique_source_problems": len(unique),
        "selection": "First source row per exact problem text; fixed-seed shuffle; first 64 unique problems",
        "seed": SEED, "independent_questions": len(selected),
        "teacher_error_categories": dict(Counter(q["teacher_error_category"] for q in questions)),
        "independent_requests": len(selected) * 3, "exploratory_transport_requests": len(examples) * 2,
        "total_requests": len(requests),
        "model": "Qwen3-8B Thinking", "dtype": "bfloat16", "backend": "vllm",
        "temperature": 0.0, "top_p": 1.0, "max_new_tokens": 2048,
        "runtime_estimate_minutes": [30, 60],
        "authorization": "2026-10-12 user removed GPU budget gate; allocate reasonable duration per experiment",
        "device": "A100 GPU4 when available; do not interrupt other users",
        "execution": "Finite 196-request batch; consult run_state.json for live progress; old budget.json is historical",
        "scope": "Critique generation only; no solver retry, model training, or mechanism claim from two transport examples",
        "missingness": "Persist each response; retain truncations, malformed/empty outputs and incomplete requests; no automatic retries",
        "evaluation": [
            "Directly review whether feedback attributes to the student a concrete reference-only claim absent from the student attempt.",
            "Separate legitimate new guidance, correct detection, unsupported student attribution and unresolved cases.",
            "Teacher annotations identify the first error only; other diagnoses need semantic review, not automatic false labels.",
            "Compare paired question-level unsupported-attribution counts and first-error detection; seeds and claims are not independent questions.",
            "For transport pairs, review unsupported student attributions that follow the reference-only helper; mere helper mentions are not errors.",
            "Grounded-reference prompting is an existing strong baseline, not a claimed new method.",
        ],
    }
    (OUT / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(config, ensure_ascii=False))


if __name__ == "__main__":
    run()
