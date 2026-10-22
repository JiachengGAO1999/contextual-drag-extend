"""Recompute paper tables from persisted, completed generations only."""
from __future__ import annotations

import hashlib
import json
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/iclr2027_evidence_20260925_completed"
INPUTS = {
    "game24_qwen8_7": ROOT / "outputs/game24-dual-anchor-validation-20260918/results.jsonl",
    "game24_qwen8_8": ROOT / "runs/game24_batch02_validation_20260921_raw/results.jsonl",
    "game24_qwen8_additional8": ROOT / "runs/game24_batch03_validation_20260925_raw/results.jsonl",
    "game24_qwen32_r0": ROOT / "runs/game24_qwen3_32b_r0_gate_15q_20260922_raw/results.jsonl",
    "game24_qwen32_r2r3": ROOT / "runs/game24_qwen3_32b_r2_r3_15q_20260923_raw/results.jsonl",
    "game24_gemma_r0": ROOT / "runs/game24_gemma4_e4b_r0_20260923_raw/results.jsonl",
    "game24_gemma_r2r3": ROOT / "runs/game24_gemma4_e4b_r2_r3_20260923_raw/results.jsonl",
    "math": ROOT / "runs/math_external_16q_20260920_raw/results.jsonl",
    "correct_control": ROOT / "runs/game24_correct_draft_specificity_20260922_raw/results.jsonl",
}


def normalized(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        gen, = raw["init_response_generations"]
        meta = gen["selective_context_metadata"]
        request = meta.get("request") or raw.get("init_response_generations_metadata", {}).get("intervention")
        assert request is not None, path
        tokens = raw.get("generated_token_ids") or []
        correct = gen.get("correctness")
        assert correct in (True, False, None)
        rows.append(dict(
            id=str(raw["id"]), seed=int(request["sample_seed"]),
            stratum=raw.get("stratum"),
            condition=request["condition_id"], correct=int(correct is True),
            score_status="correct" if correct is True else "incorrect" if correct is False else "unresolved",
            finish_reason=str(gen.get("finish_reason")), thinking_status=str(raw.get("thinking_status")),
            generated_tokens=len(tokens), first_generated_token=tokens[0] if tokens else None,
            prompt_sha256=request.get("prompt_sha256"), input_ids_sha256=request.get("input_ids_sha256"),
            draft_token_span=request.get("draft_token_span"),
        ))
    return rows


def check_factorial(rows: list[dict], conditions: tuple[str, ...], n_questions: int):
    qids = {r["id"] for r in rows}
    seeds = {r["seed"] for r in rows}
    keys = [(r["id"], r["seed"], r["condition"]) for r in rows]
    assert len(qids) == n_questions, (len(qids), n_questions)
    assert len(seeds) == 2 and len(keys) == len(set(keys))
    assert set(keys) == {(q, s, c) for q in qids for s in seeds for c in conditions}
    index = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    if "R2" in conditions and "R3" in conditions:
        for q in qids:
            for s in seeds:
                a, b = index[q, s, "R2"], index[q, s, "R3"]
                assert (a["prompt_sha256"], a["input_ids_sha256"], a["draft_token_span"], a["first_generated_token"]) == (
                    b["prompt_sha256"], b["input_ids_sha256"], b["draft_token_span"], b["first_generated_token"])
    return dict(questions=n_questions, seeds=sorted(seeds), rows=len(rows), conditions=list(conditions),
                correct_by_condition={c: sum(r["correct"] for r in rows if r["condition"] == c) for c in conditions},
                finish_reasons=dict(Counter(r["finish_reason"] for r in rows)),
                score_status=dict(Counter(r["score_status"] for r in rows)))


def stats(rows: list[dict], draws: int = 50000):
    # The existing four-condition analyzer assumes R4; compute the common
    # contrasts directly for the three-condition target-model panels.
    import random
    from collections import defaultdict
    from analyze_continued_access_math_20260921 import percentile

    rng = random.Random(20260925)
    qids = sorted({r["id"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    idx = {(r["id"], r["seed"], r["condition"]): r for r in rows}
    conditions = sorted({r["condition"] for r in rows})
    effects = {}
    for left, right in (("R0", "R2"), ("R3", "R2"), ("R3", "R0"), ("R4", "R2"), ("R4", "R3")):
        if left not in conditions or right not in conditions:
            continue
        byq = {q: [idx[q, s, left]["correct"] - idx[q, s, right]["correct"] for s in seeds] for q in qids}
        vals = [v for row in byq.values() for v in row]
        bs = [sum(sum(byq[rng.choice(qids)]) for _ in qids) / len(vals) for _ in range(draws)]
        transitions = Counter((idx[q, s, left]["correct"], idx[q, s, right]["correct"]) for q in qids for s in seeds)
        effects[f"{left}-{right}"] = dict(estimate=sum(vals) / len(vals), ci=[percentile(bs, .025), percentile(bs, .975)],
                                         transitions={f"{a}{b}": transitions[a, b] for a in (0, 1) for b in (0, 1)})
    return dict(conditions={c: dict(correct=sum(r["correct"] for r in rows if r["condition"] == c),
                                    n=sum(r["condition"] == c for r in rows),
                                    eos=sum(r["condition"] == c and r["finish_reason"] == "eos" for r in rows),
                                    unresolved=sum(r["condition"] == c and r["score_status"] == "unresolved" for r in rows))
                            for c in conditions}, effects=effects)


def main():
    input_manifest = {name: dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                      for name, path in INPUTS.items()}
    q8 = normalized(INPUTS["game24_qwen8_7"]) + normalized(INPUTS["game24_qwen8_8"])
    shared_q8 = list(q8)
    additional = normalized(INPUTS["game24_qwen8_additional8"])
    check_factorial(additional, ("R0", "R2", "R3", "R4"), 8)
    assert not {r['id'] for r in q8} & {r['id'] for r in additional}
    q8 += additional
    q32 = normalized(INPUTS["game24_qwen32_r0"]) + normalized(INPUTS["game24_qwen32_r2r3"])
    gemma = normalized(INPUTS["game24_gemma_r0"]) + normalized(INPUTS["game24_gemma_r2r3"])
    math = normalized(INPUTS["math"])
    control = normalized(INPUTS["correct_control"])
    assert {r["id"] for r in shared_q8} == {r["id"] for r in q32} == {r["id"] for r in gemma}
    panels = {
        "Game24_Qwen3_8B": dict(audit=check_factorial(q8, ("R0", "R2", "R3", "R4"), 23), stats=stats(q8)),
        "Game24_Qwen3_32B": dict(audit=check_factorial(q32, ("R0", "R2", "R3"), 15), stats=stats(q32)),
        "Game24_Gemma4_E4B": dict(audit=check_factorial(gemma, ("R0", "R2", "R3"), 15), stats=stats(gemma)),
    }
    # MATH provenance and draft source are confounded; preserve the two panels.
    for source in ("MATH500_Qwen3_1.7B", "MATH_train_Qwen3_4B"):
        subset = [r for r in math if r["stratum"] == source]
        panel = normalized(INPUTS["math"])
        subset_norm = [r for r in panel if r["id"] in {x["id"] for x in subset}]
        panels[source] = dict(audit=check_factorial(subset_norm, ("R0", "R2", "R3", "R4"), 8), stats=stats(subset_norm))
    assert len(control) == 32 and len({r["id"] for r in control}) == 8
    assert {r["condition"] for r in control} == {"C_FULL", "C_LATE"}
    control_counts = {c: sum(r["correct"] for r in control if r["condition"] == c) for c in ("C_FULL", "C_LATE")}
    assert control_counts == {"C_FULL": 16, "C_LATE": 13}
    assert {r["id"] for r in control} <= {r["id"] for r in q8}
    exclude_41 = [r for r in q8 if r["id"] != "41"]
    assert len({r["id"] for r in exclude_41}) == 22
    assert sum(r["correct"] for r in exclude_41 if r["condition"] == "R2") == 16
    assert sum(r["correct"] for r in exclude_41 if r["condition"] == "R3") == 34
    result = dict(inputs=input_manifest, panels=panels,
                  correct_history=dict(questions=8, requests=32, counts=control_counts),
                  shared_15_qwen8=dict(audit=check_factorial(shared_q8, ("R0", "R2", "R3", "R4"), 15), stats=stats(shared_q8)),
                  exclude_41=dict(audit=check_factorial(exclude_41, ("R0", "R2", "R3", "R4"), 22), stats=stats(exclude_41)),
                  exclude_381=dict(audit=check_factorial([r for r in q8 if r['id']!='381'], ("R0", "R2", "R3", "R4"), 22), stats=stats([r for r in q8 if r['id']!='381'])),
                  additional_8=dict(audit=check_factorial(additional, ("R0", "R2", "R3", "R4"), 8), stats=stats(additional)),
                  scientific_requests=524, batch03_validation="included after complete 64-request factorial, score and provenance audit")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidence.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    datasets = {"Qwen3-8B": q8, "Qwen3-32B": q32, "Gemma 4 E4B": gemma}
    qids = sorted({r["id"] for r in q8}, key=lambda value: int(value))
    per_question = []
    for model, rows in datasets.items():
        for qid in qids:
            item = {"model": model, "question": qid}
            for condition in ("R0", "R2", "R3", "R4"):
                selected = [r for r in rows if r["id"] == qid and r["condition"] == condition]
                item[condition] = sum(r["correct"] for r in selected) if selected else ""
            per_question.append(item)
    with (OUT / "game24_per_question.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "question", "R0", "R2", "R3", "R4"])
        writer.writeheader()
        writer.writerows(per_question)
    indexed = {(row["model"], row["question"]): row for row in per_question}
    table = [
        "% Generated from persisted scorer decisions by build_iclr2027_evidence_20260925.py",
        "\\begin{table}[H]", "\\centering\\small",
        "\\caption{Game24 correct counts per question. Each digit is out of two seeds. Qwen3-8B covers 23 questions in R0/R2/R3/R4; the other models cover the shared 15-question subset in R0/R2/R3. A dash denotes an unevaluated model--question combination.}",
        "\\label{tab:game24-per-question}", "\\begin{tabular}{rccc}", "\\toprule",
        "Question & Qwen3-8B & Qwen3-32B & Gemma 4 E4B \\\\", "\\midrule",
    ]
    for qid in qids:
        cells = []
        for model in datasets:
            row = indexed[model, qid]
            order = ("R0", "R2", "R3", "R4") if model == "Qwen3-8B" else ("R0", "R2", "R3")
            cells.append("/".join(str(row[c]) for c in order) if row['R0'] != '' else '---')
        table.append(qid + " & " + " & ".join(cells) + " \\\\")
    table.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    (OUT / "game24_per_question.tex").write_text("\n".join(table), encoding="utf-8")
    print(json.dumps({k: {"audit": v["audit"], "stats": v["stats"]} for k, v in panels.items()}, indent=2))


if __name__ == "__main__":
    main()
