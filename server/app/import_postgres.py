import os
import sqlite3
from pathlib import Path

from app.object_store import put_object
from app.sqlcompat import connect


def _postgres_url():
    return os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)


def copy_database(sqlite_path):
    source = sqlite3.connect(sqlite_path)
    source.row_factory = None
    names = [row[0] for row in source.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    target = connect(_postgres_url())
    raw = target.raw
    raw.execute("SET session_replication_role = replica")
    copied = {}
    for name in names:
        columns = [row[1] for row in source.execute(f"pragma table_info({name})")]
        rows = source.execute(f"select * from {name}").fetchall()
        quoted = ", ".join(columns)
        if rows:
            placeholders = ", ".join(["%s"] * len(columns))
            cursor = raw.cursor()
            cursor.executemany(
                f"INSERT INTO {name} ({quoted}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                rows,
            )
        copied[name] = len(rows)
        if "id" in columns:
            cursor = raw.cursor()
            cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", (name,))
            sequence = cursor.fetchone()[0]
            if sequence:
                cursor.execute(f"SELECT setval(%s, GREATEST((SELECT COALESCE(MAX(id), 1) FROM {name}), 1), true)", (sequence,))
    raw.execute("SET session_replication_role = origin")
    media = source.execute("select id, mime, data from media").fetchall()
    for key, mime, data in media:
        if data:
            put_object(key, mime, data)
    raw.commit()
    return copied


def reconcile(sqlite_path):
    source = sqlite3.connect(sqlite_path)
    target = connect(_postgres_url())
    checks = {}
    for name in ("users", "comments", "media", "state"):
        left = source.execute(f"select count(*) from {name}").fetchone()[0]
        right = target.execute(f"select count(*) from {name}").fetchone()[0]
        checks[name] = (left, right)
    target.raw.rollback()
    return checks


if __name__ == "__main__":
    path = os.environ.get("EKKO_IMPORT_SQLITE", str(Path(__file__).resolve().parents[2] / "data" / "sana_data.sqlite3"))
    print(copy_database(path))
    print(reconcile(path))
