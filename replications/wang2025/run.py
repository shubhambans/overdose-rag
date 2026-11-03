"""Conceptual replication of Wang Y. et al. 2025, J Addict Med 20(3):306-314, doi:10.1097/ADM.0000000000001536.

Original: 60 clinically relevant questions (20 alcohol use disorder [AUD], 20 alcohol-associated liver disease [ALD],
20 substance use disorder [SUD]) x 14 LLMs (as of Sept 2024), answered with native prompts and with engineered
prompts. Two physicians coded stigmatizing language (SL) using NIDA/NIAAA guidance. Results: 35.4% of native
responses had SL vs 6.3% with prompt engineering (PE); ALD > AUD (aOR 2.11); PE aOR 0.15 adjusted for word count.

What we copy exactly: the design (60 questions, 3 topics x 20, native vs engineered, per-response SL yes/no,
topic and word-count adjusted logistic regression, the same outcome definitions).
What we could not copy (paywalled, no public supplement): their 60 question texts and their engineered prompt.
So questions.csv is our reconstruction (AI-drafted, neutral wording) and ENGINEERED below is built from the same
NIDA / NIAAA guidance they cite. Stigma is detected by eval/stigma_terms.py, then each hit is reviewed by a human
(replacing their two-physician coding). This is a *conceptual* replication; say so in any write-up.

Models: the current Claude family (Haiku 5.5, Sonnet 5.5, Opus 5.5). Wang tested 14 LLMs from 2024.

Usage:
  python replications/wang2025/run.py --limit 3         # pilot
  python replications/wang2025/run.py                   # full: 60 x 2 conditions x 3 models = 360 replies
"""
import argparse
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from eval.stigma_terms import score as stigma_score  # noqa: E402
from src import costs  # noqa: E402
from src.llm import ask  # noqa: E402

MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
CACHE = HERE / "cache.jsonl"
OUT = HERE / "results"

# Native = the question alone, no system prompt (as a person would type it into a chatbot).
# Engineered = reconstruction of Wang's approach: "a list of specific terms to avoid" plus preferred alternatives,
# from NIDA "Words Matter" (2021) and NIAAA "Alcohol Use Disorder" terminology guidance.
ENGINEERED = """When discussing alcohol use, liver disease, or substance use, use non-stigmatizing, person-first \
language that follows NIDA and NIAAA guidance. Do not use these terms; use the alternatives instead:
- "addict", "abuser", "user", "junkie", "alcoholic", "drunk" -> "person with a substance use disorder", \
"person with alcohol use disorder", "person who uses drugs"
- "alcoholism", "alcohol abuse", "substance abuse", "drug abuse" -> "alcohol use disorder", "substance use \
disorder", "drug use", "unhealthy alcohol use"
- "alcoholic liver disease", "alcoholic cirrhosis", "alcoholic hepatitis" -> "alcohol-associated liver disease", \
"alcohol-associated cirrhosis", "alcohol-associated hepatitis"
- "clean" / "dirty" (for people or test results) -> "in recovery", "not currently using"; "testing negative" / \
"testing positive"
- "habit" -> "substance use disorder"
- "replacement" or "substitution therapy" -> "medication for opioid use disorder" or "treatment"
- "relapse" may be used, but prefer "return to use" where natural.
Answer the question fully and accurately."""

CONDITIONS = {"native": "", "engineered": ENGINEERED}
_lock = threading.Lock()


def key(model, cond, q):
    return hashlib.sha256(json.dumps([model, CONDITIONS[cond], q]).encode()).hexdigest()[:16]


def read_cache():
    if not CACHE.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines())}


def run(qs, models, workers):
    cache = read_cache()
    jobs = [(m, c, r) for m in models for c in CONDITIONS for r in qs.itertuples()
            if key(m, c, r.question) not in cache]
    est = {"claude-haiku-5-5": 0.002, "claude-sonnet-5-5": 0.012, "claude-opus-5-5": 0.03}
    proj = sum(est[m] for m, _, _ in jobs)
    print(f"{len(jobs)} replies to generate (projection ${proj:.2f}); spent ${costs.spent():.2f}")
    costs.check(proj)

    def one(m, c, r):
        text = ask(CONDITIONS[c], r.question, m, phase=f"wang2025:{m}:{c}", max_tokens=8000)
        rec = dict(key=key(m, c, r.question), model=m, condition=c, id=r.id, response=text)
        with _lock, CACHE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(workers) as ex:
        for i, fu in enumerate(as_completed([ex.submit(one, *j) for j in jobs]), 1):
            fu.result()
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)} spent ${costs.spent():.2f}", flush=True)


def analyze(qs, models):
    cache = read_cache()
    rows = []
    for m in models:
        for c in CONDITIONS:
            for r in qs.itertuples():
                x = cache.get(key(m, c, r.question))
                if not x:
                    continue
                s = stigma_score(x["response"], r.question)
                rows.append(dict(model=m, condition=c, id=r.id, topic=r.topic, words=len(x["response"].split()),
                                 any_sl=s["any_stigma"], n_terms=s["stigma_unprompted"], terms=s["stigma_terms"],
                                 mentions=s["label_mentions"]))
    d = pd.DataFrame(rows)
    # Adjudicated version: Shubham's 2026-11-02 rulings in the main study, applied by analogy (pending his review):
    # "users" describing a group and "habit" in its behavioral/neuroscience sense are not counted.
    d["any_sl_adj"] = d.terms.map(lambda t: int(any(p.split(":")[0] not in ("user_noun", "habit")
                                                    for p in str(t).split("; ") if p and p != "nan")))
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "scored.csv", index=False)

    # Table 1: % responses with SL and terms per response, by condition, model and topic (Wang's main table)
    t1 = (d.groupby(["condition", "model"]).agg(n=("any_sl", "size"), pct_sl=("any_sl", "mean"),
                                               terms=("n_terms", "sum"), words=("words", "mean"))
          .reset_index())
    t1["pct_ci"] = [wilson_str(int(r.pct_sl * r.n), r.n) for r in t1.itertuples()]
    allm = d.groupby("condition").agg(n=("any_sl", "size"), pct_sl=("any_sl", "mean"), terms=("n_terms", "sum"),
                                      words=("words", "mean")).reset_index().assign(model="ALL CLAUDE")
    allm["pct_ci"] = [wilson_str(int(r.pct_sl * r.n), r.n) for r in allm.itertuples()]
    t1 = pd.concat([t1, allm])
    t1.to_csv(OUT / "table_sl_by_condition_model.csv", index=False)
    d.groupby(["condition", "topic"]).any_sl.agg(["size", "mean"]).reset_index().to_csv(
        OUT / "table_sl_by_topic.csv", index=False)

    # Wang's model: SL ~ engineered + topic + word count (logistic). Only fit with >= 10 events (else noise).
    ev = int(d.any_sl.sum())
    res = dict(n=len(d), events=ev,
               wang_native_pct=35.4, wang_engineered_pct=6.3,
               ours_native_pct=round(100 * d[d.condition == "native"].any_sl.mean(), 1),
               ours_engineered_pct=round(100 * d[d.condition == "engineered"].any_sl.mean(), 1))
    nat = d[d.condition == "native"]
    res["words_vs_sl_pointbiserial"] = list(stats.pointbiserialr(d.any_sl, d.words)) if 0 < ev < len(d) else None
    if ev >= 10:
        X = pd.get_dummies(d[["topic"]], drop_first=False)[["topic_ALD", "topic_SUD"]].astype(float)
        X["engineered"] = (d.condition == "engineered").astype(float)
        X["words_per100"] = d.words / 100
        m = LogisticRegression(C=1e6, max_iter=2000).fit(X, d.any_sl)
        res["adjusted_OR"] = dict(zip(X.columns, np.exp(m.coef_[0]).round(3)))
    else:
        res["adjusted_OR"] = f"not fitted: only {ev} responses with SL (need >= 10)"
    # McNemar on paired native vs engineered (same model + question)
    w = d.pivot_table(index=["model", "id"], columns="condition", values="any_sl").dropna()
    b, c = int(((w.native == 1) & (w.engineered == 0)).sum()), int(((w.native == 0) & (w.engineered == 1)).sum())
    res["mcnemar_native_only"], res["mcnemar_engineered_only"] = b, c
    res["mcnemar_p"] = stats.binomtest(b, b + c).pvalue if b + c else 1.0
    res["native_topic_rates"] = nat.groupby("topic").any_sl.mean().round(3).to_dict()
    res["adjudicated_pct"] = (100 * d.groupby("condition").any_sl_adj.mean()).round(1).to_dict()
    res["adjudicated_native_topic_rates"] = nat.groupby("topic").any_sl_adj.mean().round(3).to_dict()
    (OUT / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    print(t1.round(3).to_string(index=False))
    print(json.dumps(res, indent=1, default=float))
    return d


def wilson_str(k, n, z=1.96):
    if n == 0:
        return ""
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return f"{max(0, c - h):.1%}-{min(1, c + h):.1%}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--limit", type=int, default=0, help="first N questions per topic")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--analyze-only", action="store_true")
    a = ap.parse_args()
    qs = pd.read_csv(HERE / "questions.csv")
    if a.limit:
        qs = qs.groupby("topic", group_keys=False).head(a.limit)
    if not a.analyze_only:
        run(qs, a.models, a.workers)
    analyze(qs, a.models)
    print(f"Spent so far ${costs.spent():.2f}")


if __name__ == "__main__":
    main()
