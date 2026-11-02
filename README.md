# Overdose Response Guidance Assistant

A retrieval-augmented (RAG) assistant that answers questions about opioid-overdose response using only public guidance from SAMHSA, CDC, ASAM and the Washington State Department of Health, citing a source for every claim.

**Educational only. Not medical advice. In an emergency, call 911.**

See **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** for the full design explanation and evaluation results.

## Results
Retrieval hit@5 on 20 test questions: semantic 95%, keyword 100%, **hybrid 100%**.

## Run locally
```bash
pip install -r requirements.txt
python src/ingest.py                 # chunk + embed docs/ -> index/
export ANTHROPIC_API_KEY=sk-ant-...  # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
python eval/run_eval.py              # retrieval eval (no API key needed)
```

## Sources (`docs/`)
- SAMHSA Overdose Prevention and Response Toolkit (PEP23-03-00-001, 2023)
- ASAM National Practice Guideline for the Treatment of Opioid Use Disorder, 2020 Focused Update
- CDC Stop Overdose: Fentanyl Facts; Lifesaving Naloxone; Naloxone FAQ; Test for Fentanyl
- Washington State DOH: Overdose Education and Naloxone Distribution
