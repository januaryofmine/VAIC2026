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

import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.config import get_settings
from app.services.upload_token import verify_upload_token

logger = logging.getLogger(__name__)
router = APIRouter()

# Where rag-pipeline's modules (ingest.py, parse.py, embed.py, db.py) live in the
# container. Overridable for other layouts.
RAG_PIPELINE_DIR = os.environ.get("RAG_PIPELINE_DIR", "/app/rag-pipeline")

_embedder = None  # reuse one E5 embedder across uploads

# How long to wait for the row to be created before giving up (parse of a big PDF
# can take a few seconds before the id is emitted; embedding continues after).
_EARLY_TIMEOUT_S = 120

# The BFF generates 3 kinds (each a map-reduce over the doc) → allow a generous window.
_PREP_PACK_TIMEOUT_S = 600


def _trigger_prep_pack(document_id: str | None, settings) -> None:
    """Ask the BFF to generate + persist the prep-pack once a doc is embedded, so
    summary/terms/questions exist without a user opening the doc (backend-driven).

    Best-effort: no-ops when unconfigured and NEVER raises — a BFF hiccup must not
    fail ingestion (the on-open endpoints remain a fallback).
    """
    if not document_id or not settings.bff_url:
        return
    url = settings.bff_url.rstrip("/") + "/api/internal/prep-pack"
    body = json.dumps({"document_id": document_id}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": settings.api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=_PREP_PACK_TIMEOUT_S) as resp:
            logger.info(
                "prep-pack generation triggered for %s (bff %s)", document_id, resp.status
            )
    except Exception as e:  # noqa: BLE001 — best-effort; log and move on
        logger.warning("prep-pack trigger failed for %s: %s", document_id, e)


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
    x_upload_token: str | None = Header(default=None, alias="X-Upload-Token"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    # Auth (this route is exempt from the global api-key middleware so the browser can
    # upload directly). Two ways in:
    #   • X-Upload-Token — HMAC signed by the BFF; the owner is taken FROM the token
    #     (browser can't forge it), so a browser never needs the API_KEY.
    #   • X-API-Key — trusted server-to-server; the owner comes from the form field.
    # Empty api_key (local dev) leaves the endpoint open.
    if x_upload_token:
        owner = verify_upload_token(x_upload_token, settings.api_key)
        if not owner:
            raise HTTPException(status_code=401, detail="invalid or expired upload token")
    elif settings.api_key:
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="invalid or missing API key")
        owner = user_id
    else:
        owner = user_id  # local dev (no api_key set)

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
                    user_id=owner, on_created=_on_created,
                )
            finally:
                conn.close()
            # Embedding done (doc is 'ready') → generate + store the prep-pack now,
            # server-side, so it never depends on a user opening the doc.
            _trigger_prep_pack(created.get("id"), settings)
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
