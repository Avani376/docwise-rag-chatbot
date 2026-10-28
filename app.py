from __future__ import annotations

import os
import streamlit as st

from rag import add_pdf, answer_question, delete_source, list_sources

st.set_page_config(page_title="Docwise | PDF assistant", page_icon="D", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#172b27; --muted:#657873; --paper:#f7f8f4; --green:#0f766e; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
h1,h2,h3 { font-family:'Manrope',sans-serif; letter-spacing:-.035em; }
.hero { padding:1.1rem 0 1.5rem; border-bottom:1px solid #dfe7e1; margin-bottom:1.4rem; }
.eyebrow { font-size:.77rem; font-weight:700; letter-spacing:.12em; color:#0f766e; text-transform:uppercase; }
.subtle { color:#657873; font-size:1.03rem; }
[data-testid="stSidebar"] { background:#edf2ed; }
div[data-testid="stChatMessage"] { border:1px solid #e4eae5; border-radius:16px; padding:.9rem 1rem; }
button[kind="primary"] { background:#0f766e; border-color:#0f766e; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Docwise")
    st.caption("Ask your documents. See exactly where answers come from.")
    st.markdown("### Your library")
    uploads = st.file_uploader("Add PDF documents", type=["pdf"], accept_multiple_files=True, help="Text based PDFs work best. Scanned files need OCR first.")
    if uploads and st.button("Index PDFs", type="primary", use_container_width=True):
        progress = st.progress(0, text="Preparing your library…")
        for i, file in enumerate(uploads):
            try:
                count = add_pdf(file.getvalue(), file.name)
                st.success(f"{file.name}: indexed {count} passages")
            except Exception as exc:
                st.error(f"{file.name}: {exc}")
            progress.progress((i + 1) / len(uploads), text=f"Indexed {i + 1} of {len(uploads)}")
        st.rerun()
    docs = list_sources()
    if docs:
        for name, count in docs:
            left, right = st.columns([5, 1])
            left.markdown(f"**{name}**  \n<span style='color:#657873;font-size:.8rem'>{count} passages</span>", unsafe_allow_html=True)
            if right.button("×", key=f"delete-{name}", help=f"Remove {name}"):
                delete_source(name)
                st.rerun()
    else:
        st.info("No documents indexed yet. Add one or more PDFs above.")
    st.divider()
    st.caption("Embeddings and the passage index stay on this computer. Answer synthesis uses OpenAI when OPENAI_API_KEY is set.")

st.markdown('<div class="hero"><div class="eyebrow">Your document workspace</div><h1>Answers, grounded in your PDFs.</h1><div class="subtle">Ask a question and get a clear response with page-level citations. If the documents do not say, Docwise will tell you.</div></div>', unsafe_allow_html=True)

if not docs:
    st.markdown("### Start with the sample policy")
    st.write("Try the included fictional Northstar University policy PDF to see citations and the evaluation set, or upload your own syllabus, policy, or research papers.")
    sample_path = os.path.join(os.path.dirname(__file__), "documents", "northstar_student_policy.pdf")
    if os.path.exists(sample_path) and st.button("Index sample PDF", type="primary"):
        with st.spinner("Embedding the sample document on this device…"):
            add_pdf(open(sample_path, "rb").read(), "northstar_student_policy.pdf")
        st.rerun()

for item in st.session_state.get("messages", []):
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("sources"):
            with st.expander(f"Sources ({len(item['sources'])})", expanded=True):
                for i, p in enumerate(item["sources"], 1):
                    st.markdown(f"**[{i}] {p['source']} · page {p['page']}** · similarity {p['score']:.2f}")
                    st.write(p["text"])

question = st.chat_input("Ask something about your documents…", disabled=not docs)
if question:
    st.session_state.setdefault("messages", []).append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the indexed passages…"):
            try:
                response, sources = answer_question(question, threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.39")))
            except Exception as exc:
                response, sources = f"I couldn't answer this question: {exc}", []
        st.markdown(response)
        if sources:
            with st.expander(f"Sources ({len(sources)})", expanded=True):
                for i, p in enumerate(sources, 1):
                    st.markdown(f"**[{i}] {p['source']} · page {p['page']}** · similarity {p['score']:.2f}")
                    st.write(p["text"])
    st.session_state["messages"].append({"role": "assistant", "content": response, "sources": sources})
