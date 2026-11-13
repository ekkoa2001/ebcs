from fastapi import APIRouter, HTTPException, Query, Request

from app.dependencies import require_csrf, require_permission, require_session
from app.rbac import allows
from app.schemas.creative import HookInput, ProductEntryInput
from app.services import audit, creative_hooks, product_entries, resources
from app.database import SessionLocal
from app.routers.resource_helpers import bind_resource

router = APIRouter(prefix="/api/v1/creative", tags=["creative"])
bind_resource(router, "/scripts", "scripts", "完整脚本")
bind_resource(router, "/storyboard-shots", "storyboard_shots", "分镜")
bind_resource(router, "/produced-videos", "produced_videos", "成品")


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
    with SessionLocal() as db: resources.emit_event(db,current["username"],"创意钩子",row.id,row.title); db.commit()
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


def fail_entry(error: product_entries.ProductEntryError):
    raise HTTPException(status_code=error.status, detail=error.message)


@router.get("/product-entries")
def list_product_entries(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, alias="pageSize", ge=1, le=100), search: str = "", hook_id: str = Query("", alias="hookId"), status: str = "", include_archived: bool = Query(False, alias="includeArchived")):
    current = require_session(request); require_permission(current, "content.read")
    if include_archived: require_permission(current, "content.restore")
    return product_entries.list_entries(page, page_size, search, hook_id, status, include_archived)


@router.get("/product-entries/{identifier}")
def get_product_entry(identifier: str, request: Request):
    current = require_session(request); require_permission(current, "content.read")
    try: return product_entries.public(product_entries.get_entry(identifier))
    except product_entries.ProductEntryError as error: fail_entry(error)


@router.post("/product-entries")
def create_product_entry(request: Request, body: ProductEntryInput):
    current = require_session(request); require_csrf(request, current); require_permission(current, "content.create")
    try: row = product_entries.create_entry(current["username"], body)
    except product_entries.ProductEntryError as error: fail_entry(error)
    audit.record(current["username"], f"新增产品出场 {row.code} {row.title}", request, module="creative", object_type="product_entry", object_id=row.id)
    with SessionLocal() as db: resources.emit_event(db,current["username"],"产品出场",row.id,row.title); db.commit()
    return product_entries.public(row)


@router.put("/product-entries/{identifier}")
def update_product_entry(identifier: str, request: Request, body: ProductEntryInput):
    current = require_session(request); require_csrf(request, current); require_permission(current, "content.update_own")
    try: row = product_entries.update_entry(current["username"], allows(current["role"], "content.update_any"), identifier, body)
    except product_entries.ProductEntryError as error: fail_entry(error)
    audit.record(current["username"], f"修改产品出场 {row.code} {row.title}", request, module="creative", object_type="product_entry", object_id=row.id)
    return product_entries.public(row)


@router.delete("/product-entries/{identifier}")
def archive_product_entry(identifier: str, request: Request):
    current = require_session(request); require_csrf(request, current); require_permission(current, "content.archive")
    try: row = product_entries.archive_entry(identifier)
    except product_entries.ProductEntryError as error: fail_entry(error)
    audit.record(current["username"], f"归档产品出场 {row.code} {row.title}", request, module="creative", object_type="product_entry", object_id=row.id)
    return {"ok": True}


@router.post("/product-entries/{identifier}/restore")
def restore_product_entry(identifier: str, request: Request):
    current = require_session(request); require_csrf(request, current); require_permission(current, "content.restore")
    try: row = product_entries.restore_entry(identifier)
    except product_entries.ProductEntryError as error: fail_entry(error)
    audit.record(current["username"], f"恢复产品出场 {row.code} {row.title}", request, module="creative", object_type="product_entry", object_id=row.id)
    return product_entries.public(row)
