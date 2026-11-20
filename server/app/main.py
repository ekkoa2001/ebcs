import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.legacy import dispatch
from app.routers import admin, analytics, auth, brand, comments, competitors, content, creative, dashboard, marketing, media, notifications, users


def upgrade_database():
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(config, "head")


def backup_database():
    if os.environ.get("EKKO_AUTO_BACKUP", "1") != "1" or os.environ.get("EKKO_DB"):
        return
    source = settings["database_path"]
    if not source.exists():
        return
    folder = source.parent / "backups"
    folder.mkdir(exist_ok=True)
    target = folder / ("Ekko-Script-Web-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".sqlite3")
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings["database_url"].startswith("postgres"):
        import time
        from app.sqlcompat import connect as postgres
        last_error = None
        for _ in range(30):
            try:
                with postgres(settings["database_url"]) as connection:
                    connection.execute("SELECT 1")
                last_error = None
                break
            except Exception as error:
                last_error = error
                time.sleep(1)
        if last_error:
            raise last_error
    upgrade_database()
    from app.rbac import seed
    from app.sessions import install_sessions

    seed()
    install_sessions()
    from app.redis_sessions import attach
    from app.object_store import ensure_bucket, repair_legacy_media_paths
    attach()
    run_startup_sync = os.environ.get("EKKO_RUN_STARTUP_SYNC", "0") == "1"
    try:
        ensure_bucket()
        if run_startup_sync:
            repair_legacy_media_paths()
    except Exception:
        pass
    if settings["database_url"].startswith("postgres"):
        from app.sqlcompat import connect as postgres
        with postgres(settings["database_url"]) as connection:
            count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        # The cloud image deliberately excludes data/ so an empty Supabase
        # database must not attempt to import a non-existent local SQLite
        # backup.  Local Docker still mounts that file and retains the
        # one-time import path for an explicit migration.
        if count == 0 and settings["database_path"].exists():
            from app.import_postgres import copy_database
            copy_database(settings["database_path"])
            repair_legacy_media_paths()
            run_startup_sync = True
    if run_startup_sync:
        from app.services.creative_hooks import synchronize_from_legacy_state
        synchronize_from_legacy_state()
        from app.services.product_entries import synchronize_from_legacy_state as synchronize_product_entries
        synchronize_product_entries()
        from app.services.scripts import synchronize_from_legacy_state as synchronize_scripts
        synchronize_scripts()
        from app.services.activity_backfill import backfill_creative_activity
        backfill_creative_activity()
    try:
        backup_database()
    except Exception:
        pass
    yield


app = FastAPI(title="Ekko Brand Content Strategy", version="2.0", docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json", lifespan=lifespan)
for item in (auth.router, auth.compat_router, users.router, users.compat_router, admin.router, admin.compat_router, creative.router, content.router, marketing.router, analytics.router, competitors.router, brand.router, comments.router, notifications.router, media.router, dashboard.router):
    app.include_router(item)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse({"error": detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def hidden_error(_request: Request, _exc: Exception):
    return JSONResponse({"error": "服务暂时不可用"}, status_code=500)


@app.api_route("/", methods=["GET"])
@app.api_route("/{full_path:path}", methods=["GET", "POST"])
async def legacy(request: Request, full_path: str = ""):
    return await dispatch(request)
