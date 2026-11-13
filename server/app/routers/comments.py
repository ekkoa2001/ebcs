from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from app.database import SessionLocal
from app.dependencies import require_csrf, require_permission, require_session
from app.services import audit, resources

router = APIRouter(prefix="/api/v1", tags=["comments"])


@router.get("/comments/{entity_type}/{entity_id}")
def list_comments(entity_type: str, entity_id: str, request: Request):
    current = require_session(request); require_permission(current, "content.read")
    with SessionLocal() as db:
        rows = db.execute(text("SELECT c.*, (SELECT COUNT(*) FROM comment_likes l WHERE l.comment_id=c.id) likes, EXISTS(SELECT 1 FROM comment_likes l WHERE l.comment_id=c.id AND l.actor=:actor) liked FROM comments c WHERE (c.entity_type=:type AND c.entity_id=:id) OR (c.entry_id=:id AND COALESCE(c.entity_type,'')='') ORDER BY c.id"), {"actor": current["username"], "type": entity_type, "id": entity_id}).all()
        items=[]
        for row in rows:
            item=dict(row._mapping); replies=db.execute(text("SELECT * FROM comment_replies WHERE comment_id=:id ORDER BY id"), {"id":item["id"]}).all(); item["replies"]=[dict(x._mapping) for x in replies]; items.append(item)
        return items


@router.post("/comments")
def create_comment(request: Request, body: dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"comment.create")
    content=str(body.get("content") or "").strip()
    if not 1 <= len(content) <= 2000: raise HTTPException(400,"评价为 1–2000 字")
    with SessionLocal() as db:
        event_time=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        result=db.execute(text("INSERT INTO comments(entry_id,actor,time,content,entity_type,entity_id) VALUES(:entry,:actor,:time,:content,:type,:id) RETURNING id"), {"entry":body.get("entityId", ""),"actor":current["username"],"time":event_time,"content":content,"type":body.get("entityType", ""),"id":body.get("entityId", "")}); identifier=result.scalar_one(); resources.emit_event(db,current["username"],"团队评价",str(body.get("entityId", "")),content[:100],event_time); db.commit()
    audit.record(current["username"],"添加团队评价",request,module="comments",object_type="comment",object_id=str(identifier)); return {"ok":True,"id":identifier}


@router.delete("/comments/{identifier}")
def delete_comment(identifier: int, request: Request):
    current=require_session(request); require_csrf(request,current)
    with SessionLocal() as db:
        row=db.execute(text("SELECT actor FROM comments WHERE id=:id"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"评价不存在")
        if current["role"]!="admin" and row[0].casefold()!=current["username"].casefold(): raise HTTPException(403,"只能删除自己的评价")
        db.execute(text("DELETE FROM comment_replies WHERE comment_id=:id"),{"id":identifier})
        db.execute(text("DELETE FROM comment_likes WHERE comment_id=:id"),{"id":identifier})
        db.execute(text("DELETE FROM likes WHERE comment_id=:id"),{"id":identifier})
        db.execute(text("DELETE FROM comments WHERE id=:id"),{"id":identifier}); db.commit()
    return {"ok":True}


@router.post("/comments/{identifier}/like")
def toggle_like(identifier:int, request:Request):
    current=require_session(request); require_csrf(request,current); require_permission(current,"comment.like")
    with SessionLocal() as db:
        found=db.execute(text("SELECT 1 FROM comment_likes WHERE comment_id=:id AND actor=:actor"),{"id":identifier,"actor":current["username"]}).first()
        if found: db.execute(text("DELETE FROM comment_likes WHERE comment_id=:id AND actor=:actor"),{"id":identifier,"actor":current["username"]})
        else: db.execute(text("INSERT INTO comment_likes(comment_id,actor) VALUES(:id,:actor)"),{"id":identifier,"actor":current["username"]})
        db.commit(); return {"ok":True,"liked":not bool(found)}


@router.post("/comments/{identifier}/replies")
def reply_comment(identifier:int,request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"comment.create"); content=str(body.get("content") or "").strip()
    if not 1<=len(content)<=2000: raise HTTPException(400,"回复为 1–2000 字")
    now=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    with SessionLocal() as db:
        if not db.execute(text("SELECT 1 FROM comments WHERE id=:id"),{"id":identifier}).first(): raise HTTPException(404,"评价不存在")
        reply=db.execute(text("INSERT INTO comment_replies(comment_id,actor,time,content) VALUES(:id,:actor,:time,:content) RETURNING id"),{"id":identifier,"actor":current["username"],"time":now,"content":content}).scalar_one(); db.commit()
    return {"ok":True,"id":reply,"actor":current["username"],"time":now,"content":content}


@router.delete("/comment-replies/{identifier}")
def delete_reply(identifier:int,request:Request):
    current=require_session(request); require_csrf(request,current)
    with SessionLocal() as db:
        row=db.execute(text("SELECT actor FROM comment_replies WHERE id=:id"),{"id":identifier}).first()
        if not row: raise HTTPException(404,"回复不存在")
        if current["role"]!="admin" and row.actor.casefold()!=current["username"].casefold(): raise HTTPException(403,"只能删除自己的回复")
        db.execute(text("DELETE FROM comment_replies WHERE id=:id"),{"id":identifier}); db.commit()
    return {"ok":True}
