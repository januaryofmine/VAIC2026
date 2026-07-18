"""Upload → ingest endpoint (cloud replacement for the UI subprocess call).

Local dev: the Nuxt UI shells out to rag-pipeline directly. In the cloud (UI on
Vercel = serverless Node, no Python), that can't work — so the container that
co-locates retrieval-api + rag-pipeline exposes ingestion over HTTP here.

Async: the heavy parse/embed runs on a background thread. We return the moment the
document row exists (via rag-pipeline's `on_created` hook) with status "processing"
— mirroring the local subprocess flow — so the UI returns fast and polls
`/documents/{id}/status`. Blocking waits are fine here: this is a sync endpoint,
so FastAPI runs it in a threadpool (the event loop is never blocked).

rag-pipeline is imported lazily (RAG_PIPELINE_DIR on sys.path) so importing this
router never requires rag-pipeline to be present — local retrieval-api keeps working.
This deploy keeps the self-hosted e5 embedder (no provider swap).
"""

import logging
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Where rag-pipeline's modules (ingest.py, parse.py, embed.py, db.py) live in the
# container. Overridable for other layouts.
RAG_PIPELINE_DIR = os.environ.get("RAG_PIPELINE_DIR", "/app/rag-pipeline")

_embedder = None  # reuse one E5 embedder across uploads

# How long to wait for the row to be created before giving up (parse of a big PDF
# can take a few seconds before the id is emitted; embedding continues after).
_EARLY_TIMEOUT_S = 120


def _load_rag():
    if RAG_PIPELINE_DIR not in sys.path:
        sys.path.insert(0, RAG_PIPELINE_DIR)
    import db as rag_db  # noqa: E402
    from embed import E5Embedder  # noqa: E402
    from ingest import ingest as rag_ingest  # noqa: E402

    return rag_db, rag_ingest, E5Embedder


@router.post("/ingest")
def ingest_endpoint(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
) -> dict:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    name = Path(file.filename or "upload").name
    suffix = Path(name).suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="only .pdf or .docx accepted")

    data = file.file.read()  # sync endpoint → read the underlying file directly
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
    tmp_path.write_bytes(data)

    created: dict = {}
    failure: dict = {}
    ready = threading.Event()

    def _on_created(doc_id: str) -> None:
        created["id"] = doc_id
        ready.set()

    def _run() -> None:
        try:
            conn = rag_db.connect(settings.database_url)
            try:
                rag_ingest(
                    str(tmp_path), conn, _embedder,
                    user_id=user_id, on_created=_on_created,
                )
            finally:
                conn.close()
        except Exception as e:  # unblock the waiter so it can report the failure
            logger.error("ingest failed for %s: %s", name, e, exc_info=True)
            failure["error"] = str(e)
            ready.set()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    threading.Thread(target=_run, daemon=True).start()

    if not ready.wait(timeout=_EARLY_TIMEOUT_S):
        raise HTTPException(status_code=504, detail="ingestion did not start in time")
    if "id" not in created:
        raise HTTPException(
            status_code=500, detail=f"ingest failed: {failure.get('error', 'unknown')}"
        )

    logger.info("ingesting %s -> document_id=%s (background)", name, created["id"])
    return {"document_id": created["id"], "filename": name, "status": "processing"}
