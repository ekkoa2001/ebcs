import pytest
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app,base_url="http://127.0.0.1:8875")
ORIGIN={"Origin":"http://127.0.0.1:8875"}

@pytest.fixture(scope="module",autouse=True)
def started():
    with client: yield

def session():
    assert client.post("/api/login",json={"username":"ekko","password":"123"},headers=ORIGIN).status_code==200
    return client.get("/api/session").json()

def test_all_business_collections_and_dashboard_are_available():
    session()
    paths=("/api/v1/creative/scripts","/api/v1/creative/storyboard-shots","/api/v1/creative/produced-videos","/api/v1/content/projects","/api/v1/content/assets","/api/v1/marketing/plans","/api/v1/marketing/stages","/api/v1/marketing/lifecycle","/api/v1/analytics/campaigns","/api/v1/analytics/periods","/api/v1/competitors","/api/v1/tasks")
    for path in paths:
        response=client.get(path); assert response.status_code==200,(path,response.text); assert "items" in response.json()
    dashboard=client.get("/api/v1/dashboard"); assert dashboard.status_code==200; assert dashboard.json()["counts"]["scripts"]>=1
    compass=client.get("/api/v1/analytics/compass"); assert compass.status_code==200; assert "purchases" in compass.json()

def test_create_update_archive_restore_business_resource():
    current=session(); headers={**ORIGIN,"X-CSRF-Token":current["csrf"]}
    created=client.post("/api/v1/content/projects",headers=headers,json={"name":"测试品牌内容","content_group":"产品内容","content_type":"产品卖点图","description":"自动测试"})
    assert created.status_code==200,created.text; item=created.json()
    changed=client.put(f"/api/v1/content/projects/{item['id']}",headers=headers,json={"name":"更新品牌内容","version":item["version"]})
    assert changed.status_code==200,changed.text
    assert client.delete(f"/api/v1/content/projects/{item['id']}",headers=headers).status_code==200
    assert client.post(f"/api/v1/content/projects/{item['id']}/restore",headers=headers).status_code==200

def test_team_comment_like_and_delete():
    current=session(); headers={**ORIGIN,"X-CSRF-Token":current["csrf"]}
    script=client.get("/api/v1/creative/scripts").json()["items"][0]
    created=client.post("/api/v1/comments",headers=headers,json={"entityType":"script","entityId":script["id"],"content":"自动测试评价"})
    assert created.status_code==200,created.text; identifier=created.json()["id"]
    assert client.post(f"/api/v1/comments/{identifier}/like",headers=headers).json()["liked"] is True
    listed=client.get(f"/api/v1/comments/script/{script['id']}"); assert any(x["id"]==identifier for x in listed.json())
    assert client.delete(f"/api/v1/comments/{identifier}",headers=headers).status_code==200

def test_image_upload_validation_and_deduplication():
    current=session(); headers={**ORIGIN,"X-CSRF-Token":current["csrf"]}
    stream=BytesIO(); Image.new("RGB",(40,30),(20,80,180)).save(stream,"PNG"); raw=stream.getvalue()
    first=client.post("/api/v1/media/upload",headers=headers,files={"file":("sample.png",raw,"image/png")})
    assert first.status_code==200,first.text; assert first.json()["width"]==40; assert first.json()["deduplicated"] is False
    second=client.post("/api/v1/media/upload",headers=headers,files={"file":("copy.png",raw,"image/png")})
    assert second.status_code==200; assert second.json()["id"]==first.json()["id"]; assert second.json()["deduplicated"] is True


def test_content_taxonomy_tags_and_period_comparison():
    current=session(); headers={**ORIGIN,"X-CSRF-Token":current["csrf"]}
    invalid=client.post("/api/v1/content/projects",headers=headers,json={"name":"错误分类","content_group":"品牌推广","content_type":"产品卖点图"})
    assert invalid.status_code==400
    tag=client.post("/api/v1/admin/tags",headers=headers,json={"name":"自动测试标签"})
    assert tag.status_code==200,tag.text
    tag_id=tag.json()["id"]
    script=client.get("/api/v1/creative/scripts").json()["items"][0]
    saved=client.put(f"/api/v1/admin/entity-tags/script/{script['id']}",headers=headers,json={"tagIds":[tag_id]})
    assert saved.status_code==200
    listed=client.get(f"/api/v1/admin/entity-tags/script/{script['id']}")
    assert any(x["id"]==tag_id for x in listed.json())
    comparison=client.get("/api/v1/analytics/comparison?start=2026-11-01&end=2026-11-07")
    assert comparison.status_code==200,comparison.text
    assert comparison.json()["previous"]["end"]=="2026-10-31"
    assert client.delete(f"/api/v1/admin/tags/{tag_id}",headers=headers).status_code==200


def test_normalized_script_is_visible_to_frozen_v1_ui():
    current=session(); headers={**ORIGIN,"X-CSRF-Token":current["csrf"]}
    hook=client.get("/api/v1/creative/hooks").json()["items"][0]
    entry=client.get(f"/api/v1/creative/product-entries?hookId={hook['id']}").json()["items"][0]
    created=client.post("/api/v1/creative/scripts",headers=headers,json={"hook_id":hook["id"],"product_entry_id":entry["id"],"title":"新旧界面联动测试","body":"用于验证规范化脚本会同步到旧界面。"})
    assert created.status_code==200,created.text
    identifier=created.json()["id"]
    state=client.get("/api/state").json()
    assert any(x["id"]==identifier and x["kind"]=="完整脚本" for x in state["entries"])
    assert client.delete(f"/api/v1/creative/scripts/{identifier}",headers=headers).status_code==200
    assert not any(x["id"]==identifier for x in client.get("/api/state").json()["entries"])
