"""Second-stage cross-encoder reranking for Q&A retrieval.

Stage 1 (retrieval.py) pulls a wide candidate set by embedding cosine + full-text
RRF; this stage re-scores each (question, chunk) pair with a cross-encoder that reads
the query and passage *together*, so it judges relevance far more precisely than a
bi-encoder — which lifts citation accuracy (deliverable #4 / Grounding & reliability).

Model: `BAAI/bge-reranker-v2-m3` (multilingual, num_labels=1), optionally fine-tuned
on Vietnamese legal data (see ../../../finetune, Slice 21). Loaded lazily and reused.
Disabled by default: with reranker_enabled=False this module is never imported/loaded,
so behavior is identical to before.

Fail-safe: any load/scoring error falls back to the original order (retrieval still
works), mirroring reformulation.py.

Design refs (local/rerank-technique-deep-research.md §3, §6, §9):
- max_length set at model init → truncation by *tokenizer tokens*, not characters.
- write the score onto each row (`reranking_score`) for observability.
- caller does the over-fetch and the final top_k trim (this only reorders + trims).
"""

import logging

logger = logging.getLogger(__name__)

# Chunks are ~400 tokens (Slice 10); 512 covers a (query, chunk) pair with margin.
_MAX_LENGTH = 512

_model = None
_model_name: str | None = None


def _get_model(model_name: str):
    """Lazy-load and cache the CrossEncoder (reload if the configured name changes).
    max_length caps the tokenized (query, passage) pair — tokenizer truncation, so it
    is correct for Vietnamese (unlike character slicing)."""
    global _model, _model_name
    if _model is None or _model_name != model_name:
        from sentence_transformers import CrossEncoder

        logger.info("loading reranker model %s (max_length=%d)", model_name, _MAX_LENGTH)
        _model = CrossEncoder(model_name, max_length=_MAX_LENGTH)
        _model_name = model_name
    return _model


def rerank(
    query: str,
    rows: list[dict],
    top_k: int,
    model_name: str,
) -> list[dict]:
    """Re-order `rows` (each with a 'text' field) by cross-encoder relevance to
    `query`, attach `reranking_score`, and return the top_k. On any failure, returns
    rows[:top_k] unchanged (never blocks retrieval)."""
    if not rows:
        return rows
    try:
        model = _get_model(model_name)
        pairs = [(query, r["text"]) for r in rows]
        scores = model.predict(pairs)
        ranked = sorted(zip(rows, scores), key=lambda rs: float(rs[1]), reverse=True)
        out = []
        for row, score in ranked[:top_k]:
            row["reranking_score"] = float(score)
            out.append(row)
        return out
    except Exception as e:  # never block retrieval on a reranker problem
        logger.warning("Reranking failed, using retrieval order: %s", e)
        return rows[:top_k]
