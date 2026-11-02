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

## Limitations to be upfront about
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
Python · sentence-transformers (embeddings + cross-encoder reranker) · rank-bm25 (keyword search) · NumPy · NCBI E-utilities (PubMed Central) · Anthropic API (Claude) · Streamlit · Hugging Face Spaces
