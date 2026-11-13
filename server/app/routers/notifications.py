from fastapi import APIRouter, Request
from sqlalchemy import text
from app.database import SessionLocal
from app.dependencies import require_csrf, require_session

router = APIRouter(prefix="/api/v1", tags=["notifications"])

@router.get("/notifications")
def list_notifications(request:Request):
    current=require_session(request)
    with SessionLocal() as db:
        cursor=db.execute(text("SELECT read_cursor FROM user_profiles WHERE username=:u"),{"u":current["username"]}).scalar() or 0
        rows=db.execute(text("SELECT * FROM notifications WHERE recipient='' OR recipient=:u ORDER BY id DESC LIMIT 100"),{"u":current["username"]}).all()
        return {"readCursor":cursor,"unread":sum(1 for x in rows if x.id>cursor),"items":[dict(x._mapping) for x in rows]}

@router.post("/notifications/read")
def read_notifications(request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); cursor=int(body.get("cursor") or 0)
    with SessionLocal() as db:
        db.execute(text("UPDATE user_profiles SET read_cursor=CASE WHEN read_cursor>:c THEN read_cursor ELSE :c END WHERE username=:u"),{"c":cursor,"u":current["username"]}); db.commit()
    return {"ok":True}
