---
title: VAIC Retrieval API
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Paperless Meetings — Retrieval API (HF Space)

FastAPI `retrieval-api` + `rag-pipeline` (ingest) in one Docker container. Serves the
Vietnamese legal-document RAG engine: hybrid retrieval, plain-fetch, ingest over HTTP.

- `GET  /api/healthz` — liveness (no auth)
- `POST /api/ingest` — upload PDF/DOCX → parse/chunk/embed/store (auth)
- `POST /api/retrieve` — hybrid vector+FTS search, scoped to a document (auth)
- `GET  /api/documents/{id}/full` · `/status` · `/file` (auth)

Embeddings: self-hosted `multilingual-e5-large` (1024-dim), pre-downloaded at build.

**Auth:** every `/api` route except `/api/healthz` requires header `X-API-Key`
when the `API_KEY` secret is set. **DB:** `DATABASE_URL` secret (Supabase pooler).
Deployed via `deploy/push_hf_space.py`.
