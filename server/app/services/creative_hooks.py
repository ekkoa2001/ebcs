import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

import server
from app.database import SessionLocal
from app.models.creative import CreativeHook


class HookError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def created_at_of(item: dict) -> str:
    date = str(item.get("created") or "")
    clock = str(item.get("createdTime") or "")
    return (date + ("T" + clock if clock else "")).strip("T")


def apply_legacy(row: CreativeHook, item: dict, actor: str = "") -> None:
    stamp = now()
    row.code = str(item.get("code") or "")[:80]
    row.title = str(item.get("title") or "")[:300]
    row.content = str(item.get("content") or "")
    row.hook_type = str(item.get("hook") or "")[:120]
    row.product = str(item.get("product") or "")[:200]
    row.audience = str(item.get("audience") or "")[:200]
    row.scene = str(item.get("scene") or "")[:200]
    row.reference_material = str(item.get("referenceMaterial") or "")
    row.notes = str(item.get("notes") or "")
    row.status = str(item.get("selectionStatus") or "待筛选")[:40]
    row.is_example = int(bool(item.get("isExample")))
    row.created_by = str(item.get("createdBy") or actor or "")[:64]
    row.owner = str(item.get("owner") or row.created_by)[:64]
    row.created_at = created_at_of(item) or row.created_at or stamp
    row.updated_at = stamp
    row.deleted_at = None
    row.legacy_json = json.dumps(item, ensure_ascii=False, separators=(",", ":"))


def to_legacy(row: CreativeHook) -> dict:
    try:
        item = json.loads(row.legacy_json or "{}")
    except json.JSONDecodeError:
        item = {}
    date, _, clock = (row.created_at or "").partition("T")
    item.update(
        {
            "id": row.id,
            "kind": "开头创意",
            "code": row.code,
            "title": row.title,
            "content": row.content,
            "hook": row.hook_type,
            "product": row.product,
            "audience": row.audience,
            "scene": row.scene,
            "referenceMaterial": row.reference_material,
            "notes": row.notes,
            "selectionStatus": row.status,
            "isExample": bool(row.is_example),
            "createdBy": row.created_by,
            "owner": row.owner,
            "created": date,
            "createdTime": clock,
        }
    )
    return item


def public(row: CreativeHook) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "title": row.title,
        "content": row.content,
        "hookType": row.hook_type,
        "product": row.product,
        "audience": row.audience,
        "scene": row.scene,
        "referenceMaterial": row.reference_material,
        "notes": row.notes,
        "status": row.status,
        "isExample": bool(row.is_example),
        "createdBy": row.created_by,
        "owner": row.owner,
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
        "version": row.version,
        "archivedAt": row.deleted_at,
    }


def read_legacy_entries() -> list[dict]:
    with server.connect() as connection:
        found = connection.execute("SELECT entries FROM state WHERE id=1").fetchone()
    if not found or not found[0]:
        return []
    value = json.loads(found[0])
    return value if isinstance(value, list) else []


def synchronize_from_entries(entries: list[dict], actor: str = "") -> dict:
    hooks = [item for item in entries if item.get("kind") == "开头创意" and isinstance(item.get("id"), str)]
    identifiers = {item["id"] for item in hooks}
    inserted = updated = archived = 0
    with SessionLocal() as db:
        existing = {row.id: row for row in db.scalars(select(CreativeHook)).all()}
        for item in hooks:
            row = existing.get(item["id"])
            if row is None:
                row = CreativeHook(id=item["id"], title=str(item.get("title") or ""), created_at="", updated_at="", version=1)
                db.add(row)
                inserted += 1
            else:
                updated += 1
            apply_legacy(row, item, actor)
        stamp = now()
        for identifier, row in existing.items():
            if identifier not in identifiers and row.deleted_at is None:
                row.deleted_at = stamp
                row.updated_at = stamp
                row.version += 1
                archived += 1
        db.commit()
    return {"found": len(hooks), "inserted": inserted, "updated": updated, "archived": archived}


def synchronize_from_legacy_state() -> dict:
    return synchronize_from_entries(read_legacy_entries(), "migration")


def mirror_to_legacy(row: CreativeHook | None, identifier: str, archived: bool = False) -> None:
    with server.connect() as connection:
        found = connection.execute("SELECT version,entries FROM state WHERE id=1").fetchone()
        if not found:
            return
        version, raw = found
        entries = json.loads(raw or "[]")
        index = next((position for position, item in enumerate(entries) if item.get("id") == identifier), None)
        if archived:
            if index is not None:
                entries.pop(index)
        elif row is not None:
            item = to_legacy(row)
            if index is None:
                entries.append(item)
            else:
                entries[index] = item
        connection.execute("UPDATE state SET version=?,entries=? WHERE id=1", (version + 1, json.dumps(entries, ensure_ascii=False)))
        connection.commit()


def list_hooks(page: int, page_size: int, search: str = "", status: str = "", include_archived: bool = False) -> dict:
    filters = []
    if not include_archived:
        filters.append(CreativeHook.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        filters.append(or_(CreativeHook.title.ilike(pattern), CreativeHook.code.ilike(pattern), CreativeHook.content.ilike(pattern)))
    if status:
        filters.append(CreativeHook.status == status)
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(CreativeHook).where(*filters)) or 0
        rows = db.scalars(
            select(CreativeHook)
            .where(*filters)
            .order_by(CreativeHook.created_at.desc(), CreativeHook.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return {"page": page, "pageSize": page_size, "total": total, "items": [public(row) for row in rows]}


def get_hook(identifier: str, include_archived: bool = False) -> CreativeHook:
    with SessionLocal() as db:
        row = db.get(CreativeHook, identifier)
        if row is None or (row.deleted_at and not include_archived):
            raise HookError(404, "创意钩子不存在")
        db.expunge(row)
        return row


def create_hook(actor: str, body) -> CreativeHook:
    stamp = now()
    identifier = "hook_" + secrets.token_hex(16)
    legacy = {
        "id": identifier,
        "kind": "开头创意",
        "code": body.code,
        "title": body.title.strip(),
        "content": body.content,
        "hook": body.hookType,
        "product": body.product,
        "audience": body.audience,
        "scene": body.scene,
        "referenceMaterial": body.referenceMaterial,
        "notes": body.notes,
        "selectionStatus": body.status,
        "isExample": body.isExample,
        "createdBy": actor,
        "owner": actor,
    }
    if body.createdAt:
        date, _, clock = body.createdAt.partition("T")
        legacy["created"] = date
        legacy["createdTime"] = clock
    row = CreativeHook(id=identifier, title=body.title.strip(), created_at=body.createdAt or stamp, updated_at=stamp, version=1)
    apply_legacy(row, legacy, actor)
    with SessionLocal() as db:
        db.add(row)
        db.commit()
        db.refresh(row)
        db.expunge(row)
    mirror_to_legacy(row, row.id)
    return row


def update_hook(actor: str, can_update_any: bool, identifier: str, body) -> CreativeHook:
    with SessionLocal() as db:
        row = db.get(CreativeHook, identifier)
        if row is None or row.deleted_at:
            raise HookError(404, "创意钩子不存在")
        if not can_update_any and row.created_by.casefold() != actor.casefold():
            raise HookError(403, "不能修改其他成员的内容，可在内容下添加评价")
        if body.version is not None and body.version != row.version:
            raise HookError(409, "此内容已被其他成员修改，请刷新后重试")
        legacy = to_legacy(row)
        legacy.update(
            {
                "code": body.code,
                "title": body.title.strip(),
                "content": body.content,
                "hook": body.hookType,
                "product": body.product,
                "audience": body.audience,
                "scene": body.scene,
                "referenceMaterial": body.referenceMaterial,
                "notes": body.notes,
                "selectionStatus": body.status,
                "isExample": body.isExample,
            }
        )
        apply_legacy(row, legacy, actor)
        row.version += 1
        db.commit()
        db.refresh(row)
        db.expunge(row)
    mirror_to_legacy(row, row.id)
    return row


def archive_hook(identifier: str) -> CreativeHook:
    with SessionLocal() as db:
        row = db.get(CreativeHook, identifier)
        if row is None or row.deleted_at:
            raise HookError(404, "创意钩子不存在")
        row.deleted_at = now()
        row.updated_at = row.deleted_at
        row.version += 1
        db.commit()
        db.refresh(row)
        db.expunge(row)
    mirror_to_legacy(None, identifier, archived=True)
    return row


def restore_hook(identifier: str) -> CreativeHook:
    with SessionLocal() as db:
        row = db.get(CreativeHook, identifier)
        if row is None or row.deleted_at is None:
            raise HookError(404, "归档记录不存在")
        row.deleted_at = None
        row.updated_at = now()
        row.version += 1
        db.commit()
        db.refresh(row)
        db.expunge(row)
    mirror_to_legacy(row, identifier)
    return row
