from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app.database import SessionLocal
from app.dependencies import require_permission, require_session
from app.models.foundation import ActivityLog

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


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


compat_router = APIRouter(tags=["v1-compatibility"])


@compat_router.get("/api/log")
def compatibility_log(request: Request):
    return legacy_log(request)
