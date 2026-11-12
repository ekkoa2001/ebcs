import sqlite3
from pathlib import Path

database = Path(__file__).resolve().parents[2] / "data" / "sana_data.sqlite3"
connection = sqlite3.connect(database)
names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1")]
print(", ".join(names))
print(connection.execute("SELECT COUNT(*) FROM role_permissions").fetchone()[0])
