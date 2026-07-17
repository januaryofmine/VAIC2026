import logging

import psycopg
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_db
from app.models import RetrieveChunk, RetrieveRequest, RetrieveResponse
from app.services.reformulation import reformulate_query
from app.services.retrieval import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(
    req: RetrieveRequest,
    settings: Settings = Depends(get_settings),
    conn: psycopg.Connection = Depends(get_db),
) -> RetrieveResponse:
    reformulated = reformulate_query(
        req.question,
        model=settings.reformulation_model,
        provider=settings.reformulation_provider,
        history=req.history,
        anthropic_api_key=settings.anthropic_api_key,
    )
    top_k = req.top_k or settings.retrieval_top_k
    rows = retrieve(conn, reformulated, str(req.document_id), top_k)
    logger.info(
        "retrieve doc=%s q=%r -> %d chunks", req.document_id, reformulated, len(rows)
    )
    chunks = [
        RetrieveChunk(
            id=r["id"],
            position=r["position"],
            page=r["page"],
            section=r["section"],
            text=r["text"],
            score=round(r["score"], 4),
        )
        for r in rows
    ]
    return RetrieveResponse(chunks=chunks, reformulated_query=reformulated)
