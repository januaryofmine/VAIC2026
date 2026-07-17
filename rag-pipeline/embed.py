"""Embedding via multilingual-e5-large.

e5 REQUIRES task prefixes: 'passage: ' for indexed text, 'query: ' for searches.
Wrong/missing prefix noticeably degrades recall.
"""

from __future__ import annotations

from typing import Protocol

from config import config as cfg


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class E5Embedder:
    """Real embedder. Loads the model lazily on first use (~2GB download, once)."""

    def __init__(
        self,
        model_name: str = cfg.embedding_model,
        batch_size: int = cfg.embedding_batch_size,
    ):
        self._model_name = model_name
        self._batch_size = batch_size
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        prefixed = [cfg.embedding_prefix_document + t for t in texts]
        vectors = model.encode(
            prefixed, batch_size=self._batch_size, normalize_embeddings=True
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        vector = model.encode(
            [cfg.embedding_prefix_query + text], normalize_embeddings=True
        )[0]
        return vector.tolist()
