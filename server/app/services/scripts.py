import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

import server
from app.database import SessionLocal


def now():
    return datetime.now(timezone.utc).isoformat()


def read_legacy_entries():
    with server.connect() as connection:
        row = connection.execute("SELECT entries FROM state WHERE id=1").fetchone()
    if not row or not row[0]:
        return []
    value = json.loads(row[0])
    return value if isinstance(value, list) else []


def media_id(value):
    if not isinstance(value, str) or not value:
        return None
    # Current browser URLs are /api/v1/media/<id>/<variant>.  Keeping the
    # trailing variant as the database id turned a valid cover into the
    # literal id "preview", which then violated the media foreign key on
    # application startup or any legacy-state save.
    matched = re.search(r"/media/([^/]+)/(?:original|preview|thumbnail)(?:\?.*)?$", value)
    if matched:
        return matched.group(1)
    return value.rsplit("/", 1)[-1].split("?", 1)[0] or None


def created_at(item):
    date = str(item.get("created") or "")
    clock = str(item.get("createdTime") or "")
    return (date + ("T" + clock if clock else "")).strip("T") or now()


def script_status(item):
    if item.get("usedDate"):
        return "已投放"
    if item.get("producedDate") or item.get("videoCount"):
        return "已产出"
    return str(item.get("productionStatus") or "草稿")


def upsert(db, table, identifier, values):
    exists = db.execute(text(f"SELECT 1 FROM {table} WHERE id=:id"), {"id": identifier}).first()
    payload = {"id": identifier, **values}
    if exists:
        db.execute(
            text(f"UPDATE {table} SET " + ",".join(f"{key}=:{key}" for key in values) + " WHERE id=:id"),
            payload,
        )
    else:
        names = list(payload)
        db.execute(
            text(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(':'+key for key in names)})"),
            payload,
        )


def synchronize_from_entries(entries, actor=""):
    scripts = [item for item in entries if item.get("kind") == "完整脚本" and isinstance(item.get("id"), str)]
    identifiers = {item["id"] for item in scripts}
    stamp = now()
    counts = {"scripts": 0, "shots": 0, "videos": 0, "periods": 0, "archived": 0}
    with SessionLocal() as db:
        for item in scripts:
            identifier = item["id"]
            previous = db.execute(text("SELECT version,created_at FROM scripts WHERE id=:id"), {"id": identifier}).first()
            raw = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            upsert(db, "scripts", identifier, {
                "hook_id": str(item.get("parent") or ""),
                "product_entry_id": str(item.get("transitionId") or ""),
                "code": str(item.get("code") or "")[:80],
                "title": str(item.get("title") or "")[:300],
                "body": str(item.get("content") or ""),
                "cover_media_id": media_id(item.get("coverImage")),
                "product": str(item.get("product") or "")[:200],
                "audience": str(item.get("audience") or "")[:200],
                "scene": str(item.get("scene") or "")[:200],
                "notes": str(item.get("notes") or ""),
                "production_status": script_status(item),
                "source_hook_content": str(item.get("sourceHookContent") or ""),
                "source_entry_content": str(item.get("sourceTransitionContent") or item.get("transition") or ""),
                "produced_date": str(item.get("producedDate") or "")[:20],
                "used_date": str(item.get("usedDate") or "")[:20],
                "video_count": int(item.get("videoCount") or 0),
                "owner": str(item.get("owner") or item.get("createdBy") or actor)[:64],
                "due_date": str(item.get("dueDate") or "")[:20],
                "review_notes": str(item.get("reviewNotes") or ""),
                "is_example": int(bool(item.get("isExample"))),
                "created_by": str(item.get("createdBy") or actor)[:64],
                "created_at": previous[1] if previous else created_at(item),
                "updated_at": stamp,
                "version": (int(previous[0]) + 1) if previous else 1,
                "deleted_at": None,
                "legacy_json": raw,
            })
            counts["scripts"] += 1

            # Only deterministic legacy children are replaced. API-created children remain intact.
            db.execute(text("DELETE FROM storyboard_shots WHERE script_id=:id AND id LIKE :prefix"), {"id": identifier, "prefix": identifier + ":%"})
            for order, shot in enumerate(item.get("shots") or []):
                shot_id = f"{identifier}:{order}"
                upsert(db, "storyboard_shots", shot_id, {
                    "script_id": identifier, "sort_order": order,
                    "name": str(shot.get("name") or shot.get("title") or f"镜头 {order + 1}")[:200],
                    "description": str(shot.get("description") or shot.get("content") or shot.get("visual") or ""),
                    "scale": str(shot.get("scale") or shot.get("shotSize") or "")[:80],
                    "duration": str(shot.get("duration") or shot.get("seconds") or "")[:40],
                    "media_id": media_id(shot.get("image") or shot.get("mediaUrl")),
                    "action": str(shot.get("action") or ""), "dialogue": str(shot.get("dialogue") or shot.get("line") or ""),
                    "product_info": str(shot.get("productInfo") or ""), "notes": str(shot.get("notes") or ""),
                    "created_at": stamp, "updated_at": stamp,
                })
                counts["shots"] += 1

            db.execute(text("DELETE FROM produced_videos WHERE script_id=:id AND is_placeholder=1"), {"id": identifier})
            for index in range(int(item.get("videoCount") or 0)):
                video_id = f"{identifier}:legacy-video:{index}"
                upsert(db, "produced_videos", video_id, {
                    "script_id": identifier, "name": f"成品 {index + 1}", "material_code": str(item.get("code") or "")[:80],
                    "produced_on": str(item.get("producedDate") or "")[:20], "producer": str(item.get("createdBy") or actor)[:80],
                    "source_path": "", "preview_url": "", "version_label": "", "notes": "", "is_placeholder": 1,
                    "created_at": stamp, "updated_at": stamp,
                })
                counts["videos"] += 1

            ad = item.get("ad") if isinstance(item.get("ad"), dict) else {}
            campaign_id = f"{identifier}:legacy"
            rows = ad.get("rows") if isinstance(ad.get("rows"), list) else []
            start = str(ad.get("launchDate") or (rows[0].get("periodStart") if rows else "") or "")[:20]
            end = str(ad.get("endDate") or (rows[-1].get("periodEnd") if rows else "") or "")[:20]
            duration = None
            try:
                if start and end: duration = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days + 1
            except ValueError:
                pass
            today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
            if not start: status = "准备投放"
            elif start > today: status = "准备投放"
            elif end and end < today: status = "投放结束"
            else: status = "正在投放"
            upsert(db, "ad_campaigns", campaign_id, {
                "object_type": "script", "object_id": identifier, "legacy_key": "legacy",
                "material_code": str(ad.get("materialCode") or item.get("code") or "")[:80], "batch": str(ad.get("batch") or "")[:80],
                "platform": str(ad.get("platform") or "")[:80], "currency": str(ad.get("currency") or "")[:16],
                "start_date": start, "end_date": end, "duration_days": duration, "status": status,
                "review_notes": str(ad.get("notes") or ""), "created_at": stamp, "updated_at": stamp,
            })
            db.execute(text("DELETE FROM ad_period_records WHERE campaign_id=:id"), {"id": campaign_id})
            for index, row in enumerate(rows):
                row_id = str(row.get("id") or index)
                period_id = f"{identifier}:{row_id}"[:140]
                start_date = str(row.get("periodStart") or row.get("date") or "")[:20]
                end_date = str(row.get("periodEnd") or row.get("date") or "")[:20]
                upsert(db, "ad_period_records", period_id, {
                    "campaign_id": campaign_id, "period_start": start_date, "period_end": end_date,
                    "platform": str(row.get("platform") or ad.get("platform") or "")[:80], "currency": str(row.get("currency") or ad.get("currency") or "")[:16],
                    "batch": str(row.get("batch") or ad.get("batch") or "")[:80], "material_code": str(row.get("materialCode") or ad.get("materialCode") or item.get("code") or "")[:80],
                    "spend": row.get("spend"), "impressions": row.get("impressions"), "link_clicks": row.get("clicks"), "lpv": row.get("lpv"),
                    "add_to_cart": row.get("addToCart"), "initiate_checkout": row.get("initiateCheckout"), "purchases": row.get("purchases"),
                    "revenue": row.get("revenue"), "frequency": row.get("frequency"), "video_plays": row.get("videoPlays"),
                    "view3": row.get("view3"), "view50": row.get("view50"), "created_at": stamp, "updated_at": stamp,
                })
                counts["periods"] += 1

        # Archive only records that originated from the legacy state.
        legacy_rows = db.execute(text("SELECT id FROM scripts WHERE legacy_json IS NOT NULL AND legacy_json <> '' AND deleted_at IS NULL")).all()
        for (identifier,) in legacy_rows:
            if identifier not in identifiers:
                db.execute(text("UPDATE scripts SET deleted_at=:now,updated_at=:now,version=version+1 WHERE id=:id"), {"now": stamp, "id": identifier})
                counts["archived"] += 1
        db.commit()
    return counts


def synchronize_from_legacy_state():
    return synchronize_from_entries(read_legacy_entries(), "migration")


def mirror_to_legacy(identifier, archived=False):
    """Expose normalized script edits to the frozen V1 pages during migration."""
    with SessionLocal() as db:
        script = db.execute(text("SELECT * FROM scripts WHERE id=:id"), {"id": identifier}).first()
        if script:
            script = dict(script._mapping)
            shots = [dict(row._mapping) for row in db.execute(text("SELECT * FROM storyboard_shots WHERE script_id=:id ORDER BY sort_order,id"), {"id": identifier}).all()]
            videos = [dict(row._mapping) for row in db.execute(text("SELECT * FROM produced_videos WHERE script_id=:id ORDER BY created_at,id"), {"id": identifier}).all()]
            campaign = db.execute(text("SELECT * FROM ad_campaigns WHERE object_type='script' AND object_id=:id ORDER BY updated_at DESC LIMIT 1"), {"id": identifier}).first()
            periods = [dict(row._mapping) for row in db.execute(text("SELECT * FROM ad_period_records WHERE campaign_id=:id ORDER BY period_start,id"), {"id": campaign.id}).all()] if campaign else []
    with server.connect() as connection:
        state = connection.execute("SELECT version,entries FROM state WHERE id=1").fetchone()
        if not state:
            return
        version, raw = state
        entries = json.loads(raw or "[]")
        index = next((i for i, item in enumerate(entries) if item.get("id") == identifier), None)
        if archived or not script:
            if index is not None:
                entries.pop(index)
        else:
            try:
                item = json.loads(script.get("legacy_json") or "{}")
            except json.JSONDecodeError:
                item = {}
            date, _, clock = str(script.get("created_at") or "").partition("T")
            item.update({
                "id": identifier, "kind": "完整脚本", "parent": script["hook_id"], "transitionId": script["product_entry_id"],
                "code": script["code"], "title": script["title"], "content": script["body"], "notes": script["notes"],
                "product": script["product"], "audience": script["audience"], "scene": script["scene"],
                "sourceHookContent": script["source_hook_content"], "sourceTransitionContent": script["source_entry_content"],
                "producedDate": script["produced_date"], "usedDate": script["used_date"], "videoCount": len(videos),
                "createdBy": script["created_by"], "owner": script["owner"], "created": date, "createdTime": clock,
                "isExample": bool(script["is_example"]), "productionStatus": script["production_status"],
                "coverImage": f"/api/v1/media/{script['cover_media_id']}/thumbnail" if script.get("cover_media_id") else "",
                "shots": [{"id": row["id"], "name": row["name"], "description": row["description"], "scale": row["scale"],
                    "duration": row["duration"], "image": f"/api/v1/media/{row['media_id']}/preview" if row.get("media_id") else "",
                    "action": row["action"], "dialogue": row["dialogue"], "productInfo": row["product_info"], "notes": row["notes"]} for row in shots],
            })
            if campaign:
                campaign = dict(campaign._mapping)
                item["ad"] = {"materialCode": campaign["material_code"], "batch": campaign["batch"], "platform": campaign["platform"],
                    "currency": campaign["currency"], "launchDate": campaign["start_date"], "endDate": campaign["end_date"],
                    "durationDays": campaign["duration_days"], "status": campaign["status"], "notes": campaign["review_notes"],
                    "rows": [{"id": row["id"], "periodStart": row["period_start"], "periodEnd": row["period_end"], "platform": row["platform"],
                        "currency": row["currency"], "batch": row["batch"], "materialCode": row["material_code"], "spend": row["spend"],
                        "impressions": row["impressions"], "clicks": row["link_clicks"], "lpv": row["lpv"], "addToCart": row["add_to_cart"],
                        "initiateCheckout": row["initiate_checkout"], "purchases": row["purchases"], "revenue": row["revenue"],
                        "frequency": row["frequency"], "videoPlays": row["video_plays"], "view3": row["view3"], "view50": row["view50"]} for row in periods]}
            if index is None:
                entries.append(item)
            else:
                entries[index] = item
        connection.execute("UPDATE state SET version=?,entries=? WHERE id=1", (version + 1, json.dumps(entries, ensure_ascii=False)))
        connection.commit()


def script_id_for(table, identifier):
    if table == "scripts":
        return identifier
    with SessionLocal() as db:
        if table in {"storyboard_shots", "produced_videos"}:
            return db.execute(text(f"SELECT script_id FROM {table} WHERE id=:id"), {"id": identifier}).scalar()
        if table == "ad_campaigns":
            row = db.execute(text("SELECT object_type,object_id FROM ad_campaigns WHERE id=:id"), {"id": identifier}).first()
            return row.object_id if row and row.object_type == "script" else None
        if table == "ad_period_records":
            row = db.execute(text("SELECT c.object_type,c.object_id FROM ad_period_records r JOIN ad_campaigns c ON c.id=r.campaign_id WHERE r.id=:id"), {"id": identifier}).first()
            return row.object_id if row and row.object_type == "script" else None
