# Docwise user guide

Docwise lets you search text-based PDFs and inspect the passages behind each response. The bundled Northstar University policy is fictional and is safe to use for a first run.

## First run

1. Start the app with `python -m streamlit run app.py` and open the local URL Streamlit prints.
2. On the empty-library screen, select **Index sample PDF**. The first run downloads the embedding model, so this can take longer than later indexing.
3. Ask an evidence-backed question, such as: `When does the fall semester begin?`
4. Read the response and open **Retrieved evidence**. Each item shows the source filename, original PDF page, similarity score, and passage text.
5. Ask an unsupported question, such as: `What are the campus gym's weekend opening hours?` The bundled policy does not answer it, so Docwise should display **No supported answer** instead of guessing.

## Add your own PDFs

1. In the sidebar, choose one or more PDF files.
2. Select **Index PDFs** and wait for the per-file result message.
3. Ask questions in the chat box once at least one document is listed in **Your library**.

Docwise accepts text-based PDFs. It reports clear errors for empty, encrypted, malformed, and image-only/scanned PDFs. Run OCR on scanned PDFs before uploading them.

Uploading an unchanged file with the same filename reuses the existing index. Uploading a changed file with that filename replaces its old passages. Use the `×` button next to a document to remove it, or **Clear this library** to remove the entire current library and chat history.

## Read an answer responsibly

Docwise has several answer states:

| State | Meaning |
|---|---|
| **Local extractive answer** | A sentence from retrieved, threshold-qualified text is shown with a numbered evidence reference. |
| **Synthesized answer (OpenAI)** | Optional OpenAI synthesis used the question and retrieved passages only. Check every cited passage. |
| **Local fallback — OpenAI synthesis unavailable** | An optional provider request failed; Docwise fell back to local extraction and labels that fact. |
| **No supported answer** | The threshold or local evidence check could not support an answer. Retrieved passages may be related but are not proof. |

Similarity scores rank nearby passages; they do not establish that a claim is true. Treat the original page and source text as the evidence, especially for policies, deadlines, and decisions.

## Privacy and storage

The default `DOCWISE_LIBRARY_MODE=session` gives each browser session a separate SQLite index in temporary host storage. This prevents normal app searches across browser sessions, but it is not a formal privacy boundary and files are not automatically deleted when the browser closes. Use **Clear this library** when you are finished.

Use `DOCWISE_LIBRARY_MODE=persistent` only for a private, single-user local installation. On the public Vercel demo, the filesystem and session state are ephemeral; do not upload confidential PDFs.

Local extraction, embeddings, and retrieval do not call OpenAI. If `OPENAI_API_KEY` is configured, Docwise sends the question and only the retrieved passages to OpenAI for optional synthesis; it does not upload the full PDF. See the [configuration reference](../README.md#configuration) for details.

## Quick troubleshooting

| Symptom | Suggested action |
|---|---|
| Indexing is slow on the first run | Allow the embedding model download and CPU initialization to finish. |
| No text can be extracted | Use a valid text PDF or OCR a scanned document. |
| A relevant answer is missing | Rephrase the question, verify the PDF contains the fact, and inspect retrieved passages. |
| The app says “No supported answer” | Treat it as an intentional abstention; add a relevant document instead of relying on a guess. |
| A document disappeared after a restart | Session-mode storage is temporary. Re-index it, or use private local persistent mode. |

For installation, configuration, benchmark limits, and deployment notes, return to the [README](../README.md).
