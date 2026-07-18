"""Wiring test for the reranker in the /retrieve endpoint (H1 over-fetch).

Verifies the fix for review finding H1: when reranking is enabled, stage-1 must
OVER-FETCH `retrieval_candidates` (not top_k) and the reranker trims to top_k.
retrieve() + rerank() are stubbed so no DB or model is needed.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.retrieve as rr
from app.config import Settings
from app.deps import get_db
from app.main import app

_DOC = "11111111-1111-1111-1111-111111111111"


def _fake_db():
    yield None


def _settings(**over):
    base = dict(
        database_url="postgresql://x", retrieval_top_k=10, over_fetch_multiplier=6,
        rrf_k=60, min_chunk_chars=30, retrieval_candidates=30,
        reformulation_provider="none",
    )
    base.update(over)
    return Settings(**base)


def _install(monkeypatch, settings):
    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[rr.get_settings] = lambda: settings
    monkeypatch.setattr(rr, "reformulate_query", lambda q, **k: q)  # identity, no LLM
    calls = {"retrieve_topk": None, "rerank_topk": None, "rerank_called": False}

    def fake_retrieve(conn, query, doc, top_k, **kwargs):
        calls["retrieve_topk"] = top_k
        return [{"id": f"c{i}", "position": i, "page": 1, "section": None, "text": f"t{i}", "score": 0.5}
                for i in range(top_k)]

    def fake_rerank(query, rows, top_k, model_name):
        calls["rerank_called"] = True
        calls["rerank_topk"] = top_k
        return rows[:top_k]

    monkeypatch.setattr(rr, "retrieve", fake_retrieve)
    monkeypatch.setattr(rr, "rerank", fake_rerank)
    return calls


def teardown_function():
    app.dependency_overrides.clear()


def _body():
    return {"question": "phạm vi điều chỉnh?", "document_id": _DOC, "history": [], "top_k": 10}


def test_reranker_enabled_overfetches_candidates_then_trims(monkeypatch):
    calls = _install(monkeypatch, _settings(reranker_enabled=True))
    r = TestClient(app).post("/api/retrieve", json=_body())
    assert r.status_code == 200
    assert calls["retrieve_topk"] == 30   # H1: stage-1 over-fetches retrieval_candidates
    assert calls["rerank_called"] is True
    assert calls["rerank_topk"] == 10     # reranker trims to top_k
    assert len(r.json()["chunks"]) == 10


def test_reranker_disabled_keeps_old_path(monkeypatch):
    calls = _install(monkeypatch, _settings(reranker_enabled=False))
    r = TestClient(app).post("/api/retrieve", json=_body())
    assert r.status_code == 200
    assert calls["retrieve_topk"] == 10   # no over-fetch
    assert calls["rerank_called"] is False
    assert len(r.json()["chunks"]) == 10
