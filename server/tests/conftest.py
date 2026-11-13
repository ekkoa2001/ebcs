import os
import shutil
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
source = ROOT / "data" / "sana_data.sqlite3"
temporary = Path(tempfile.mkdtemp(prefix="ekko-phase2-"))
database = temporary / "test.sqlite3"
shutil.copy(source, database)
for variable in ("DATABASE_URL", "REDIS_URL", "S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
    os.environ.pop(variable, None)
os.environ["EKKO_DB"] = str(database)
os.environ["EKKO_AUTO_BACKUP"] = "0"
os.environ["EKKO_ENV"] = "test"
