import pytest
from fastapi.testclient import TestClient

from backend.app import authentication
from backend.app.api.routes import auth as auth_routes
from backend.app.database import database
from backend.app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "predictions.sqlite")
    monkeypatch.setattr(auth_routes, "AUTH_USERNAME", "test-analyst")
    monkeypatch.setattr(auth_routes, "AUTH_PASSWORD", "unit-test-password")
    monkeypatch.setattr(authentication, "AUTH_USERNAME", "test-analyst")
    monkeypatch.setattr(authentication, "AUTH_SESSION_SECRET", "test-session-signing-secret")
    database.initialize_database()
    with TestClient(app) as test_client:
        yield test_client


def test_login_sets_http_only_session_and_authorizes_api(client) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "test-analyst", "password": "unit-test-password"},
    )
    assert login.status_code == 200
    assert login.json() == {"authenticated": True, "username": "test-analyst"}
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert client.get("/api/auth/session").json()["authenticated"] is True
    assert client.get("/api/model/").status_code == 200


def test_login_rejects_incorrect_credentials(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "test-analyst", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_protected_api_rejects_anonymous_requests(client) -> None:
    assert client.get("/api/analytics/overview").status_code == 401
    assert client.get("/api/auth/session").json() == {"authenticated": False}
    assert client.get("/api/health").status_code == 200


def test_logout_removes_access_to_protected_api(client) -> None:
    client.post(
        "/api/auth/login",
        json={"username": "test-analyst", "password": "unit-test-password"},
    )
    assert client.get("/api/model/").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/model/").status_code == 401
