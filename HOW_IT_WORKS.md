# How this works (and why it's built this way)

## The one-sentence version
It's a **retrieval-augmented generation (RAG)** system: instead of trusting what an LLM "remembers," it looks up the relevant passages from official guidance first, then makes the model answer *only* from those passages and cite them.

## Why RAG and not just ask ChatGPT/Claude?
- **Grounding:** LLMs can state outdated or made-up clinical facts with confidence. Forcing answers to come from SAMHSA/CDC/ASAM text cuts that risk, and every claim is traceable to a page.
- **Updatable:** when guidance changes, you swap a PDF and re-run one script. No retraining.
- **Cheaper than fine-tuning:** fine-tuning teaches a model *style*, not reliable *facts*, and it needs hundreds of labeled examples and a GPU. RAG needs neither.

## The pipeline, step by step

### 1. Collect sources (`docs/`)
7 public documents: the SAMHSA Overdose Prevention & Response Toolkit (2023), the ASAM National Practice Guideline for OUD (2020 focused update), 4 CDC Stop Overdose pages (fentanyl facts, naloxone, naloxone FAQ, fentanyl test strips), and WA DOH's naloxone page.
*Why these:* they're the authoritative US sources for lay overdose response (SAMHSA, CDC), clinical treatment (ASAM), and Washington-specific access (DOH).

### 2. Chunk (`src/ingest.py`)
Each document is split into ~250-word pieces with a 50-word overlap, tagged with source and page number. Result: 496 chunks.
*Why chunk:* you can't send a 95-page guideline to the model for every question; it's slow, costly, and buries the relevant part. Small chunks let you retrieve just what's needed.
*Why overlap:* so a sentence that straddles a boundary still appears whole in at least one chunk.
*Why keep page numbers:* so every answer can cite "SAMHSA toolkit, p.17."

### 3. Embed (`src/ingest.py`)
Each chunk is turned into a 384-number vector using `all-MiniLM-L6-v2`, a small open-source sentence-embedding model. Texts with similar meaning get similar vectors.
*Why this model:* free, runs on a laptop CPU in seconds, good enough for a few hundred chunks. No vector database needed at this size; a NumPy array is fine.

### 4. Retrieve (`src/rag.py`), hybrid search
When a question comes in, two searches run:
- **Semantic search:** embed the question, find chunks with the closest vectors (cosine similarity). Good at paraphrase ("can't breathe" ≈ "respiratory depression").
- **Keyword search (BM25):** classic search-engine ranking on exact words. Good at specific terms ("xylazine", "recovery position").

The two rankings are merged with **reciprocal rank fusion** (a chunk scores well if either method ranks it high), and the top 5 go forward.
*Why hybrid:* semantic-only search missed "What is the recovery position?" because the ASAM guideline's many uses of "recovery" (as in addiction recovery) looked more similar than SAMHSA's section on the body position. Adding keyword search fixed it. That's a real failure I found through evaluation, not a guess.

### 5. Generate (`src/rag.py`)
The 5 chunks are numbered [1]–[5] and sent to Claude with a system prompt: answer only from these excerpts, cite each claim, say "not in the sources" if it isn't, and for an active overdose always lead with 911 + naloxone + rescue breathing.
*Why these rules:* citation makes it checkable; "say you don't know" prevents filling gaps from memory; the 911 rule is a safety floor.

### 6. Interface (`app.py`)
A Streamlit web page: type a question, get the answer, expand "Sources used" to see the exact excerpts and pages.

### 7. Evaluate (`eval/`)
20 test questions, each labeled with which source(s) contain the answer. The script checks whether a correct source shows up in the top 5 retrieved chunks (**hit@5**) for each of the 3 search modes.

| Search mode | hit@5 |
|---|---|
| Semantic only | 19/20 (95%) |
| Keyword only | 20/20 (100%) |
| Hybrid | 20/20 (100%) |

*Limits to be upfront about:* 20 questions is small, and "right document in the top 5" is a coarse check. The next step is grading the *answers* themselves (correct? cited properly? refuses when it should?), ideally across several models. That's the evaluation part of the project.

## Likely questions and short answers
- **"Why not fine-tune?"** Fine-tuning changes how a model talks, not what it reliably knows. For factual clinical guidance, retrieval + citation is more accurate, cheaper, and updatable.
- **"How do you stop it hallucinating?"** It only sees retrieved excerpts, must cite each claim, and is told to say when the sources don't cover something. The eval measures whether retrieval finds the right material in the first place.
- **"Why is ASAM a problem for retrieval?"** It's 80% of all chunks (396 of 496), so it crowds the results. Hybrid search and source-balanced retrieval are ways to handle that.
- **"What would you do next?"** Grade answer accuracy across models, add more question types (including ones it should refuse), and test with real users such as harm-reduction workers.

## Stack
Python · sentence-transformers (embeddings) · rank-bm25 (keyword search) · NumPy (vector search) · Anthropic API (Claude) · Streamlit (UI) · Hugging Face Spaces (hosting)
