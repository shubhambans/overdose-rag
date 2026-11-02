# How this works (and why it's built this way)

## The one-sentence version
It's a **retrieval-augmented generation (RAG)** system: instead of trusting what an LLM "remembers," it first looks up relevant passages from official guidance and peer-reviewed research, then makes the model answer *only* from those passages and cite them. A built-in experiment measures whether that actually beats the same model answering from memory.

## Why RAG and not just ask ChatGPT/Claude?
- **Grounding:** LLMs can state outdated or made-up clinical facts with confidence. Forcing answers to come from SAMHSA/CDC/ASAM text and published studies cuts that risk, and every claim is traceable.
- **Updatable:** when guidance changes, you swap a document and re-run one script. No retraining.
- **Cheaper than fine-tuning:** fine-tuning teaches a model *style*, not reliable *facts*, and needs hundreds of labeled examples and a GPU.
- **But it's a hypothesis, not a given:** strong models already know a lot. That's why the project tests RAG vs. no-RAG instead of assuming RAG wins (step 8).

## The pipeline, step by step

### 1. Sources: two collections
**Guidance (`docs/`, 7 documents):** SAMHSA Overdose Prevention & Response Toolkit (2023), ASAM National Practice Guideline for OUD (2020), 4 CDC Stop Overdose pages, WA DOH naloxone page.

**Research (`papers/papers.csv`, 26 papers; 24 downloaded, 21 as full text):** peer-reviewed work on how clinicians talk to and treat people who use drugs, in three groups:
- *Stigma & language* (11): e.g. what people who use heroin want to be called; a randomized study showing stigmatizing chart notes make the next doctor treat pain less aggressively; how often stigmatizing language appears in hospital notes.
- *Patient experience* (8): qualitative studies of ED care, inpatient withdrawal, naloxone in the ED, opioid substitution treatment.
- *Clinician side* (7): harm-reduction clinics, motivational interviewing, peer support, the 2024 Canadian OUD guideline.

*How papers get in:* the repo stores only the **list** of papers. `src/fetch_papers.py` downloads each one's full text from PubMed Central's free API (NCBI E-utilities) and strips out references. *Why:* the GitHub repo is public, and most papers can't be redistributed even when they're free to read. This also scales: to add 500 papers, add 500 rows.

### 2. Chunk (`src/ingest.py`)
Each document is split into ~250-word pieces with a 50-word overlap, tagged with source, page, title, and collection (guidance vs. research). 950 chunks total.
*Why chunk:* you can't send 90,000 words with every question; small chunks let you retrieve just what's needed. *Why overlap:* so a sentence that straddles a boundary still appears whole somewhere.

### 3. Embed (`src/ingest.py`)
Each chunk becomes a 384-number vector (`all-MiniLM-L6-v2`, a small open-source model). Texts with similar meaning get similar vectors. No vector database needed at this size; a NumPy array works.

### 4. Retrieve (`src/rag.py`): built up in stages, each justified by a measured failure
1. **Semantic search:** find chunks whose vectors are closest to the question's. Good at paraphrase.
2. **+ Keyword search (BM25):** classic search-engine ranking on exact words. Added because semantic search missed "What is the recovery position?" and returned chunks about addiction *recovery* instead.
3. **Hybrid:** merge both rankings with reciprocal rank fusion (a chunk scores well if *either* method ranks it high).
4. **+ Reranker:** take the hybrid top 20 and re-score each with a cross-encoder (`ms-marco-MiniLM-L-6-v2`), a model that reads the question and passage *together*. Slower but more precise than comparing two pre-computed vectors, so it's only run on 20 candidates. Added because once the papers went in, the "recovery" problem came back: semantic search outvoted keyword search.

| Search mode | right source in top 5 | right source ranked #1 | MRR |
|---|---|---|---|
| Semantic only | 97% | 77% | 0.84 |
| Keyword only | 97% | 87% | 0.91 |
| Hybrid | 97% | 94% | 0.95 |
| **Hybrid + rerank (default)** | **100%** | **94%** | **0.97** |

*31 test questions. MRR (mean reciprocal rank) = 1 if the right source is always #1, 0.5 if always #2, etc.*

### 5. Generate (`src/rag.py`)
The top 5 chunks are numbered [1]–[5] and sent to Claude with rules: answer only from these excerpts; cite every claim; if a claim comes from one study, say so rather than presenting it as settled guidance; say "not in the sources" when it isn't; for an active overdose, lead with 911 + naloxone.

### 6. Interface (`app.py`)
Streamlit page: ask a question, see the cited answer and the exact excerpts. A **compare toggle** shows the RAG answer next to the same model answering without sources.

### 7. Retrieval eval (`eval/run_eval.py`, free, no API key)
31 questions (20 overdose/treatment, 10 clinician communication, 1 emergency), each labeled with which source(s) contain the answer. Produces the table above.

### 8. RAG vs. no-RAG experiment (`eval/compare.py`)
For each question and each model:
- **rag:** retrieve, then answer from excerpts.
- **no_rag:** same model, same question, answering from memory.

A separate judge model (Claude Opus) grades every answer against a written **answer key** (key points drawn from the source documents):
- **Coverage:** share of key points the answer gets right (covered = 1, partial = 0.5).
- **Errors:** does it state anything wrong or unsafe?
- **Faithfulness** (RAG only): is every claim actually supported by the excerpts it was given? (Catches the model sneaking in outside knowledge or misreading a source.)
- **Safety** (emergency question): does it say 911 + naloxone first?

*Design choices to defend:*
- **Blinding:** citation tags like [2] are stripped before grading, so the judge can't tell which system wrote the answer.
- **Different judge model** from the answering model, to reduce a model grading its own style favorably.
- **One trap question** (Washington's Good Samaritan law) whose answer is *not* in the corpus: tests whether RAG admits the gap, and shows the real tradeoff that no-RAG may get it right from memory.
- **Caching:** every answer and grade is saved, so re-runs only pay for new work.
- **Multiple models:** `--models claude-sonnet-5-5,claude-haiku-5-5` tests the hypothesis that RAG helps smaller models more.

### 9. Which AI model (`src/llm.py`)
One function, `ask()`, sends a prompt to either Claude (paid API) or Gemini (free tier), based on which key is in `.env`. For Gemini it asks Google which models the key can use, test-pings them newest-first, and uses the first that responds (new models are often "overloaded" on the free tier). It spaces out requests to stay under the per-minute limit, waits and retries when Google says "busy" or "slow down," and stops cleanly when the daily limit (about 20 requests per model) runs out. Answers come from Gemini Flash; grading uses a Flash-Lite model, so the judge is a different model and the two use separate daily limits.

### Pilot result (Gemini 3.5 Flash, judged by Gemini 3.1 Flash-Lite, first 6 questions)
| | Coverage of answer key | Errors | Faithful to sources |
|---|---|---|---|
| Without sources | 94% | 0/6 | – |
| With sources (RAG) | 82% | 0/6 | 6/6 |

*What happened:* on basic overdose questions, a strong model already knows the answers. RAG lost points mainly on "How do you give nasal naloxone?": the documents don't contain step-by-step nozzle instructions (the SAMHSA toolkit points to the product label), so RAG correctly said so and stopped, while the model answered fully from memory. This shows RAG is only as good as its library, and that the answer key should be checked against what the sources actually contain. Six questions is a pilot, not a result; the full 31-question run is the real test, and the communication/research questions are where RAG should matter most.

## Tone study (Study 1): how does the AI *talk* to people who use drugs?
Accuracy turned out to be mostly solved, so the question moved to tone: empathy, pushiness, moralizing, stigma
and over-caution. Full results are in `results/RESULTS.md`; every deviation from the plan is in
`results/decisions.md`.

1. **Messages (`eval/make_tone_messages.py` → `eval/tone_messages.csv`).**
   - 10 scenarios × 6 substances = 60 texting-style messages. Examples: relapse after 7 months, a near-overdose
     after mixing, a parent whose husband says "kick him out".
   - Same scenario, different substance, so any difference between substances isn't caused by a different
     story.
   - AI-written for now and labeled as such; Shubham reviews and edits them.
2. **Three conditions (`eval/tone_run.py`).** Claude Sonnet 5.5 answers each message:
   - plain ("You are a helpful assistant");
   - with RAG excerpts from our corpus;
   - with an MI/harm-reduction system prompt.
   - Replies are cached, so a re-run only pays for changed messages.
3. **Rubric (`eval/tone_rubric.md`).**
   - Adapted from the MITI 4.2.1, the standard tool for rating motivational-interviewing quality, plus
     TIP 35 and harm-reduction papers.
   - Five 1–5 scores (empathy, autonomy, non-judgment, harm reduction, helpfulness), over-caution yes/no, and
     MITI behavior codes such as "persuade without permission".
   - The plain-language cheat sheet is `eval/scoring_cheatsheet.html`.
4. **Judge (`eval/tone_judge.py`).**
   - Claude Opus 5.5 scores each reply. It is blinded (never told the condition), sees replies in shuffled
     order, and writes its reason before each score.
   - **Why a different model:** a model judging its own output tends to favor it.
5. **Stigma counter (`eval/stigma_terms.py`, no AI).**
   - Counts NIDA *Words Matter* terms. A term the sender used first doesn't count (mirroring rule).
   - A term the reply only *mentions* doesn't count either, e.g. *avoid labels like "addict"*.
   - That second rule was added after the first count wrongly showed RAG tripling stigma (decisions #13).
     Always read the hits.
6. **Is the judge any good? (`eval/judge_validation.py`, `eval/compute_agreement.py`)**
   - On real counseling transcripts that experts labeled high or low MI quality (AnnoMI), the judge separates
     them with AUC 0.98.
   - Shubham also scores 30 replies blind, and weighted kappa measures agreement with the judge.
7. **Statistics (`eval/tone_analysis.py`).**
   - Every message is answered under all three conditions, so each message is compared with itself (paired
     tests: Wilcoxon, McNemar).
   - Confidence intervals are bootstrapped over messages.
   - Holm correction is applied because 5 dimensions are tested at once.
   - Figures go in `figures/`.

**Main results (preliminary, AI-written messages):**
- Default Claude was already good (a ceiling effect).
- The MI prompt helped most, especially autonomy: +0.6, and "pushing treatment unasked" dropped from 13% to 0%.
- RAG helped a little.
- Stigmatizing words were rare (0–3%).
- Over-caution: 0/180.

**Study 2A (`study2/`):** can masked message wording reveal the substance? So far only a pipeline check on our
own templates, not a finding. Real data needs Erowid's permission. There is a dual-use risk, so nothing that
profiles people gets built.

## Limitations to be upfront about
- Tone study: AI-written messages; the judge is the same vendor as the model; rubric, RAG corpus and MI prompt
  share sources (circularity); one reply per message. See `results/RESULTS.md`.
- 31 questions is small; the answer key was written by one person; an LLM judge is not a clinician. Next step: have a clinician grade a sample to check the judge agrees.
- Only CC-licensed or PMC-available papers are included, which skews toward open-access journals.
- ASAM is 396 of 950 chunks; a large document can crowd results (the reranker helps).

## Likely questions and short answers
- **"Why not fine-tune?"** Fine-tuning changes how a model talks, not what it reliably knows. Retrieval + citation is more accurate, cheaper, and updatable, and the experiment tests whether it even beats no retrieval.
- **"How do you know it works?"** Two levels: retrieval metrics (does it find the right source?) and answer grading against a key, with RAG vs. no-RAG as the comparison.
- **"How do you stop hallucination?"** Answers only from retrieved excerpts, with citations; a faithfulness check flags any claim not supported by them.
- **"Why a reranker?"** Fast search finds candidates; a slower, more accurate model orders them. It fixed a failure the eval caught.
- **"How would you scale the data?"** Add rows to `papers.csv` (or generate them from a PubMed search); the fetcher and indexer handle the rest. Past ~10k chunks, move to a vector database.

## Stack
Python · sentence-transformers (embeddings + cross-encoder reranker) · rank-bm25 (keyword search) · NumPy · NCBI E-utilities (PubMed Central) · Anthropic API (Claude) / Google Gemini API · Streamlit · Hugging Face Spaces
