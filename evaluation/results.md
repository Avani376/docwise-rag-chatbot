# Demo evaluation results

- **Run date:** 2026-10-29
- **Corpus:** bundled fictional Northstar University policy PDF (2 pages)
- **Python:** 3.11
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` on CPU
- **Similarity threshold:** 0.39
**Questions:** 25 total (19 answerable, 6 unanswerable)

| Measure | Verified result |
|---|---:|
| Answerable questions with expected evidence in retrieved passages | 18/19 (95%) |
| Unanswerable questions rejected by similarity threshold alone | 4/6 (67%) |
| Unanswerable questions declined by the local extractive answer path | 6/6 (100%) |
| Combined evidence and abstention checks | 24/25 (96%) |

The retrieval miss remains the spring-semester start-date question. The strengthened local fallback now abstains on all six unsupported questions, including the previously false-positive campus-gym-hours query. The similarity threshold still admits semantically related passages for two unsupported questions, which is why the local evidence check remains important.

The benchmark uses a temporary SQLite index, so it does not clear or replace the app's normal library. It measures whether threshold-qualified retrieval contains the expected evidence and whether the local extractive path abstains; it does **not** score OpenAI-generated answer quality. A separate manual smoke check returned the local answer “The fall semester begins September 3. [1]” with `northstar_student_policy.pdf`, page 1, in the retrieved-evidence panel. OpenAI synthesis was not exercised because no API key was configured.

This is a small demonstration benchmark on invented content, not an accuracy guarantee for other PDFs. For a real project, replace the corpus and expected terms with reviewed documents and questions, then evaluate the retrieval and abstention behavior again.
