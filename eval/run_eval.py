"""Measure retrieval quality: is a correct source in the top 5 chunks?

Usage: python eval/run_eval.py            # compare search modes (free, no API key)
       python eval/run_eval.py --answers  # also generate Claude answers -> eval/results.csv
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag import answer, retrieve  # noqa: E402

QS = json.loads((Path(__file__).parent / "questions.json").read_text())
MODES = ["semantic", "keyword", "hybrid", "rerank"]


def is_hit(expected, hits):
    expected = [expected] if isinstance(expected, str) else expected
    return any(e.lower() in h["source"].lower() for e in expected for h in hits)


def first_correct_rank(expected, hits):
    """1-based rank of the first chunk from a correct source (None if not in hits)."""
    for rank, h in enumerate(hits, 1):
        if is_hit(expected, [h]):
            return rank
    return None


def main():
    totals = {m: 0 for m in MODES}
    top1 = {m: 0 for m in MODES}
    mrr = {m: 0.0 for m in MODES}
    rows = []
    for item in QS:
        row = {"question": item["question"], "expected": item["expected_source"]}
        for m in MODES:
            hits = retrieve(item["question"], mode=m)
            ok = is_hit(item["expected_source"], hits)
            rank = first_correct_rank(item["expected_source"], hits)
            totals[m] += ok
            top1[m] += rank == 1
            mrr[m] += 1 / rank if rank else 0
            row[m] = ok
        row["hybrid_sources"] = "; ".join(h["source"] for h in retrieve(item["question"]))
        if "--answers" in sys.argv:
            row["answer"] = answer(item["question"])[0]
        rows.append(row)
        print(" ".join("✓" if row[m] else "✗" for m in MODES), item["question"])

    n = len(QS)
    print(f"\nRetrieval quality, n={n} questions  [columns above: {' / '.join(MODES)}]")
    print(f"  {'mode':9s} {'hit@5':>7s} {'hit@1':>7s} {'MRR':>6s}")
    for m in MODES:
        print(f"  {m:9s} {totals[m] / n:7.0%} {top1[m] / n:7.0%} {mrr[m] / n:6.2f}")

    out = Path(__file__).parent / "results.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
