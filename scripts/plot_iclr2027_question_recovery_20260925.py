"""Render the Qwen3-8B Game24 question-level R2/R3 recovery figure.

All plotted values are read from the frozen question-level analysis CSV. Before
plotting, they are checked against both the Appendix LaTeX table and the frozen
aggregate evidence manifest. No outcomes are rescored or entered by hand.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "texts/iclr-2027-style-files/iclr2027"
EVIDENCE_DIR = ROOT / "runs/iclr2027_evidence_20260925_completed"
EVIDENCE_JSON = EVIDENCE_DIR / "evidence.json"
QUESTION_CSV = EVIDENCE_DIR / "game24_per_question.csv"
APPENDIX_TEX = EVIDENCE_DIR / "game24_per_question.tex"

R2_COLOR = "#C56F5A"  # muted coral
R3_COLOR = "#328C85"  # muted teal
CONNECTOR = "#C9CED1"
GRID = "#E7EAEC"
TEXT = "#293238"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv_counts() -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    with QUESTION_CSV.open(newline="", encoding="utf-8") as handle:
        for source_row in csv.DictReader(handle):
            if source_row["model"] != "Qwen3-8B":
                continue
            rows.append({
                "question": int(source_row["question"]),
                "R2": int(source_row["R2"]),
                "R3": int(source_row["R3"]),
            })
    if len(rows) != 23 or len({row["question"] for row in rows}) != len(rows):
        raise ValueError(f"Expected 23 unique Qwen3-8B questions, found {len(rows)}")
    if any(not (0 <= row["R2"] <= 2 and 0 <= row["R3"] <= 2) for row in rows):
        raise ValueError("Correct-generation counts must be in {0, 1, 2}")
    return rows


def load_appendix_counts() -> dict[int, tuple[int, int]]:
    """Read Qwen3-8B R2/R3 counts from the exact LaTeX table used in Appendix."""
    counts: dict[int, tuple[int, int]] = {}
    for line in APPENDIX_TEX.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("&")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        question = int(cells[0])
        qwen8_counts = tuple(int(value) for value in cells[1].split("/") )
        if len(qwen8_counts) != 4:
            raise ValueError(f"Expected R0/R2/R3/R4 counts for question {question}")
        counts[question] = (qwen8_counts[1], qwen8_counts[2])
    return counts


def verify_frozen_inputs(evidence: dict) -> dict[str, str]:
    """Verify the three frozen Qwen3-8B Game24 batches referenced by evidence."""
    hashes: dict[str, str] = {}
    keys = sorted(key for key in evidence["inputs"] if key.startswith("game24_qwen8_"))
    if not keys:
        raise ValueError("No frozen Qwen3-8B Game24 input files are listed in evidence.json")
    for key in keys:
        item = evidence["inputs"][key]
        path = ROOT / Path(item["path"].replace("\\", "/"))
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != item["sha256"]:
            raise ValueError(f"Frozen input hash mismatch for {key}")
        hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = actual
    return hashes


def category(row: dict[str, int]) -> tuple[int, str]:
    change = row["R3"] - row["R2"]
    if change == 2:
        return 0, "0 to 2"
    if change == 1:
        return 1, "gain"
    if change == 0:
        return 2, "unchanged"
    return 3, "decline"


def main() -> None:
    evidence = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    panel = evidence["panels"]["Game24_Qwen3_8B"]
    rows = load_csv_counts()
    appendix = load_appendix_counts()
    csv_counts = {row["question"]: (row["R2"], row["R3"]) for row in rows}

    if csv_counts != appendix:
        mismatches = {
            question: {"analysis_csv": csv_counts.get(question),
                       "appendix_table": appendix.get(question)}
            for question in sorted(set(csv_counts) | set(appendix))
            if csv_counts.get(question) != appendix.get(question)
        }
        raise ValueError(f"Question counts do not match the Appendix table: {mismatches}")
    for condition in ("R2", "R3"):
        total = sum(row[condition] for row in rows)
        expected = panel["audit"]["correct_by_condition"][condition]
        if total != expected:
            raise ValueError(f"{condition} question counts sum to {total}, frozen aggregate is {expected}")
    if panel["audit"]["questions"] != len(rows):
        raise ValueError("Question-level count does not match the frozen aggregate panel")

    rows.sort(key=lambda row: (category(row)[0], row["question"]))
    y_positions: list[float] = []
    separators: list[float] = []
    prior_group: int | None = None
    y = 0.0
    for row in rows:
        group = category(row)[0]
        if prior_group is not None and group != prior_group:
            separators.append(y - 0.25)
            y += 0.5
        y_positions.append(y)
        y += 1.0
        prior_group = group

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 7.8,
        "legend.fontsize": 7.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
    })
    fig, ax = plt.subplots(figsize=(5.45, 4.35))
    fig.subplots_adjust(left=0.13, right=0.99, top=0.86, bottom=0.14)

    ax.set_axisbelow(True)
    ax.set_xticks([0, 1, 2])
    ax.set_xlim(-0.30, 2.30)
    ax.grid(axis="x", color=GRID, linewidth=0.65)
    for separator in separators:
        ax.axhline(separator, color="#EFF1F2", linewidth=0.65, zorder=0)

    for row, row_y in zip(rows, y_positions):
        r2, r3 = row["R2"], row["R3"]
        ax.plot([r2, r3], [row_y, row_y], color=CONNECTOR, linewidth=1.05, zorder=1)
        ax.scatter([r2], [row_y], s=25, marker="o", color=R2_COLOR,
                   edgecolors="white", linewidths=0.45, zorder=3)
        # A hollow diamond keeps the R2 circle visible when both values tie.
        ax.scatter([r3], [row_y], s=34, marker="D", facecolors="none",
                   edgecolors=R3_COLOR, linewidths=1.05, zorder=4)

    ax.set_yticks(y_positions, [str(row["question"]) for row in rows])
    ax.invert_yaxis()
    ax.set_ylim(y_positions[-1] + 0.45, y_positions[0] - 0.45)
    ax.set_ylabel("Game24 question ID", labelpad=5, color=TEXT)
    ax.set_xlabel("Correct seeds (out of 2)", labelpad=5, color=TEXT)
    ax.tick_params(axis="both", colors=TEXT, length=0)
    ax.tick_params(axis="y", pad=4)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#AEB5B9")

    legend_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=5.0,
               markerfacecolor=R2_COLOR, markeredgecolor="white",
               label="Full"),
        Line2D([0], [0], marker="D", linestyle="none", markersize=5.2,
               markerfacecolor="none", markeredgecolor=R3_COLOR,
               label="LateBlock"),
    ]
    ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.60, 1.005),
              ncol=2, frameon=False, handletextpad=0.4, columnspacing=1.25,
              borderaxespad=0.0)

    for suffix in ("pdf", "png"):
        fig.savefig(PAPER / f"figure3_question_level_recovery.{suffix}",
                    dpi=300, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    transitions: dict[str, int] = {"large_gain_0_to_2": 0, "gain_1_seed": 0,
                                   "unchanged": 0, "decline": 0}
    ordered_rows = []
    for row in rows:
        group, _ = category(row)
        key = ("large_gain_0_to_2" if group == 0 else
               "gain_1_seed" if group == 1 else
               "unchanged" if group == 2 else "decline")
        transitions[key] += 1
        ordered_rows.append({**row, "change_R3_minus_R2": row["R3"] - row["R2"],
                             "transition_group": key})
    with (PAPER / "figure3_question_level_recovery.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ordered_rows[0]))
        writer.writeheader()
        writer.writerows(ordered_rows)

    raw_hashes = verify_frozen_inputs(evidence)
    sources = (EVIDENCE_JSON, QUESTION_CSV, APPENDIX_TEX)
    provenance = {
        "figure": "figure3_question_level_recovery",
        "question_count": len(rows),
        "condition": {"R2": "full access", "R3": "late access blocking"},
        "metric": "correct generations out of two paired seeds per question",
        "aggregate_correct_generations": {
            "R2": panel["audit"]["correct_by_condition"]["R2"],
            "R3": panel["audit"]["correct_by_condition"]["R3"],
            "trials_per_condition": 2 * len(rows),
        },
        "question_transition_counts": transitions,
        "sort_order": ["0-to-2 gains", "1-seed gains", "unchanged", "declines",
                       "question ID ascending within each group"],
        "sources_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in sources
        },
        "raw_frozen_input_sha256": raw_hashes,
        "question_rows_in_plot_order": ordered_rows,
        "claim_scope": "distribution over the selected 23-question set; no outlier or population-generalization claim",
    }
    (PAPER / "figure3_question_level_recovery_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"questions": len(rows), "aggregate_correct_generations":
                      provenance["aggregate_correct_generations"],
                      "question_transition_counts": transitions}, indent=2))


if __name__ == "__main__":
    main()
