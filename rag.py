"""PDF ingestion, local embedding index, retrieval, and cited answer generation."""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from pypdf import PdfReader


def _load_env_file(path: Path) -> None:
    """Load simple KEY=value lines from the project .env without overriding shell vars."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(Path(__file__).parent / ".env")
# Keep model downloads in the app's writable data directory, not the user's home cache.
Path(__file__).parent.joinpath("data").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(Path(__file__).parent / "data" / "hf_cache"))
from sentence_transformers import SentenceTransformer

DB_PATH = Path(os.getenv("VECTOR_DB_PATH", str(Path(__file__).parent / "data" / "vectors.sqlite3")))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_model = None


def embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return _model


@dataclass
class Chunk:
    text: str
    source: str
    page: int
    chunk_id: str


def extract_pdf(pdf_bytes: bytes, filename: str) -> list[tuple[str, int]]:
    reader = PdfReader(__import__("io").BytesIO(pdf_bytes))
    return [(page.extract_text() or "", number) for number, page in enumerate(reader.pages, 1)]


def chunk_pages(pages: Iterable[tuple[str, int]], source: str, size: int = 850, overlap: int = 140) -> list[Chunk]:
    chunks = []
    for text, page in pages:
        paragraphs = re.sub(r"[ \t]+", " ", text)
        paragraphs = re.sub(r"\n{2,}", "\n", paragraphs).strip()
        if not paragraphs:
            continue
        start = 0
        while start < len(paragraphs):
            end = min(start + size, len(paragraphs))
            if end < len(paragraphs):
                boundary = paragraphs.rfind(" ", start + int(size * .7), end)
                if boundary > start:
                    end = boundary
            body = paragraphs[start:end].strip()
            digest = hashlib.sha1(f"{source}|{page}|{start}|{body}".encode()).hexdigest()[:14]
            chunks.append(Chunk(body, source, page, digest))
            if end == len(paragraphs):
                break
            start = max(end - overlap, start + 1)
    return chunks


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, source TEXT, page INTEGER, text TEXT, vector BLOB, dim INTEGER)")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def add_pdf(pdf_bytes: bytes, filename: str) -> int:
    chunks = chunk_pages(extract_pdf(pdf_bytes, filename), filename)
    if not chunks:
        raise ValueError("No extractable text found. This PDF may be scanned; run OCR first.")
    vectors = embedding_model().encode([c.text for c in chunks], normalize_embeddings=True, show_progress_bar=False)
    with _connect() as db:
        db.execute("DELETE FROM chunks WHERE source = ?", (filename,))
        db.executemany("INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?)", [
            (c.chunk_id, c.source, c.page, c.text, np.asarray(v, dtype=np.float32).tobytes(), len(v))
            for c, v in zip(chunks, vectors)
        ])
    return len(chunks)


def list_sources() -> list[tuple[str, int]]:
    with _connect() as db:
        return db.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source ORDER BY source").fetchall()


def delete_source(source: str) -> None:
    with _connect() as db:
        db.execute("DELETE FROM chunks WHERE source = ?", (source,))


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    with _connect() as db:
        rows = db.execute("SELECT id, source, page, text, vector, dim FROM chunks").fetchall()
    if not rows:
        return []
    q = embedding_model().encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    scored = []
    for chunk_id, source, page, text, blob, dim in rows:
        vector = np.frombuffer(blob, dtype=np.float32, count=dim)
        score = float(np.dot(q, vector))
        scored.append({"id": chunk_id, "source": source, "page": page, "text": text, "score": score})
    return sorted(scored, key=lambda row: row["score"], reverse=True)[:top_k]


def _terms(text: str) -> set[str]:
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "what", "when", "where", "which", "who", "whom", "why", "how", "much", "many", "can", "could", "may", "might", "should", "would", "will", "i", "me", "my", "we", "our", "you", "your", "they", "their", "it", "and", "or", "but", "to", "of", "in", "on", "for", "from", "by", "with", "at", "as", "about", "after", "before", "per", "this", "that", "these", "those", "than", "then", "into", "through", "all", "any", "each", "doesn"}
    words = re.findall(r"[a-z0-9]+", text.casefold())
    result = set()
    for word in words:
        if word in stop or len(word) < 3:
            continue
        if len(word) > 5 and word.endswith("ing"):
            word = word[:-3]
        elif len(word) > 4 and word.endswith("ed"):
            word = word[:-2]
        elif len(word) > 4 and word.endswith("s"):
            word = word[:-1]
        result.add(word)
    return result


def _extractive_answer(question: str, passages: list[dict]) -> str:
    query_terms = _terms(question)
    candidates = []
    for index, passage in enumerate(passages, 1):
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", passage["text"]):
            sentence = sentence.strip()
            overlap = query_terms & _terms(sentence)
            if len(overlap) >= 2:
                candidates.append((len(overlap) / max(len(query_terms), 1), len(overlap), passage["score"], sentence, index))
    if not candidates:
        return "I couldn't find this information in the indexed documents. Try rephrasing your question or adding a relevant PDF."
    _, _, _, sentence, index = max(candidates)
    return f"{sentence} [{index}]"


def answer_question(question: str, top_k: int = 5, threshold: float = 0.39) -> tuple[str, list[dict]]:
    passages = retrieve(question, top_k)
    relevant = [p for p in passages if p["score"] >= threshold]
    if not relevant:
        return "I couldn't find this information in the indexed documents. Try rephrasing your question or adding a relevant PDF.", []
    context = "\n\n".join(f"[{i}] {p['source']} — page {p['page']}\n{p['text']}" for i, p in enumerate(relevant, 1))
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        response = OpenAI().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[{"role": "system", "content": "Answer only from the supplied passages. If they do not contain the answer, say you cannot find it. Cite each factual claim with passage markers like [1]. Never invent citations."},
                   {"role": "user", "content": f"Question: {question}\n\nPassages:\n{context}"}],
        )
        return response.output_text, relevant
    # Extractive fallback gives a short, locally generated answer without an API key.
    return _extractive_answer(question, relevant), relevant
