"""Study 1b: the 30 harder messages. Same pipeline as the main study (Sonnet 5.5 x 3 conditions, blinded Opus judge).

Compares conditions within the hard set (paired Wilcoxon, Holm) and the hard set with the main set (same
condition, different messages: Mann-Whitney). Draws fig11. Reads results/judged_hard.csv and results/judged.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval import figstyle as fs  # noqa: E402

RES = ROOT / "results"
DIMS = ["empathy", "autonomy", "nonjudgment", "harm_reduction", "helpfulness"]


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(p) - r) * p[i]))
        adj[i] = run
    return adj


def main():
    h = pd.read_csv(RES / "judged_hard.csv")
    m = pd.read_csv(RES / "judged.csv")
    h["scenario"] = h.template_id.str.replace("h_", "", regex=False)

    means = []
    for name, d in [("main (60 msgs)", m), ("hard (30 msgs)", h)]:
        g = d.groupby("condition")[DIMS + ["overcaution", "any_stigma", "words"]].mean()
        g["set"] = name
        means.append(g.reset_index())
    means = pd.concat(means)
    means.to_csv(RES / "table_hard_vs_main_means.csv", index=False)

    tests = []
    for comp in ["rag", "mi_prompt"]:
        ps, rows = [], []
        for dim in DIMS:
            w = h.pivot_table(index="message_id", columns="condition", values=dim)
            diff = (w[comp] - w["default"]).dropna()
            p = stats.wilcoxon(diff).pvalue if (diff != 0).any() else 1.0
            rows.append(dict(comparison=f"{comp} vs default (hard)", measure=dim, mean_diff=diff.mean(),
                             n_better=int((diff > 0).sum()), n_worse=int((diff < 0).sum()), p=p))
            ps.append(p)
        for r, a in zip(rows, holm(ps)):
            r["p_holm"] = a
        tests += rows
    for c in ["default", "rag", "mi_prompt"]:
        for dim in DIMS:
            x, y = h[h.condition == c][dim], m[m.condition == c][dim]
            tests.append(dict(comparison=f"hard vs main ({c})", measure=dim, mean_diff=x.mean() - y.mean(),
                              p=stats.mannwhitneyu(x, y).pvalue))
    t = pd.DataFrame(tests)
    t.to_csv(RES / "table_hard_tests.csv", index=False)

    sc = h.groupby(["scenario", "condition"])[DIMS + ["overcaution"]].mean().round(2)
    sc.to_csv(RES / "table_hard_by_scenario.csv")
    low = h.assign(minscore=h[DIMS].min(axis=1)).sort_values("minscore").head(10)
    low[["message_id", "condition", "minscore"] + DIMS + ["overcaution", "stigma_terms"]].to_csv(
        RES / "table_hard_lowest.csv", index=False)

    print(means.round(2).to_string(index=False))
    print(t.round(3).to_string(index=False))
    print(sc.to_string())
    fig11(means)


def fig11(means):
    fig, axes = fs.plt.subplots(1, len(DIMS), figsize=(13, 3.8), sharey=True)
    for ax, dim in zip(axes, DIMS):
        for j, c in enumerate(fs.CONDITIONS):
            mm = means.set_index(["set", "condition"])
            a, b = mm.loc[("main (60 msgs)", c), dim], mm.loc[("hard (30 msgs)", c), dim]
            ax.plot([j, j], [a, b], color=fs.COLOR[c], lw=1.5, alpha=0.7)
            ax.scatter(j, a, marker="o", s=40, facecolor=fs.SURFACE, edgecolor=fs.COLOR[c], linewidth=1.5, zorder=3)
            ax.scatter(j, b, marker=fs.MARKER[c], s=55, color=fs.COLOR[c], zorder=3)
        ax.set_xticks(range(3), ["Default", "RAG", "MI"])
        ax.set_title(fs.DIM_LABEL[dim], fontsize=10.5)
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.5, 2.5)
    axes[0].set_ylabel("Mean judge score (1-5)")
    axes[0].scatter([], [], marker="o", facecolor=fs.SURFACE, edgecolor=fs.INK2, label="Main set (60 messages)")
    axes[0].scatter([], [], marker="s", color=fs.INK2, label="Hard set (30 messages)")
    fig.legend(*axes[0].get_legend_handles_labels(), fontsize=9, loc="upper right", ncol=2, frameon=False)
    fig.suptitle("Harder messages: does the ceiling break?", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fs.save(fig, "fig11_hard_vs_main",
            "Hollow = main set, filled = hard set (hostile, not stopping, self-labeling, dosing, emergencies, family "
            "ultimatums, stigma traps). AI-written composite messages. Same Sonnet 5.5 responder and blinded Opus 5.5 judge.")


if __name__ == "__main__":
    main()
