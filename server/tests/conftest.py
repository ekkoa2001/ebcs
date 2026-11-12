import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "data" / "sana_data.sqlite3"
temporary = Path(tempfile.mkdtemp(prefix="ekko-phase2-"))
database = temporary / "test.sqlite3"
shutil.copy(source, database)
os.environ["EKKO_DB"] = str(database)
os.environ["EKKO_AUTO_BACKUP"] = "0"
os.environ["EKKO_ENV"] = "test"
