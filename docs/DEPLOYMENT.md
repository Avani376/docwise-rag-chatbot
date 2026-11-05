# Docwise deployment runbook

This guide covers the existing Vercel Container Runtime deployment. It is intentionally small: Docwise remains a Streamlit app with a local SQLite index and no external database.

## What is deployed

- **Entry point:** `app.py`
- **Container definition:** `Dockerfile.vercel`
- **Runtime:** Python 3.11 with CPU-only PyTorch from `requirements.txt`
- **HTTP server:** Streamlit, bound to Vercel's `$PORT`
- **Library mode:** forced to `session`
- **Model cache:** `/tmp/docwise-hf`
- **Maximum upload size:** 4 MB

`Dockerfile.vercel` copies only the application, RAG module, requirements, and fictional sample document. It does not package a local vector database, cached model weights, or `.env` file.

## Deploy or redeploy

1. Verify that the current branch is the intended existing branch and that working-tree changes are reviewed and committed.
2. In Vercel, use the existing project connected to this repository's `main` branch and its `Dockerfile.vercel` configuration.
3. Leave `OPENAI_API_KEY` unset for the API-key-free demonstration, or add it only through Vercel's encrypted environment-variable settings. Never put it in Git.
4. Trigger a deployment and inspect the actual build and runtime logs. The CPU PyTorch wheel is deliberate; replacing it with a CUDA build can exceed practical deployment image limits.
5. Open the resulting production URL in a fresh browser session before calling the deployment complete.

The currently verified public deployment is [docwise-rag-chatbot.vercel.app](https://docwise-rag-chatbot.vercel.app). A deployment URL is not proof of a working RAG flow; perform the smoke test below after every material runtime change.

## Production smoke test

1. Load the app in a new browser session.
2. Select **Index sample PDF** and wait for the success message.
3. Ask: `When does the fall semester begin?`
4. Confirm that the answer is grounded, the evidence names `northstar_student_policy.pdf`, and the citation maps to page 1.
5. Ask: `What are the campus gym's weekend opening hours?`
6. Confirm that the app displays **No supported answer** rather than inventing a response.
7. If optional OpenAI synthesis is enabled, confirm that a provider failure is visibly labeled as a local fallback or unsupported result.

## Storage and privacy boundaries

Vercel containers and `/tmp` storage are ephemeral. The SQLite library and Hugging Face cache may disappear after an instance restart or redeployment. The session-scoped design avoids normal cross-browser library searches, but it is not multi-tenant authentication, durable storage, or a formal retention system.

Do not present the hosted demo as suitable for confidential PDFs. Do not persist user uploads, index files, credentials, or model weights in the repository or public object storage without an explicit security and retention design.

## Troubleshoot and roll back

- **Build image too large:** keep the CPU-only PyTorch pin and do not copy runtime caches into the image.
- **First request is slow:** `all-MiniLM-L6-v2` downloads and initializes on cold instances.
- **Upload rejected:** the host request limit and Streamlit's configured 4 MB upload limit apply.
- **RAG flow fails:** inspect deployment logs, reproduce locally with the sample corpus, and confirm `DOCWISE_LIBRARY_MODE=session` is active.
- **Regression after release:** promote a previously verified Vercel deployment through the Vercel dashboard or redeploy the known-good Git commit. Do not rewrite Git history to roll back.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for local validation and [README.md](../README.md) for feature and configuration details.
