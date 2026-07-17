"""Query-side embedding with multilingual-e5-large.

Must match the ingestion model + dim. e5 uses the 'query: ' prefix for searches
(ingestion used 'passage: '). Model is loaded lazily and reused across requests.
"""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        name = get_settings().embedding_model
        logger.info("loading embedding model %s", name)
        _model = SentenceTransformer(name)
    return _model


def embed_query(text: str) -> list[float]:
    settings = get_settings()
    vector = _get_model().encode(
        [settings.embedding_prefix_query + text], normalize_embeddings=True
    )[0]
    return vector.tolist()
