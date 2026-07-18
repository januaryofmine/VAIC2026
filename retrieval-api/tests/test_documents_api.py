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


def test_status_ok(monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "fetch_document_status",
        lambda conn, doc_id: {
            "document_id": _DOC_ID,
            "filename": "x.pdf",
            "doc_type": "pdf",
            "status": "embedding",
            "page_count": 3,
            "chunk_count": 12,
        },
    )
    r = _client().get(f"/api/documents/{_DOC_ID}/status")
    assert r.status_code == 200
    assert r.json()["status"] == "embedding"
    assert r.json()["chunk_count"] == 12


def test_status_404(monkeypatch):
    monkeypatch.setattr(documents_router, "fetch_document_status", lambda conn, doc_id: None)
    assert _client().get(f"/api/documents/{_DOC_ID}/status").status_code == 404


def test_get_file_ok(monkeypatch, tmp_path):
    blob = tmp_path / "orig.pdf"
    blob.write_bytes(b"%PDF-1.4 original bytes")
    monkeypatch.setattr(
        documents_router,
        "fetch_document_file",
        lambda conn, doc_id: {
            "filename": "Nghị quyết.pdf",
            "doc_type": "pdf",
            "storage_path": str(blob),
        },
    )
    r = _client().get(f"/api/documents/{_DOC_ID}/file")
    assert r.status_code == 200
    assert r.content == b"%PDF-1.4 original bytes"
    assert r.headers["content-type"] == "application/pdf"
    assert "inline" in r.headers.get("content-disposition", "")


def test_get_file_404_when_document_missing(monkeypatch):
    monkeypatch.setattr(documents_router, "fetch_document_file", lambda conn, doc_id: None)
    assert _client().get(f"/api/documents/{_DOC_ID}/file").status_code == 404


def test_get_file_404_when_blob_not_stored(monkeypatch):
    # Row exists but storage_path is null (e.g. a doc ingested before Slice 17).
    monkeypatch.setattr(
        documents_router,
        "fetch_document_file",
        lambda conn, doc_id: {"filename": "x.pdf", "doc_type": "pdf", "storage_path": None},
    )
    assert _client().get(f"/api/documents/{_DOC_ID}/file").status_code == 404


_USER_ID = "22222222-2222-2222-2222-222222222222"


def test_list_documents_ok(monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "list_documents",
        lambda conn, user_id, *a, **k: [
            {
                "document_id": _DOC_ID, "filename": "x.pdf", "doc_type": "pdf",
                "status": "ready", "page_count": 3, "chunk_count": 10,
                "size_bytes": 1234, "uploaded_at": "2026-07-18T09:24:00+07",
            }
        ],
    )
    r = _client().get(f"/api/documents?user_id={_USER_ID}")
    assert r.status_code == 200
    docs = r.json()["documents"]
    assert len(docs) == 1 and docs[0]["filename"] == "x.pdf" and docs[0]["chunk_count"] == 10


def test_list_documents_requires_user_id():
    assert _client().get("/api/documents").status_code == 422


def test_healthz():
    assert _client().get("/api/healthz").json() == {"status": "ok"}
