from pathlib import Path
import sqlite3
from datetime import datetime

root = Path(__file__).resolve().parent.parent
source = root / 'data' / 'sana_data.sqlite3'
if not source.exists():
    raise SystemExit('数据库不存在，请先启动网站。')
folder = root / 'data' / 'backups'
folder.mkdir(exist_ok=True)
target = folder / ('Ekko-Script-Web-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
print('完整备份已保存：' + str(target))
