"""Study 2A: can the wording of a message reveal which substance the writer uses?

*** PIPELINE CHECK ONLY. NOT A FINDING. ***
The 60 messages were written by AI from 10 templates where ONLY substance-specific details differ.
Any accuracy here measures how much substance information we put into those slots, not how real
people write. Real data (Study 2B) needs Erowid permission or a gated Reddit dataset (see README.md).

Steps:
  1. Mask drug names and slang with [SUBSTANCE] (following Friedman et al. 2023, who removed drug names
     so a classifier can't win on trivial cues). Context words (e.g. "track marks", "nodding out") stay:
     they are exactly what the study asks about.
  2. Baseline: TF-IDF + logistic regression. Cross-validation is GROUPED BY TEMPLATE (5 folds, each
     holding out 2 whole scenarios), so the model is always tested on scenarios it never saw.
     A plain random split would leak: the other 5 versions of the same template would be in training.
  3. LLM zero-shot: claude-haiku-5-5 picks one of the 6 substances or "unsure".
  4. Report accuracy vs chance (1/6 = 16.7%), confusion matrix (figure 8), top predictive words.
"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval import figstyle as fs  # noqa: E402
from src import costs  # noqa: E402
from src.llm import ask  # noqa: E402

HERE = Path(__file__).parent
MESSAGES = ROOT / "eval" / "tone_messages.csv"
SUBS = ["alcohol", "cannabis", "cocaine", "methamphetamine", "heroin_fentanyl", "benzodiazepines"]
CAVEAT = "PIPELINE CHECK on 60 AI-written template messages. Not a finding about real people's writing."

# Drug names and slang -> [SUBSTANCE]. Longest patterns first.
MASK = [
    r"blood alcohol", r"fentanyl", r"\bfent\b", r"heroin", r"\bdope\b", r"cocaine", r"\bcoke(?:head)?\b",
    r"\bcrack\b", r"\bmeth\b", r"crystal(?: looking stuff)?", r"\btweaker\b", r"\bxanax\b", r"\bbars?\b",
    r"\bbenzos?\b", r"\bpillhead\b", r"\bweed\b", r"cannabis", r"marijuana", r"\bdabs?\b", r"\bcarts?\b",
    r"\bedibles?\b", r"\bstoner\b", r"\bvodka\b", r"\bbeers?\b", r"\balcohol\b", r"\bbooze\b", r"\bjunkie\b",
    r"\bdrunk\b", r"\bnarcan\b",
]


def mask(text: str) -> str:
    for p in MASK:
        text = re.sub(p, "[SUBSTANCE]", text, flags=re.I)
    return text


def baseline(df):
    X, y, groups = df.masked.values, df.substance.values, df.template_id.values
    pred = np.empty(len(df), dtype=object)
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        clf = LogisticRegression(max_iter=2000, C=5)
        clf.fit(vec.fit_transform(X[tr]), y[tr])
        pred[te] = clf.predict(vec.transform(X[te]))
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    clf = LogisticRegression(max_iter=2000, C=5).fit(vec.fit_transform(X), y)
    vocab = np.array(vec.get_feature_names_out())
    top = {c: list(vocab[np.argsort(-clf.coef_[i])[:6]]) for i, c in enumerate(clf.classes_)}
    return pred, top


LLM_PROMPT = """Here is a message someone sent to a chatbot. Drug names have been replaced with [SUBSTANCE]. \
Based on the details, which substance is the writer (or the person they're writing about) most likely using?
Answer with exactly one of: alcohol, cannabis, cocaine, methamphetamine, heroin_fentanyl, benzodiazepines, unsure.

Message:
{text}"""


def llm(df):
    cache_f = HERE / "llm_cache.jsonl"
    cache = {}
    if cache_f.exists():
        cache = {r["masked"]: r["answer"] for r in map(json.loads, cache_f.read_text(encoding="utf-8").splitlines())}
    out = []
    with cache_f.open("a", encoding="utf-8") as f:
        for t in df.masked:
            if t not in cache:
                a = ask("Answer with one label only.", LLM_PROMPT.format(text=t), "claude-haiku-5-5",
                        phase="study2_llm", effort="low", max_tokens=1000).strip().lower()
                a = next((s for s in SUBS + ["unsure"] if s in a), "unsure")
                cache[t] = a
                f.write(json.dumps({"masked": t, "answer": a}) + "\n")
            out.append(cache[t])
    return np.array(out)


def plot(cms, accs):
    fig, axes = fs.plt.subplots(1, 2, figsize=(11, 5))
    labels = [fs.SUB_LABEL[s] for s in SUBS]
    for ax, (name, cm), acc in zip(axes, cms.items(), accs):
        cmn = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
        cmap = fs.SEQ.copy()
        cmap.set_bad(fs.SURFACE)
        ax.imshow(np.ma.masked_where(cm == 0, cmn), cmap=cmap, vmin=0, vmax=1)
        ax.grid(False)
        cols = cm.shape[1]
        xl = labels + (["Unsure"] if cols == 7 else [])
        ax.set_xticks(range(cols), xl, rotation=40, ha="right")
        ax.set_yticks(range(6), labels)
        for i in range(6):
            for j in range(cols):
                if cm[i, j]:
                    ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=9,
                            color="white" if cmn[i, j] > 0.55 else fs.INK)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True substance")
        ax.set_title(f"{name}\naccuracy {acc:.0%} (chance 17%)", fontsize=10.5)
    fig.suptitle("Study 2A: pipeline check on AI-written messages, not a finding",
                 x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fs.save(fig, "fig8_study2_confusion", CAVEAT + " Drug names masked; classifier cross-validated by held-out scenario.")


def main():
    df = pd.read_csv(MESSAGES)
    df["masked"] = df.text.map(mask)
    pred_b, top = baseline(df)
    proj = costs.projection(60, 150, 200, "claude-haiku-5-5")
    costs.check(proj)
    pred_l = llm(df)
    acc_b, acc_l = accuracy_score(df.substance, pred_b), accuracy_score(df.substance, pred_l)
    df["pred_baseline"], df["pred_llm"] = pred_b, pred_l
    df[["id", "template_id", "substance", "masked", "pred_baseline", "pred_llm"]].to_csv(HERE / "predictions.csv", index=False)
    cms = {"TF-IDF + logistic regression": confusion_matrix(df.substance, pred_b, labels=SUBS),
           "Claude Haiku 5.5, zero-shot": confusion_matrix(df.substance, pred_l, labels=SUBS + ["unsure"])[:6]}
    plot(cms, [acc_b, acc_l])
    with (HERE / "results.md").open("w", encoding="utf-8") as f:
        f.write(f"# Study 2A results (pipeline check, NOT a finding)\n\n{CAVEAT}\n\n")
        f.write("| Method | Accuracy | Chance |\n|---|---|---|\n")
        f.write(f"| TF-IDF + logistic regression (5-fold, grouped by scenario) | {acc_b:.0%} | 17% |\n")
        f.write(f"| Claude Haiku 5.5 zero-shot | {acc_l:.0%} ({(pred_l=='unsure').sum()} 'unsure') | 17% |\n\n")
        f.write("## Top words per substance (baseline, fit on all 60; masked text)\n\n")
        for c, w in top.items():
            f.write(f"- **{c}**: {', '.join(w)}\n")
        f.write("\nThese are the residual cues left after masking, i.e. the substance-specific details we wrote "
                "into the template slots (e.g. 'track marks', 'nodding out', 'up for days'). On real data, "
                "this list is what to inspect for leakage.\n")
    print(f"Baseline accuracy {acc_b:.0%}, Haiku zero-shot {acc_l:.0%} (chance 17%). Spent ${costs.spent():.2f}")
    print("Top words:", json.dumps(top, indent=1))
    print("Masked example:", df.masked.iloc[23])


if __name__ == "__main__":
    main()
