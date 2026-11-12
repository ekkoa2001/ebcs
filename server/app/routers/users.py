from fastapi import APIRouter, HTTPException, Request

from app.dependencies import require_csrf, require_permission, require_session
from app.schemas.identity import ProfileUpdateInput, TeamUpdateInput, UserCreateInput, UserUpdateInput
from app.services import audit, identity

router = APIRouter(prefix="/api/v1/users", tags=["users"])
compat_router = APIRouter(tags=["v1-compatibility"])


def fail(error: identity.IdentityError):
    raise HTTPException(status_code=error.status, detail=error.message)


def manager(request: Request) -> dict:
    current = require_session(request)
    require_permission(current, "user.manage")
    return current


def writer(request: Request) -> dict:
    current = manager(request)
    require_csrf(request, current)
    return current


def list_impl(request: Request):
    manager(request)
    return identity.list_users()


def create_impl(request: Request, body: UserCreateInput):
    current = writer(request)
    try:
        identity.create_user(body.username, body.password, body.role)
    except identity.IdentityError as error:
        fail(error)
    audit.record(current["username"], f"创建账号 {body.username}（{body.role}）", request, object_type="user", object_id=body.username)
    return {"ok": True}


def update_impl(request: Request, body: UserUpdateInput):
    current = writer(request)
    try:
        identity.update_user(current["username"], body.username, body.role, body.active, body.password)
    except identity.IdentityError as error:
        fail(error)
    suffix = "，重置密码" if body.password else ""
    state = "启用" if body.active else "停用"
    audit.record(current["username"], f"更新账号 {body.username}（{body.role}，{state}{suffix}）", request, object_type="user", object_id=body.username)
    return {"ok": True}


def team_impl(request: Request, body: TeamUpdateInput):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "team.update")
    try:
        identity.update_team(body.username, body.team, body.tag)
    except identity.IdentityError as error:
        fail(error)
    audit.record(current["username"], f"更新成员团队与岗位 {body.username}", request, object_type="user", object_id=body.username)
    return {"ok": True}


def profile_impl(request: Request, body: ProfileUpdateInput):
    current = require_session(request)
    require_csrf(request, current)
    require_permission(current, "profile.update_self")
    try:
        result = identity.update_profile(current["username"], body.name, body.avatar)
    except identity.IdentityError as error:
        fail(error)
    audit.record(current["username"], "更新个人资料", request, object_type="user", object_id=current["username"])
    return result


@router.get("")
def list_users(request: Request):
    return list_impl(request)


@router.post("")
def create_user(request: Request, body: UserCreateInput):
    return create_impl(request, body)


@router.patch("/{username}")
def update_user(username: str, request: Request, body: UserUpdateInput):
    body.username = username
    return update_impl(request, body)


@router.patch("/me/profile")
def update_own_profile(request: Request, body: ProfileUpdateInput):
    return profile_impl(request, body)


@compat_router.get("/api/users")
def compatibility_list_users(request: Request):
    return list_impl(request)


@compat_router.get("/api/team")
def compatibility_team(request: Request):
    return list_impl(request)


@compat_router.post("/api/users/create")
def compatibility_create_user(request: Request, body: UserCreateInput):
    return create_impl(request, body)


@compat_router.post("/api/users/update")
def compatibility_update_user(request: Request, body: UserUpdateInput):
    return update_impl(request, body)


@compat_router.post("/api/team/update")
def compatibility_update_team(request: Request, body: TeamUpdateInput):
    return team_impl(request, body)


@compat_router.post("/api/profile")
def compatibility_update_profile(request: Request, body: ProfileUpdateInput):
    return profile_impl(request, body)
