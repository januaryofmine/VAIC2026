"""Router tests with the DB dependency overridden and the service stubbed."""

from fastapi.testclient import TestClient

import app.routers.documents as documents_router
from app.deps import get_db
from app.main import app

_DOC_ID = "11111111-1111-1111-1111-111111111111"


def _fake_db():
    yield None  # service is stubbed, so the connection is never used


def _client() -> TestClient:
    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_get_full_document_ok(monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "fetch_full_document",
        lambda conn, doc_id: {
            "id": _DOC_ID,
            "filename": "x.pdf",
            "doc_type": "pdf",
            "page_count": 3,
            "status": "ready",
            "chunks": [
                {"id": "a", "position": 0, "page": 1, "section": "Điều 1", "text": "t0"},
                {"id": "b", "position": 1, "page": 1, "section": "Điều 1", "text": "t1"},
            ],
        },
    )
    r = _client().get(f"/api/documents/{_DOC_ID}/full")
    assert r.status_code == 200
    body = r.json()
    assert body["chunk_count"] == 2
    assert [c["position"] for c in body["chunks"]] == [0, 1]
    assert "embedding" not in body["chunks"][0]  # plain-fetch: no vectors leaked


def test_get_full_document_404(monkeypatch):
    monkeypatch.setattr(documents_router, "fetch_full_document", lambda conn, doc_id: None)
    r = _client().get(f"/api/documents/{_DOC_ID}/full")
    assert r.status_code == 404


def test_invalid_uuid_is_422():
    r = _client().get("/api/documents/not-a-uuid/full")
    assert r.status_code == 422


def test_healthz():
    assert _client().get("/api/healthz").json() == {"status": "ok"}
