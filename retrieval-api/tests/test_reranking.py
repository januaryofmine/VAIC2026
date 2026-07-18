"""Unit tests for the reranking service (no model loaded — _get_model is patched)."""

import app.services.reranking as rr
from app.services.reranking import rerank


class _FakeModel:
    """Returns a preset score per passage text."""

    def __init__(self, scores_by_text):
        self._scores = scores_by_text

    def predict(self, pairs):
        return [self._scores[text] for _query, text in pairs]


def _rows(*texts):
    return [{"id": t, "text": t, "score": 0.5} for t in texts]


def test_reorders_by_cross_encoder_score(monkeypatch):
    monkeypatch.setattr(rr, "_get_model", lambda name: _FakeModel({"a": 0.1, "b": 0.9, "c": 0.5}))
    out = rerank("q", _rows("a", "b", "c"), top_k=3, model_name="x")
    assert [r["id"] for r in out] == ["b", "c", "a"]  # descending by score


def test_truncates_to_top_k(monkeypatch):
    monkeypatch.setattr(rr, "_get_model", lambda name: _FakeModel({"a": 0.1, "b": 0.9, "c": 0.5}))
    out = rerank("q", _rows("a", "b", "c"), top_k=2, model_name="x")
    assert [r["id"] for r in out] == ["b", "c"]


def test_attaches_reranking_score(monkeypatch):
    # report §6: write the cross-encoder score onto each row for observability.
    monkeypatch.setattr(rr, "_get_model", lambda name: _FakeModel({"a": 0.1, "b": 0.9}))
    out = rerank("q", _rows("a", "b"), top_k=2, model_name="x")
    assert out[0]["id"] == "b" and out[0]["reranking_score"] == 0.9
    assert out[1]["id"] == "a" and out[1]["reranking_score"] == 0.1


def test_empty_rows_passthrough():
    assert rerank("q", [], top_k=5, model_name="x") == []


def test_fallback_to_retrieval_order_on_failure(monkeypatch):
    def boom(name):
        raise RuntimeError("model load failed")

    monkeypatch.setattr(rr, "_get_model", boom)
    out = rerank("q", _rows("a", "b", "c"), top_k=2, model_name="x")
    assert [r["id"] for r in out] == ["a", "b"]  # original order, truncated
