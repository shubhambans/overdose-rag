"""Shared figure style so every figure reads as one system.

Palette: the validated reference categorical palette, first three slots (blue, orange, aqua).
These pass all-pairs colorblind checks (worst CVD Delta E 9.2; normal-vision 24.0). Aqua is below 3:1
contrast on white, so every chart also uses a distinct marker shape per condition and direct labels,
and every number is in a CSV table in results/ (never color alone).
Sequential: one blue hue, light to dark.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

FIG = Path(__file__).resolve().parent.parent / "figures"
FIG.mkdir(exist_ok=True)

CONDITIONS = ["default", "rag", "mi_prompt"]
LABEL = {"default": "Default assistant", "rag": "With guidance (RAG)", "mi_prompt": "MI-style prompt"}
COLOR = {"default": "#2a78d6", "rag": "#eb6834", "mi_prompt": "#1baf7a"}
MARKER = {"default": "o", "rag": "s", "mi_prompt": "D"}
DIM_LABEL = {"empathy": "Empathy", "autonomy": "Autonomy", "nonjudgment": "Non-judgment",
             "harm_reduction": "Harm reduction", "helpfulness": "Helpfulness"}
SUB_LABEL = {"alcohol": "Alcohol", "cannabis": "Cannabis", "cocaine": "Cocaine", "methamphetamine": "Meth",
             "heroin_fentanyl": "Heroin/fentanyl", "benzodiazepines": "Benzos"}
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("blue_seq", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "xtick.color": INK2, "ytick.color": INK2, "legend.frameon": False, "lines.linewidth": 2,
})


def save(fig, name: str, note: str = ""):
    """Save PNG (300 dpi) + SVG. `note` is a small grey caption at the bottom (caveats)."""
    if note:
        fig.text(0.01, -0.01, note, fontsize=7.5, color=INK2, ha="left", va="top", wrap=True)
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved figures/{name}.png/.svg")
