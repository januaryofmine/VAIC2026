"""Direct-upload auth on /api/ingest: browser HMAC token vs server X-API-Key."""

import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.routers.ingest as ingest_router
from app.main import app
from app.services.upload_token import make_upload_token

SECRET = "secret123"


def _install(monkeypatch, fake_ingest, api_key):
    settings = SimpleNamespace(database_url="postgresql://x", max_upload_mb=25, api_key=api_key)
    monkeypatch.setattr(ingest_router, "get_settings", lambda: settings)
    monkeypatch.setattr(ingest_router, "_embedder", object())
    fake_db = SimpleNamespace(connect=lambda url: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(ingest_router, "_load_rag", lambda: (fake_db, fake_ingest, object))


def _pdf():
    return {"file": ("d.pdf", b"%PDF-1.4", "application/pdf")}


def test_valid_upload_token_ingests_with_token_owner(monkeypatch):
    seen = {}

    def fake_ingest(path, conn, embedder, user_id=None, on_created=None):
        seen["user_id"] = user_id
        on_created("doc-1")
        return "doc-1"

    _install(monkeypatch, fake_ingest, SECRET)
    tok = make_upload_token("owner-42", SECRET, exp=int(time.time()) + 300)
    r = TestClient(app).post("/api/ingest", files=_pdf(), headers={"X-Upload-Token": tok})
    assert r.status_code == 200
    assert seen["user_id"] == "owner-42"  # owner comes from the signed token


def test_token_overrides_form_user_id(monkeypatch):
    seen = {}

    def fake_ingest(path, conn, embedder, user_id=None, on_created=None):
        seen["user_id"] = user_id
        on_created("doc-9")
        return "doc-9"

    _install(monkeypatch, fake_ingest, SECRET)
    tok = make_upload_token("token-owner", SECRET, exp=int(time.time()) + 300)
    r = TestClient(app).post(
        "/api/ingest", files=_pdf(), data={"user_id": "form-owner"},
        headers={"X-Upload-Token": tok},
    )
    assert r.status_code == 200
    assert seen["user_id"] == "token-owner"  # a browser can't spoof ownership via the form


def test_invalid_token_rejected(monkeypatch):
    _install(monkeypatch, lambda *a, **k: "x", SECRET)
    r = TestClient(app).post("/api/ingest", files=_pdf(), headers={"X-Upload-Token": "bad.1.sig"})
    assert r.status_code == 401


def test_expired_token_rejected(monkeypatch):
    _install(monkeypatch, lambda *a, **k: "x", SECRET)
    tok = make_upload_token("u", SECRET, exp=int(time.time()) - 10)
    r = TestClient(app).post("/api/ingest", files=_pdf(), headers={"X-Upload-Token": tok})
    assert r.status_code == 401


def test_no_auth_rejected_when_key_set(monkeypatch):
    _install(monkeypatch, lambda *a, **k: "x", SECRET)
    r = TestClient(app).post("/api/ingest", files=_pdf())
    assert r.status_code == 401


def test_api_key_still_works_server_to_server(monkeypatch):
    seen = {}

    def fake_ingest(path, conn, embedder, user_id=None, on_created=None):
        seen["user_id"] = user_id
        on_created("doc-2")
        return "doc-2"

    _install(monkeypatch, fake_ingest, SECRET)
    r = TestClient(app).post(
        "/api/ingest", files=_pdf(), data={"user_id": "srv-owner"},
        headers={"X-API-Key": SECRET},
    )
    assert r.status_code == 200
    assert seen["user_id"] == "srv-owner"  # trusted server path: owner from form
