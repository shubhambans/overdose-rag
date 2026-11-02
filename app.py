from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Overdose Response Guidance Assistant", page_icon="💊")
ROOT = Path(__file__).parent

# First run (e.g. a fresh Hugging Face Space): download papers, then build the search index.
if not (ROOT / "index" / "chunks.json").exists():
    from src import fetch_papers, ingest

    with st.spinner("Downloading research papers and building search index (first run only)..."):
        if not (ROOT / "docs" / "papers").exists():
            fetch_papers.main()
        ingest.main()

from src.llm import default_model  # noqa: E402
from src.rag import answer, answer_no_rag, cite  # noqa: E402

try:
    MODEL = default_model()
except SystemExit as e:
    st.error(str(e))
    st.stop()

st.title("Overdose Response Guidance Assistant")
st.caption(
    "Answers grounded in SAMHSA / CDC / ASAM guidance and peer-reviewed research on addiction care, "
    f"with citations. Model: `{MODEL}`. Educational only — not medical advice. "
    "**In an emergency, call 911.**"
)

examples = [
    "What are the signs of an opioid overdose?",
    "How do I give nasal naloxone?",
    "What should I do after giving naloxone?",
    "Can naloxone hurt someone who isn't overdosing?",
    "What words should clinicians avoid when talking about drug use?",
    "What do people with OUD say about their emergency department care?",
]
pick = st.selectbox("Try an example", [""] + examples)
q = st.text_input("Ask a question", value=pick)
compare = st.toggle("Compare with the same model answering without sources")

if q:
    cols = st.columns(2) if compare else [st.container()]
    with cols[0]:
        if compare:
            st.subheader("With sources (RAG)")
        with st.spinner("Searching guidance and research..."):
            text, hits = answer(q)
        st.markdown(text)
        with st.expander("Sources used"):
            for n, h in enumerate(hits, 1):
                st.markdown(f"**[{n}] {cite(h)}**")
                st.caption(h["text"][:500] + "…")
    if compare:
        with cols[1]:
            st.subheader("Without sources")
            with st.spinner("Answering from memory..."):
                st.markdown(answer_no_rag(q))
