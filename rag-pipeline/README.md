# rag-pipeline

Ingestion for Paperless Meetings: **parse → chunk → embed → Postgres/pgvector**.
Runs per uploaded document. Preserves `page` (PDF) and `section` (Điều/Khoản, legal
documents) on every chunk so retrieval can cite them.

```bash
uv sync
source ../.env
uv run python ingest.py "<path to .pdf or .docx>"
```

Modules: `parse.py` (pdftotext / python-docx → blocks with page/section),
`chunk.py` (blocks → chunks, metadata preserved), `embed.py` (multilingual-e5-large,
`passage:`/`query:` prefixes), `db.py` (insert), `ingest.py` (orchestrate + CLI).
