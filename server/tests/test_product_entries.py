from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, base_url="http://127.0.0.1:8875")
ORIGIN = {"Origin": "http://127.0.0.1:8875"}


@pytest.fixture(scope="module", autouse=True)
def started_application():
    with client: yield


def login():
    response = client.post("/api/login", json={"username": "ekko", "password": "123"}, headers=ORIGIN)
    assert response.status_code == 200
    return client.get("/api/session").json()


def test_product_entry_crud_and_legacy_mirror():
    session = login(); headers = {**ORIGIN, "X-CSRF-Token": session["csrf"]}
    hook = client.get("/api/v1/creative/hooks").json()["items"][0]
    body = {"hookId": hook["id"], "code": "ENTRY-" + uuid4().hex[:8], "title": "API 产品出场",
        "entryType": "递入惊喜型", "entryTime": "6秒", "transitionLogic": "人物拿起产品进入镜头。",
        "sellingPoints": "声音与放松", "visualDescription": "中景，产品居中", "product": "Sana",
        "notes": "自动测试", "status": "待筛选", "isExample": False, "createdAt": "2026-11-12T11:00:00"}
    created = client.post("/api/v1/creative/product-entries", json=body, headers=headers)
    assert created.status_code == 200, created.text
    item = created.json()
    state = client.get("/api/state").json()
    assert any(x["id"] == item["id"] and x["kind"] == "产品出场" for x in state["entries"])
    body.update({"title": "更新产品出场", "version": item["version"]})
    updated = client.put(f"/api/v1/creative/product-entries/{item['id']}", json=body, headers=headers)
    assert updated.status_code == 200
    assert client.delete(f"/api/v1/creative/product-entries/{item['id']}", headers=headers).status_code == 200
    assert client.post(f"/api/v1/creative/product-entries/{item['id']}/restore", headers=headers).status_code == 200


def test_legacy_entries_are_available():
    login()
    response = client.get("/api/v1/creative/product-entries")
    assert response.status_code == 200
    assert response.json()["total"] >= 5
