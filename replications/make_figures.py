"""Figures for the replications (fig9, fig10). Reads each replication's results; no API calls.

  fig9_hripbench_safety: safety-boundary accuracy, Claude vs the 11 models in HRIPBench (Instruction condition)
                         + direction of Claude's errors (over-cautious vs risky)
  fig10_wang_replication: % replies with stigmatizing language, native vs engineered, Claude vs Wang et al. 2025
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval import figstyle as fs  # noqa: E402

# HRIPBench Table 4, Instruction column (Wang K. et al. 2025, arXiv 2507.21815)
PAPER_SAFETY = {"GPT-4.1": 88.0, "GPT-4o-mini": 88.4, "o4-mini": 88.8, "o3-mini": 87.7, "HuatuoGPT-70B": 88.2,
                "OpenBio-70B": 59.0, "DeepSeek-R1-70B": 88.0, "LLaMA-3.3-70B": 86.3, "Phi-3.5-MoE": 86.9,
                "Qwen-3-32B": 81.7, "Gemma-3-27B": 83.4}
CLAUDE = {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5",
          "claude-opus-5-5": "Claude Opus 5.5"}
CLAUDE_COLOR = fs.COLOR["default"]


def fig9():
    s = pd.read_csv(ROOT / "replications/hripbench/results/predictions.csv")
    a = s[(s.task == "safety") & s.answered]
    acc = a.groupby("model").correct.mean() * 100
    fig, (ax, bx) = fs.plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.15, 1]})
    rows = sorted([(v, k, False) for k, v in PAPER_SAFETY.items()] + [(acc[m], CLAUDE[m], True) for m in acc.index])
    for i, (v, name, is_c) in enumerate(rows):
        ax.plot([50, v], [i, i], color=fs.GRID if not is_c else CLAUDE_COLOR, lw=1.5, zorder=1)
        ax.scatter(v, i, s=70 if is_c else 45, color=CLAUDE_COLOR if is_c else fs.MUTED, zorder=2,
                   edgecolor=fs.SURFACE, linewidth=1.5)
        ax.text(v + 0.6, i, f"{v:.1f}", va="center", fontsize=8.5, color=fs.INK if is_c else fs.INK2)
    ax.set_yticks(range(len(rows)), [r[1] for r in rows])
    for lab, r in zip(ax.get_yticklabels(), rows):
        if r[2]:
            lab.set_fontweight("bold")
    ax.set_xlim(50, 95)
    ax.set_xlabel("Safety-boundary accuracy (%), 1,638 yes/no questions")
    ax.grid(axis="y", visible=False)
    ax.set_title("Claude vs the 11 models in the HRIPBench paper", fontsize=11)

    # Error direction on "Is it safe to...?" questions
    sb = a[a.question_type == "safe_boundary"]
    models = [m for m in CLAUDE if m in set(sb.model)]
    over = [((sb.model == m) & (sb.truth_label == "Yes") & (sb.pred_label == "No")).sum() for m in models]
    risky = [((sb.model == m) & (sb.truth_label == "No") & (sb.pred_label == "Yes")).sum() for m in models]
    n_yes = [((sb.model == m) & (sb.truth_label == "Yes")).sum() for m in models]
    n_no = [((sb.model == m) & (sb.truth_label == "No")).sum() for m in models]
    x = np.arange(len(models))
    bx.bar(x - 0.18, [100 * o / n for o, n in zip(over, n_yes)], 0.34, color=fs.COLOR["rag"], label="Said 'not safe' when the source said safe")
    bx.bar(x + 0.18, [100 * r / n for r, n in zip(risky, n_no)], 0.34, color=fs.COLOR["mi_prompt"], label="Said 'safe' when the source said not safe")
    for i in range(len(models)):
        bx.text(i - 0.18, 100 * over[i] / n_yes[i] + 1.5, f"{over[i]}/{n_yes[i]}", ha="center", fontsize=8.5, color=fs.INK2)
        bx.text(i + 0.18, 100 * risky[i] / n_no[i] + 1.5, f"{risky[i]}/{n_no[i]}", ha="center", fontsize=8.5, color=fs.INK2)
    bx.set_xticks(x, [CLAUDE[m] for m in models])
    bx.set_ylabel("% of questions of that kind")
    bx.set_ylim(0, 80)
    bx.legend(fontsize=8.5, loc="upper right", frameon=False)
    bx.grid(axis="x", visible=False)
    bx.set_title("Which way Claude errs on 'Is it safe to...?'", fontsize=11)
    fig.suptitle("HRIPBench replication: Claude is as accurate as the paper's best models, and errs toward caution",
                 x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fs.save(fig, "fig9_hripbench_safety",
            "Instruction condition, the paper's verbatim system prompt. Paper values from its Table 4 (models from 2024-25). "
            "Some 'errors' are answer-key problems (e.g. the key says methadone in pregnancy is not safe); see replications/hripbench/README.md.")


def fig10():
    d = pd.read_csv(ROOT / "replications/wang2025/results/scored.csv")
    fig, ax = fs.plt.subplots(figsize=(8.5, 4.8))
    groups = [("Wang et al. 2025\n(14 LLMs, 2024)", 35.4, 6.3, fs.MUTED)]
    for m in CLAUDE:
        x = d[d.model == m]
        if len(x):
            groups.append((CLAUDE[m], 100 * x[x.condition == "native"].any_sl_adj.mean(),
                           100 * x[x.condition == "engineered"].any_sl_adj.mean(), CLAUDE_COLOR))
    for i, (name, nat, eng, col) in enumerate(groups):
        ax.plot([i, i], [eng, nat], color=col, lw=2, zorder=1)
        ax.scatter(i, nat, s=70, marker="o", color=col, zorder=2, edgecolor=fs.SURFACE, linewidth=1.5)
        ax.scatter(i, eng, s=70, marker="D", color=col, zorder=2, edgecolor=fs.SURFACE, linewidth=1.5)
        ax.text(i + 0.08, nat, f"{nat:.1f}%", va="center", fontsize=9, color=fs.INK)
        ax.text(i + 0.08, eng, f"{eng:.1f}%", va="center", fontsize=9, color=fs.INK2)
    ax.scatter([], [], marker="o", color=fs.INK2, label="Native prompt (question only)")
    ax.scatter([], [], marker="D", color=fs.INK2, label="Engineered prompt (terms to avoid)")
    ax.legend(fontsize=9, loc="upper right", frameon=False)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups])
    ax.set_ylabel("% of replies with stigmatizing language")
    ax.set_ylim(0, 42)
    ax.set_xlim(-0.5, len(groups) - 0.3)
    ax.grid(axis="x", visible=False)
    ax.set_title("Wang et al. 2025 replication: the prompt-engineering effect holds in Claude")
    fs.save(fig, "fig10_wang_replication",
            "Claude: 60 reconstructed questions (20 AUD, 20 ALD, 20 SUD) per model and condition; adjudicated counts. "
            "Most native hits are outdated liver-disease names ('alcoholic hepatitis'). Wang: physician-coded, original questions.")


if __name__ == "__main__":
    fig9()
    fig10()
