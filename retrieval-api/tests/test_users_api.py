"""Users router test with the DB dependency overridden and the service stubbed."""

from fastapi.testclient import TestClient

import app.routers.users as users_router
from app.deps import get_db
from app.main import app

_USER_ID = "22222222-2222-2222-2222-222222222222"


def _fake_db():
    yield None


def _client() -> TestClient:
    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_upsert_user_ok(monkeypatch):
    monkeypatch.setattr(
        users_router,
        "upsert_user",
        lambda conn, github_id, username, name, avatar_url: {
            "id": _USER_ID, "github_id": github_id, "username": username,
            "name": name, "avatar_url": avatar_url,
        },
    )
    r = _client().post(
        "/api/users/upsert",
        json={"github_id": 4711, "username": "khanhtiet", "name": "Khanh", "avatar_url": "http://x/a.png"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == _USER_ID
    assert body["github_id"] == 4711 and body["username"] == "khanhtiet"


def test_upsert_user_requires_fields():
    # github_id + username are required
    assert _client().post("/api/users/upsert", json={"name": "x"}).status_code == 422
