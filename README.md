# Paperless 

AI for document processing & meeting preparation, built for the **VAIC 2026**.

## Problem Statement

Provincial-level meetings deal with 40–60-page documents full of specialized legal, administrative, and technical terminology. Officials often receive them just one day before. There is no time to read carefully, so meetings run long re-explaining the basics, and counter-points go unprepared. 

This AI application lets an official **upload a document and, in under a minute, read, understand, and prepare** for the meeting. Every answer grounded in the source with page/section citations.

- [x] **1. Smart summarization**: upload a 40+ page PDF/DOCX -> a structured summary (*context · main content · decision points · impact*) in **< 60s**.
- [x] **2. Terminology highlight & explain**: detect **≥ 10** specialized legal/administrative terms and explain each correctly.
- [x] **3. Suggested critical questions**: auto-generate **≥ 5** quality counter-point questions from the document's content.
- [x] **4. Document-grounded Q&A**: ask in natural Vietnamese. The answer cites the specific **page / Điều-Khoản**.

## Architecture

Single monorepo. 

![Architecture](./docs/paperless.png)

#### Updates

- Per-user document scoping: `users` table + `documents.user_id`, GitHub-login gating, "Tài liệu của tôi" Home (navy + gold).
- Persist the original file (blob storage) with content-hash dedup ([`ffa1712`](https://github.com/januaryofmine/VAIC2026/commit/ffa1712)).
- GitHub OAuth login via `nuxt-auth-utils` ([`b351501`](https://github.com/januaryofmine/VAIC2026/commit/b351501)).
- Plan-and-fan-out Q&A: multi-query, Ask-style retrieval ([`9ef4aaf`](https://github.com/januaryofmine/VAIC2026/commit/9ef4aaf)).
- Token/structure-aware chunking (never splits across `Điều N`) ([`36e2116`](https://github.com/januaryofmine/VAIC2026/commit/36e2116)).
- Async document ingestion with status polling ([`f880481`](https://github.com/januaryofmine/VAIC2026/commit/f880481)).
- Hybrid retrieval: dense vector + Postgres full-text, fused with RRF + neighbor expansion.

## Project Structure

This is a monorepo with several moving parts.

| Directory | Component | Description |
|:--|:--|:--|
| [`paperless-ui/`](./paperless-ui) | UI / BFF | Nuxt 4 app ([AI SDK](https://ai-sdk.dev/) v6): upload, prep-pack, streaming Q&A, GitHub OAuth. Proxies the Python API. |
| [`retrieval-api/`](./retrieval-api) | Retrieval Backend | [FastAPI](https://fastapi.tiangolo.com/) service: hybrid `/api/retrieve`, plain-fetch `/api/documents`, `/api/ingest`, `/api/users`. |
| [`rag-pipeline/`](./rag-pipeline) | RAG Pipeline | Parse → chunk → embed an uploaded PDF/DOCX into pgvector, preserving `page` + `section`. |
| [`db/`](./db) | Database | Postgres 17 + [pgvector](https://github.com/pgvector/pgvector) schema (`init.sql`): users · documents · chunks · chat. |
| [`deploy/`](./deploy) | Deployment | Scripts to load the schema to Supabase and ship the API/UI to the cloud. |
| [`docker-compose.yaml`](./docker-compose.yaml) | Local DB | Brings up Postgres + pgvector for local development. |

## LLMs

Runtime models are configurable via `runtimeConfig.ai` in [`paperless-ui/nuxt.config.ts`](./paperless-ui/nuxt.config.ts) and `retrieval-api/app/config.py`. Chat/summarization run on Anthropic through the AI SDK; embeddings run locally.

| Task | Model | Notes |
|:--|:--|:--|
| Embedding (passage & query) | `intfloat/multilingual-e5-large` | 1024-dim, local (torch). `passage:` / `query:` prefixes. |
| Summarize / Terms / Questions | Claude Haiku 4.5 | Cheap/fast per-chunk pass. |
| Summarize / Terms / Questions | Claude Sonnet 4.6 | Quality structured output. |
| Chat (Q&A over document) | Claude Sonnet 4.6 | Streamed, grounded, cites page/section. |
| Q&A search planning | Claude Haiku 4.5 | Plans the multi-query retrieval strategy. |
| Query reformulation (retrieval) | Claude Haiku 4.5 | Optional; `REFORMULATION_PROVIDER=none` = passthrough. |


## RAG Pipeline

The pipeline grounds the LLM in the **user's uploaded document**. It preserves `page` (PDF) and `section` (`Điều`/`Khoản`, for legal documents) on every chunk so answers can cite them.

> [!NOTE]
> Requires the running Postgres database. See [Local Development](#local-development) for `docker-compose.yaml` setup.

To ingest a document directly from the CLI:

```bash
cd rag-pipeline
uv sync
source ../.env
uv run python ingest.py "<path to .pdf or .docx>"
```

## Local Development

Three services: **Postgres** (Docker), the **retrieval-api** (Python), and the **paperless-ui** (Nuxt).

### Step 1: Setup environment variables

- Copy `.env.sample` to `.env` and fill in your values. Most are self-explanatory.
- `NUXT_SESSION_PASSWORD` is a ≥ 32-character string used to encrypt and sign session cookies (`openssl rand -hex 24`).
- Set `ANTHROPIC_API_KEY` — required for summarization, terms, questions, and chat.

### Step 2: Create a GitHub OAuth App

The application only works when logged in, so create a GitHub OAuth App:

1. Create one at [github.com/settings/applications/new](https://github.com/settings/applications/new).
2. Set the callback URL to `http://localhost:3100/api/auth/github`.
3. Put the Client ID and Secret into `.env` (`NUXT_OAUTH_GITHUB_CLIENT_ID` / `NUXT_OAUTH_GITHUB_CLIENT_SECRET`).

### Step 3: Start Postgres

```bash
docker compose up -d
```

`db/init.sql` runs once on first boot (users · documents · chunks · chat, with the pgvector extension).

### Step 4: Start the retrieval-api

```bash
cd retrieval-api
uv sync
source ../.env
uv run uvicorn app.main:app --port 8001 --reload
```

### Step 5: Start the UI

```bash
cd paperless-ui
npm install
npm run dev   # http://localhost:3100
```

### Step 6: Open the browser

Open [http://localhost:3100](http://localhost:3100), **log in with GitHub**, then upload a 40+ page PDF/DOCX. The document ingests (parse → chunk → embed), and you get the summary, highlighted terms, suggested questions, and a grounded Q&A chat. 

Each answer citing the specific page and `Điều`/`Khoản`.
