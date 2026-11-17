import base64
import secrets
import time
from datetime import datetime, timezone

from argon2 import PasswordHasher
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

import server
from app.database import SessionLocal
from app.models.identity import Profile, User

ROLES = {"admin", "editor", "viewer"}
hasher = PasswordHasher()


class IdentityError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def valid_username(value: str) -> bool:
    return 1 <= len(value) <= 64 and all(char.isalnum() or char in "._-@" for char in value)


def valid_password(value: str) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 200 and value.isascii() and value.isalnum()


def profile_dict(profile: Profile) -> dict:
    return {
        "name": profile.name,
        "avatar": profile.avatar,
        "team": profile.team,
        "tag": profile.tag,
        "joined": profile.joined,
        "mustChange": bool(profile.must_change),
        "readCursor": profile.read_cursor,
    }


def ensure_profile(db, username: str) -> Profile:
    profile = db.get(Profile, username)
    if profile is None:
        profile = Profile(
            username=username,
            name=username,
            avatar="",
            team="市场部",
            tag="",
            joined=datetime.now(timezone.utc).isoformat(),
            must_change=0,
            read_cursor=0,
        )
        db.add(profile)
        db.flush()
    return profile


def authenticate(username: str, password: str) -> tuple[User, dict] | None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.username) == username.casefold()))
        if user is None or not user.active or not server.password_matches(password, user.salt, user.password_hash):
            return None
        if not bytes(user.password_hash).startswith(b"$argon2"):
            user.salt = b""
            user.password_hash = hasher.hash(password).encode("utf-8")
        profile = ensure_profile(db, user.username)
        result = User(username=user.username, salt=user.salt, password_hash=user.password_hash, role=user.role, active=user.active)
        profile_result = profile_dict(profile)
        db.commit()
        return result, profile_result


def get_user(username: str) -> User | None:
    with SessionLocal() as db:
        user = db.get(User, username)
        if user is None:
            return None
        return User(username=user.username, salt=user.salt, password_hash=user.password_hash, role=user.role, active=user.active)


def get_profile(username: str) -> dict:
    with SessionLocal() as db:
        profile = ensure_profile(db, username)
        result = profile_dict(profile)
        db.commit()
        return result


def list_users() -> list[dict]:
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.username)).all()
        items = []
        for user in users:
            profile = ensure_profile(db, user.username)
            items.append(
                {
                    "username": user.username,
                    "role": user.role,
                    "active": bool(user.active),
                    "name": profile.name,
                    "avatar": profile.avatar,
                    "team": profile.team,
                    "tag": profile.tag,
                    "joined": profile.joined,
                }
            )
        db.commit()
        return items


def create_user(username: str, password: str, role: str) -> None:
    if not valid_username(username) or role not in ROLES:
        raise IdentityError(400, "账号或权限不符合要求")
    if not valid_password(password):
        raise IdentityError(400, "密码只能使用数字和字母")
    with SessionLocal() as db:
        try:
            db.add(User(username=username, salt=b"", password_hash=hasher.hash(password).encode("utf-8"), role=role, active=1))
            db.flush()
            db.add(
                Profile(
                    username=username,
                    name=username,
                    avatar="",
                    team="市场部",
                    tag="",
                    joined=datetime.now(timezone.utc).isoformat(),
                    must_change=1,
                    read_cursor=0,
                )
            )
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise IdentityError(409, "账号已存在") from error


def update_user(actor: str, username: str, role: str, active: bool, password: str = "") -> None:
    if not valid_username(username) or role not in ROLES:
        raise IdentityError(400, "账号或权限无效")
    if password and not valid_password(password):
        raise IdentityError(400, "密码只能使用数字和字母")
    with SessionLocal() as db:
        user = db.get(User, username)
        if user is None:
            raise IdentityError(404, "账号不存在")
        if user.username.casefold() == actor.casefold() and (not active or role != "admin"):
            raise IdentityError(400, "不能停用或降权当前登录的管理员")
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.active == 1)) or 0
        if user.role == "admin" and user.active and (role != "admin" or not active) and active_admins <= 1:
            raise IdentityError(400, "至少保留一个启用的管理员")
        user.role = role
        user.active = int(active)
        profile = ensure_profile(db, username)
        if password:
            user.salt = b""
            user.password_hash = hasher.hash(password).encode("utf-8")
            profile.must_change = 1
        db.commit()
    revoke_sessions(username)


def delete_user(actor: str, username: str) -> None:
    if actor.casefold() == username.casefold():
        raise IdentityError(400, "不能删除当前登录的管理员")
    with SessionLocal() as db:
        user = db.get(User, username)
        if user is None:
            raise IdentityError(404, "账号不存在")
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.active == 1)) or 0
        if user.role == "admin" and user.active and active_admins <= 1:
            raise IdentityError(400, "至少保留一个启用的管理员")
        profile = db.get(Profile, username)
        if profile is not None:
            db.delete(profile)
        db.execute(text("DELETE FROM user_profiles WHERE username=:username"), {"username": username})
        db.delete(user)
        db.commit()
    revoke_sessions(username)


def update_team(username: str, team: str, tag: str) -> None:
    with SessionLocal() as db:
        if db.get(User, username) is None:
            raise IdentityError(404, "账号不存在")
        profile = ensure_profile(db, username)
        profile.team = team
        profile.tag = tag
        db.commit()


def avatar_valid(value: str) -> bool:
    if not value:
        return True
    try:
        header, payload = value.split(";base64,", 1)
        raw = base64.b64decode(payload, validate=True)
    except (ValueError, TypeError):
        return False
    return (
        (header == "data:image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n"))
        or (header == "data:image/jpeg" and raw.startswith(b"\xff\xd8\xff"))
        or (header == "data:image/webp" and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
    )


def update_profile(username: str, name: str, avatar: str) -> dict:
    if not name.strip() or not avatar_valid(avatar):
        raise IdentityError(400, "名字为 1–40 字；头像请用小于 300 KB 的 PNG/JPG/WebP")
    with SessionLocal() as db:
        profile = ensure_profile(db, username)
        profile.name = name.strip()
        profile.avatar = avatar
        result = profile_dict(profile)
        db.commit()
        return result


def change_password(username: str, current: str, password: str) -> None:
    if password == current:
        raise IdentityError(400, "新密码不能与当前密码相同")
    if not valid_password(password):
        raise IdentityError(400, "密码只能使用数字和字母")
    with SessionLocal() as db:
        user = db.get(User, username)
        if user is None or not user.active or not server.password_matches(current, user.salt, user.password_hash):
            raise IdentityError(403, "当前密码不正确")
        user.salt = b""
        user.password_hash = hasher.hash(password).encode("utf-8")
        ensure_profile(db, username).must_change = 0
        db.commit()
    revoke_sessions(username)


def create_session(username: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    server.SESSIONS[token] = {"username": username, "csrf": csrf, "created": time.time(), "activeAt": time.time()}
    return token, csrf


def revoke_sessions(username: str) -> None:
    for token, record in list(server.SESSIONS.items()):
        if str(record.get("username", "")).casefold() == username.casefold():
            server.SESSIONS.pop(token, None)


def login_allowed(ip: str, username: str) -> bool:
    now = time.time()
    key = f"{ip}|{username.casefold()[:64]}"
    attempts = [value for value in server.ATTEMPTS.get(key, []) if now - value < 900]
    ip_attempts = [value for value in server.IP_ATTEMPTS.get(ip, []) if now - value < 900]
    server.ATTEMPTS[key] = attempts
    server.IP_ATTEMPTS[ip] = ip_attempts
    return len(attempts) < 5 and len(ip_attempts) < 25


def register_failure(ip: str, username: str) -> None:
    now = time.time()
    key = f"{ip}|{username.casefold()[:64]}"
    attempts = list(server.ATTEMPTS.get(key, []))
    attempts.append(now)
    server.ATTEMPTS[key] = attempts
    ip_attempts = list(server.IP_ATTEMPTS.get(ip, []))
    ip_attempts.append(now)
    server.IP_ATTEMPTS[ip] = ip_attempts


def clear_failures(ip: str, username: str) -> None:
    server.ATTEMPTS.pop(f"{ip}|{username.casefold()[:64]}", None)
    server.IP_ATTEMPTS.pop(ip, None)
