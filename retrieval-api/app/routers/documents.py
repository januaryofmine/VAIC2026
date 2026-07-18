import logging
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.deps import get_db
from app.models import (
    ChatMessage,
    ChatMessageAppendRequest,
    ChatMessagesResponse,
    DocumentChunk,
    DocumentListItem,
    DocumentListResponse,
    DocumentOwnerResponse,
    DocumentStatusResponse,
    FullDocumentResponse,
    PrepPackResponse,
    PrepPackUpsertRequest,
)
from app.services.chat import append_chat_message, list_chat_messages
from app.services.documents import (
    fetch_document_file,
    fetch_document_owner,
    fetch_document_status,
    fetch_full_document,
    list_documents,
)
from app.services.prep_packs import get_prep_pack, upsert_prep_pack

logger = logging.getLogger(__name__)
router = APIRouter()

# Original-file MIME types so the browser can render the blob inline (PDF viewer).
_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/documents", response_model=DocumentListResponse)
def get_documents(
    user_id: UUID,  # required query param — owner scope
    type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    conn: psycopg.Connection = Depends(get_db),
) -> DocumentListResponse:
    rows = list_documents(conn, str(user_id), type, date_from, date_to, q)
    return DocumentListResponse(documents=[DocumentListItem(**r) for r in rows])


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


@router.get("/documents/{document_id}/owner", response_model=DocumentOwnerResponse)
def get_document_owner(
    document_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> DocumentOwnerResponse:
    # Owner-only lookup so the BFF can authorize a request before any data-serving
    # endpoint runs. Returns just the owner id (or null); never document content.
    row = fetch_document_owner(conn, str(document_id))
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentOwnerResponse(document_id=str(document_id), user_id=row["user_id"])


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> FileResponse:
    row = fetch_document_file(conn, str(document_id))
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = row["storage_path"]
    if not path or not os.path.isfile(path):
        # Row exists but the original blob was never stored (older doc) or is missing.
        raise HTTPException(status_code=404, detail="original file not available")
    media_type = _MEDIA_TYPES.get(row["doc_type"], "application/octet-stream")
    # inline so a PDF opens in the browser viewer instead of downloading.
    return FileResponse(
        path,
        media_type=media_type,
        filename=row["filename"],
        content_disposition_type="inline",
    )


@router.get("/documents/{document_id}/prep-pack", response_model=PrepPackResponse)
def get_document_prep_pack(
    document_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> PrepPackResponse:
    row = get_prep_pack(conn, str(document_id))
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    return PrepPackResponse(**row)


@router.put("/documents/{document_id}/prep-pack")
def put_document_prep_pack(
    document_id: UUID,
    body: PrepPackUpsertRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> dict:
    try:
        upsert_prep_pack(conn, str(document_id), body.kind, body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/documents/{document_id}/chat/messages", response_model=ChatMessagesResponse)
def get_chat_messages(
    document_id: UUID,
    conn: psycopg.Connection = Depends(get_db),
) -> ChatMessagesResponse:
    rows = list_chat_messages(conn, str(document_id))
    return ChatMessagesResponse(messages=[ChatMessage(**r) for r in rows])


@router.post("/documents/{document_id}/chat/messages")
def post_chat_message(
    document_id: UUID,
    body: ChatMessageAppendRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> dict:
    append_chat_message(conn, str(document_id), body.id, body.role, body.parts, body.metadata)
    return {"ok": True}


@router.get("/healthz")
def health() -> dict:
    return {"status": "ok"}
