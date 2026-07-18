"""Upload → ingest endpoint (cloud replacement for the UI subprocess call).

Local dev: the Nuxt UI shells out to rag-pipeline directly. In the cloud (UI on
Vercel = serverless Node, no Python), that can't work — so the container that
co-locates retrieval-api + rag-pipeline exposes ingestion over HTTP here.

rag-pipeline is imported lazily (its modules live on RAG_PIPELINE_DIR, added to
sys.path only when this endpoint is first hit) so importing this router never
requires rag-pipeline to be present — local retrieval-api keeps working.

This deploy keeps the self-hosted e5 embedder (no provider swap), so ingestion
uses rag-pipeline's E5Embedder directly, reused across uploads.
"""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Where rag-pipeline's modules (ingest.py, parse.py, embed.py, db.py) live in the
# container. Overridable for other layouts.
RAG_PIPELINE_DIR = os.environ.get("RAG_PIPELINE_DIR", "/app/rag-pipeline")

_embedder = None  # reuse one E5 embedder across uploads


def _load_rag():
    if RAG_PIPELINE_DIR not in sys.path:
        sys.path.insert(0, RAG_PIPELINE_DIR)
    import db as rag_db  # noqa: E402
    from embed import E5Embedder  # noqa: E402
    from ingest import ingest as rag_ingest  # noqa: E402

    return rag_db, rag_ingest, E5Embedder


@router.post("/ingest")
async def ingest_endpoint(file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    name = Path(file.filename or "upload").name
    suffix = Path(name).suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="only .pdf or .docx accepted")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"file too large (max {settings.max_upload_mb}MB)"
        )

    try:
        rag_db, rag_ingest, E5Embedder = _load_rag()
    except Exception as e:  # rag-pipeline not available (e.g. local retrieval-api)
        logger.error("rag-pipeline unavailable: %s", e)
        raise HTTPException(status_code=501, detail="ingestion not available on this host")

    global _embedder
    if _embedder is None:
        _embedder = E5Embedder()  # self-hosted e5; this deploy keeps e5 (no gemini)

    # Preserve the original filename (rag_ingest records Path(path).name).
    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir) / name
    try:
        tmp_path.write_bytes(data)
        conn = rag_db.connect(settings.database_url)
        try:
            doc_id = rag_ingest(str(tmp_path), conn, _embedder)
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ingest failed for %s: %s", name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ingest failed: {e}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    logger.info("ingested %s -> document_id=%s", name, doc_id)
    return {"document_id": doc_id, "filename": name}
