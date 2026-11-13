import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

import server
from app.database import SessionLocal
from app.models.creative import CreativeHook, ProductEntry


class ProductEntryError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def now(): return datetime.now(timezone.utc).isoformat()


def created_at_of(item):
    date, clock = str(item.get("created") or ""), str(item.get("createdTime") or "")
    return (date + ("T" + clock if clock else "")).strip("T")


def apply_legacy(row, item, actor=""):
    stamp = now()
    row.hook_id = str(item.get("parent") or item.get("hookId") or "")[:80]
    row.code = str(item.get("code") or "")[:80]
    row.title = str(item.get("title") or "")[:300]
    row.entry_type = str(item.get("transition") or item.get("entryType") or "")[:120]
    row.entry_time = str(item.get("entryTime") or "")[:80]
    row.transition_logic = str(item.get("content") or item.get("transitionLogic") or "")
    row.selling_points = str(item.get("sellingPoints") or "")
    row.visual_description = str(item.get("visualDescription") or "")
    row.product = str(item.get("product") or "")[:200]
    row.notes = str(item.get("notes") or "")
    row.status = str(item.get("selectionStatus") or "待筛选")[:40]
    row.is_example = int(bool(item.get("isExample")))
    row.created_by = str(item.get("createdBy") or actor or "")[:64]
    row.owner = str(item.get("owner") or row.created_by)[:64]
    row.created_at = created_at_of(item) or row.created_at or stamp
    row.updated_at, row.deleted_at = stamp, None
    row.legacy_json = json.dumps(item, ensure_ascii=False, separators=(",", ":"))


def to_legacy(row):
    try: item = json.loads(row.legacy_json or "{}")
    except json.JSONDecodeError: item = {}
    date, _, clock = (row.created_at or "").partition("T")
    item.update({"id": row.id, "kind": "产品出场", "parent": row.hook_id, "hookId": row.hook_id,
        "code": row.code, "title": row.title, "transition": row.entry_type, "entryType": row.entry_type,
        "entryTime": row.entry_time, "content": row.transition_logic, "transitionLogic": row.transition_logic,
        "sellingPoints": row.selling_points, "visualDescription": row.visual_description, "product": row.product,
        "notes": row.notes, "selectionStatus": row.status, "isExample": bool(row.is_example),
        "createdBy": row.created_by, "owner": row.owner, "created": date, "createdTime": clock})
    return item


def public(row):
    return {"id": row.id, "hookId": row.hook_id, "code": row.code, "title": row.title,
        "entryType": row.entry_type, "entryTime": row.entry_time, "transitionLogic": row.transition_logic,
        "sellingPoints": row.selling_points, "visualDescription": row.visual_description, "product": row.product,
        "notes": row.notes, "status": row.status, "isExample": bool(row.is_example), "createdBy": row.created_by,
        "owner": row.owner, "createdAt": row.created_at, "updatedAt": row.updated_at, "version": row.version,
        "archivedAt": row.deleted_at}


def read_legacy_entries():
    with server.connect() as connection: found = connection.execute("SELECT entries FROM state WHERE id=1").fetchone()
    value = json.loads(found[0]) if found and found[0] else []
    return value if isinstance(value, list) else []


def synchronize_from_entries(entries, actor=""):
    items = [x for x in entries if x.get("kind") == "产品出场" and isinstance(x.get("id"), str)]
    identifiers = {x["id"] for x in items}; inserted = updated = archived = skipped = 0
    with SessionLocal() as db:
        existing = {x.id: x for x in db.scalars(select(ProductEntry)).all()}
        hooks = {x.id for x in db.scalars(select(CreativeHook)).all()}
        for item in items:
            hook_id = str(item.get("parent") or item.get("hookId") or "")
            if hook_id not in hooks: skipped += 1; continue
            row = existing.get(item["id"])
            if row is None:
                row = ProductEntry(id=item["id"], hook_id=hook_id, title=str(item.get("title") or ""), created_at="", updated_at="", version=1)
                db.add(row); inserted += 1
            else: updated += 1
            apply_legacy(row, item, actor)
        stamp = now()
        for identifier, row in existing.items():
            if identifier not in identifiers and row.deleted_at is None:
                row.deleted_at, row.updated_at, row.version = stamp, stamp, row.version + 1; archived += 1
        db.commit()
    return {"found": len(items), "inserted": inserted, "updated": updated, "archived": archived, "skipped": skipped}


def synchronize_from_legacy_state(): return synchronize_from_entries(read_legacy_entries(), "migration")


def mirror_to_legacy(row, identifier, archived=False):
    with server.connect() as connection:
        found = connection.execute("SELECT version,entries FROM state WHERE id=1").fetchone()
        if not found: return
        version, raw = found; entries = json.loads(raw or "[]")
        index = next((i for i, x in enumerate(entries) if x.get("id") == identifier), None)
        if archived and index is not None: entries.pop(index)
        elif not archived and row is not None:
            item = to_legacy(row)
            if index is None: entries.append(item)
            else: entries[index] = item
        connection.execute("UPDATE state SET version=?,entries=? WHERE id=1", (version + 1, json.dumps(entries, ensure_ascii=False))); connection.commit()


def list_entries(page, page_size, search="", hook_id="", status="", include_archived=False):
    filters = []
    if not include_archived: filters.append(ProductEntry.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"; filters.append(or_(ProductEntry.title.ilike(pattern), ProductEntry.code.ilike(pattern), ProductEntry.transition_logic.ilike(pattern)))
    if hook_id: filters.append(ProductEntry.hook_id == hook_id)
    if status: filters.append(ProductEntry.status == status)
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(ProductEntry).where(*filters)) or 0
        rows = db.scalars(select(ProductEntry).where(*filters).order_by(ProductEntry.created_at.desc(), ProductEntry.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
        return {"page": page, "pageSize": page_size, "total": total, "items": [public(x) for x in rows]}


def get_entry(identifier, include_archived=False):
    with SessionLocal() as db:
        row = db.get(ProductEntry, identifier)
        if row is None or (row.deleted_at and not include_archived): raise ProductEntryError(404, "产品出场不存在")
        db.expunge(row); return row


def create_entry(actor, body):
    with SessionLocal() as db:
        if db.get(CreativeHook, body.hookId) is None: raise ProductEntryError(400, "关联创意钩子不存在")
    stamp = now(); identifier = "entry_" + secrets.token_hex(16)
    legacy = {"id": identifier, "kind": "产品出场", "parent": body.hookId, "code": body.code,
        "title": body.title.strip(), "transition": body.entryType, "entryTime": body.entryTime,
        "content": body.transitionLogic, "sellingPoints": body.sellingPoints, "visualDescription": body.visualDescription,
        "product": body.product, "notes": body.notes, "selectionStatus": body.status, "isExample": body.isExample,
        "createdBy": actor, "owner": actor}
    if body.createdAt: legacy["created"], _, legacy["createdTime"] = body.createdAt.partition("T")
    row = ProductEntry(id=identifier, hook_id=body.hookId, title=body.title.strip(), created_at=body.createdAt or stamp, updated_at=stamp, version=1)
    apply_legacy(row, legacy, actor)
    with SessionLocal() as db: db.add(row); db.commit(); db.refresh(row); db.expunge(row)
    mirror_to_legacy(row, row.id); return row


def update_entry(actor, can_update_any, identifier, body):
    with SessionLocal() as db:
        row = db.get(ProductEntry, identifier)
        if row is None or row.deleted_at: raise ProductEntryError(404, "产品出场不存在")
        if not can_update_any and row.created_by.casefold() != actor.casefold(): raise ProductEntryError(403, "不能修改其他成员的内容，可在内容下添加评价")
        if body.version is not None and body.version != row.version: raise ProductEntryError(409, "此内容已被其他成员修改，请刷新后重试")
        if db.get(CreativeHook, body.hookId) is None: raise ProductEntryError(400, "关联创意钩子不存在")
        legacy = to_legacy(row); legacy.update({"parent": body.hookId, "code": body.code, "title": body.title.strip(),
            "transition": body.entryType, "entryTime": body.entryTime, "content": body.transitionLogic,
            "sellingPoints": body.sellingPoints, "visualDescription": body.visualDescription, "product": body.product,
            "notes": body.notes, "selectionStatus": body.status, "isExample": body.isExample})
        apply_legacy(row, legacy, actor); row.version += 1; db.commit(); db.refresh(row); db.expunge(row)
    mirror_to_legacy(row, row.id); return row


def archive_entry(identifier):
    with SessionLocal() as db:
        row = db.get(ProductEntry, identifier)
        if row is None or row.deleted_at: raise ProductEntryError(404, "产品出场不存在")
        row.deleted_at = row.updated_at = now(); row.version += 1; db.commit(); db.refresh(row); db.expunge(row)
    mirror_to_legacy(None, identifier, True); return row


def restore_entry(identifier):
    with SessionLocal() as db:
        row = db.get(ProductEntry, identifier)
        if row is None or row.deleted_at is None: raise ProductEntryError(404, "归档记录不存在")
        row.deleted_at = None; row.updated_at = now(); row.version += 1; db.commit(); db.refresh(row); db.expunge(row)
    mirror_to_legacy(row, identifier); return row
