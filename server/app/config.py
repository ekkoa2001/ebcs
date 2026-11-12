import json
import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
ROOT = SERVER_DIR.parent
DATA = ROOT / "data"
CONFIG_FILE = SERVER_DIR / "server_config.json"


def sqlite_url(path: Path) -> str:
    return "sqlite:///" + path.resolve().as_posix()


def load_settings():
    file_config = {"host": "127.0.0.1", "port": 8875, "allowed_hosts": ["127.0.0.1", "localhost"], "cert": "", "key": ""}
    if CONFIG_FILE.exists():
        supplied = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(supplied, dict):
            file_config.update(supplied)
    database_path = Path(os.environ["EKKO_DB"]) if os.environ.get("EKKO_DB") else DATA / "sana_data.sqlite3"
    database_url = os.environ.get("DATABASE_URL") or sqlite_url(database_path)
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    elif database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    return {
        "host": file_config["host"],
        "port": int(file_config["port"]),
        "allowed_hosts": {str(item).lower() for item in file_config["allowed_hosts"]} | {item.strip().lower() for item in os.environ.get("EKKO_ALLOWED_HOSTS", "").split(",") if item.strip()},
        "cert": file_config.get("cert") or "",
        "key": file_config.get("key") or "",
        "secure": bool(file_config.get("cert") and file_config.get("key")) or os.environ.get("EKKO_SECURE") == "1",
        "database_path": database_path,
        "database_url": database_url,
        "environment": os.environ.get("EKKO_ENV", "development"),
    }


settings = load_settings()
