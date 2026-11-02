"""Measure retrieval quality: is a correct source in the top 5 chunks?

Usage: python eval/run_eval.py            # compare semantic / keyword / hybrid (free, no API key)
       python eval/run_eval.py --answers  # also generate Claude answers -> eval/results.csv
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag import answer, retrieve  # noqa: E402

QS = json.loads((Path(__file__).parent / "questions.json").read_text())
MODES = ["semantic", "keyword", "hybrid"]


def is_hit(expected, hits):
    expected = [expected] if isinstance(expected, str) else expected
    return any(e in h["source"].lower() for e in expected for h in hits)


def main():
    totals = {m: 0 for m in MODES}
    rows = []
    for item in QS:
        row = {"question": item["question"], "expected": item["expected_source"]}
        for m in MODES:
            hits = retrieve(item["question"], mode=m)
            ok = is_hit(item["expected_source"], hits)
            totals[m] += ok
            row[m] = ok
        row["hybrid_sources"] = "; ".join(h["source"] for h in retrieve(item["question"]))
        if "--answers" in sys.argv:
            row["answer"] = answer(item["question"])[0]
        rows.append(row)
        print(" ".join("✓" if row[m] else "✗" for m in MODES), item["question"])

    print(f"\nRetrieval hit@5 (n={len(QS)})  [columns above: {' / '.join(MODES)}]")
    for m in MODES:
        print(f"  {m:9s} {totals[m]}/{len(QS)} = {totals[m] / len(QS):.0%}")

    out = Path(__file__).parent / "results.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
