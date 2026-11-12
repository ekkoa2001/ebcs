import time

from fastapi import HTTPException, Request

import server
from app.config import settings
from app.rbac import allows


def session_from(request: Request):
    token = request.cookies.get("sana_session")
    if not token:
        return None
    record = server.SESSIONS.get(token)
    if not record or time.time() - float(record.get("created", 0)) > server.MAX_SESSION:
        if token:
            server.SESSIONS.pop(token, None)
        return None
    with server.connect() as connection:
        row = connection.execute("SELECT username,role,active FROM users WHERE username=?", (record.get("username"),)).fetchone()
    if not row or not row[2]:
        server.SESSIONS.pop(token, None)
        return None
    return {"token": token, "username": row[0], "role": row[1], "csrf": record.get("csrf", "")}


def require_session(request: Request):
    found = session_from(request)
    if not found:
        raise HTTPException(status_code=401, detail="请先登录")
    return found


def require_same_origin(request: Request):
    host = request.headers.get("host", "")
    expected = ("https://" if settings["secure"] else "http://") + host
    if request.headers.get("origin", "") != expected:
        raise HTTPException(status_code=403, detail="请求来源无效")


def require_csrf(request: Request, current: dict):
    require_same_origin(request)
    import hmac
    supplied = request.headers.get("x-csrf-token", "")
    if not hmac.compare_digest(supplied, current.get("csrf", "")):
        raise HTTPException(status_code=403, detail="请求校验失败")


def require_permission(current: dict, code: str):
    if not allows(current["role"], code):
        raise HTTPException(status_code=403, detail="没有权限")
