"""Verify the editorial revision against frozen evidence and export diagnostics."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "texts/iclr-2027-style-files/iclr2027"
REV = ROOT / "texts/revisions/iclr2027_submission_ready_20260925"


def main():
    REV.mkdir(parents=True, exist_ok=True)
    evidence = json.loads((ROOT / "runs/iclr2027_evidence_20260925_completed/evidence.json").read_text(encoding="utf-8"))
    tex = (PAPER / "contextual_drag_continued_access.tex").read_text(encoding="utf-8")
    abstract = re.search(r"\\begin\{abstract\}\s*(.*?)\s*\\end\{abstract\}", tex, re.S).group(1).replace(r"\%", "%")
    for value in ('23 Game24', '40/46', '18/46', '36/46', '+39.1', '+23.9', '+54.3', '15-question subset',
                  'positive point estimates', 'cross-task directional check'):
        assert value in abstract, value
    main_panel = evidence['panels']['Game24_Qwen3_8B']
    assert main_panel['audit']['questions'] == 23
    assert main_panel['audit']['correct_by_condition'] == dict(R0=40,R2=18,R3=36,R4=35)
    assert all(main_panel['stats']['conditions'][c]['n'] == 46 for c in ('R0', 'R2', 'R3', 'R4'))
    main_effect = main_panel['stats']['effects']['R3-R2']
    assert round(main_effect['estimate'] * 100, 1) == 39.1
    assert [round(x * 100, 1) for x in main_effect['ci']] == [23.9, 54.3]
    title = re.search(r"\\title\{(.*?)\}", tex, re.S).group(1).replace(r"\\", "")
    assert "".join(title.split()) == "AfterErrorFeedback:ContinuedAccesstoFailedReasoningContributestoContextualDrag"
    assert "Sustains" not in title
    exclude_41 = evidence['exclude_41']
    assert exclude_41['audit']['questions'] == 22
    assert exclude_41['stats']['conditions']['R2']['correct'] == 16
    assert exclude_41['stats']['conditions']['R3']['correct'] == 34
    id41_effect = exclude_41['stats']['effects']['R3-R2']
    assert round(id41_effect['estimate'] * 100, 1) == 40.9
    assert [round(x * 100, 1) for x in id41_effect['ci']] == [25.0, 56.8]
    assert 'question 41' in tex and '40.9 points' in tex and '[+25.0,+56.8]' in tex
    assert 'The main conclusion is unchanged when excluding the single question admitted under an earlier eligibility rule' in tex
    assert 'an anonymous public artifact link can be added' not in tex
    assert 'final anonymous supplement will contain' not in tex
    assert '81.8%' not in tex
    assert 'Blocking can harm correct history' in tex
    assert 'Blocking begins only after $y_1$ has been sampled' in tex
    figure = json.loads((PAPER / "figure2_access_effects_provenance.json").read_text(encoding="utf-8"))
    fig_main = figure['rows'][0]
    assert fig_main['questions'] == 23
    assert round(fig_main['effect_pp'], 1) == 39.1
    assert [round(fig_main[k], 1) for k in ('low_pp', 'high_pp')] == [23.9, 54.3]
    assert '23 questions for Qwen3-8B' in tex
    assert r'Qwen3-8B & 40/46 & 18/46 & 36/46 & $+39.1$ [$+23.9,+54.3$]' in tex
    assert r'Pooled main sample & 23 & 18/46 & 36/46 & $+39.1$ [$+23.9,+54.3$]' in tex
    assert r'Exclude question 381 & 22 & 17/44 & 34/44 & $+38.6$ [$+22.7,+54.5$]' in tex
    assert r'Exclude question 41 & 22 & 16/44 & 34/44 & $+40.9$ [$+25.0,+56.8$]' in tex
    assert not re.search(r"\b(pilot|Stage-1|confirmatory|Batch03|Batch04|resultpending|draftnote|RESULT PENDING|DRAFT NOTE)\b", tex, re.I)
    (REV / "abstract_after.txt").write_text(abstract + "\n", encoding="utf-8")
    (ROOT / "texts/abstract.txt").write_text(abstract + "\n", encoding="utf-8")
    manifest = {}
    total = 0
    length_scoring = Counter()
    lengths = []
    normalized = []
    for name, entry in evidence["inputs"].items():
        path = ROOT / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], path
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        total += len(records)
        manifest[name] = {"rows": len(records), "sha256_matches": True}
        for raw in records:
            gen, = raw["init_response_generations"]
            meta = gen["selective_context_metadata"]
            req = meta.get("request") or raw["init_response_generations_metadata"]["intervention"]
            if name.startswith("game24_qwen8"):
                group = "Game24 / Qwen3-8B"
            elif name.startswith("game24_qwen32"):
                group = "Game24 / Qwen3-32B"
            elif name.startswith("game24_gemma"):
                group = "Game24 / Gemma 4 E4B"
            elif name == "correct_control":
                group = "Correct history / Qwen3-8B"
            else:
                group = "MATH500 / Qwen3-8B" if raw["stratum"] == "MATH500_Qwen3_1.7B" else "MATH-train / Qwen3-8B"
            row = dict(group=group, id=str(raw["id"]), seed=req["sample_seed"], condition=req["condition_id"],
                       correct=gen.get("correctness") is True, unresolved=gen.get("correctness") is None,
                       finish=gen.get("finish_reason"))
            normalized.append(row)
            if row["finish"] == "length":
                length_scoring[str(gen.get("correctness"))] += 1
                lengths.append(row)
    assert total == 524, total
    figure = json.loads((PAPER / "figure2_access_effects_provenance.json").read_text(encoding="utf-8"))
    for relative, digest in figure["sources"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert len(figure["rows"]) == 6
    figure3 = json.loads((PAPER / "figure3_question_level_recovery_provenance.json").read_text(encoding="utf-8"))
    for relative, digest in figure3["sources_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    for relative, digest in figure3["raw_frozen_input_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert len(figure3["question_rows_in_plot_order"]) == main_panel["audit"]["questions"]
    assert figure3["aggregate_correct_generations"]["R2"] == main_panel["audit"]["correct_by_condition"]["R2"]
    assert figure3["aggregate_correct_generations"]["R3"] == main_panel["audit"]["correct_by_condition"]["R3"]
    assert figure3["aggregate_correct_generations"]["trials_per_condition"] == 2 * main_panel["audit"]["questions"]

    question_csv = {}
    with (ROOT / "runs/iclr2027_evidence_20260925_completed/game24_per_question.csv").open(
            newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model"] == "Qwen3-8B":
                question_csv[int(row["question"])] = (int(row["R2"]), int(row["R3"]))
    question_appendix = {}
    for line in (ROOT / "runs/iclr2027_evidence_20260925_completed/game24_per_question.tex").read_text(
            encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("&")]
        if len(cells) == 4 and cells[0].isdigit():
            qwen8_counts = [int(value) for value in cells[1].split("/")]
            assert len(qwen8_counts) == 4
            question_appendix[int(cells[0])] = (qwen8_counts[1], qwen8_counts[2])
    figure3_counts = {
        row["question"]: (row["R2"], row["R3"])
        for row in figure3["question_rows_in_plot_order"]
    }
    assert question_csv == question_appendix == figure3_counts
    deltas = [r3 - r2 for r2, r3 in question_csv.values()]
    assert sum(delta > 0 for delta in deltas) == figure3["question_transition_counts"]["large_gain_0_to_2"] + figure3["question_transition_counts"]["gain_1_seed"]
    assert sum(delta == 0 for delta in deltas) == figure3["question_transition_counts"]["unchanged"]
    assert sum(delta < 0 for delta in deltas) == figure3["question_transition_counts"]["decline"]
    assert r"\includegraphics[width=0.92\textwidth]{figure3_question_level_recovery.pdf}" in tex
    assert r"\label{fig:question-recovery}" in tex and r"\ref{fig:question-recovery}" in tex
    assert (PAPER / "figure3_question_level_recovery.pdf").is_file()
    assert (PAPER / "figure3_question_level_recovery.png").is_file()
    table = ["% Generated by audit_iclr2027_revision_20260925.py",
             r"\begin{table}[H]", r"\centering\small",
             r"\caption{All completed requests in the paper. Correctness uses persisted benchmark scores; unresolved answers count as incorrect. Termination is reported separately. MATH rows use the Qwen3-8B target.}",
             r"\label{tab:diagnostics}", r"\begin{tabular}{llrrrr}", r"\toprule",
             r"Task / target & Condition & Correct & EOS & Length & Unresolved \\", r"\midrule"]
    for group in dict.fromkeys(row["group"] for row in normalized):
        available = {row["condition"] for row in normalized if row["group"] == group}
        for i, condition in enumerate(c for c in ("R0", "R2", "R3", "R4", "C_FULL", "C_LATE") if c in available):
            rows = [row for row in normalized if row["group"] == group and row["condition"] == condition]
            label = group if i == 0 else ""
            cond_label = condition.replace("_", r"\_")
            vals = [f"{sum(r['correct'] for r in rows)}/{len(rows)}", str(sum(r['finish']=='eos' for r in rows)),
                    str(sum(r['finish']=='length' for r in rows)), str(sum(r['unresolved'] for r in rows))]
            table.append(label + " & " + cond_label + " & " + " & ".join(vals) + r" \\")
        table.append(r"\addlinespace[3pt]")
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (PAPER / "generation_diagnostics.tex").write_text("\n".join(table), encoding="utf-8")
    report = dict(abstract_numbers_updated_to_completed_evidence=True, title_updated_to_conservative_claim=True,
                  main_counts_consistent_across_text_table_figure_appendix=True, manuscript_no_pending_or_batch_claims=True,
                  frozen_inputs=manifest, scientific_requests=total, figure_source_hashes_match=True,
                  figure3_question_level_data_matches_appendix=True,
                  figure3_question_count=len(figure3_counts),
                  figure3_question_transition_counts=figure3["question_transition_counts"],
                  length_stop_scoring=dict(length_scoring), length_stopped_requests=lengths,
                  caveat="Static checks complement, but do not replace, editorial claim review in revision_memo.md.")
    (REV / "revision_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "length_stopped_requests"}, indent=2))


if __name__ == "__main__":
    main()
