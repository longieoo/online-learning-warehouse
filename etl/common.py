import io
import json
import os
import tempfile
from contextlib import closing
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from etl.config import (
    ch_connect as ch_connect,
    pg_connect as pg_connect,
    source_connect as source_connect,
    staging_connect,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.getenv("DW_ARTIFACTS_DIR", str(ROOT / "artifacts")))


def save_json(name, data):
    path = ARTIFACTS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    # Mỗi writer có file tạm riêng để không ghi đè lẫn nhau.
    fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, indent=2, ensure_ascii=False, default=str)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def copy_frame(conn, table, frame):
    buf = io.StringIO()
    frame.to_csv(buf, index=False, header=False, na_rep="\\N", date_format="%Y-%m-%d %H:%M:%S.%f")
    buf.seek(0)
    with conn.cursor() as cur:
        cols = ",".join('"' + c + '"' for c in frame.columns)
        cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')", buf)


@contextmanager
def project_lock(shared=False):
    conn = staging_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        function = "pg_try_advisory_lock_shared" if shared else "pg_try_advisory_lock"
        cur.execute(f"SELECT {function}(202210132024)")
        if not cur.fetchone()[0]:
            conn.close()
            raise RuntimeError("Another project command is running; retry after it finishes")
    try:
        yield
    finally:
        conn.close()


def require_success():
    # PostgreSQL là nguồn trạng thái bền vững. File JSON hỗ trợ đọc log và export.
    with closing(staging_connect()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT manifest FROM staging.published_state WHERE singleton=true")
        row = cursor.fetchone()
        cursor.execute("SELECT 1 FROM staging.pipeline_runs WHERE phase='publishing' LIMIT 1")
        if cursor.fetchone():
            raise RuntimeError("Kho dữ liệu đang phục hồi công bố. Hãy chạy pipeline rồi thử lại.")
        if row:
            return row[0]
    path = ARTIFACTS / "pipeline.json"
    if not path.exists():
        raise RuntimeError("Run pipeline first")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "success":
        raise RuntimeError("Gold is unavailable: last pipeline did not succeed. Rerun pipeline.")
    return manifest
