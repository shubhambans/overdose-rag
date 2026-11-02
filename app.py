from pathlib import Path

import streamlit as st

# Build the search index on first run (e.g. a fresh Hugging Face Space).
if not (Path(__file__).parent / "index" / "chunks.json").exists():
    from src import ingest

    with st.spinner("Building search index (first run only)..."):
        ingest.main()

from src.rag import answer  # noqa: E402

st.set_page_config(page_title="Overdose Response Guidance Assistant", page_icon="💊")
st.title("Overdose Response Guidance Assistant")
st.caption(
    "Answers grounded in public SAMHSA / CDC / ASAM guidance, with citations. "
    "Educational only — not medical advice. **In an emergency, call 911.**"
)

examples = [
    "What are the signs of an opioid overdose?",
    "How do I give nasal naloxone?",
    "What should I do after giving naloxone?",
    "Can naloxone hurt someone who isn't overdosing?",
]
pick = st.selectbox("Try an example", [""] + examples)
q = st.text_input("Ask a question", value=pick)

if q:
    with st.spinner("Searching guidance..."):
        text, hits = answer(q)
    st.markdown(text)
    with st.expander("Sources used"):
        for n, h in enumerate(hits, 1):
            st.markdown(f"**[{n}] {h['source']}, p.{h['page']}** (similarity {h['score']:.2f})")
            st.caption(h["text"][:500] + "…")
