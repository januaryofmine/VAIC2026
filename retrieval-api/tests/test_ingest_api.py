"""Ingest router test: async early-return + user_id passthrough (B3).

rag-pipeline is stubbed via _load_rag so no live DB / model is needed. The fake
ingest fires on_created (like the real one) so the endpoint returns the id early.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.ingest as ingest_router
from app.main import app


def _settings(**over):
    base = dict(database_url="postgresql://x", max_upload_mb=25, api_key="")
    base.update(over)
    return SimpleNamespace(**base)


class _FakeEmbedder:
    pass


def _install(monkeypatch, fake_ingest, settings=None):
    monkeypatch.setattr(ingest_router, "get_settings", lambda: settings or _settings())
    monkeypatch.setattr(ingest_router, "_embedder", object())  # skip real E5 load
    fake_db = SimpleNamespace(connect=lambda url: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(ingest_router, "_load_rag", lambda: (fake_db, fake_ingest, _FakeEmbedder))


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake"


def test_ingest_returns_early_with_processing(monkeypatch):
    def fake_ingest(path, conn, embedder, user_id=None, on_created=None):
        on_created("doc-abc")  # id available immediately
        return "doc-abc"

    _install(monkeypatch, fake_ingest)
    r = TestClient(app).post(
        "/api/ingest", files={"file": ("Luat.pdf", _pdf_bytes(), "application/pdf")}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == "doc-abc"
    assert body["filename"] == "Luat.pdf"
    assert body["status"] == "processing"


def test_ingest_passes_user_id(monkeypatch):
    seen = {}

    def fake_ingest(path, conn, embedder, user_id=None, on_created=None):
        seen["user_id"] = user_id
        on_created("doc-xyz")
        return "doc-xyz"

    _install(monkeypatch, fake_ingest)
    r = TestClient(app).post(
        "/api/ingest",
        files={"file": ("d.docx", b"PK\x03\x04", "application/octet-stream")},
        data={"user_id": "u-123"},
    )
    assert r.status_code == 200
    assert seen["user_id"] == "u-123"


def test_ingest_rejects_bad_extension(monkeypatch):
    _install(monkeypatch, lambda *a, **k: "x")
    r = TestClient(app).post(
        "/api/ingest", files={"file": ("evil.exe", b"MZ", "application/octet-stream")}
    )
    assert r.status_code == 400


def test_ingest_rejects_oversized(monkeypatch):
    _install(monkeypatch, lambda *a, **k: "x", settings=_settings(max_upload_mb=0))
    r = TestClient(app).post(
        "/api/ingest", files={"file": ("big.pdf", _pdf_bytes(), "application/pdf")}
    )
    assert r.status_code == 413


def test_ingest_500_when_id_never_emitted(monkeypatch):
    # ingest raises before creating the row → endpoint must surface a failure, not hang.
    def boom(path, conn, embedder, user_id=None, on_created=None):
        raise RuntimeError("parse blew up")

    _install(monkeypatch, boom)
    r = TestClient(app).post(
        "/api/ingest", files={"file": ("d.pdf", _pdf_bytes(), "application/pdf")}
    )
    assert r.status_code == 500
