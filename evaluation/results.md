# Demo evaluation results

**Run date:** 2026-10-29  
**Corpus:** bundled fictional Northstar University policy PDF (2 pages)  
**Model:** `sentence-transformers/all-MiniLM-L6-v2`, CPU  
**Similarity threshold:** 0.39  
**Questions:** 25 total (19 answerable, 6 unanswerable)

| Measure | Result |
|---|---:|
| Answerable questions with expected evidence in retrieved passages | 18/19 (95%) |
| Unanswerable questions rejected by similarity threshold alone | 4/6 (67%) |
| Unanswerable questions declined by the local extractive answer path | 5/6 (83%) |
| Combined evidence and abstention checks | 23/25 (92%) |

The retrieval miss was the spring-semester start-date question. The local fallback incorrectly answered the campus gym weekend-hours question because a semantically similar passage scored above threshold. The summer-housing question also retrieved a related passage, but the local answer path abstained because it could not find a matching source sentence.

With no API key configured, the chatbot uses an extractive fallback. A manual smoke check for “When does the fall semester begin?” returned “The fall semester begins September 3. [1]” with the source passage and page available in the citation panel. OpenAI answer synthesis was not tested because no API key was configured.

This is a small demonstration benchmark on invented sample content, not a claim of accuracy on other PDFs. For a real project, replace the corpus and expected terms with the actual documents and reviewed questions, then tune the abstention threshold against those examples.
