import logging
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_db
from app.models import DocumentChunk, DocumentStatusResponse, FullDocumentResponse
from app.services.documents import fetch_document_status, fetch_full_document

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents/{document_id}/full", response_model=FullDocumentResponse)
def get_full_document(
    document_id: UUID,  # FastAPI 422s on a malformed UUID before we touch the DB
    conn: psycopg.Connection = Depends(get_db),
) -> FullDocumentResponse:
    doc = fetch_full_document(conn, str(document_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    logger.info("full document %s -> %d chunks", document_id, len(doc["chunks"]))
    return FullDocumentResponse(
        document_id=doc["id"],
        filename=doc["filename"],
        doc_type=doc["doc_type"],
        page_count=doc["page_count"],
        status=doc["status"],
        chunk_count=len(doc["chunks"]),
        chunks=[DocumentChunk(**c) for c in doc["chunks"]],
    )


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> DocumentStatusResponse:
    row = fetch_document_status(conn, str(document_id))
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentStatusResponse(**row)


@router.get("/healthz")
def health() -> dict:
    return {"status": "ok"}
