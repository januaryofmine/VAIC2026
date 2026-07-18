"""Prep-pack router tests with the DB dependency overridden and services stubbed."""

from fastapi.testclient import TestClient

import app.routers.documents as documents_router
from app.deps import get_db
from app.main import app

_DOC_ID = "11111111-1111-1111-1111-111111111111"


def _fake_db():
    yield None


def _client() -> TestClient:
    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_get_prep_pack_ok(monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "get_prep_pack",
        lambda conn, doc_id: {
            "document_id": _DOC_ID, "filename": "x.pdf",
            "summary": {"context": "c"}, "terms": None, "questions": None,
        },
    )
    r = _client().get(f"/api/documents/{_DOC_ID}/prep-pack")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == {"context": "c"} and body["terms"] is None


def test_get_prep_pack_404(monkeypatch):
    monkeypatch.setattr(documents_router, "get_prep_pack", lambda conn, doc_id: None)
    assert _client().get(f"/api/documents/{_DOC_ID}/prep-pack").status_code == 404


def test_put_prep_pack_ok(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        documents_router,
        "upsert_prep_pack",
        lambda conn, doc_id, kind, value: seen.update(kind=kind, value=value),
    )
    r = _client().put(
        f"/api/documents/{_DOC_ID}/prep-pack",
        json={"kind": "questions", "value": ["q1", "q2"]},
    )
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert seen == {"kind": "questions", "value": ["q1", "q2"]}


def test_put_prep_pack_invalid_kind_400(monkeypatch):
    def _raise(conn, doc_id, kind, value):
        raise ValueError("invalid prep-pack kind")

    monkeypatch.setattr(documents_router, "upsert_prep_pack", _raise)
    r = _client().put(f"/api/documents/{_DOC_ID}/prep-pack", json={"kind": "bad", "value": 1})
    assert r.status_code == 400
