from fastapi import APIRouter, HTTPException, Query, Request

from app.dependencies import require_csrf, require_permission, require_session
from app.rbac import allows
from app.schemas.creative import HookInput
from app.services import audit, creative_hooks

router = APIRouter(prefix="/api/v1/creative", tags=["creative"])


def fail(error: creative_hooks.HookError):
    raise HTTPException(status_code=error.status, detail=error.message)


@router.get("/hooks")
def list_hooks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    search: str = Query("", max_length=200),
    status: str = Query("", max_length=40),
    include_archived: bool = Query(False, alias="includeArchived"),
):
    current = require_session(request)
    require_permission(current, "content.read")
    if include_archived:
        require_permission(current, "content.restore")
    return creative_hooks.list_hooks(page, page_size, search, status, include_archived)


@router.get("/hooks/{identifier}")
def get_hook(identifier: str, request: Request):
    current = require_session(request)
    require_permission(current, "content.read")
    try:
        return creative_hooks.public(creative_hooks.get_hook(identifier))
    except creative_hooks.HookError as error:
        fail(error)


@router.post("/hooks")
def create_hook(request: Request, body: HookInput):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "content.create")
    try:
        row = creative_hooks.create_hook(current["username"], body)
    except creative_hooks.HookError as error:
        fail(error)
    audit.record(current["username"], f"新增创意钩子 {row.code} {row.title}", request, module="creative", object_type="creative_hook", object_id=row.id)
    return creative_hooks.public(row)


@router.put("/hooks/{identifier}")
def update_hook(identifier: str, request: Request, body: HookInput):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "content.update_own")
    try:
        row = creative_hooks.update_hook(current["username"], allows(current["role"], "content.update_any"), identifier, body)
    except creative_hooks.HookError as error:
        fail(error)
    audit.record(current["username"], f"修改创意钩子 {row.code} {row.title}", request, module="creative", object_type="creative_hook", object_id=row.id)
    return creative_hooks.public(row)


@router.delete("/hooks/{identifier}")
def archive_hook(identifier: str, request: Request):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "content.archive")
    try:
        row = creative_hooks.archive_hook(identifier)
    except creative_hooks.HookError as error:
        fail(error)
    audit.record(current["username"], f"归档创意钩子 {row.code} {row.title}", request, module="creative", object_type="creative_hook", object_id=row.id)
    return {"ok": True}


@router.post("/hooks/{identifier}/restore")
def restore_hook(identifier: str, request: Request):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "content.restore")
    try:
        row = creative_hooks.restore_hook(identifier)
    except creative_hooks.HookError as error:
        fail(error)
    audit.record(current["username"], f"恢复创意钩子 {row.code} {row.title}", request, module="creative", object_type="creative_hook", object_id=row.id)
    return creative_hooks.public(row)
