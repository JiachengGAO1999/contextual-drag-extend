"""Frozen materials and question-level analysis for late-invalidation feasibility."""
from collections import Counter, defaultdict
from decimal import Decimal
import json
from pathlib import Path
import random
import re
import statistics

SEED = 20261012
CONDITIONS = ("CLEAN", "NEUTRAL", "PRE", "POST", "PLACEBO_PRE", "PLACEBO_POST")
LABELS = {
    "note": ("Draft A note: incorrect.\n", "Draft A note: included.\n", "Draft A note: provided.\n"),
    "sentence": ("Draft A is wrong.\n", "Draft A is shown.\n", "Draft A is supplied.\n"),
}
NUMBER = re.compile(r"^[\s$]*([-+]?\d[\d,]*(?:\.\d+)?)[\s$.]*$")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def final_number(text):
    match = NUMBER.fullmatch(text.strip().splitlines()[-1])
    if not match:
        raise ValueError("Ambiguous numeric final line")
    return str(Decimal(match[1].replace(",", "")))


def materials(root):
    base = Path(root) / "outputs/generation-diagnostics-20261005"
    source = base / "public_verification_preview/dataset.json"
    excluded = {q["problem"].strip() for q in read(base / "public_verification_preview/source_binding_probe/questions.json")}
    unique = {}
    for index, row in enumerate(read(source)):
        unique.setdefault(row["problem"].strip(), (index, row))
    pool, skipped = [], []
    for problem, (index, row) in unique.items():
        if problem in excluded:
            continue
        try:
            good = final_number(row["reference_solution"])
            bad = final_number(row["student_incorrect_solution"][-1])
            if Decimal(good) == Decimal(bad):
                raise ValueError("Same final answer")
            if row["student_incorrect_solution"][row["incorrect_index"]].strip() != row["incorrect_step"].strip():
                raise ValueError("First-error index does not align")
        except ValueError as exc:
            skipped.append(dict(source_row=index, reason=str(exc)))
            continue
        pool.append(dict(id=f"independent_{index:04d}", problem=problem,
            draft="\n".join(row["student_incorrect_solution"]), good_draft=row["reference_solution"],
            correct_candidate=good, old_candidate=bad, source=str(source.relative_to(root)),
            source_row=index, teacher_first_error_step=row["incorrect_index"],
            teacher_error_description=row["error_description"], error_category=row["error_category"],
            candidate_scope="Dataset final numerical answers; no claim that this measures an abstract reasoning strategy."))
    random.Random(SEED).shuffle(pool)
    if len(pool) < 128:
        raise ValueError("Insufficient independent materials; do not replenish by model outcome")
    independent = pool[:128]
    for i, q in enumerate(independent):
        q.update(cohort="discovery" if i < 32 else "confirmation", frozen_order=i)
    old_source = base / "candidate_adoption/manifest.json"
    calibration = []
    for i, q in enumerate(read(old_source)["questions"]):
        calibration.append(dict(id="calibration_"+q["id"], cohort="calibration", frozen_order=i,
             problem=q["problem"], draft=q["draft"], good_draft=q["legal_numeric"],
             correct_candidate=q["legal_numeric"], old_candidate=q["old_numeric"],
             source=str(old_source.relative_to(root)), source_question=q["id"],
             candidate_scope="Previously audited legal and illegal Game24 expressions; calibration only."))
    return dict(calibration=calibration, independent=independent, excluded_source_binding_questions=len(excluded),
                eligible_pool=len(pool), eligibility_skips=skipped)


def prompt(q, condition, wording, order):
    invalid, neutral, placebo = LABELS[wording]
    before, after = {
        "NEUTRAL": (neutral, neutral), "PRE": (invalid, neutral), "POST": (neutral, invalid),
        "PLACEBO_PRE": (placebo, neutral), "PLACEBO_POST": (neutral, placebo),
        "CLEAN": ("", ""),
    }[condition]
    text = "Solve the original problem under all its constraints.\nProblem:\n" + q["problem"] + "\n\n"
    if condition != "CLEAN":
        text += before + "--- Draft A ---\n" + q["draft"] + "\n--- End Draft A ---\n" + after + "\n"
    candidates = [q["correct_candidate"], q["old_candidate"]]
    if order == 1:
        candidates.reverse()
    text += (f"Candidate 1: {candidates[0]}\nCandidate 2: {candidates[1]}\n\n"
             "Choose the candidate that correctly answers the original problem. "
             "Do not merely repeat the draft. The answer must be option 1 or option 2.")
    return text


def compile_requests(tokenizer, m, revision):
    result = []
    stem = ("\n</think>\n{\"choice\": " if revision else
            "I need to check the original constraints. The correct final answer is option ")
    option_ids = [tokenizer.encode(s, add_special_tokens=False) for s in ("1", "2")]
    if any(len(ids) != 1 for ids in option_ids):
        raise ValueError("Expected single-token option labels")
    for q in m["calibration"] + m["independent"]:
        wordings = ["note"] if q["cohort"] == "calibration" else list(LABELS)
        for wording in wordings:
            align = {}
            for condition in CONDITIONS:
                if q["cohort"] == "calibration" and condition not in ("CLEAN", "NEUTRAL", "POST"):
                    continue
                if condition == "CLEAN" and wording != "note":
                    continue
                for order in (0, 1):
                    user = prompt(q, condition, wording, order)
                    rendered = tokenizer.apply_chat_template([dict(role="user", content=user)],
                        tokenize=False, add_generation_prompt=True, enable_thinking=True) + stem
                    encoding = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
                    ids = encoding["input_ids"]
                    if len(ids) + 1 > 32768:
                        raise ValueError(f"Context overflow: {q['id']}")
                    # Verify the exact scored suffix, rather than assuming tokenization is compositional.
                    if any(tokenizer.encode(rendered+s, add_special_tokens=False) != ids+label
                           for s, label in zip(("1", "2"), option_ids)):
                        raise ValueError("Scored option boundary changed")
                    span = None
                    if condition != "CLEAN":
                        start = rendered.index("--- Draft A ---\n") + len("--- Draft A ---\n")
                        end = start + len(q["draft"])
                        positions = [i for i, (a,b) in enumerate(encoding["offset_mapping"]) if a < end and b > start]
                        span = [positions[0], positions[-1]+1]
                        align[(condition,order)] = (span, ids[span[0]:span[1]], len(ids))
                    result.append(dict(request_id=f"r{revision}:{q['id']}:{wording}:{condition}:{order}",
                        id=q["id"], cohort=q["cohort"], condition=condition, wording=wording, order=order,
                        revision=revision, input_ids=ids, option_token_ids=[v[0] for v in option_ids],
                        correct_option=0 if order == 0 else 1, draft_span=span,
                        source=q["source"], source_row=q.get("source_row")))
            for order in (0,1):
                present = [align[(c,order)] for c in CONDITIONS if (c,order) in align]
                if present and any(v != present[0] for v in present[1:]):
                    raise ValueError(f"Draft positions, tokens or readout position differ: {q['id']} {wording}")
    return result


def effect(values):
    import numpy as np
    a = np.asarray(values, dtype=float)
    if not len(a):
        return dict(n=0, mean=None, ci95=None)
    rng = np.random.default_rng(SEED)
    means = a[rng.integers(0, len(a), size=(5000, len(a)))].mean(axis=1)
    return dict(n=len(a), mean=float(a.mean()), ci95=np.quantile(means,[.025,.975]).tolist())


def gate0(m, records, revision):
    keyed = {(r["id"],r["condition"],r["order"]):r for r in records
             if r["revision"] == revision and r["wording"] == "note"}
    result = {}
    for cohort, qs in (("calibration",m["calibration"]),
                       ("discovery",[q for q in m["independent"] if q["cohort"] == "discovery"])):
        differences, clean, mass, missing = [], [], [], []
        for q in qs:
            keys = [(q["id"], c, o) for c in ("CLEAN","POST") for o in (0,1)]
            if not all(k in keyed for k in keys):
                missing.append(q["id"])
                continue
            clean.append(statistics.mean(keyed[q["id"],"CLEAN",o]["p_correct"] for o in (0,1)))
            differences.append(clean[-1]-statistics.mean(keyed[q["id"],"POST",o]["p_correct"] for o in (0,1)))
            mass.extend(keyed[k]["option_mass"] for k in keys)
        e = effect(differences)
        competent = bool(clean) and statistics.mean(clean) >= .60
        readable = bool(mass) and statistics.mean(mass) >= .10
        passed = e["n"] >= .9*len(qs) and competent and readable and e["mean"] >= .05 and e["ci95"][0] > 0
        result[cohort] = dict(clean_preference=statistics.mean(clean) if clean else None,
            mean_option_mass=statistics.mean(mass) if mass else None, drag=e, missing=missing, passed=passed)
    return dict(revision=revision, cohorts=result, passed=all(v["passed"] for v in result.values()))


def gate1(m, records, revision, cohort):
    keyed = {(r["id"],r["wording"],r["condition"],r["order"]):r for r in records if r["revision"] == revision}
    qs = [q for q in m["independent"] if q["cohort"] == cohort]
    values, raw, by_wording, missing = [], [], defaultdict(list), []
    for q in qs:
        required = [(q["id"],w,c,o) for w in LABELS for c in ("PRE","POST","PLACEBO_PRE","PLACEBO_POST") for o in (0,1)]
        if not all(k in keyed for k in required):
            missing.append(q["id"])
            continue
        item, direct = [], []
        for w in LABELS:
            avg = {c:statistics.mean(keyed[q["id"],w,c,o]["p_correct"] for o in (0,1))
                   for c in ("PRE","POST","PLACEBO_PRE","PLACEBO_POST")}
            d = avg["PRE"]-avg["POST"]
            corrected = d-(avg["PLACEBO_PRE"]-avg["PLACEBO_POST"])
            direct.append(d); item.append(corrected); by_wording[w].append(corrected)
        values.append(statistics.mean(item)); raw.append(statistics.mean(direct))
    e = effect(values)
    wordings = {w:effect(v) for w,v in by_wording.items()}
    passed = (e["n"] >= .9*len(qs) and e["mean"] >= .05 and e["ci95"][0] > 0
              and all(v["mean"] > 0 for v in wordings.values()) and len(wordings) == len(LABELS))
    return dict(cohort=cohort, corrected_pre_minus_post=e, raw_pre_minus_post=effect(raw),
                by_wording=wordings, missing=missing, passed=passed,
                unit="Question, averaged over both option orders and label wordings. Conditional candidate probability, not accuracy.")
