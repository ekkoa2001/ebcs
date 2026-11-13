from fastapi import HTTPException, Query, Request

from app.dependencies import require_csrf, require_permission, require_session
from app.rbac import allows
from app.services import audit, resources


def failure(error): raise HTTPException(status_code=error.status, detail=error.message)


def bind_resource(router, path, table, object_type):
    mutation_permission = "ad.update" if table in {"ad_campaigns", "ad_period_records"} else None
    @router.get(path)
    def listing(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, alias="pageSize", ge=1, le=100), search: str = "", include_archived: bool = Query(False, alias="includeArchived")):
        current = require_session(request); require_permission(current, "content.read")
        if include_archived: require_permission(current, "content.restore")
        reserved={"page","pageSize","search","includeArchived"}
        filters={key:value for key,value in request.query_params.items() if key not in reserved}
        return resources.list_rows(table, page, page_size, search, include_archived, filters)

    @router.get(path + "/{identifier}")
    def detail(identifier: str, request: Request):
        current = require_session(request); require_permission(current, "content.read")
        try: return resources.get_row(table, identifier)
        except resources.ResourceError as error: failure(error)

    @router.post(path)
    def create(request: Request, body: dict):
        current = require_session(request); require_csrf(request, current); require_permission(current, mutation_permission or "content.create")
        try: row = resources.create_row(table, current["username"], body)
        except resources.ResourceError as error: failure(error)
        audit.record(current["username"], f"新增{object_type} {row.get(resources.CONFIG[table]['title'],'')}", request, module=object_type, object_type=object_type, object_id=row["id"])
        mirror_script_resource(table, row["id"])
        return row

    @router.put(path + "/{identifier}")
    def update(identifier: str, request: Request, body: dict):
        current = require_session(request); require_csrf(request, current); require_permission(current, mutation_permission or "content.update_own")
        try: row = resources.update_row(table, current["username"], allows(current["role"], "content.update_any"), identifier, body)
        except resources.ResourceError as error: failure(error)
        audit.record(current["username"], f"修改{object_type}", request, module=object_type, object_type=object_type, object_id=identifier)
        mirror_script_resource(table, identifier)
        return row

    @router.delete(path + "/{identifier}")
    def archive(identifier: str, request: Request):
        current = require_session(request); require_csrf(request, current); require_permission(current, mutation_permission or "content.archive")
        script_id = script_resource_id(table, identifier)
        try: result = resources.archive_row(table, identifier, False, current["username"], "用户归档")
        except resources.ResourceError as error: failure(error)
        audit.record(current["username"], f"归档{object_type}", request, module=object_type, object_type=object_type, object_id=identifier)
        if script_id:
            from app.services.scripts import mirror_to_legacy
            mirror_to_legacy(script_id, archived=(table == "scripts"))
        return result

    if resources.CONFIG[table].get("soft"):
        @router.post(path + "/{identifier}/restore")
        def restore(identifier: str, request: Request):
            current = require_session(request); require_csrf(request, current); require_permission(current, "content.restore")
            try: result = resources.archive_row(table, identifier, True, current["username"])
            except resources.ResourceError as error: failure(error)
            audit.record(current["username"], f"恢复{object_type}", request, module=object_type, object_type=object_type, object_id=identifier)
            mirror_script_resource(table, identifier)
            return result


def script_resource_id(table, identifier):
    if table not in {"scripts", "storyboard_shots", "produced_videos", "ad_campaigns", "ad_period_records"}:
        return None
    from app.services.scripts import script_id_for
    return script_id_for(table, identifier)


def mirror_script_resource(table, identifier):
    script_id = script_resource_id(table, identifier)
    if script_id:
        from app.services.scripts import mirror_to_legacy
        mirror_to_legacy(script_id)
