"""Conceptual replication of Campos V.M. et al. 2025, Am J Addict 35(3):362-369, doi:10.1111/ajad.70101.

Original: 50 opioid use disorder (OUD) FAQs from U.S. health organizations (agencies, academic medical centers,
professional societies), each question entered into ChatGPT (GPT-4o); the official answer and the chatbot answer
compared pairwise on:
  - word count, sentence count, lexical density, characters per word, syllables per word, words per sentence
  - six readability indices: Coleman-Liau, Gunning Fog, SMOG, Flesch-Kincaid Grade, Automated Readability Index,
    Flesch Reading Ease
  - stigmatizing terms (NIDA "Words Matter"), per answer
  - paired t tests or Wilcoxon signed-rank tests
Their results: ChatGPT 253.7 vs FAQ 76.6 words; every grade-level index ~3-4 grades higher; Flesch Reading Ease
-20.4; stigma terms 0.98 vs 0.28 per answer (not significant).

What we copy exactly: the comparison design, all the outcome measures, and the statistics.
What we could not copy: their 50 FAQs (not published). faqs.csv is rebuilt from the same kinds of sources
(verbatim official Q&As, mostly U.S. federal agencies), so the official-answer side is real text, not AI-written.

Conditions (the person types the question with no system prompt, as in ChatGPT):
  - claude-sonnet-5-5 (Claude.ai's default model class) and claude-haiku-5-5, and claude-opus-5-5 if --models given
  - EXTENSION (not in Campos): Sonnet with a plain-language instruction, testing the authors' own recommendation
    ("the need for plain language prompting").

Usage:
  python replications/campos2025/run.py --limit 3
  python replications/campos2025/run.py
"""
import argparse
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import textstat
from scipy import stats
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from eval.stigma_terms import find as stigma_find  # noqa: E402
from eval.stigma_terms import score as stigma_score  # noqa: E402
from src import costs  # noqa: E402
from src.llm import ask  # noqa: E402

CACHE = HERE / "cache.jsonl"
OUT = HERE / "results"
PLAIN = ("Answer in plain language that a person with a 6th-8th grade reading level can understand: short sentences, "
         "common words, and no jargon. Keep it brief.")
ARMS = {  # name: (model, system prompt)
    "claude-sonnet-5-5": ("claude-sonnet-5-5", ""),
    "claude-haiku-5-5": ("claude-haiku-5-5", ""),
    "claude-opus-5-5": ("claude-opus-5-5", ""),
    "sonnet_plain_language": ("claude-sonnet-5-5", PLAIN),
}
_lock = threading.Lock()


def key(arm, q):
    m, s = ARMS[arm]
    return hashlib.sha256(json.dumps([m, s, q]).encode()).hexdigest()[:16]


def read_cache():
    if not CACHE.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines())}


def run(faqs, arms, workers):
    cache = read_cache()
    jobs = [(a, r) for a in arms for r in faqs.itertuples() if key(a, r.question) not in cache]
    est = {"claude-haiku-5-5": 0.002, "claude-sonnet-5-5": 0.012, "claude-opus-5-5": 0.03}
    proj = sum(est[ARMS[a][0]] for a, _ in jobs)
    print(f"{len(jobs)} replies to generate (projection ${proj:.2f}); spent ${costs.spent():.2f}")
    costs.check(proj)

    def one(a, r):
        m, s = ARMS[a]
        text = ask(s, r.question, m, phase=f"campos2025:{a}", max_tokens=8000)
        with _lock, CACHE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(key=key(a, r.question), arm=a, id=r.id, response=text), ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(workers) as ex:
        for i, fu in enumerate(as_completed([ex.submit(one, *j) for j in jobs]), 1):
            fu.result()
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)} spent ${costs.spent():.2f}", flush=True)


def plain(text, split_lines=True):
    """Markdown -> plain prose so formatting symbols don't distort readability formulas."""
    t = re.sub(r"`{1,3}[^`]*`{1,3}", " ", text)
    t = re.sub(r"^\s*#+\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)
    t = re.sub(r"[*_|>]+", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # a line without end punctuation (heading, bullet) is its own sentence
    if split_lines:
        t = "\n".join(ln.strip() + ("" if re.search(r"[.!?:]$", ln.strip()) else ".")
                      for ln in t.splitlines() if ln.strip())
    return re.sub(r"\s+", " ", t).strip()


def measures(text, question="", split_lines=True):
    t = plain(text, split_lines)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", t)
    n = max(len(words), 1)
    sents = max(textstat.sentence_count(t), 1)
    content = [w for w in words if w.lower() not in ENGLISH_STOP_WORDS]
    s = stigma_score(text, question)
    sentences = re.split(r"(?<=[.!?])\s+", t)
    return dict(
        words=len(words), sentences=sents, words_per_sentence=len(words) / sents,
        lexical_density=100 * len(content) / n,  # % content words (stop-word approximation; see README)
        chars_per_word=sum(len(w) for w in words) / n,
        syllables_per_word=textstat.syllable_count(t) / n,
        coleman_liau=textstat.coleman_liau_index(t), gunning_fog=textstat.gunning_fog(t), smog=textstat.smog_index(t),
        flesch_kincaid=textstat.flesch_kincaid_grade(t), ari=textstat.automated_readability_index(t),
        flesch_reading_ease=textstat.flesch_reading_ease(t),
        stigma_terms=s["stigma_unprompted"],
        pct_sentences_stigma=100 * np.mean([bool(stigma_find(x)) for x in sentences]) if sentences else 0.0,
        stigma_detail=s["stigma_terms"])


MEASURES = ["words", "sentences", "lexical_density", "chars_per_word", "syllables_per_word", "words_per_sentence",
            "coleman_liau", "gunning_fog", "smog", "flesch_kincaid", "ari", "flesch_reading_ease", "stigma_terms",
            "pct_sentences_stigma"]
CAMPOS_DIFF = {"words": 177.1, "sentences": 9.2, "lexical_density": 6.5, "chars_per_word": 0.55,
               "syllables_per_word": 0.19, "coleman_liau": 3.43, "gunning_fog": 3.47, "smog": 2.96,
               "flesch_kincaid": 3.61, "ari": 4.33, "flesch_reading_ease": -20.4, "stigma_terms": 0.70,
               "pct_sentences_stigma": 3.57}


def paired_test(a, b):
    """Campos: paired t test, or Wilcoxon signed-rank when the differences aren't normal (Shapiro-Wilk p < .05)."""
    d = np.asarray(a) - np.asarray(b)
    if np.allclose(d, 0):
        return "none", 1.0
    if len(d) >= 3 and stats.shapiro(d).pvalue >= 0.05:
        return "paired t", stats.ttest_rel(a, b).pvalue
    return "Wilcoxon", stats.wilcoxon(a, b).pvalue


def analyze(faqs, arms):
    cache = read_cache()
    rows = []
    for r in faqs.itertuples():
        rows.append(dict(id=r.id, source="official_faq", **measures(r.answer, r.question)))
        for a in arms:
            x = cache.get(key(a, r.question))
            if x:
                rows.append(dict(id=r.id, source=a, **measures(x["response"], r.question)))
    d = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "measures.csv", index=False)

    out = []
    faq = d[d.source == "official_faq"].set_index("id")
    for a in arms:
        ai = d[d.source == a].set_index("id")
        ids = faq.index.intersection(ai.index)
        if not len(ids):
            continue
        for m in MEASURES:
            x, y = ai.loc[ids, m].astype(float), faq.loc[ids, m].astype(float)
            diff = x - y
            rng = np.random.default_rng(0)
            bs = [rng.choice(diff.values, len(diff)).mean() for _ in range(2000)]
            test, p = paired_test(x.values, y.values)
            out.append(dict(arm=a, measure=m, n_pairs=len(ids), claude_mean=x.mean(), faq_mean=y.mean(),
                            diff=diff.mean(), diff_lo=np.percentile(bs, 2.5), diff_hi=np.percentile(bs, 97.5),
                            test=test, p=p, campos_chatgpt_diff=CAMPOS_DIFF.get(m)))
    t = pd.DataFrame(out)
    t.to_csv(OUT / "table_paired_differences.csv", index=False)

    # Sensitivity: bullets/headings NOT treated as separate sentences (they run on into the next line).
    # Readability formulas reward short sentences, so this shows how much the main result depends on that rule.
    sens = []
    idx = ["coleman_liau", "gunning_fog", "smog", "flesch_kincaid", "ari", "flesch_reading_ease", "words_per_sentence"]
    for a in arms:
        for r in faqs.itertuples():
            x = cache.get(key(a, r.question))
            if x:
                mo, ma = measures(r.answer, split_lines=False), measures(x["response"], split_lines=False)
                sens.append(dict(arm=a, id=r.id, **{f"{m}_diff": ma[m] - mo[m] for m in idx}))
    if sens:
        st = pd.DataFrame(sens).groupby("arm")[[f"{m}_diff" for m in idx]].mean().reset_index()
        st.to_csv(OUT / "table_sensitivity_no_line_split.csv", index=False)
        print("\nSensitivity (bullets not split into sentences), mean Claude minus FAQ:")
        print(st.round(2).to_string(index=False))
    print(t.round(3).to_string(index=False))
    return d, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["claude-sonnet-5-5", "claude-haiku-5-5", "sonnet_plain_language"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--analyze-only", action="store_true")
    a = ap.parse_args()
    faqs = pd.read_csv(HERE / "faqs.csv")
    if a.limit:
        faqs = faqs.head(a.limit)
    if not a.analyze_only:
        run(faqs, a.arms, a.workers)
    analyze(faqs, a.arms)
    print(f"Spent so far ${costs.spent():.2f}")


if __name__ == "__main__":
    main()
