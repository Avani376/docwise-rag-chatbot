from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from rag import ABSTENTION_MESSAGE, _extractive_answer, add_pdf, answer_question, chunk_pages, clear_library, list_sources


class _FakeEmbeddingModel:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts, **_kwargs):
        self.calls += 1
        return np.ones((len(texts), 3), dtype=np.float32)


class RagRegressionTests(unittest.TestCase):
    def test_chunks_keep_their_original_page(self) -> None:
        chunks = chunk_pages([("First page text", 1), ("Second page text", 2)], "policy.pdf", size=50, overlap=5)
        self.assertEqual([chunk.page for chunk in chunks], [1, 2])
        self.assertTrue(all(chunk.source == "policy.pdf" for chunk in chunks))

    def test_extractive_fallback_rejects_generic_overlap(self) -> None:
        passages = [
            {
                "source": "policy.pdf",
                "page": 1,
                "score": 0.82,
                "text": "The campus health center is open Monday through Friday from 8:30 a.m. to 5 p.m.",
            }
        ]
        answer = _extractive_answer("What is the campus gym's weekend opening time?", passages)
        self.assertEqual(answer, ABSTENTION_MESSAGE)

    def test_abstaining_local_answer_is_labeled_as_unsupported(self) -> None:
        passages = [
            {
                "source": "policy.pdf",
                "page": 1,
                "score": 0.82,
                "text": "The campus health center is open Monday through Friday from 8:30 a.m. to 5 p.m.",
            }
        ]
        with patch("rag.retrieve", return_value=passages), patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            answer, evidence = answer_question("What is the campus gym's weekend opening time?")
        self.assertTrue(answer.startswith("**No supported answer**"))
        self.assertEqual(evidence, passages)

    def test_unchanged_upload_skips_a_second_embedding_pass(self) -> None:
        model = _FakeEmbeddingModel()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "vectors.sqlite3"
            pages = [("The fall semester begins September 3.", 1)]
            with patch("rag.extract_pdf", return_value=pages), patch("rag.embedding_model", return_value=model):
                first_count = add_pdf(b"same pdf bytes", "policy.pdf", database)
                second_count = add_pdf(b"same pdf bytes", "policy.pdf", database)
            self.assertEqual((first_count, second_count), (1, 1))
            self.assertEqual(model.calls, 1)
            self.assertEqual(list_sources(database), [("policy.pdf", 1)])

    def test_clear_library_removes_the_session_database(self) -> None:
        model = _FakeEmbeddingModel()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "vectors.sqlite3"
            with patch("rag.extract_pdf", return_value=[("The fall semester begins September 3.", 1)]), patch(
                "rag.embedding_model", return_value=model
            ):
                add_pdf(b"pdf bytes", "policy.pdf", database)
            clear_library(database)
            self.assertFalse(database.exists())

    def test_openai_failure_is_labeled_and_keeps_retrieved_evidence(self) -> None:
        passages = [
            {
                "source": "policy.pdf",
                "page": 1,
                "score": 0.91,
                "text": "The fall semester begins September 3.",
            }
        ]
        with patch("rag.retrieve", return_value=passages), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False
        ), patch("openai.OpenAI", side_effect=RuntimeError("provider unavailable")):
            answer, evidence = answer_question("When does fall semester begin?")
        self.assertIn("Local fallback — OpenAI synthesis unavailable", answer)
        self.assertIn("September 3", answer)
        self.assertEqual(evidence, passages)


if __name__ == "__main__":
    unittest.main()
