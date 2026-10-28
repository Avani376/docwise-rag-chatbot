# Docwise: a RAG chatbot for PDF documents

Docwise lets you upload PDFs, ask questions about their contents, and inspect the source passages and page citations used to answer. It includes a fictional sample policy PDF and a 25-question benchmark with both answerable and unanswerable questions.

> **Demo content:** Northstar University and its policy PDF are fictional. Do not rely on them as real policies.

## Features

- Upload one or more text-based PDF files.
- Extract text page by page and split it into overlapping passages.
- Embed passages and questions locally with Sentence Transformers.
- Store embeddings and passage metadata in a persistent SQLite vector index.
- Retrieve passages by cosine similarity and show their source filename, page, similarity score, and text.
- Abstain when no retrieved passage meets the configured similarity threshold.
- Use a local extractive answer fallback without an API key.
- Optionally synthesize an answer with the OpenAI Responses API. Only the question and retrieved passages are sent to OpenAI; the original PDF is not uploaded by this app.
- Evaluate retrieval evidence and abstention using the included 25-question dataset.

## Repository contents

```text
app.py                         Streamlit interface
rag.py                         PDF parsing, chunking, embedding, retrieval, answers
evaluate.py                    Isolated benchmark runner
requirements.txt               Python dependencies
.env.example                   Safe configuration template; contains no secret
.gitignore                     Excludes secrets, local data, and Python caches
documents/
  northstar_student_policy.pdf Fictional demo corpus used by the app and benchmark
  northstar_student_policy.txt Editable source for the demo PDF
evaluation/
  questions.csv                25 questions with expected evidence and answerability
  results.md                   Recorded benchmark results and limitations
data/                          Created at runtime; local index/model cache, ignored by Git
```

## Requirements

- Python 3.10 or newer
- CPU; **a GPU is not required**
- Internet access on first run to install packages and download the embedding model
- About 91 MB for the `all-MiniLM-L6-v2` model weights, plus the Python runtime and dependencies
- As a practical estimate, use at least 4 GB system RAM; 8 GB is more comfortable. CPU indexing can take longer on slower machines.
- An OpenAI API key is optional. Without one, the app answers by quoting a matching source sentence or abstains. With one, OpenAI synthesizes an answer from retrieved passages.

## Run locally

From this directory, create an environment and install dependencies.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` if you want OpenAI-synthesized answers. Add your key to `OPENAI_API_KEY`; never commit `.env` or paste a real key into `.env.example`. The app loads `.env` automatically. `OPENAI_MODEL` defaults to `gpt-4.1-mini`.

Start Docwise:

```bash
python -m streamlit run app.py
```

On first launch, choose **Index sample PDF** in the app or upload your own PDF documents. Text extraction and embeddings run locally. Scanned/image-only PDFs need OCR before upload.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | unset | Optional key for synthesized answers. If unset, the local extractive fallback is used. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model used when a key is configured. |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model for passages and questions. |
| `SIMILARITY_THRESHOLD` | `0.39` | Minimum cosine similarity for retrieved passages to be considered. Increase it to encourage more abstentions; tune using your own questions. |
| `VECTOR_DB_PATH` | `data/vectors.sqlite3` | Optional custom path for the persistent SQLite index. |

The model cache and SQLite index are stored under `data/` by default. Delete the local index to clear the library; it will be rebuilt when you index documents again. `data/` is excluded from Git.

## Evaluation

The included dataset contains 25 questions: 19 answerable from the sample PDF and 6 it cannot answer. Run the benchmark from the repository root:

```bash
python evaluate.py
```

To evaluate a directory of your own PDFs:

```bash
python evaluate.py path/to/pdfs --threshold 0.39
```

The benchmark uses a temporary SQLite index, so it does not clear or replace the app's saved document library. It reports whether retrieved passages contain expected evidence, threshold-only abstentions, local-answer abstentions, and a combined pass rate. The expected terms and answerability labels in `evaluation/questions.csv` should be reviewed and adapted to match any replacement corpus.

### Recorded sample result

On the bundled fictional PDF, the benchmark found expected evidence for **18 of 19** answerable questions. The similarity threshold alone rejected **4 of 6** unanswerable questions; the local extractive answer path abstained on **5 of 6**. The combined evidence/abstention check passed **23 of 25 (92%)**. One spring-term date was missed, and one question about gym hours received a false answer because a semantically related passage scored above threshold. Full details are in [`evaluation/results.md`](evaluation/results.md).

This is a small demo benchmark, not an accuracy guarantee for other documents. OpenAI answer synthesis was not included in the recorded score. Review generated answers and citations against your source PDFs, and tune the threshold using a representative evaluation set.

## Data handling

- PDF extraction, passage chunking, embeddings, vector storage, and retrieval are local.
- The model weights are downloaded from Hugging Face on first use and cached locally.
- If `OPENAI_API_KEY` is set, the question and retrieved text passages are sent to OpenAI for answer synthesis. If no key is set, no question or passage is sent to OpenAI.
- Do not index confidential documents unless the data handling of any configured answer provider is appropriate for those documents.

## Push this project to GitHub

Use this directory (`outputs/rag-chatbot`) as the repository root. Create an empty repository on GitHub, then run these commands here, replacing the URL with your repository URL:

```bash
git init
git add .
git commit -m "Build PDF RAG chatbot"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

The `.gitignore` excludes `.env`, Python environments/caches, the local vector database, and model cache. The demo PDF, source text, evaluation questions, and recorded results are included in the repository.

## Implementation notes

- PDF text extraction: `pypdf`
- Chunking: page-preserving passages, approximately 850 characters with 140-character overlap
- Embeddings: Sentence Transformers `all-MiniLM-L6-v2`, CPU inference
- Vector store: SQLite with normalized float vectors and cosine-similarity ranking
- Answer generation: OpenAI Responses API when configured; local extractive fallback otherwise
- Interface: Streamlit
