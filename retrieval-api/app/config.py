from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    # Shared-secret gate (S1). Empty = open (local dev). When set, every /api route
    # except /api/healthz requires header `X-API-Key: <api_key>`. Set it on the
    # public cloud host; the Nuxt proxy forwards the same key.
    api_key: str = ""
    max_upload_mb: int = 25  # reject oversized ingest uploads (DoS guard)

    # embedding (query side) — must match the ingestion model / dim.
    # provider: "e5" (self-hosted sentence-transformers) | "gemini" (API, no torch).
    embedding_provider: str = "e5"
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_prefix_query: str = "query: "
    gemini_api_key: str = ""

    # hybrid retrieval (dense vector + Postgres full-text, fused with RRF)
    retrieval_top_k: int = 10
    over_fetch_multiplier: int = 6  # candidate pool per arm = top_k * this
    rrf_k: int = 60  # reciprocal rank fusion constant
    min_chunk_chars: int = 30  # skip noise chunks (headings/page numbers) at query time

    # reranking (optional 2nd stage). Disabled by default → identical old behavior.
    # When enabled: retrieve `retrieval_candidates` by cosine, then cross-encoder
    # re-ranks down to retrieval_top_k. Point reranker_model at the fine-tuned dir.
    reranker_enabled: bool = False
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    retrieval_candidates: int = 30

    # reformulation (optional LLM query rewrite). "none" = passthrough (no LLM call).
    reformulation_provider: str = "none"  # "none" | "anthropic"
    reformulation_model: str = "claude-haiku-4-5-20251001"
    anthropic_api_key: str = ""

    model_config = {"env_file": "../.env", "extra": "ignore"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
