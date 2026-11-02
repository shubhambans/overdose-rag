# CLAUDE.md: context for Claude Code sessions on this project

## Who you're working with
Shubham (repo owner) has a harm-reduction background: he founded a naloxone-distribution nonprofit, worked as a CNA, and did overdose surveillance at a medical examiner's office. He is building technical/AI skills through this project and needs to be able to **explain every step and design choice himself** (interviews, write-ups).
- Explain what you're doing and why in plain language, briefly. Keep replies concise.
- Where it makes sense, let him do pieces himself (writing test messages, hand-scoring, running commands) and review his work, rather than doing everything.
- His domain judgment beats yours on what real messages from people who use drugs sound like and what "good" harm-reduction communication is. Ask him.

## What the project is
A RAG system over overdose/addiction guidance (SAMHSA, CDC, ASAM, WA DOH) plus 24 PubMed Central papers on stigma, patient experience, and clinician communication. Plus evaluation harnesses.

**The research question has shifted (Nov 2026).** Accuracy is mostly solved by modern models. The real question is **how AI responds to people who use drugs and their families**: empathy, pushiness, moralizing, stigmatizing language, harm-reduction stance, over-caution. See "Next: tone study" below.

## Files
| Path | What it does |
|---|---|
| `papers/papers.csv` | List of research papers (PMIDs/PMCIDs). Repo stores the list only; papers aren't redistributed. |
| `src/fetch_papers.py` | Downloads full text from PubMed Central (NCBI E-utilities) into `docs/papers/` (git-ignored). |
| `src/ingest.py` | Chunks all docs (~250 words, 50 overlap), embeds with all-MiniLM-L6-v2, writes `index/`. |
| `src/rag.py` | Retrieval (semantic + BM25 → reciprocal rank fusion → cross-encoder rerank of top 20 → top 5) and answer generation, with and without retrieval. System prompts live here. |
| `src/llm.py` | `ask(system, user, model)` for Claude (API) or Gemini (free tier). Reads keys from `.env`. Gemini: auto-picks a responsive model, throttles, retries 429/503, raises `QuotaExhausted` at the daily limit. |
| `app.py` | Streamlit UI with a RAG vs no-RAG compare toggle. |
| `eval/run_eval.py` | Retrieval eval (hit@5, hit@1, MRR) across 4 search modes. Free, no API key. |
| `eval/questions.json` | 31 factual questions with answer keys (key_points) and expected sources. |
| `eval/compare.py` | Accuracy experiment: RAG vs no-RAG, LLM judge (coverage, errors, faithfulness, safety), citation tags stripped for blinding, cached in `eval/cache/`, resumes after quota stops. |
| `HOW_IT_WORKS.md` | Plain-language explanation of everything, for Shubham. Keep it updated when the design changes. |

## Setup (Windows)
```powershell
pip install -r requirements.txt
python src/fetch_papers.py
python src/ingest.py
python eval/run_eval.py
python src/llm.py      # shows which model will be used + test call
```
API keys go in `.env` in the project root (git-ignored), one per line:
```
ANTHROPIC_API_KEY=...   # Shubham has $100 of Claude Console API credits; preferred
GEMINI_API_KEY=...      # free tier, only ~20 requests/day per model
```
**Important:**
- Never commit `.env`. Before every commit, run `git grep -n "API_KEY="` to check.
- Keep `ANTHROPIC_API_KEY` in `.env` only, NOT as a Windows environment variable. If it's set system-wide, Claude Code itself bills the API instead of the Pro plan.
- When both keys are present, `llm.py` uses Claude by default. Override with `LLM_MODEL=` / `JUDGE_MODEL=` in `.env` or the `--models` / `--judge` flags.

**First task in a new session:** this Desktop folder may not be a git clone yet. If `git status` fails, connect it to `https://github.com/shubhambans/overdose-rag` (`git init`, add remote, `git fetch`, `git reset origin/main`). Don't overwrite local files without checking. `eval/_gemini_run/` is a leftover temp folder from a cloud session and is safe to delete.

## Results so far
- **Retrieval** (31 questions; right source #1 / in top 5): semantic 77%/97%, keyword 87%/97%, hybrid 94%/97%, **hybrid+rerank 94%/100% (MRR 0.97)**. The reranker was added because "recovery position" kept retrieving addiction-*recovery* chunks.
- **Accuracy pilot** (6 questions, Gemini 3.5 Flash answering, Gemini 3.1 Flash-Lite judging): no-RAG 94% coverage vs RAG 82%; 0 errors either way; RAG 6/6 faithful. The gap came mostly from "how to give nasal naloxone": the corpus has no step-by-step nozzle instructions, so RAG correctly declined.
  - Lesson: answer keys must only expect what the corpus contains, or the eval measures corpus coverage instead of RAG.
- **Tone study, first full run (2026-11-02).** Details: `results/RESULTS.md`, deviations: `results/decisions.md`.
  - Design: 60 AI-written messages × 3 conditions; Sonnet 5.5 responds, Opus 5.5 judges (blinded).
  - **Judge validated** on AnnoMI: AUC 0.98.
  - **Ceiling effect:** default replies already score 4–5.
  - **MI prompt:** best on every dimension; autonomy +0.60 (95% CI 0.45 to 0.75); "persuade without
    permission" 13% → 0%.
  - **RAG:** small gains (empathy +0.15, non-judgment +0.15; Holm p < 0.05).
  - **Stigma terms:** 0% / 2% / 0% after Shubham reviewed each hit (eval/stigma_rulings.csv), vs Wang 2025: 35%.
    - The naive counter wrongly counted *advice against labels* as stigma. Fixed with the mention-vs-use
      rule (decisions #13).
  - **Over-caution:** 0/180.
  - **Study 2A:** pipeline check only.
  - **Spend:** $9.27 of $18.
  - **Pending (Shubham):**
    - review and edit the messages, then re-run;
    - hand-score `eval/hand_scoring_sheet.csv`, then run `python eval/compute_agreement.py`;
    - send the Erowid email.
- Gemini free tier: newest Flash models (3.6–3.8) often return 503 "high demand"; 3.5 Flash works but allows only 20 requests/day.

## ▶ CURRENT TASK: execute `PLAN.md`
Shubham's latest decisions:
- Claude API only (budget **$20, hard stop $18**).
- Focus on **RAG grounding vs. default vs. MI-prompt**.
- Add **Study 2**: can message wording reveal the substance?
- Figures go in `figures/`.
- Run autonomously; don't stop to ask unless the action is over budget or destructive.

`PLAN.md` supersedes the older design notes below where they conflict (e.g. no Gemini comparison).

## Earlier design notes: tone study
**Question:** How do AI models respond to people who use drugs and their families: empathy, autonomy vs. pushiness, moralizing, stigma?

**Compare three conditions:**
1. **Models:** Claude (API) and Gemini (free); optionally GPT later, which needs an OpenAI key and an `ask()` provider.
2. **With vs. without RAG:** does grounding in guidance and stigma literature make responses warmer, or more clinical and preachy?
3. **Default vs. MI-instructed:** the same model with a system prompt asking for a motivational-interviewing style.

**Senders:** people who use drugs (active use, not wanting to quit, relapse, safer-use questions, overdose fears, bad ER experiences) and family/friends (parent, partner, roommate, naloxone questions).

**Scoring rubric:** an LLM judge using a rubric adapted from the **MITI 4.2.1** (Motivational Interviewing Treatment Integrity), 1–5 scales with anchors:
- empathy
- autonomy support vs. pushing treatment or abstinence unasked
- moralizing/lecturing
- harm-reduction alignment (meets the person where they are)
- over-caution (refusal, hedging, hotline-dumping instead of helping)
- actionable help

Plus an **automatic stigma-term count** (addict, abuser, junkie, clean/dirty, substance abuse, etc.), grounded in `paper_stigma_PMC6732023` and the stigma papers.

**Build plan:**
1. `eval/tone_messages.json`: about 40 realistic first-person messages. **Shubham should write or edit these**; AI-written ones sound too polished.
2. `eval/tone_rubric.md`: dimensions with score anchors, citing MITI and the stigma papers.
3. `eval/tone_compare.py`: generate responses per model × condition, judge with the rubric, count stigma terms, randomize order and blind the judge to model and condition, cache everything, write CSV and a summary table.
4. **Judge bias:** don't let Claude be the only judge of Claude. Cross-judge (Claude judges Gemini and Gemini judges Claude, or both judge all) and report agreement.
5. **Validation:** Shubham hand-scores about 30 responses blind; compute weighted Cohen's kappa between his scores and the judge's. This is the step reviewers will ask about.
6. Start small (`--limit 5`) and check cost in the Console before full runs.
