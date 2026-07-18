"""Router tests with DB dependency overridden and service/reformulation stubbed."""

import pytest
from fastapi.testclient import TestClient

import app.routers.retrieve as retrieve_router
from app.deps import get_db
from app.main import app

_DOC_ID = "11111111-1111-1111-1111-111111111111"


def _fake_db():
    yield None


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


def test_retrieve_ok(monkeypatch):
    monkeypatch.setattr(retrieve_router, "reformulate_query", lambda q, **kw: q)
    monkeypatch.setattr(
        retrieve_router,
        "retrieve",
        lambda conn, q, doc, top_k, **kw: [
            {"id": "a", "position": 0, "page": 2, "section": "Điều 1", "text": "t", "score": 0.87}
        ],
    )
    r = TestClient(app).post(
        "/api/retrieve", json={"question": "hỏi gì đó", "document_id": _DOC_ID}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reformulated_query"] == "hỏi gì đó"
    assert body["chunks"][0]["section"] == "Điều 1"
    assert body["chunks"][0]["page"] == 2
    assert body["chunks"][0]["score"] == 0.87


def test_retrieve_uses_reformulated_query(monkeypatch):
    monkeypatch.setattr(retrieve_router, "reformulate_query", lambda q, **kw: "TRUY VẤN VIẾT LẠI")
    captured = {}

    def _fake_retrieve(conn, q, doc, top_k, **kw):
        captured["q"] = q
        return []

    monkeypatch.setattr(retrieve_router, "retrieve", _fake_retrieve)
    r = TestClient(app).post(
        "/api/retrieve", json={"question": "gốc", "document_id": _DOC_ID}
    )
    assert r.status_code == 200
    assert captured["q"] == "TRUY VẤN VIẾT LẠI"  # retrieval uses the reformulated query


def _stub_stage1(monkeypatch, captured):
    """Stub reformulation + stage-1 retrieval, recording the top_k it was asked for."""
    monkeypatch.setattr(retrieve_router, "reformulate_query", lambda q, **kw: q)

    def _fake_retrieve(conn, q, doc, top_k, **kw):
        captured["fetch_k"] = top_k
        return [
            {"id": str(i), "position": i, "page": 1, "section": None, "text": f"t{i}",
             "score": 0.5}
            for i in range(top_k)
        ]

    monkeypatch.setattr(retrieve_router, "retrieve", _fake_retrieve)


def test_stage1_fetches_only_top_k_when_reranker_off(monkeypatch):
    captured = {}
    _stub_stage1(monkeypatch, captured)
    r = TestClient(app).post(
        "/api/retrieve", json={"question": "q", "document_id": _DOC_ID, "top_k": 5}
    )
    assert r.status_code == 200
    assert captured["fetch_k"] == 5  # no second stage → no reason to over-fetch
    assert r.json()["reranked"] is False


def test_stage1_fetches_wide_candidate_pool_when_reranker_on(monkeypatch):
    """The reranker can only promote a chunk stage 1 returned, so with rerank on,
    stage 1 must fetch retrieval_candidates (not top_k)."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "reranker_enabled", True)
    monkeypatch.setattr(settings, "retrieval_candidates", 30)

    captured = {}
    _stub_stage1(monkeypatch, captured)
    # Keep the cross-encoder out of it: assert the plumbing, not the model.
    monkeypatch.setattr(
        retrieve_router, "rerank", lambda q, rows, top_k, model: rows[:top_k]
    )

    r = TestClient(app).post(
        "/api/retrieve", json={"question": "q", "document_id": _DOC_ID, "top_k": 5}
    )
    assert r.status_code == 200
    assert captured["fetch_k"] == 30  # wide pool handed to stage 2
    body = r.json()
    assert len(body["chunks"]) == 5  # narrowed back down for the caller
    assert body["reranked"] is True


def test_retrieve_bad_uuid_422():
    r = TestClient(app).post("/api/retrieve", json={"question": "x", "document_id": "nope"})
    assert r.status_code == 422


def test_retrieve_missing_document_id_422():
    r = TestClient(app).post("/api/retrieve", json={"question": "x"})
    assert r.status_code == 422
