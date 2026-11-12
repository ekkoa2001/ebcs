import pytest

from app.sqlcompat import Result, translate


def test_insert_ignore_becomes_conflict_nothing():
    sql, params = translate("INSERT OR IGNORE INTO media VALUES(?,?,?)")
    assert "ON CONFLICT DO NOTHING" in sql
    assert "%s" in sql
    assert params is None


def test_pragma_table_info_uses_the_second_column_for_the_name():
    sql, params = translate("PRAGMA table_info(events)")
    assert "information_schema.columns" in sql
    assert params == ("events",)


def test_archive_replace_updates_the_same_entry():
    sql, _params = translate("INSERT OR REPLACE INTO archive(entry_id,content,actor,time) VALUES(?,?,?,?)")
    assert "ON CONFLICT (entry_id) DO UPDATE" in sql


def test_configured_redis_does_not_fall_back_when_down(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    import app.redis_sessions as sessions
    with pytest.raises(Exception):
        sessions.attach()


def test_result_is_sqlite_cursor_compatible():
    result = Result([(1, "first"), (2, "second")], rowcount=2)

    assert list(result) == [(1, "first"), (2, "second")]
    assert result.fetchone() is None
