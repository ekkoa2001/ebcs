import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import server
from app.config import settings
from app.dependencies import require_csrf, require_same_origin, require_session
from app.schemas.identity import LoginInput, PasswordInput
from app.services import audit, identity

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
compat_router = APIRouter(tags=["v1-compatibility"])


def fail(error: identity.IdentityError):
    raise HTTPException(status_code=error.status, detail=error.message)


def session_payload(found: dict) -> dict:
    return {
        "username": found["username"],
        "role": found["role"],
        "csrf": found["csrf"],
        "profile": identity.get_profile(found["username"]),
    }


async def login_impl(request: Request, body: LoginInput):
    require_same_origin(request)
    ip = request.client.host if request.client else "127.0.0.1"
    if not identity.login_allowed(ip, body.username):
        raise HTTPException(status_code=429, detail="登录尝试过多，请 15 分钟后再试。")
    found = identity.authenticate(body.username, body.password)
    if found is None:
        identity.register_failure(ip, body.username)
        audit.record(body.username[:64] or "anonymous", "登录失败", request, result="denied")
        raise HTTPException(status_code=401, detail="账号或密码错误")
    user, _profile = found
    identity.clear_failures(ip, body.username)
    token, _csrf = identity.create_session(user.username)
    audit.record(user.username, "登录成功", request)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        "sana_session",
        token,
        max_age=server.MAX_SESSION,
        httponly=True,
        secure=settings["secure"],
        samesite="strict",
        path="/",
    )
    return response


async def logout_impl(request: Request):
    current = require_session(request)
    require_csrf(request, current)
    server.SESSIONS.pop(current["token"], None)
    audit.record(current["username"], "退出登录", request)
    response = JSONResponse({"ok": True})
    response.delete_cookie("sana_session", path="/", httponly=True, secure=settings["secure"], samesite="strict")
    return response


async def password_impl(request: Request, body: PasswordInput):
    current = require_session(request)
    require_csrf(request, current)
    try:
        identity.change_password(current["username"], body.current, body.password)
    except identity.IdentityError as error:
        fail(error)
    audit.record(current["username"], "修改密码", request, object_type="user", object_id=current["username"])
    response = JSONResponse({"ok": True, "relogin": True})
    response.delete_cookie("sana_session", path="/", httponly=True, secure=settings["secure"], samesite="strict")
    return response


@router.post("/login")
async def login(request: Request, body: LoginInput):
    return await login_impl(request, body)


@router.post("/logout")
async def logout(request: Request):
    return await logout_impl(request)


@router.post("/password")
async def password(request: Request, body: PasswordInput):
    return await password_impl(request, body)


@router.get("/session")
def current(request: Request):
    return session_payload(require_session(request))


@compat_router.post("/api/login")
async def compatibility_login(request: Request, body: LoginInput):
    return await login_impl(request, body)


@compat_router.post("/api/logout")
async def compatibility_logout(request: Request):
    return await logout_impl(request)


@compat_router.post("/api/password")
async def compatibility_password(request: Request, body: PasswordInput):
    return await password_impl(request, body)


@compat_router.get("/api/session")
def compatibility_session(request: Request):
    return session_payload(require_session(request))


@compat_router.get("/api/bootstrap")
def compatibility_bootstrap(request: Request):
    """Return the data the legacy workspace needs for its first render in one request."""
    current = require_session(request)
    with server.LOCK, server.connect() as connection:
        version, raw_entries = connection.execute(
            "SELECT version, entries FROM state WHERE id=1"
        ).fetchone()
    return {
        "session": session_payload(current),
        "state": {
            "version": version,
            "entries": json.loads(raw_entries) if raw_entries else [],
        },
    }


@compat_router.get("/api/state/version")
def compatibility_state_version(request: Request):
    """Small polling endpoint used to avoid repeatedly transferring all workspace data."""
    require_session(request)
    with server.LOCK, server.connect() as connection:
        version = connection.execute("SELECT version FROM state WHERE id=1").fetchone()[0]
    return {"version": version}
