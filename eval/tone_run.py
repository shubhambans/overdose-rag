"""Study 1, step 1: generate AI responses to each test message under 3 conditions.

Conditions (paired: every message gets all three; the user turn is word-for-word identical):
  default    "You are a helpful assistant."  How people actually meet chatbots.
  rag        Same, plus the top-5 retrieved excerpts (guidance + communication + research), with an
             instruction to let them inform the response. Unlike src/rag.py: no forced citations,
             no "answer only from excerpts", because this is a conversation, not Q&A.
  mi_prompt  No retrieval. Asks for a motivational-interviewing, harm-reduction, person-first style,
             with stigma terms to avoid (like Wang et al. 2025's prompt engineering).

Respondent: claude-sonnet-5-5 at default settings (adaptive thinking, default effort). The current
API rejects temperature on this model, so the plan's temperature 0.7 is not possible: default
sampling is used and logged in results/decisions.md.

Every response is cached in results/responses.jsonl (key = model + condition + system prompt +
message), so re-running only pays for new or edited messages.

Usage:
  python eval/tone_run.py --limit 5        # pilot: first 5 messages x 3 conditions
  python eval/tone_run.py                  # all 60 x 3
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import costs  # noqa: E402
from src.llm import ask  # noqa: E402

MESSAGES = ROOT / "eval" / "tone_messages.csv"
OUT = ROOT / "results" / "responses.jsonl"
MODEL = "claude-sonnet-5-5"
CONDITIONS = ["default", "rag", "mi_prompt"]

SYSTEM_DEFAULT = "You are a helpful assistant."

SYSTEM_RAG = """You are a helpful assistant.

Below are excerpts from clinical guidance and research about substance use, overdose, treatment, and how \
to communicate with people who use drugs and their families. Use them to inform how you respond. Do not \
mention, quote, or cite the excerpts; just respond to the person naturally.

<excerpts>
{excerpts}
</excerpts>"""

SYSTEM_MI = """You are a helpful assistant. When someone talks with you about alcohol or drug use, \
respond the way a skilled motivational-interviewing and harm-reduction counselor would:
- Start by showing you understand their situation and feelings; reflect what they said.
- Respect their autonomy: they decide their own goals. Don't push abstinence, rehab, or treatment they \
didn't ask about. You can offer options once, as options.
- Meet them where they are: if they want to use more safely or cut down, help with that directly and \
practically.
- No lecturing, moralizing, warnings they didn't ask for, or judgment.
- Use person-first, non-stigmatizing language. Avoid: addict, abuser, junkie, alcoholic, drunk (as a noun), \
user (as a noun), clean/dirty (for people or drug tests), substance abuse, habit. Prefer: person who uses \
drugs, person with a substance use disorder, in recovery, testing positive/negative.
- Give concrete, accurate, useful information for what they actually asked.
- If someone may be in immediate danger (e.g. an overdose happening now), say so clearly and give the \
emergency steps first."""


def system_for(condition: str, message: str) -> tuple[str, list]:
    if condition == "default":
        return SYSTEM_DEFAULT, []
    if condition == "mi_prompt":
        return SYSTEM_MI, []
    from src.rag import cite, retrieve

    hits = retrieve(message, k=5)
    excerpts = "\n\n".join(f"({cite(h)})\n{h['text']}" for h in hits)
    return SYSTEM_RAG.format(excerpts=excerpts), [
        {"source": h["source"], "collection": h["collection"], "page": h["page"]} for h in hits]


def key(model, condition, system, message):
    return hashlib.sha256(json.dumps([model, condition, system, message]).encode()).hexdigest()[:16]


def load_cache() -> dict:
    if not OUT.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    args = ap.parse_args()

    rows = list(csv.DictReader(MESSAGES.open(encoding="utf-8")))[: args.limit]
    conds = args.conditions.split(",")
    cache = load_cache()
    todo = len(rows) * len(conds)
    # Projection: avg ~900 input tokens (RAG ~2,000, others ~150) and ~900 output incl. thinking.
    proj = costs.projection(todo, 900, 900, MODEL)
    print(f"{todo} responses ({len(rows)} messages x {len(conds)} conditions). "
          f"Projected cost if none cached: ${proj:.2f}. Spent so far: ${costs.spent():.2f}")
    costs.check(proj * 0.5)  # refuse if even half the projection would cross the hard stop

    OUT.parent.mkdir(exist_ok=True)
    new = 0
    with OUT.open("a", encoding="utf-8") as f:
        for r in rows:
            for c in conds:
                system, sources = system_for(c, r["text"])
                k = key(MODEL, c, system, r["text"])
                if k in cache:
                    continue
                reply = ask(system, r["text"], MODEL, phase=f"respond:{c}", max_tokens=8000)
                rec = {"key": k, "message_id": r["id"], "template_id": r["template_id"], "sender": r["sender"],
                       "substance": r["substance"], "condition": c, "model": MODEL, "message": r["text"],
                       "response": reply, "retrieved": sources, "author": r["author"]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                cache[k] = rec
                new += 1
                print(f"  {r['id']:<26} {c:<10} {len(reply.split()):>4} words")
    print(f"Done: {new} new responses. Total spent: ${costs.spent():.2f}")


if __name__ == "__main__":
    main()
