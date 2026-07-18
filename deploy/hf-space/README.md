---
title: VAIC Retrieval API
emoji: 📄
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# VAIC2026 — Retrieval API (retrieval-api + rag-pipeline)

FastAPI service for the Paperless Meetings system:

- `POST /api/ingest` — upload PDF/DOCX → parse → chunk → embed (e5) → Postgres/pgvector
- `POST /api/retrieve` — vector search (+ optional cross-encoder reranker) with page/section citations
- `GET  /api/documents/{id}/full` — full ordered chunk list
- `GET  /api/healthz`

## Required environment (Space → Settings → Variables & secrets)

| Name | Example | Notes |
|------|---------|-------|
| `DATABASE_URL` | `postgresql://...supabase.co:5432/postgres` | Supabase (pgvector). **Secret.** |
| `CORS_ORIGINS` | `["https://your-ui.vercel.app"]` | JSON list; the Vercel UI origin |
| `RERANKER_ENABLED` | `false` | `true` to turn on the reranker stage |
| `RERANKER_MODEL` | `honglongdng/bge-reranker-dienbien` | HF model id or local path |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | only if query reformulation via Claude is enabled |

The embedding model (multilingual-e5-large) is baked into the image.
