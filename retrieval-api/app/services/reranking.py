"""Second-stage cross-encoder reranking for Q&A retrieval.

Stage 1 (retrieval.py) pulls a wide candidate set by embedding cosine; this stage
re-scores each (question, chunk) pair with a cross-encoder and keeps the best
top_k. The cross-encoder reads the query and passage *together*, so it judges
relevance far more precisely than a bi-encoder — which directly lifts citation
accuracy (deliverable #4 / criteria: Grounding & reliability).

Model: `BAAI/bge-reranker-v2-m3`, optionally fine-tuned on Vietnamese legal data
(see ../../../finetune). Loaded lazily and reused across requests. Disabled by
default: with reranker_enabled=False this module is never imported/loaded, so the
system behaves exactly as before.

Fail-safe: any load/scoring error falls back to the original order (retrieval
still works), mirroring reformulation.py.
"""

import logging

logger = logging.getLogger(__name__)

_model = None
_model_name: str | None = None


def _get_model(model_name: str):
    """Lazy-load and cache the CrossEncoder (reload if the configured name changes)."""
    global _model, _model_name
    if _model is None or _model_name != model_name:
        from sentence_transformers import CrossEncoder

        logger.info("loading reranker model %s", model_name)
        _model = CrossEncoder(model_name)
        _model_name = model_name
    return _model


def rerank(
    query: str,
    rows: list[dict],
    top_k: int,
    model_name: str,
) -> list[dict]:
    """Re-order `rows` (each with a 'text' field) by cross-encoder relevance to
    `query`, returning the top_k. On any failure, returns rows[:top_k] unchanged."""
    if not rows:
        return rows
    try:
        model = _get_model(model_name)
        pairs = [(query, r["text"]) for r in rows]
        scores = model.predict(pairs)
        ranked = sorted(zip(rows, scores), key=lambda rs: float(rs[1]), reverse=True)
        return [row for row, _ in ranked[:top_k]]
    except Exception as e:  # never block retrieval on a reranker problem
        logger.warning("Reranking failed, using retrieval order: %s", e)
        return rows[:top_k]
