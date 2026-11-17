import json
from datetime import datetime, timezone

from app.config import settings
from app.sqlcompat import connect


LABELS = {"开头创意": "创意钩子", "产品出场": "产品出场", "完整脚本": "完整脚本", "图片素材": "图片素材"}


def clock(value):
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if "T" in raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return raw[:19]


def _insert(connection, when, actor, action, object_type, object_id):
    action = action[:300]
    object_id = str(object_id or "")[:80]
    if connection.execute(
        "SELECT 1 FROM activity_logs WHERE module='creative' AND object_id=? AND action=? LIMIT 1",
        (object_id, action),
    ).fetchone():
        return
    connection.execute(
        "INSERT INTO activity_logs(time,actor,module,action,object_type,object_id,result,ip,user_agent,repeat_count) VALUES(?,?,?,?,?,?,?,?,?,1)",
        (when, str(actor or "")[:100], "creative", action, str(object_type or "")[:40], object_id, "success", "", ""),
    )


def backfill_creative_activity():
    """Copy older creative creates into the activity log once they are missing."""
    try:
        _backfill()
    except Exception:
        return


def _backfill():
    with connect(settings["database_url"]) as connection:
        events = connection.execute(
            "SELECT actor,time,kind,entry_id,title FROM events WHERE kind IN ('开头创意','产品出场','完整脚本','图片素材')"
        ).fetchall()
        for actor, when, kind, entry_id, title in events:
            label = LABELS.get(kind, "内容")
            _insert(connection, clock(when), actor, f"新增{label} {title}", kind, entry_id)
        state = connection.execute("SELECT entries FROM state WHERE id=1").fetchone()
        entries = json.loads(state[0] or "[]") if state and state[0] else []
        created = {(str(entry_id), kind): clock(when) for _actor, when, kind, entry_id, _title in events}
        for item in entries:
            if not isinstance(item, dict) or item.get("kind") != "完整脚本":
                continue
            shots = item.get("shots") if isinstance(item.get("shots"), list) else []
            if not shots:
                continue
            when = created.get((str(item.get("id")), "完整脚本")) or clock(item.get("created") or item.get("createdAt"))
            _insert(connection, when, item.get("createdBy") or "", f"新增分镜 {item.get('title') or ''}（{len(shots)} 个镜头）", "分镜", item.get("id"))
