"""Hand-scoring sheet + agreement between Shubham's scores and the AI judge.

1) python eval/compute_agreement.py --make-sheet
   Draws 30 random responses (stratified by condition, 10 each) into eval/hand_scoring_sheet.csv.
   The sheet shows ONLY a random ID, the sender's message, and the reply: no condition, no judge scores.
   The key linking IDs to responses is results/hand_scoring_key.csv. Don't open it until you're done.

2) Fill in the empty columns using eval/tone_rubric.md:
   empathy, autonomy, nonjudgment, harm_reduction, helpfulness (1-5), overcaution (0/1).

3) python eval/compute_agreement.py
   Reports weighted Cohen's kappa (quadratic weights: being off by 2 counts more than off by 1)
   per dimension between you and the judge, plus exact and within-1 agreement. Over-caution
   (yes/no) uses plain Cohen's kappa. Rough guide: <0.40 poor, 0.40-0.60 moderate, 0.60-0.80
   substantial, >0.80 near-perfect.
"""
import argparse
import random
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SHEET = ROOT / "eval" / "hand_scoring_sheet.csv"
KEY = ROOT / "results" / "hand_scoring_key.csv"
JUDGED = ROOT / "results" / "judged.csv"
OUT = ROOT / "results" / "agreement.csv"
DIMS = ["empathy", "autonomy", "nonjudgment", "harm_reduction", "helpfulness"]


def make_sheet(n_per_condition=10):
    from eval.tone_judge import current_responses, strip_tags

    if SHEET.exists() and pd.read_csv(SHEET)[DIMS].notna().any().any():
        raise SystemExit(f"{SHEET} already has scores in it; not overwriting.")
    items = current_responses()
    rng = random.Random(2026)
    picked = []
    for c in ["default", "rag", "mi_prompt"]:
        pool = [i for i in items if i["condition"] == c]
        picked += rng.sample(pool, n_per_condition)
    rng.shuffle(picked)
    ids = rng.sample(range(100, 1000), len(picked))
    sheet = pd.DataFrame([{"item": f"H{i}", "message": p["message"], "reply": strip_tags(p["response"]),
                           **{d: "" for d in DIMS}, "overcaution": "", "notes": ""} for i, p in zip(ids, picked)])
    key = pd.DataFrame([{"item": f"H{i}", "message_id": p["message_id"], "condition": p["condition"]}
                        for i, p in zip(ids, picked)])
    sheet.to_csv(SHEET, index=False, encoding="utf-8-sig")  # utf-8-sig so Excel shows apostrophes correctly
    KEY.parent.mkdir(exist_ok=True)
    key.to_csv(KEY, index=False)
    print(f"Wrote {len(sheet)} items to {SHEET}. Key (don't peek): {KEY}")


def agreement():
    sheet = pd.read_csv(SHEET, encoding="utf-8-sig")
    key = pd.read_csv(KEY)
    judged = pd.read_csv(JUDGED)
    m = sheet.merge(key, on="item").merge(judged, on=["message_id", "condition"], suffixes=("_human", "_judge"))
    rows = []
    for d in DIMS + ["overcaution"]:
        x = m[[f"{d}_human", f"{d}_judge"]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(x) < 5:
            print(f"{d}: only {len(x)} scored items, skipping")
            continue
        h, j = x.iloc[:, 0].astype(int), x.iloc[:, 1].astype(int)
        w = None if d == "overcaution" else "quadratic"
        k = cohen_kappa_score(h, j, weights=w, labels=sorted(set(h) | set(j) | ({0, 1} if w is None else set(range(1, 6)))))
        rows.append(dict(dimension=d, n=len(x), kappa=round(k, 2), kappa_type="unweighted" if w is None else "quadratic-weighted",
                         exact_agreement=round((h == j).mean(), 2), within_1=round(((h - j).abs() <= 1).mean(), 2),
                         human_mean=round(h.mean(), 2), judge_mean=round(j.mean(), 2)))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.to_string(index=False))
    print("\nNote: if everyone scores almost everything 5, kappa can be low even when agreement is high "
          "(little variation to agree on). Report exact/within-1 agreement alongside kappa.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-sheet", action="store_true")
    a = ap.parse_args()
    make_sheet() if a.make_sheet else agreement()
