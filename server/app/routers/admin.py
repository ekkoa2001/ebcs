from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, select, text
import secrets
from datetime import datetime, timezone

from app.database import SessionLocal
from app.dependencies import require_csrf, require_permission, require_session
from app.models.foundation import ActivityLog
from app.services import resources

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# These are product defaults, not hard-coded front-end-only labels.  Keeping
# them in the database lets the type manager rename or remove every type.
DEFAULT_CONTENT_TYPES = {
    "brand_content": ["品牌推广图", "品牌 UGC 图", "新品发布图", "产品详情图", "产品卖点图", "产品场景图", "EDM 营销图", "折扣营销图", "节日／大促图", "独立站 Banner", "SEO 文章配图"],
    "after_sales": ["使用教程方案", "产品保养方案", "常见问题方案", "故障排查方案", "配件说明方案", "售后流程方案", "客户关怀方案"],
    "marketing_plan": ["草稿", "待执行", "执行中", "已结束", "已复盘"],
    "competitor_insight": ["竞品产品内容", "竞品独立站", "竞品营销策略", "竞品广告素材", "竞品 EDM", "竞品 SEO Blog"],
}


def ensure_default_content_types(db):
    """Seed a group only once so a user may later delete every type if needed."""
    now = datetime.now(timezone.utc).isoformat()
    for group, names in DEFAULT_CONTENT_TYPES.items():
        exists = db.execute(text("SELECT 1 FROM content_types WHERE group_name=:group LIMIT 1"), {"group": group}).first()
        if exists:
            continue
        for index, name in enumerate(names, start=1):
            db.execute(text("INSERT INTO content_types(id,group_name,code,name,origin,description,created_at,updated_at) VALUES(:id,:group,:code,:name,:origin,'',:now,:now)"), {"id": f"system_{group}_{index}", "group": group, "code": str(index), "name": name, "origin": "system", "now": now})
    db.commit()


@router.get("/activity-logs")
def activity_logs(request: Request, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), actor: str = "", module: str = ""):
    current = require_session(request)
    require_permission(current, "audit.read")
    filters = []
    if actor:
        filters.append(ActivityLog.actor == actor)
    if module:
        filters.append(ActivityLog.module == module)
    with SessionLocal() as db:
        query = select(ActivityLog).where(*filters).order_by(ActivityLog.id.desc())
        total = db.scalar(select(func.count()).select_from(ActivityLog).where(*filters)) or 0
        rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
        return {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "items": [
                {"id": row.id, "time": row.time, "actor": row.actor, "module": row.module, "action": row.action, "objectType": row.object_type, "objectId": row.object_id, "result": row.result, "ip": row.ip, "userAgent": row.user_agent, "repeatCount": row.repeat_count}
                for row in rows
            ],
        }


@router.get("/legacy-log")
def legacy_log(request: Request):
    current = require_session(request)
    require_permission(current, "audit.read")
    with SessionLocal() as db:
        rows = db.scalars(select(ActivityLog).order_by(ActivityLog.id.desc()).limit(1000)).all()
        return [{"time": row.time, "actor": row.actor, "action": row.action} for row in rows]


@router.get("/tags")
def tags(request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db: return [dict(x._mapping) for x in db.execute(text("SELECT * FROM tags ORDER BY name")).all()]


@router.post("/tags")
def create_tag(request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access"); name=str(body.get("name") or "").strip()
    if not name or len(name)>80: raise HTTPException(400,"标签名称无效")
    with SessionLocal() as db:
        try: identifier=db.execute(text("INSERT INTO tags(name) VALUES(:name) RETURNING id"),{"name":name}).scalar_one(); db.commit()
        except Exception: db.rollback(); raise HTTPException(409,"标签已存在")
    return {"id":identifier,"name":name}


@router.delete("/tags/{identifier}")
def delete_tag(identifier:int,request:Request):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access")
    with SessionLocal() as db:
        db.execute(text("DELETE FROM entity_tags WHERE tag_id=:id"),{"id":identifier})
        result=db.execute(text("DELETE FROM tags WHERE id=:id"),{"id":identifier}); db.commit()
    if not result.rowcount: raise HTTPException(404,"标签不存在")
    return {"ok":True}


@router.get("/entity-tags/{entity_type}/{entity_id}")
def entity_tags(entity_type:str,entity_id:str,request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db:
        return [dict(x._mapping) for x in db.execute(text("SELECT t.* FROM tags t JOIN entity_tags e ON e.tag_id=t.id WHERE e.entity_type=:type AND e.entity_id=:id ORDER BY t.name"),{"type":entity_type,"id":entity_id}).all()]


@router.put("/entity-tags/{entity_type}/{entity_id}")
def set_entity_tags(entity_type:str,entity_id:str,request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"content.update_own")
    identifiers=body.get("tagIds") or []
    if not isinstance(identifiers,list) or any(not isinstance(x,int) for x in identifiers): raise HTTPException(400,"标签列表无效")
    with SessionLocal() as db:
        db.execute(text("DELETE FROM entity_tags WHERE entity_type=:type AND entity_id=:id"),{"type":entity_type,"id":entity_id})
        for tag_id in set(identifiers): db.execute(text("INSERT INTO entity_tags(entity_type,entity_id,tag_id) VALUES(:type,:id,:tag)"),{"type":entity_type,"id":entity_id,"tag":tag_id})
        db.commit()
    return {"ok":True}


@router.get("/content-types")
def content_types(request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db:
        ensure_default_content_types(db)
        return [dict(x._mapping) for x in db.execute(text("SELECT * FROM content_types ORDER BY group_name,code,name")).all()]


@router.post("/content-types")
def create_content_type(request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access")
    name=str(body.get("name") or "").strip(); group=str(body.get("groupName") or "").strip()
    if not name or not group: raise HTTPException(400,"请填写分组和名称")
    now=datetime.now(timezone.utc).isoformat(); identifier="type_"+secrets.token_hex(12)
    with SessionLocal() as db:
        db.execute(text("INSERT INTO content_types(id,group_name,code,name,origin,description,created_at,updated_at) VALUES(:id,:group,:code,:name,:origin,:description,:now,:now)"),{"id":identifier,"group":group,"code":str(body.get("code") or ""),"name":name,"origin":"custom","description":str(body.get("description") or ""),"now":now}); db.commit()
    return {"id":identifier,"group_name":group,"name":name}


@router.delete("/content-types/{identifier}")
def delete_content_type(identifier:str,request:Request):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access")
    with SessionLocal() as db:
        row=db.execute(text("SELECT origin FROM content_types WHERE id=:id"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"类型不存在")
        db.execute(text("DELETE FROM content_types WHERE id=:id"),{"id":identifier}); db.commit()
    return {"ok":True}


@router.put("/content-types/{identifier}")
def update_content_type(identifier:str,request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access")
    name=str(body.get("name") or "").strip(); description=str(body.get("description") or "").strip()
    if not name: raise HTTPException(400,"请填写类型名称")
    now=datetime.now(timezone.utc).isoformat()
    with SessionLocal() as db:
        row=db.execute(text("SELECT group_name,name FROM content_types WHERE id=:id"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"类型不存在")
        group_name, previous_name = row
        db.execute(text("UPDATE content_types SET name=:name,description=:description,updated_at=:now WHERE id=:id"),{"id":identifier,"name":name,"description":description,"now":now}); db.commit()
        # Keep existing records connected when a visible type is renamed.
        if group_name in ("brand_content", "after_sales"):
            db.execute(text("UPDATE brand_content_projects SET content_type=:name WHERE content_type=:old"), {"name": name, "old": previous_name})
        elif group_name == "marketing_plan":
            db.execute(text("UPDATE marketing_plans SET status=:name WHERE status=:old"), {"name": name, "old": previous_name})
        elif group_name == "competitor_insight":
            db.execute(text("UPDATE competitor_insights SET insight_type=:name WHERE insight_type=:old"), {"name": name, "old": previous_name})
        db.commit()
    return {"id":identifier,"name":name,"description":description}


@router.get("/archives")
def archives(request:Request,page:int=Query(1,ge=1),page_size:int=Query(50,alias="pageSize",ge=1,le=200)):
    current=require_session(request); require_permission(current,"content.restore")
    with SessionLocal() as db:
        total=db.execute(text("SELECT COUNT(*) FROM archives WHERE purged_at IS NULL")).scalar_one(); rows=db.execute(text("SELECT * FROM archives WHERE purged_at IS NULL ORDER BY id DESC LIMIT :limit OFFSET :offset"),{"limit":page_size,"offset":(page-1)*page_size}).all()
        return {"page":page,"pageSize":page_size,"total":total,"items":[dict(x._mapping) for x in rows]}


@router.post("/archives/{identifier}/restore")
def restore_archive(identifier:int,request:Request):
    current=require_session(request); require_csrf(request,current); require_permission(current,"content.restore")
    with SessionLocal() as db: row=db.execute(text("SELECT * FROM archives WHERE id=:id AND purged_at IS NULL"),{"id":identifier}).first()
    if not row: raise HTTPException(404,"归档记录不存在")
    if row.entity_type not in resources.CONFIG or not resources.CONFIG[row.entity_type].get("soft"): raise HTTPException(400,"该记录不能自动恢复")
    try: resources.archive_row(row.entity_type,row.entry_id,True,current["username"])
    except resources.ResourceError as error: raise HTTPException(error.status,error.message)
    with SessionLocal() as db: db.execute(text("UPDATE archives SET purged_at=:time WHERE id=:id"),{"time":datetime.now(timezone.utc).isoformat(),"id":identifier}); db.commit()
    return {"ok":True}


@router.delete("/archives/{identifier}")
def purge_archive(identifier:int,request:Request,confirm:str=Query("")):
    current=require_session(request); require_csrf(request,current); require_permission(current,"admin.access")
    if confirm!="PERMANENT": raise HTTPException(400,"永久删除需要明确确认")
    with SessionLocal() as db:
        row=db.execute(text("SELECT entry_id,entity_type FROM archives WHERE id=:id AND purged_at IS NULL"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"归档记录不存在")
        if row.entity_type in resources.CONFIG:
            try: db.execute(text(f"DELETE FROM {row.entity_type} WHERE id=:entry"),{"entry":row.entry_id})
            except Exception: db.rollback(); raise HTTPException(409,"该记录仍被其他内容引用，不能永久删除")
        db.execute(text("UPDATE archives SET purged_at=:time WHERE id=:id"),{"time":datetime.now(timezone.utc).isoformat(),"id":identifier}); db.commit()
    return {"ok":True}


compat_router = APIRouter(tags=["v1-compatibility"])


@compat_router.get("/api/log")
def compatibility_log(request: Request):
    return legacy_log(request)
