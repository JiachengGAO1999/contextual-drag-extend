"""Render Figure 2 from frozen analysis files; no rescoring or new inference."""
from pathlib import Path
import csv
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "texts/iclr-2027-style-files/iclr2027"
EVIDENCE = ROOT / "runs/iclr2027_evidence_20260925_completed/evidence.json"
CONTROL = ROOT / "runs/game24_correct_draft_specificity_20260922_analysis/analysis.json"


def main():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    control = json.loads(CONTROL.read_text(encoding="utf-8"))
    rows = []
    labels = [
        ("Game24_Qwen3_8B", "Qwen3-8B / Game24", 23),
        ("Game24_Qwen3_32B", "Qwen3-32B / Game24", 15),
        ("Game24_Gemma4_E4B", "Gemma 4 E4B / Game24", 15),
        ("MATH500_Qwen3_1.7B", "Qwen3-8B / MATH500", 8),
        ("MATH_train_Qwen3_4B", "Qwen3-8B / MATH-train", 8),
    ]
    for key, label, questions in labels:
        panel = evidence["panels"][key]
        assert panel["audit"]["questions"] == questions
        eff = panel["stats"]["effects"]["R3-R2"]
        rows.append(dict(label=label, history="Failed", questions=questions,
                         effect_pp=100 * eff["estimate"], low_pp=100 * eff["ci"][0], high_pp=100 * eff["ci"][1]))
    assert control["audit"]["complete_factorial_and_source_gates"]
    eff = control["correct_history_effect"]
    rows.append(dict(label="Qwen3-8B / Game24", history="Correct", questions=8,
                     effect_pp=100 * eff["estimate"], low_pp=100 * eff["question_cluster_bootstrap_95ci"][0],
                     high_pp=100 * eff["question_cluster_bootstrap_95ci"][1]))
    for r in rows:
        assert r["low_pp"] <= r["effect_pp"] <= r["high_pp"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                        "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, ax = plt.subplots(figsize=(7.2, 4.25))
    fig.subplots_adjust(left=.345, right=.745, top=.89, bottom=.17)
    ys = [5.7, 4.65, 3.6, 2.35, 1.3, -.1]
    ax.axvline(0, color="#626b73", lw=1, zorder=0)
    ax.axhline(.56, color="#d5dade", lw=.8, zorder=0)
    for y, r in zip(ys, rows):
        color = "#147d92" if r["history"] == "Failed" else "#ad531d"
        marker = "o" if r["history"] == "Failed" else "s"
        ax.errorbar(r["effect_pp"], y,
                    xerr=[[r["effect_pp"]-r["low_pp"]], [r["high_pp"]-r["effect_pp"]]],
                    fmt=marker, color=color, ecolor=color, lw=1.8, capsize=3.3, markersize=6, zorder=3)
        ax.text(1.04, y, f"{r['effect_pp']:+.1f} [{r['low_pp']:+.1f}, {r['high_pp']:+.1f}]",
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=10.3, color="#25333d")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['label']}\n{r['history']} history, {r['questions']} questions" for r in rows], fontsize=10.5)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xlim(-45, 103)
    ax.set_ylim(-.75, 6.35)
    ax.set_xticks([-40, 0, 40, 80, 100])
    ax.set_xlabel("Accuracy: LateBlock − Full (pp)", fontsize=11, labelpad=9)
    ax.tick_params(axis="x", labelsize=10)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#a6afb7")
    ax.text(0, 1.06, "Late access blocking", transform=ax.transAxes, fontweight="bold", fontsize=11)
    ax.text(1.04, 1.06, "Effect [95% CI]", transform=ax.transAxes, fontsize=10.5)
    for suffix in ("pdf", "png"):
        fig.savefig(PAPER / f"figure2_access_effects.{suffix}", dpi=220, facecolor="white")
    plt.close(fig)
    with (PAPER / "figure2_access_effects.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provenance = {"sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (EVIDENCE, CONTROL)},
                  "intervals": "percentile 95% bootstrap over questions; 50000 draws; both seeds retained",
                  "scope": "Qwen3-8B Game24: 23 questions; other targets: shared 15-question subset; correct control: matched eight-question subset",
                  "rows": rows}
    (PAPER / "figure2_access_effects_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
