"""Embeddings via the Gemini API (free tier) — replaces the self-hosted e5 model
for the cloud deployment, so the service needs no torch and fits a free host.

Implements the same interface rag-pipeline's ingest expects (`embed_documents`,
`embed_query`), so it can be injected into ingestion as well as query-time search.

Model: `text-embedding-004` (768-dim). Task types matter for retrieval quality:
`RETRIEVAL_QUERY` for the question, `RETRIEVAL_DOCUMENT` for indexed chunks.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"
_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")


class GeminiEmbedder:
    """Gemini embeddings. API key from GEMINI_API_KEY (or passed in)."""

    def __init__(self, api_key: str | None = None, model: str = _MODEL):
        self._key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model = model
        if not self._key:
            raise RuntimeError("GEMINI_API_KEY not set")

    def _embed(self, text: str, task_type: str) -> list[float]:
        url = f"{_BASE}/models/{self._model}:embedContent?key={self._key}"
        payload = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }
        r = httpx.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["embedding"]["values"]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, "RETRIEVAL_QUERY")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # text-embedding-004 has no public batch endpoint on v1beta; embed serially.
        # Chunk counts per doc are modest (tens–low hundreds) so this is fine.
        return [self._embed(t, "RETRIEVAL_DOCUMENT") for t in texts]


_singleton: GeminiEmbedder | None = None


def get_embedder() -> GeminiEmbedder:
    global _singleton
    if _singleton is None:
        _singleton = GeminiEmbedder()
    return _singleton


def embed_query(text: str) -> list[float]:
    """Module-level helper mirroring the old embedding.embed_query signature."""
    return get_embedder().embed_query(text)
