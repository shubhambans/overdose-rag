# Overdose Response Guidance Assistant

A retrieval-augmented (RAG) assistant that answers questions about opioid-overdose response, addiction treatment, and how clinicians communicate with people who use drugs. It uses only official guidance (SAMHSA, CDC, ASAM, WA DOH) and 24 peer-reviewed papers, citing a source for every claim. It also includes an experiment comparing RAG against the same model answering without sources.

**Educational only. Not medical advice. In an emergency, call 911.**

See **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** for the full design and results.

## Results so far
Retrieval on 31 test questions (right source ranked #1 / in top 5):
semantic 77% / 97% → hybrid 94% / 97% → **hybrid + rerank 94% / 100%** (MRR 0.97).

## Run locally
```bash
pip install -r requirements.txt
python src/fetch_papers.py           # download research papers from PubMed Central -> docs/papers/
python src/ingest.py                 # chunk + embed everything in docs/ -> index/
python eval/run_eval.py              # retrieval eval (no API key needed)

# needs an Anthropic API key:
export ANTHROPIC_API_KEY=sk-ant-...  # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py                 # web app
python eval/compare.py               # RAG vs no-RAG experiment -> eval/results_compare.csv
python eval/compare.py --models claude-sonnet-5-5,claude-haiku-5-5
```

## Sources
**Guidance (`docs/`):** SAMHSA Overdose Prevention and Response Toolkit (2023) · ASAM National Practice Guideline for OUD, 2020 Focused Update · CDC Stop Overdose (Fentanyl Facts, Lifesaving Naloxone, Naloxone FAQ, Test for Fentanyl) · WA DOH Overdose Education and Naloxone Distribution

**Research (`papers/papers.csv`):** 26 papers on stigma and language, patient experiences, and clinician practice, fetched from PubMed Central at build time (not redistributed in this repo).
