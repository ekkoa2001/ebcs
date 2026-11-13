from fastapi import APIRouter, HTTPException, Request
from app.dependencies import require_csrf, require_permission, require_session
from app.rbac import allows
from app.services import resources
from app.routers.resource_helpers import bind_resource

router = APIRouter(prefix="/api/v1", tags=["content"])
bind_resource(router, "/content/projects", "brand_content_projects", "品牌内容")
bind_resource(router, "/content/assets", "content_assets", "内容图片")

@router.post("/content/assets/{identifier}/review")
def review_asset(identifier:str,request:Request,body:dict):
    current=require_session(request); require_csrf(request,current); require_permission(current,"content.update_own")
    status=str(body.get("status") or "")
    if status not in {"待审核","已通过","待修改"}: raise HTTPException(400,"审核状态无效")
    try: return resources.update_row("content_assets",current["username"],allows(current["role"],"content.update_any"),identifier,{"review_status":status,"is_final":int(bool(body.get("isFinal")))})
    except resources.ResourceError as error: raise HTTPException(error.status,error.message)
