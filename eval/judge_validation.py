"""Validate the AI judge on expert-labelled MI conversations (AnnoMI).

AnnoMI (Wu et al.) has real counselling transcripts that experts labelled high- or low-quality MI.
If our judge understands the rubric, it should score the counsellor in high-quality transcripts
higher on empathy, autonomy and non-judgment. We report AUC: the chance that a randomly chosen
high-quality transcript outscores a randomly chosen low-quality one (0.5 = coin flip, 1.0 = perfect).
PLAN.md: if AUC < 0.75, say so prominently.

Sample: all 23 low-quality transcripts + 20 high-quality ones, chosen to match topics where possible
and to have similar length (high-quality transcripts are longer on average, and length could
otherwise act as a cue). Each transcript is cut to its first ~1,500 words; MITI itself rates a
segment of a session, not the whole thing.

Output: results/judge_validation.csv. Figure 7 is drawn by eval/tone_analysis.py.
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.tone_judge import JUDGE, JUDGE_SYSTEM, parse_json  # noqa: E402
from src import costs  # noqa: E402
from src.llm import claude_create, text_of  # noqa: E402

DATA = ROOT / "rubric_sources" / "Conversations" / "AnnoMI-full.csv"
OUT = ROOT / "results" / "judge_validation.csv"
CACHE = ROOT / "results" / "judge_validation_cache.jsonl"
MAX_WORDS = 1500
N_HIGH = 20
DIMS = ["empathy", "autonomy", "nonjudgment"]

TASK = """This time you are rating a COUNSELLING CONVERSATION, not a single AI reply. Rate the THERAPIST \
across the whole excerpt on rubric dimensions A (empathy), B (autonomy / partnership) and C \
(non-judgment), using the original MITI 4.2.1 global-score logic quoted in the rubric (start at 3, \
move up or down; overall gestalt). The topic may not be substance use; apply the same principles.

Respond with JSON only:
{"empathy": {"why": "<one sentence>", "score": 1-5},
 "autonomy": {"why": "...", "score": 1-5},
 "nonjudgment": {"why": "...", "score": 1-5}}"""


def transcripts():
    d = pd.read_csv(DATA).drop_duplicates(["transcript_id", "utterance_id"]).sort_values(["transcript_id", "utterance_id"])
    out = []
    for tid, g in d.groupby("transcript_id"):
        lines, words = [], 0
        for _, u in g.iterrows():
            who = "THERAPIST" if u.interlocutor == "therapist" else "CLIENT"
            text = str(u.utterance_text)
            if words + len(text.split()) > MAX_WORDS and lines:
                break
            lines.append(f"{who}: {text}")
            words += len(text.split())
        out.append(dict(transcript_id=tid, mi_quality=g.mi_quality.iloc[0], topic=g.topic.iloc[0],
                        full_words=int(sum(len(str(x).split()) for x in g.utterance_text)),
                        used_words=words, text="\n".join(lines)))
    return pd.DataFrame(out)


def sample(t: pd.DataFrame) -> pd.DataFrame:
    low = t[t.mi_quality == "low"]
    high = t[(t.mi_quality == "high") & (t.full_words <= low.full_words.max())].copy()
    rng = random.Random(7)
    # prefer high-quality transcripts whose topic appears among the low-quality ones
    high["topic_match"] = high.topic.isin(set(low.topic)).astype(int)
    high["r"] = [rng.random() for _ in range(len(high))]
    high = high.sort_values(["topic_match", "r"], ascending=[False, True]).head(N_HIGH)
    return pd.concat([low, high.drop(columns=["topic_match", "r"])]).sample(frac=1, random_state=1)


def main():
    s = sample(transcripts())
    cache = {}
    if CACHE.exists():
        cache = {r["transcript_id"]: r["judgment"] for r in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines())}
    todo = [r for _, r in s.iterrows() if r.transcript_id not in cache]
    proj = len(todo) * costs.price(JUDGE, 2200, 1500, 0, 9000)
    print(f"{len(s)} transcripts ({(s.mi_quality=='high').sum()} high, {(s.mi_quality=='low').sum()} low); "
          f"{len(todo)} to judge, projected ${proj:.2f}. Spent so far ${costs.spent():.2f}")
    costs.check(proj * 0.5)
    system = [{"type": "text", "text": JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}},
              {"type": "text", "text": TASK}]
    with CACHE.open("a", encoding="utf-8") as f:
        for r in todo:
            msg = claude_create(phase="judge_validation", model=JUDGE, max_tokens=6000, system=system,
                                messages=[{"role": "user", "content": f"<transcript>\n{r.text}\n</transcript>"}],
                                output_config={"effort": "medium"})
            try:
                j = parse_json(text_of(msg))
            except Exception as e:
                j = {"error": str(e)}
            cache[r.transcript_id] = j
            f.write(json.dumps({"transcript_id": int(r.transcript_id), "judgment": j}) + "\n")
            f.flush()
            print(f"  transcript {r.transcript_id} ({r.mi_quality}) judged")

    rows = []
    for _, r in s.iterrows():
        j = cache[r.transcript_id]
        row = dict(transcript_id=r.transcript_id, mi_quality=r.mi_quality, topic=r.topic,
                   full_words=r.full_words, used_words=r.used_words)
        for d in DIMS:
            row[d] = j.get(d, {}).get("score")
        rows.append(row)
    v = pd.DataFrame(rows).dropna(subset=DIMS)
    v["relational_mean"] = v[DIMS].mean(axis=1)
    v.to_csv(OUT, index=False)
    y = (v.mi_quality == "high").astype(int)
    print("\nAUC (high vs low MI quality):")
    for d in DIMS + ["relational_mean"]:
        auc = roc_auc_score(y, v[d])
        print(f"  {d:<16} AUC {auc:.2f}   mean high {v[y==1][d].mean():.2f} vs low {v[y==0][d].mean():.2f}"
              + ("   <-- BELOW 0.75: judge NOT reliable on this dimension" if auc < 0.75 else ""))
    print(f"Total spent: ${costs.spent():.2f}")


if __name__ == "__main__":
    main()
