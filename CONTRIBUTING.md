# Contributing to Docwise

Thanks for improving Docwise. Keep changes small, evidence-driven, and faithful to its core promise: answers must remain traceable to the original PDF page or clearly abstain.

## Development setup

Use Python 3.11 when possible. It is the version used for the verified benchmark and Vercel image.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`OPENAI_API_KEY` is optional. Never commit `.env`, credentials, private PDFs, SQLite databases, model caches, or generated local runtime files.

## Validate a change

Run the narrowest relevant checks before committing. From the repository root:

```powershell
python -m py_compile app.py rag.py evaluate.py
python -m unittest discover -s tests -v
python evaluate.py
python -m streamlit run app.py
```

The compile check catches syntax/import parsing issues. The regression tests cover page attribution, abstention, duplicate-index avoidance, library cleanup, and OpenAI-failure fallback. The benchmark uses a temporary SQLite database rather than the normal local library; it measures retrieval evidence and local abstention on the fictional corpus, not general model accuracy. A browser smoke test should index the sample PDF, answer the fall-semester question with page-1 evidence, and abstain for the fictional campus-gym question.

If dependencies are not installed, install them from `requirements.txt` rather than marking a check as passed. Record any unrun validation honestly in the pull request or commit handoff.

## Engineering guardrails

- Preserve the PDF → page-aware chunks → local embeddings → SQLite → retrieval → answer/abstention flow unless a concrete issue requires a change.
- Keep the original filename and one-based PDF page on every chunk and displayed citation.
- Never silently turn failed retrieval or provider synthesis into an apparently evidence-backed answer.
- Keep the API-key-free local fallback functional. Optional synthesis must receive only the question and retrieved passages, not the whole PDF.
- Test threshold changes against both answerable and unsupported questions; do not tune solely for the bundled benchmark.
- Do not add model weights, vector databases, caches, screenshots with private data, or large binaries without a specific repository need.
- Update the README or a guide when user-facing behavior, configuration, evaluation methodology, or deployment behavior changes.

## Visual assets

The banner is reproducible and intentionally code-rendered so its workflow labels reflect the actual implementation.

```powershell
python tools/generate_docwise_banner.py
```

This regenerates `assets/docwise-banner.gif` and `assets/docwise-banner.png`. Review both outputs before committing. The README uses fixed, verified raw GitHub asset URLs for the banner because GitHub's branch-level CDN can serve an older binary immediately after a push.

## Commit and review checklist

Before publishing a cohesive change, inspect `git diff --check`, `git status`, and the exact staged files. Confirm that links resolve, no secret or private document is included, and the existing `main` history is not rewritten. Use ordinary commits and pushes only; never force-push.

For deployment-specific checks, use the [deployment runbook](docs/DEPLOYMENT.md).
