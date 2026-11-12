import json
import sqlite3

import server


class SessionData(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.get("token"):
            save_session(self["token"], self)


class SessionStore(dict):
    def __setitem__(self, key, value):
        record = value if isinstance(value, SessionData) else SessionData(value)
        record["token"] = key
        super().__setitem__(key, record)
        save_session(key, record)

    def pop(self, key, *args):
        existed = key in self
        result = super().pop(key, *args)
        if existed:
            delete_session(key)
        return result


def save_session(token, data):
    with sqlite3.connect(server.database_file(), timeout=20) as connection:
        connection.execute(
            "INSERT INTO sessions(token,username,csrf,created_at,active_at,payload) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(token) DO UPDATE SET username=excluded.username,csrf=excluded.csrf,created_at=excluded.created_at,active_at=excluded.active_at,payload=excluded.payload",
            (token, data.get("username", ""), data.get("csrf", ""), float(data.get("created", 0)), float(data.get("activeAt", 0)), json.dumps(data, ensure_ascii=False)),
        )


def delete_session(token):
    with sqlite3.connect(server.database_file(), timeout=20) as connection:
        connection.execute("DELETE FROM sessions WHERE token=?", (token,))


def load_sessions():
    records = {}
    try:
        with sqlite3.connect(server.database_file(), timeout=20) as connection:
            rows = connection.execute("SELECT token,payload,created_at FROM sessions").fetchall()
    except sqlite3.OperationalError:
        return records
    now = __import__("time").time()
    for token, payload, created_at in rows:
        if now - float(created_at or 0) > server.MAX_SESSION:
            delete_session(token)
            continue
        data = json.loads(payload)
        data["token"] = token
        records[token] = SessionData(data)
    return records


def install_sessions():
    server.SESSIONS = SessionStore(load_sessions())
