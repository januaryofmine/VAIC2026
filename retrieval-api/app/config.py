from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    # embedding (query side) — must match the ingestion model (multilingual-e5-large)
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_prefix_query: str = "query: "
    retrieval_top_k: int = 5

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
