"""Load PDFs/TXT from docs/, chunk them, embed, and save an index.

Usage: python src/ingest.py
"""
import json
import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
INDEX = ROOT / "index"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_WORDS = 250
OVERLAP_WORDS = 50


def load_pages(path: Path):
    """Yield (page_number, text) for a PDF or text file."""
    if path.suffix.lower() == ".pdf":
        for i, page in enumerate(PdfReader(path).pages, start=1):
            yield i, page.extract_text() or ""
    else:
        yield 1, path.read_text(errors="ignore")


def chunk(text: str):
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    step = CHUNK_WORDS - OVERLAP_WORDS
    for start in range(0, max(len(words), 1), step):
        piece = " ".join(words[start : start + CHUNK_WORDS])
        if len(piece) > 100:
            yield piece


def main():
    files = sorted(p for p in DOCS.iterdir() if p.suffix.lower() in {".pdf", ".txt", ".md"})
    if not files:
        raise SystemExit(f"No documents in {DOCS}. Add PDFs first.")

    chunks = []
    for f in files:
        for page, text in load_pages(f):
            for piece in chunk(text):
                chunks.append({"source": f.stem, "page": page, "text": piece})
        print(f"{f.name}: {sum(c['source'] == f.stem for c in chunks)} chunks")

    model = SentenceTransformer(EMBED_MODEL)
    vecs = model.encode([c["text"] for c in chunks], normalize_embeddings=True, show_progress_bar=True)

    INDEX.mkdir(exist_ok=True)
    np.save(INDEX / "embeddings.npy", vecs.astype(np.float32))
    (INDEX / "chunks.json").write_text(json.dumps(chunks))
    print(f"Saved {len(chunks)} chunks to {INDEX}/")


if __name__ == "__main__":
    main()
