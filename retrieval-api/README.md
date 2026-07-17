# retrieval-api

Serving-tier API for Paperless Meetings (FastAPI, :8001).

- **`documents.py`** (Slice 3) — plain-fetch a full document's chunks by
  `document_id`, ordered by `position`. **No embedding, no vector search.**
  Used by the prep-pack endpoints (summarize / terms / questions).
- `retrieval.py` + `reformulation.py` (Slice 4) — vector search for Q&A.

```bash
uv sync
source ../.env
uv run uvicorn app.main:app --port 8001 --reload
# GET http://localhost:8001/api/documents/<uuid>/full
```
