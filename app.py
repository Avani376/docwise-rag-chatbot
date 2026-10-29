from __future__ import annotations

import html
import os
import tempfile
import uuid
from pathlib import Path

import streamlit as st

from rag import add_pdf, answer_question, clear_library, delete_source, list_sources


st.set_page_config(page_title="Docwise | PDF assistant", page_icon="D", layout="wide")


def _library_path() -> Path | None:
    """Use one temporary SQLite library per browser session unless local persistence is explicit."""
    if os.getenv("DOCWISE_LIBRARY_MODE", "session").strip().casefold() == "persistent":
        return None
    if "docwise_library_id" not in st.session_state:
        st.session_state["docwise_library_id"] = uuid.uuid4().hex
    return (
        Path(tempfile.gettempdir())
        / "docwise-session-libraries"
        / st.session_state["docwise_library_id"]
        / "vectors.sqlite3"
    )


def _similarity_threshold() -> float:
    try:
        value = float(os.getenv("SIMILARITY_THRESHOLD", "0.39"))
        return value if -1.0 <= value <= 1.0 else 0.39
    except ValueError:
        return 0.39


def _render_evidence(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Retrieved evidence ({len(sources)})", expanded=True):
        for index, passage in enumerate(sources, 1):
            source = html.escape(str(passage["source"]))
            st.markdown(
                f"**[{index}] {source} · page {passage['page']}** · "
                f"similarity `{passage['score']:.2f}`"
            )
            st.write(passage["text"])


def _render_index_feedback() -> None:
    for level, message in st.session_state.pop("index_feedback", []):
        getattr(st, level)(message)


LIBRARY_PATH = _library_path()
IS_SESSION_LIBRARY = LIBRARY_PATH is not None

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#172b27; --muted:#657873; --paper:#f7f8f4; --green:#0f766e; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
h1,h2,h3 { font-family:'Manrope',sans-serif; letter-spacing:-.035em; }
.hero { padding:1.1rem 0 1.5rem; border-bottom:1px solid #dfe7e1; margin-bottom:1.4rem; }
.eyebrow { font-size:.77rem; font-weight:700; letter-spacing:.12em; color:#0f766e; text-transform:uppercase; }
.subtle { color:#657873; font-size:1.03rem; }
[data-testid="stSidebar"] { background:#edf2ed; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] * { color:var(--ink) !important; }
[data-testid="stSidebar"] [data-testid="stAlert"] * { color:#174c76 !important; }
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] button *,
[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] * { color:#f8fafc !important; }
div[data-testid="stChatMessage"] { border:1px solid #e4eae5; border-radius:16px; padding:.9rem 1rem; }
button[kind="primary"] { background:#0f766e; border-color:#0f766e; }
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Docwise")
    st.caption("Ask your documents. See exactly where answers come from.")
    st.markdown("### Your library")
    _render_index_feedback()
    uploads = st.file_uploader(
        "Add PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Text-based PDFs work best. Scanned files need OCR first.",
    )
    if uploads and st.button("Index PDFs", type="primary", use_container_width=True):
        progress = st.progress(0, text="Preparing your library…")
        feedback = []
        for index, uploaded_file in enumerate(uploads):
            try:
                count = add_pdf(uploaded_file.getvalue(), uploaded_file.name, LIBRARY_PATH)
                feedback.append(("success", f"{uploaded_file.name}: ready with {count} passages"))
            except ValueError as exc:
                feedback.append(("warning", f"{uploaded_file.name}: {exc}"))
            except Exception:
                feedback.append(
                    ("error", f"{uploaded_file.name}: Docwise could not index this PDF. Please try another text-based file.")
                )
            progress.progress((index + 1) / len(uploads), text=f"Processed {index + 1} of {len(uploads)}")
        st.session_state["index_feedback"] = feedback
        st.rerun()

    docs = list_sources(LIBRARY_PATH)
    if docs:
        for name, count in docs:
            left, right = st.columns([5, 1])
            left.markdown(f"**{html.escape(name)}**  \n<span style='color:#657873;font-size:.8rem'>{count} passages</span>", unsafe_allow_html=True)
            if right.button("×", key=f"delete-{name}", help=f"Remove {name}"):
                delete_source(name, LIBRARY_PATH)
                st.rerun()
        if st.button("Clear this library", use_container_width=True):
            clear_library(LIBRARY_PATH)
            st.session_state["messages"] = []
            st.rerun()
    else:
        st.info("No documents indexed yet. Add one or more PDFs above.")
    st.divider()
    if IS_SESSION_LIBRARY:
        st.caption(
            "This browser session uses an isolated SQLite library in host temporary storage. It is not automatically "
            "deleted when the browser closes; Clear this library removes its database files. Set "
            "DOCWISE_LIBRARY_MODE=persistent only for a private local installation."
        )
    else:
        st.caption("This private local installation uses a persistent SQLite library.")
    st.caption("Embeddings stay local. OpenAI answer synthesis is optional and uses only the question plus retrieved passages.")

st.markdown(
    '<div class="hero"><div class="eyebrow">Your document workspace</div><h1>Answers, grounded in your PDFs.</h1><div class="subtle">Ask a question and get a clear response with page-level citations. If the documents do not say, Docwise will tell you.</div></div>',
    unsafe_allow_html=True,
)

if not docs:
    st.markdown("### Start with the sample policy")
    st.write(
        "Try the included fictional Northstar University policy PDF to see citations and the evaluation set, "
        "or upload your own syllabus, policy, or research papers."
    )
    sample_path = Path(__file__).parent / "documents" / "northstar_student_policy.pdf"
    if sample_path.is_file() and st.button("Index sample PDF", type="primary"):
        feedback = []
        with st.spinner("Embedding the sample document on this device…"):
            try:
                count = add_pdf(sample_path.read_bytes(), sample_path.name, LIBRARY_PATH)
                feedback.append(("success", f"Sample PDF ready with {count} passages."))
            except ValueError as exc:
                feedback.append(("warning", str(exc)))
            except Exception:
                feedback.append(("error", "Docwise could not index the sample PDF. Please restart the app and try again."))
        st.session_state["index_feedback"] = feedback
        st.rerun()

for item in st.session_state.get("messages", []):
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        _render_evidence(item.get("sources", []))

question = st.chat_input("Ask something about your documents…", disabled=not docs)
if question:
    st.session_state.setdefault("messages", []).append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the indexed passages…"):
            try:
                response, sources = answer_question(
                    question,
                    threshold=_similarity_threshold(),
                    db_path=LIBRARY_PATH,
                )
            except ValueError as exc:
                response, sources = f"**Unable to answer**\n\n{exc}", []
            except Exception:
                response, sources = (
                    "**Unable to answer**\n\nDocwise had trouble searching this library. Please try again.",
                    [],
                )
        st.markdown(response)
        _render_evidence(sources)
    st.session_state["messages"].append({"role": "assistant", "content": response, "sources": sources})
