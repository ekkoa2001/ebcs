import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, base_url="http://127.0.0.1:8875")
ORIGIN = {"Origin": "http://127.0.0.1:8875"}


@pytest.fixture(scope="module", autouse=True)
def started_application():
    with client:
        yield


def login(username="ekko", password="123"):
    response = client.post("/api/login", json={"username": username, "password": password}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    session = client.get("/api/session")
    assert session.status_code == 200, session.text
    return session.json()


def test_legacy_login_keeps_cookie_session_and_csrf():
    body = login()
    assert body["username"] == "ekko"
    assert body["role"] == "admin"
    assert body["csrf"]
    assert body["profile"]["name"]
    denied = client.post("/api/logout", json={}, headers=ORIGIN)
    assert denied.status_code == 403
    accepted = client.post("/api/logout", json={}, headers={**ORIGIN, "X-CSRF-Token": body["csrf"]})
    assert accepted.status_code == 200
    assert client.get("/api/state").status_code == 401


def test_new_auth_session_and_audit_are_available():
    body = login()
    current = client.get("/api/v1/auth/session")
    assert current.status_code == 200
    assert current.json()["username"] == "ekko"
    logs = client.get("/api/v1/admin/activity-logs")
    assert logs.status_code == 200
    assert any(item["action"] == "登录成功" for item in logs.json()["items"])
    client.post("/api/logout", json={}, headers={**ORIGIN, "X-CSRF-Token": body["csrf"]})


def test_viewer_cannot_change_state_or_read_audit():
    admin = login()
    created = client.post(
        "/api/users/create",
        json={"username": "phase2viewer", "role": "viewer", "password": "phase2-viewer", "active": True},
        headers={**ORIGIN, "X-CSRF-Token": admin["csrf"]},
    )
    assert created.status_code == 200, created.text
    client.post("/api/logout", json={}, headers={**ORIGIN, "X-CSRF-Token": admin["csrf"]})
    viewer = login("phase2viewer", "phase2-viewer")
    forbidden = client.post("/api/state", json={"version": 1, "entries": []}, headers={**ORIGIN, "X-CSRF-Token": viewer["csrf"]})
    assert forbidden.status_code == 403
    assert client.get("/api/v1/admin/activity-logs").status_code == 403
    client.post("/api/logout", json={}, headers={**ORIGIN, "X-CSRF-Token": viewer["csrf"]})


def test_pages_still_render_for_anonymous_and_admin():
    client.cookies.clear()
    page = client.get("/")
    assert page.status_code == 200
    assert "登录" in page.text
    login()
    home = client.get("/")
    assert home.status_code == 200
    assert "Ekko Script Web" in home.text
    asset = client.get("/assets/css/tokens.css")
    assert asset.status_code == 200
    assert "box-sizing" in asset.text
