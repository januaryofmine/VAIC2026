import logging

import psycopg
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_db
from app.models import RetrieveChunk, RetrieveRequest, RetrieveResponse
from app.services.reformulation import reformulate_query
from app.services.reranking import rerank
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
    # Two-stage retrieval: when the cross-encoder runs, stage 1 must hand it a WIDER
    # pool than the caller asked for — the reranker can only promote a chunk that
    # stage 1 actually returned. Fetching just top_k here would let it reorder the
    # same k rows and never rescue a correct chunk that ranked, say, 12th.
    fetch_k = (
        max(top_k, settings.retrieval_candidates) if settings.reranker_enabled else top_k
    )
    rows = retrieve(
        conn,
        reformulated,
        str(req.document_id),
        fetch_k,
        over_fetch_multiplier=settings.over_fetch_multiplier,
        rrf_k=settings.rrf_k,
        min_chunk_chars=settings.min_chunk_chars,
    )
    # Optional 2nd-stage cross-encoder rerank over the fused candidates.
    if settings.reranker_enabled:
        rows = rerank(reformulated, rows, top_k, settings.reranker_model)
    logger.info(
        "retrieve doc=%s q=%r -> %d chunks (rerank=%s, stage1=%d)",
        req.document_id, reformulated, len(rows), settings.reranker_enabled, fetch_k,
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
    return RetrieveResponse(
        chunks=chunks, reformulated_query=reformulated, reranked=settings.reranker_enabled
    )
