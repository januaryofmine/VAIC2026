import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    embedding_model: str
    embedding_prefix_document: str
    embedding_prefix_query: str
    embedding_vector_dim: int
    embedding_batch_size: int
    chunk_max_chars: int
    chunk_min_chars: int


_defaults = Config(
    database_url="",
    embedding_model="intfloat/multilingual-e5-large",
    embedding_prefix_document="passage: ",  # e5: prefix for indexed passages
    embedding_prefix_query="query: ",        # e5: prefix for search queries
    embedding_vector_dim=1024,               # multilingual-e5-large
    embedding_batch_size=32,
    chunk_max_chars=1500,
    chunk_min_chars=200,
)


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


config = Config(
    database_url=os.environ.get("DATABASE_URL", _defaults.database_url),
    embedding_model=os.environ.get("EMBEDDING_MODEL", _defaults.embedding_model),
    embedding_prefix_document=os.environ.get(
        "EMBEDDING_PREFIX_DOCUMENT", _defaults.embedding_prefix_document
    ),
    embedding_prefix_query=os.environ.get(
        "EMBEDDING_PREFIX_QUERY", _defaults.embedding_prefix_query
    ),
    embedding_vector_dim=_int("EMBEDDING_VECTOR_DIM", _defaults.embedding_vector_dim),
    embedding_batch_size=_int("EMBEDDING_BATCH_SIZE", _defaults.embedding_batch_size),
    chunk_max_chars=_int("CHUNK_MAX_CHARS", _defaults.chunk_max_chars),
    chunk_min_chars=_int("CHUNK_MIN_CHARS", _defaults.chunk_min_chars),
)
