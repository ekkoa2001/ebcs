from fastapi import APIRouter, Request

from app.dependencies import require_csrf, require_session
from app.legacy import dispatch

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request):
    return await dispatch(request, "/api/login")


@router.post("/logout")
async def logout(request: Request):
    return await dispatch(request, "/api/logout")


@router.post("/password")
async def password(request: Request):
    return await dispatch(request, "/api/password")


@router.get("/session")
def current(request: Request):
    found = require_session(request)
    require_csrf(request, found) if request.method == "POST" else None
    return dispatch_session(found)


def dispatch_session(found: dict):
    import team_server
    with team_server.connect() as connection:
        profile = team_server.profile(connection, found["username"])
    return {"username": found["username"], "role": found["role"], "csrf": found["csrf"], "profile": profile}
