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
        lambda conn, q, doc, top_k: [
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

    def _fake_retrieve(conn, q, doc, top_k):
        captured["q"] = q
        return []

    monkeypatch.setattr(retrieve_router, "retrieve", _fake_retrieve)
    r = TestClient(app).post(
        "/api/retrieve", json={"question": "gốc", "document_id": _DOC_ID}
    )
    assert r.status_code == 200
    assert captured["q"] == "TRUY VẤN VIẾT LẠI"  # retrieval uses the reformulated query


def test_retrieve_bad_uuid_422():
    r = TestClient(app).post("/api/retrieve", json={"question": "x", "document_id": "nope"})
    assert r.status_code == 422


def test_retrieve_missing_document_id_422():
    r = TestClient(app).post("/api/retrieve", json={"question": "x"})
    assert r.status_code == 422
