"""Unit tests for the backend-driven prep-pack trigger fired after embedding."""

import json

import app.routers.ingest as ingest_mod


class _Settings:
    def __init__(self, bff_url: str = "", api_key: str = ""):
        self.bff_url = bff_url
        self.api_key = api_key


def _headers_lower(req) -> dict:
    return {k.lower(): v for k, v in req.headers.items()}


def test_noop_when_bff_url_empty(monkeypatch):
    called = []
    monkeypatch.setattr(
        ingest_mod.urllib.request, "urlopen", lambda *a, **k: called.append(1)
    )
    ingest_mod._trigger_prep_pack("doc1", _Settings(bff_url=""))
    assert called == []  # no BFF configured → do nothing


def test_noop_when_document_id_missing(monkeypatch):
    called = []
    monkeypatch.setattr(
        ingest_mod.urllib.request, "urlopen", lambda *a, **k: called.append(1)
    )
    ingest_mod._trigger_prep_pack(None, _Settings(bff_url="http://bff:3000"))
    assert called == []


def test_posts_to_bff_with_key_and_body(monkeypatch):
    captured = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = _headers_lower(req)
        captured["body"] = json.loads(req.data)
        return _Resp()

    monkeypatch.setattr(ingest_mod.urllib.request, "urlopen", fake_urlopen)
    ingest_mod._trigger_prep_pack(
        "doc-123", _Settings(bff_url="http://bff:3000/", api_key="secret")
    )
    assert captured["url"] == "http://bff:3000/api/internal/prep-pack"
    assert captured["method"] == "POST"
    assert captured["headers"]["x-api-key"] == "secret"
    assert captured["body"] == {"document_id": "doc-123"}


def test_swallows_bff_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("bff down")

    monkeypatch.setattr(ingest_mod.urllib.request, "urlopen", boom)
    # Must NOT raise — a BFF hiccup can never fail ingestion.
    ingest_mod._trigger_prep_pack("doc1", _Settings(bff_url="http://bff", api_key="k"))
