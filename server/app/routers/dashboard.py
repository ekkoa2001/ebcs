from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from sqlalchemy import text
from app.database import SessionLocal
from app.dependencies import require_permission, require_session
from app.routers.resource_helpers import bind_resource

router=APIRouter(prefix="/api/v1",tags=["dashboard"])
bind_resource(router,"/tasks","team_tasks","待办")

def scalar(db, sql, params=None): return db.execute(text(sql),params or {}).scalar() or 0

@router.get("/dashboard/summary")
def dashboard_summary(request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db:
        today=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        counts={"hooks":scalar(db,"SELECT COUNT(*) FROM creative_hooks WHERE deleted_at IS NULL"),"productEntries":scalar(db,"SELECT COUNT(*) FROM product_entries WHERE deleted_at IS NULL"),"scripts":scalar(db,"SELECT COUNT(*) FROM scripts WHERE deleted_at IS NULL"),"shots":scalar(db,"SELECT COUNT(*) FROM storyboard_shots"),"videos":scalar(db,"SELECT COUNT(*) FROM produced_videos"),"brandContent":scalar(db,"SELECT COUNT(*) FROM brand_content_projects WHERE deleted_at IS NULL"),"marketingPlans":scalar(db,"SELECT COUNT(*) FROM marketing_plans WHERE deleted_at IS NULL"),"activeCampaigns":scalar(db,"SELECT COUNT(*) FROM ad_campaigns WHERE COALESCE(start_date,'')!='' AND start_date<=:today AND (COALESCE(end_date,'')='' OR end_date>=:today)",{"today":today}),"competitorInsights":scalar(db,"SELECT COUNT(*) FROM competitor_insights WHERE deleted_at IS NULL")}
    return {"counts":counts}

@router.get("/dashboard")
def dashboard(request:Request):
    current=require_session(request); require_permission(current,"content.read")
    with SessionLocal() as db:
        today=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        counts={"hooks":scalar(db,"SELECT COUNT(*) FROM creative_hooks WHERE deleted_at IS NULL"),"productEntries":scalar(db,"SELECT COUNT(*) FROM product_entries WHERE deleted_at IS NULL"),"scripts":scalar(db,"SELECT COUNT(*) FROM scripts WHERE deleted_at IS NULL"),"shots":scalar(db,"SELECT COUNT(*) FROM storyboard_shots"),"videos":scalar(db,"SELECT COUNT(*) FROM produced_videos"),"brandContent":scalar(db,"SELECT COUNT(*) FROM brand_content_projects WHERE deleted_at IS NULL"),"marketingPlans":scalar(db,"SELECT COUNT(*) FROM marketing_plans WHERE deleted_at IS NULL"),"activeCampaigns":scalar(db,"SELECT COUNT(*) FROM ad_campaigns WHERE COALESCE(start_date,'')!='' AND start_date<=:today AND (COALESCE(end_date,'')='' OR end_date>=:today)",{"today":today}),"competitorInsights":scalar(db,"SELECT COUNT(*) FROM competitor_insights WHERE deleted_at IS NULL")}
        latest={}
        for key,table in (("creative","scripts"),("content","brand_content_projects"),("marketing","marketing_plans")):
            rows=db.execute(text(f"SELECT * FROM {table} WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT 5")).all(); latest[key]=[dict(x._mapping) for x in rows]
        tasks=[dict(x._mapping) for x in db.execute(text("SELECT * FROM team_tasks WHERE deleted_at IS NULL AND (assignee=:u OR owner=:u OR :role='admin') ORDER BY due_date,updated_at DESC LIMIT 10"),{"u":current["username"],"role":current["role"]}).all()]
        activity=[dict(x._mapping) for x in db.execute(text("SELECT actor,time,action,object_type,object_id FROM activity_logs ORDER BY id DESC LIMIT 12")).all()]
    return {"counts":counts,"latest":latest,"tasks":tasks,"activity":activity}
