from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.creative import CreativeHook

client = TestClient(app, base_url="http://127.0.0.1:8875")
ORIGIN = {"Origin": "http://127.0.0.1:8875"}


@pytest.fixture(scope="module", autouse=True)
def started_application():
    with client:
        yield


def login():
    response = client.post("/api/login", json={"username": "ekko", "password": "123"}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    session = client.get("/api/session")
    assert session.status_code == 200
    return session.json()


def payload(title="API 创意钩子", version=None):
    return {
        "code": "HOOK-" + uuid4().hex[:8],
        "title": title,
        "content": "这是用于验证新架构的创意内容。",
        "hookType": "C｜生活痛点型",
        "product": "Sana",
        "audience": "北美女性",
        "scene": "居家瑜伽",
        "referenceMaterial": "",
        "notes": "自动测试",
        "status": "待筛选",
        "isExample": False,
        "createdAt": "2026-11-12T10:00:00",
        "version": version,
    }


def test_legacy_hooks_are_imported_into_normalized_table():
    response = client.get("/api/v1/creative/hooks")
    if response.status_code == 401:
        login()
        response = client.get("/api/v1/creative/hooks")
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1


def test_create_update_archive_restore_and_legacy_mirror():
    session = login()
    headers = {**ORIGIN, "X-CSRF-Token": session["csrf"]}
    created = client.post("/api/v1/creative/hooks", json=payload(), headers=headers)
    assert created.status_code == 200, created.text
    hook = created.json()

    state = client.get("/api/state").json()
    assert any(item["id"] == hook["id"] and item["kind"] == "开头创意" for item in state["entries"])

    changed = payload("已更新的创意钩子", hook["version"])
    updated = client.put(f"/api/v1/creative/hooks/{hook['id']}", json=changed, headers=headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "已更新的创意钩子"

    conflict = client.put(f"/api/v1/creative/hooks/{hook['id']}", json=changed, headers=headers)
    assert conflict.status_code == 409

    archived = client.delete(f"/api/v1/creative/hooks/{hook['id']}", headers=headers)
    assert archived.status_code == 200
    assert client.get(f"/api/v1/creative/hooks/{hook['id']}").status_code == 404

    restored = client.post(f"/api/v1/creative/hooks/{hook['id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert client.get(f"/api/v1/creative/hooks/{hook['id']}").status_code == 200


def test_legacy_save_synchronizes_normalized_hook():
    session = login()
    headers = {**ORIGIN, "X-CSRF-Token": session["csrf"]}
    state = client.get("/api/state").json()
    hook = next(item for item in state["entries"] if item.get("kind") == "开头创意")
    before_title = hook["title"]
    hook["title"] = before_title + "｜同步验证"
    saved = client.post("/api/state", json={"version": state["version"], "entries": state["entries"]}, headers=headers)
    assert saved.status_code == 200, saved.text

    with SessionLocal() as db:
        normalized = db.get(CreativeHook, hook["id"])
        assert normalized is not None
        assert normalized.title == hook["title"]

    current = client.get("/api/state").json()
    current_hook = next(item for item in current["entries"] if item.get("id") == hook["id"])
    current_hook["title"] = before_title
    reset = client.post("/api/state", json={"version": current["version"], "entries": current["entries"]}, headers=headers)
    assert reset.status_code == 200
