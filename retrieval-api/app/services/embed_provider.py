"""Pick the embedding backend by config: 'gemini' (API, no torch) or 'e5' (local).

Keeps retrieval.py / ingest.py provider-agnostic. The document-side embedder is
returned as an object with `embed_documents` so it can be injected into ingestion.
"""

from __future__ import annotations

from app.config import get_settings


def embed_query(text: str) -> list[float]:
    if get_settings().embedding_provider == "gemini":
        from app.services.gemini_embed import get_embedder

        return get_embedder().embed_query(text)
    from app.services.embedding import embed_query as e5_embed_query

    return e5_embed_query(text)


def get_document_embedder():
    """Embedder with `embed_documents(list[str]) -> list[list[float]]` for ingestion.
    Returns None for the e5 path (ingest falls back to rag-pipeline's E5Embedder)."""
    if get_settings().embedding_provider == "gemini":
        from app.services.gemini_embed import get_embedder

        return get_embedder()
    return None
