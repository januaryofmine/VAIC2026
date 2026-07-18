"""Chat-history router tests with the DB dependency overridden and services stubbed."""

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


def test_list_chat_messages_ok(monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "list_chat_messages",
        lambda conn, doc_id: [
            {"id": "m1", "role": "user", "parts": [{"type": "text", "text": "q"}], "metadata": None},
        ],
    )
    r = _client().get(f"/api/documents/{_DOC_ID}/chat/messages")
    assert r.status_code == 200
    assert r.json()["messages"][0]["id"] == "m1"


def test_append_chat_message_ok(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        documents_router,
        "append_chat_message",
        lambda conn, doc_id, mid, role, parts, metadata: seen.update(
            mid=mid, role=role, parts=parts, metadata=metadata
        ),
    )
    r = _client().post(
        f"/api/documents/{_DOC_ID}/chat/messages",
        json={"id": "m2", "role": "assistant", "parts": [{"type": "text", "text": "a"}],
              "metadata": {"sources": []}},
    )
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert seen["mid"] == "m2" and seen["role"] == "assistant"
