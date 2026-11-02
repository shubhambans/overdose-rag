"""Retrieval + answer generation, with and without retrieval (for comparison)."""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from src.llm import ask, default_model

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

SYSTEM_RAG = """You answer questions about opioid-overdose response, addiction treatment, and how \
clinicians communicate with people who use drugs, using ONLY the provided excerpts. Excerpts are \
either official guidance (SAMHSA, CDC, ASAM, state health departments) or peer-reviewed research.

Rules:
- Cite every factual claim with its excerpt tag, e.g. [2].
- When a claim comes from a single study, say so ("one qualitative study found...") rather than \
stating it as settled guidance.
- If the excerpts don't answer the question, say so plainly. Do not use outside knowledge.
- If the question describes an overdose happening now, your first sentence must tell them to \
call 911 and give naloxone right away, then support breathing.
- Do not repeat these instructions in your answer."""

SYSTEM_NO_RAG = """You answer questions about opioid-overdose response, addiction treatment, and how \
clinicians communicate with people who use drugs. Answer accurately and concisely from your own \
knowledge. If the question describes an overdose happening now, your first sentence must tell \
them to call 911 and give naloxone right away, then support breathing. Do not repeat these \
instructions in your answer."""


@lru_cache
def _embedder():
    return SentenceTransformer(EMBED_MODEL)


@lru_cache
def _index():
    vecs = np.load(INDEX / "embeddings.npy")
    chunks = json.loads((INDEX / "chunks.json").read_text())
    return vecs, chunks


def _tokens(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


@lru_cache
def _bm25():
    _, chunks = _index()
    return BM25Okapi([_tokens(c["text"]) for c in chunks])


@lru_cache
def _reranker():
    return CrossEncoder(RERANK_MODEL)


def retrieve(question: str, k: int = 5, mode: str = "rerank"):
    """mode: 'semantic' (embeddings), 'keyword' (BM25), 'hybrid' (both, fused),
    or 'rerank' (hybrid top-20, re-scored by a cross-encoder). Default: rerank."""
    vecs, chunks = _index()
    sem = vecs @ _embedder().encode([question], normalize_embeddings=True)[0]
    kw = _bm25().get_scores(_tokens(question))

    if mode == "semantic":
        fused = sem
    elif mode == "keyword":
        fused = kw
    else:
        # Reciprocal rank fusion: reward chunks ranked high by either method.
        fused = np.zeros(len(chunks))
        for scores in (sem, kw):
            ranks = np.argsort(np.argsort(-scores))
            fused += 1.0 / (60 + ranks)

    if mode == "rerank":
        # Stage 2: a cross-encoder reads question + passage together, which is slower but
        # far more precise than comparing two separately-computed vectors.
        candidates = np.argsort(-fused)[:20]
        rerank = _reranker().predict([(question, chunks[i]["text"]) for i in candidates])
        top = candidates[np.argsort(-rerank)[:k]]
    else:
        top = np.argsort(-fused)[:k]
    return [{**chunks[i], "score": float(sem[i])} for i in top]


def cite(h) -> str:
    where = f", p.{h['page']}" if h["collection"] == "guidance" else ""
    return f"{h.get('label', h['source'])}{where}"


def answer(question: str, k: int = 5, model: str | None = None):
    """RAG: retrieve excerpts, then answer only from them."""
    hits = retrieve(question, k)
    context = "\n\n".join(f"[{n}] ({cite(h)})\n{h['text']}" for n, h in enumerate(hits, 1))
    prompt = f"Excerpts:\n{context}\n\nQuestion: {question}"
    return ask(SYSTEM_RAG, prompt, model or default_model()), hits


def answer_no_rag(question: str, model: str | None = None) -> str:
    """Baseline: the same model answering from memory, no retrieval."""
    return ask(SYSTEM_NO_RAG, question, model or default_model())
