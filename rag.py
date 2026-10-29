"""PDF ingestion, local embedding index, retrieval, and cited answer generation."""
from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from pypdf import PdfReader


ABSTENTION_MESSAGE = (
    "I couldn't find this information in the indexed documents. "
    "Try rephrasing your question or adding a relevant PDF."
)


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
DEFAULT_DATA_DIR = Path(__file__).parent / "data"
os.environ.setdefault("HF_HOME", str(DEFAULT_DATA_DIR / "hf_cache"))
from sentence_transformers import SentenceTransformer


DB_PATH = Path(os.getenv("VECTOR_DB_PATH", str(DEFAULT_DATA_DIR / "vectors.sqlite3")))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_model = None


def embedding_model():
    """Load the CPU embedding model once per Python process."""
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


def _safe_source_name(filename: str) -> str:
    """Store just the supplied file name, never a client-side path."""
    source = Path(str(filename).replace("\\", "/")).name.strip()
    if not source:
        raise ValueError("The PDF needs a filename before it can be indexed.")
    return source


def _database_path(db_path: Path | str | None) -> Path:
    return Path(db_path) if db_path is not None else DB_PATH


def extract_pdf(pdf_bytes: bytes, filename: str) -> list[tuple[str, int]]:
    """Extract text while keeping the original one-based PDF page number."""
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise ValueError(
            f"{filename} could not be read as a PDF. Check that the upload is a valid, non-encrypted PDF."
        ) from exc
    if reader.is_encrypted:
        raise ValueError(f"{filename} is encrypted. Upload an unlocked PDF instead.")
    try:
        pages = [(page.extract_text() or "", number) for number, page in enumerate(reader.pages, 1)]
    except Exception as exc:
        raise ValueError(
            f"Text could not be extracted from {filename}. Try a text-based PDF or run OCR first."
        ) from exc
    if not pages:
        raise ValueError(f"{filename} has no pages to index.")
    return pages


def chunk_pages(pages: Iterable[tuple[str, int]], source: str, size: int = 850, overlap: int = 140) -> list[Chunk]:
    """Split each page independently so every chunk retains its source page."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Chunk size must be positive and larger than overlap.")
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
                boundary = paragraphs.rfind(" ", start + int(size * 0.7), end)
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
def _connect(db_path: Path | str | None = None):
    """Open a short-lived SQLite connection and keep schema setup in one place."""
    path = _database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.execute("PRAGMA busy_timeout = 10000")
        db.execute(
            "CREATE TABLE IF NOT EXISTS chunks "
            "(id TEXT PRIMARY KEY, source TEXT, page INTEGER, text TEXT, vector BLOB, dim INTEGER)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS sources "
            "(source TEXT PRIMARY KEY, content_hash TEXT NOT NULL)"
        )
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def add_pdf(pdf_bytes: bytes, filename: str, db_path: Path | str | None = None) -> int:
    """Index a PDF, skipping embedding work when the same named file is unchanged."""
    source = _safe_source_name(filename)
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    with _connect(db_path) as db:
        existing = db.execute(
            "SELECT sources.content_hash, COUNT(chunks.id) "
            "FROM sources LEFT JOIN chunks ON chunks.source = sources.source "
            "WHERE sources.source = ? GROUP BY sources.source",
            (source,),
        ).fetchone()
        if existing and existing[0] == content_hash and existing[1]:
            return int(existing[1])

    chunks = chunk_pages(extract_pdf(pdf_bytes, source), source)
    if not chunks:
        raise ValueError("No extractable text found. This PDF may be scanned; run OCR first.")
    vectors = embedding_model().encode(
        [chunk.text for chunk in chunks], normalize_embeddings=True, show_progress_bar=False
    )
    with _connect(db_path) as db:
        db.execute("DELETE FROM chunks WHERE source = ?", (source,))
        db.executemany(
            "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    chunk.chunk_id,
                    chunk.source,
                    chunk.page,
                    chunk.text,
                    np.asarray(vector, dtype=np.float32).tobytes(),
                    len(vector),
                )
                for chunk, vector in zip(chunks, vectors)
            ],
        )
        db.execute(
            "INSERT OR REPLACE INTO sources (source, content_hash) VALUES (?, ?)",
            (source, content_hash),
        )
    return len(chunks)


def list_sources(db_path: Path | str | None = None) -> list[tuple[str, int]]:
    with _connect(db_path) as db:
        return db.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source ORDER BY source").fetchall()


def delete_source(source: str, db_path: Path | str | None = None) -> None:
    with _connect(db_path) as db:
        db.execute("DELETE FROM chunks WHERE source = ?", (source,))
        db.execute("DELETE FROM sources WHERE source = ?", (source,))


def clear_library(db_path: Path | str | None = None) -> None:
    """Remove one SQLite library and its write-ahead-log sidecars, if present."""
    path = _database_path(db_path)
    with _connect(path) as db:
        db.execute("DELETE FROM chunks")
        db.execute("DELETE FROM sources")
    for suffix in ("", "-wal", "-shm"):
        candidate = path.with_name(f"{path.name}{suffix}")
        if candidate.is_file():
            candidate.unlink()


def retrieve(query: str, top_k: int = 5, db_path: Path | str | None = None) -> list[dict]:
    """Return the nearest normalized embedding vectors, with their original metadata."""
    query = query.strip()
    if not query or top_k <= 0:
        return []
    with _connect(db_path) as db:
        rows = db.execute("SELECT id, source, page, text, vector, dim FROM chunks").fetchall()
    if not rows:
        return []
    query_vector = np.asarray(
        embedding_model().encode([query], normalize_embeddings=True, show_progress_bar=False)[0], dtype=np.float32
    )
    scored = []
    for chunk_id, source, page, text, blob, dim in rows:
        try:
            vector = np.frombuffer(blob, dtype=np.float32, count=dim)
        except (TypeError, ValueError):
            continue
        # A model change can leave stale vectors with another dimension in an existing DB.
        if vector.size != dim or vector.size != query_vector.size:
            continue
        score = float(np.dot(query_vector, vector))
        scored.append({"id": chunk_id, "source": source, "page": page, "text": text, "score": score})
    return sorted(scored, key=lambda row: row["score"], reverse=True)[:top_k]


def _terms(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
        "what", "when", "where", "which", "who", "whom", "why", "how", "much", "many", "can", "could",
        "may", "might", "should", "would", "will", "i", "me", "my", "we", "our", "you", "your", "they",
        "their", "it", "and", "or", "but", "to", "of", "in", "on", "for", "from", "by", "with", "at",
        "as", "about", "after", "before", "per", "this", "that", "these", "those", "than", "then", "into",
        "through", "all", "any", "each", "doesn",
    }
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


def _has_specific_overlap(query_terms: set[str], sentence_terms: set[str]) -> bool:
    """Reject generic overlap such as 'campus' + 'open' for an unsupported question."""
    if not query_terms:
        return False
    longest_term = max(map(len, query_terms))
    salient_terms = {term for term in query_terms if len(term) >= max(4, longest_term - 1)}
    return bool(salient_terms & sentence_terms)


def _extractive_answer(question: str, passages: list[dict]) -> str:
    """Quote a source sentence only when it contains specific question evidence."""
    query_terms = _terms(question)
    candidates = []
    for index, passage in enumerate(passages, 1):
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", passage["text"]):
            sentence = sentence.strip()
            sentence_terms = _terms(sentence)
            overlap = query_terms & sentence_terms
            if len(overlap) >= 2 and _has_specific_overlap(query_terms, sentence_terms):
                candidates.append(
                    (
                        len(overlap) / max(len(query_terms), 1),
                        len(overlap),
                        passage["score"],
                        sentence,
                        index,
                    )
                )
    if not candidates:
        return ABSTENTION_MESSAGE
    _, _, _, sentence, index = max(candidates, key=lambda candidate: candidate[:3])
    return f"{sentence} [{index}]"


def answer_question(
    question: str,
    top_k: int = 5,
    threshold: float = 0.39,
    db_path: Path | str | None = None,
) -> tuple[str, list[dict]]:
    """Answer only from threshold-qualified retrieved passages, with a visible answer mode."""
    if not question.strip():
        return f"**No supported answer**\n\n{ABSTENTION_MESSAGE}", []
    passages = retrieve(question, top_k, db_path)
    relevant = [passage for passage in passages if passage["score"] >= threshold]
    if not relevant:
        return f"**No supported answer**\n\n{ABSTENTION_MESSAGE}", []
    context = "\n\n".join(
        f"[{index}] {passage['source']} — page {passage['page']}\n{passage['text']}"
        for index, passage in enumerate(relevant, 1)
    )
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            response = OpenAI().responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the supplied passages. If they do not contain the answer, say you "
                            "cannot find it. Cite each factual claim with passage markers like [1]. Never invent citations."
                        ),
                    },
                    {"role": "user", "content": f"Question: {question}\n\nPassages:\n{context}"},
                ],
            )
            generated = response.output_text.strip()
            if not generated:
                raise RuntimeError("The answer provider returned no text.")
            return f"**Synthesized answer (OpenAI)**\n\n{generated}", relevant
        except Exception:
            fallback = _extractive_answer(question, relevant)
            if fallback == ABSTENTION_MESSAGE:
                return (
                    "**No supported answer**\n\n"
                    "OpenAI synthesis is unavailable, and the local fallback could not find a supporting answer.\n\n"
                    f"{fallback}\n\n_The retrieved evidence below is related but does not support an answer._",
                    relevant,
                )
            return (
                "**Local fallback — OpenAI synthesis unavailable**\n\n"
                f"{fallback}\n\n_The retrieved evidence below remains available for review._",
                relevant,
            )
    local_answer = _extractive_answer(question, relevant)
    if local_answer == ABSTENTION_MESSAGE:
        return f"**No supported answer**\n\n{local_answer}", relevant
    return f"**Local extractive answer**\n\n{local_answer}", relevant
