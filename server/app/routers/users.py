from fastapi import APIRouter, Request

from app.dependencies import require_csrf, require_permission, require_session
from app.legacy import dispatch

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
async def list_users(request: Request):
    current = require_session(request)
    require_permission(current, "user.manage")
    return await dispatch(request, "/api/users")


@router.post("")
async def create_user(request: Request):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "user.manage")
    return await dispatch(request, "/api/users/create")
