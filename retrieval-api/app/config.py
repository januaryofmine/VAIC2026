from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    # Shared-secret gate (S1). Empty = open (local dev). When set, every /api route
    # except /api/healthz requires header `X-API-Key: <api_key>`. Set it on the
    # public cloud host; the Nuxt proxy forwards the same key.
    api_key: str = ""
    max_upload_mb: int = 25  # reject oversized ingest uploads (DoS guard)

    # embedding (query side) — must match the ingestion model (multilingual-e5-large)
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_prefix_query: str = "query: "

    # hybrid retrieval (dense vector + Postgres full-text, fused with RRF)
    retrieval_top_k: int = 10
    over_fetch_multiplier: int = 6  # candidate pool per arm = top_k * this
    rrf_k: int = 60  # reciprocal rank fusion constant
    min_chunk_chars: int = 30  # skip noise chunks (headings/page numbers) at query time

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
