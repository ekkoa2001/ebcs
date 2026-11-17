from datetime import datetime, timezone

from fastapi import Request

from app.database import SessionLocal
from app.models.foundation import ActivityLog


def record(
    actor: str,
    action: str,
    request: Request | None = None,
    *,
    module: str = "identity",
    object_type: str = "",
    object_id: str = "",
    result: str = "success",
) -> None:
    with SessionLocal() as db:
        db.add(
            ActivityLog(
                time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                actor=actor[:100],
                module=module[:40],
                action=action[:300],
                object_type=object_type[:40],
                object_id=object_id[:80],
                result=result[:20],
                ip=(request.client.host if request and request.client else "")[:64],
                user_agent=(request.headers.get("user-agent", "") if request else "")[:300],
                repeat_count=1,
            )
        )
        db.commit()
