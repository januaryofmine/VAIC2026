"""Test doubles so unit tests don't need the 2GB e5 model."""

import math


class FakeEmbedder:
    """Deterministic embedder returning normalized vectors of the configured dim."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        base = (len(text) % 7) + 1
        raw = [((base + i) % 10) / 10.0 for i in range(self.dim)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)
