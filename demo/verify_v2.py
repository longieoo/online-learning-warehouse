"""Kịch bản nghiệm thu trên OLTP giả lập đang chạy."""

import json
from argparse import ArgumentParser
import subprocess
import sys
from contextlib import closing

from etl.common import ARTIFACTS, pg_connect, source_connect, staging_connect, save_json


def pipeline():
    subprocess.run([sys.executable, "cli.py", "pipeline", "--mode", "incremental"], check=True)
    return json.loads((ARTIFACTS / "pipeline.json").read_text(encoding="utf-8"))


with closing(source_connect()) as src, src.cursor() as cur:
    cur.execute("""SELECT current_setting('transaction_read_only'),
        has_table_privilege(current_user,'oltp.users','UPDATE')""")
    readonly, writable = cur.fetchone()
    assert readonly == "on" and not writable

parser = ArgumentParser()
parser.add_argument("--attempt-number", type=int, default=99)
args = parser.parse_args()
baseline = json.loads((ARTIFACTS / "pipeline.json").read_text(encoding="utf-8"))
assert baseline["status"] == "success"
subprocess.run(
    [sys.executable, "-m", "demo.seed_incremental", "--attempt-number", str(args.attempt_number)],
    check=True,
)
with closing(pg_connect()) as pg, pg, pg.cursor() as cur:
    cur.execute("SELECT email FROM oltp.users WHERE user_id=1 FOR UPDATE")
    previous_email = cur.fetchone()[0]
    cur.execute(
        "UPDATE oltp.users SET email='invalid-v2-fixture' WHERE user_id=1 RETURNING updated_at"
    )
    invalid_stamp = cur.fetchone()[0]
    cur.execute("UPDATE oltp.enrollments SET completed_at=completed_at WHERE enrollment_id=1")
try:
    changed = pipeline()
    assert changed["fact_actions"]["fact_quiz_attempts"] == "appended", changed["fact_actions"]
    assert changed["fact_actions"]["fact_enrollments"] == "versioned", changed["fact_actions"]
    delta = changed["tables"]["quiz_attempts"] - baseline["tables"]["quiz_attempts"]
    assert delta == 10000, delta
    with closing(staging_connect()) as pg, pg.cursor() as cur:
        cur.execute(
            """SELECT error_code,raw_payload->>'email'
            FROM quarantine.quarantine_records
            WHERE table_name='users' AND source_id=1 AND source_updated_at=%s""",
            (invalid_stamp,),
        )
        assert cur.fetchone() == ("ERR_INVALID_EMAIL", "invalid-v2-fixture")
finally:
    with closing(pg_connect()) as pg, pg, pg.cursor() as cur:
        cur.execute(
            "UPDATE oltp.users SET email=%s WHERE user_id=1 AND email='invalid-v2-fixture'",
            (previous_email,),
        )
restored = pipeline()
repeated = pipeline()
assert restored["fingerprints"] == repeated["fingerprints"] == changed["fingerprints"]
assert not any(repeated["extracted"].values()) and repeated["gold_reused"]
save_json(
    "verification_v2.json",
    dict(
        source_readonly=True,
        inserted_attempts=delta,
        quarantine_error="ERR_INVALID_EMAIL",
        baseline_run=baseline["run_id"],
        changed_run=changed["run_id"],
        repeated_run=repeated["run_id"],
        extracted=changed["extracted"],
        fact_actions=changed["fact_actions"],
        changed_seconds=changed["seconds"],
        repeated_seconds=repeated["seconds"],
        identical_gold=True,
    ),
)
print("Refactor integration verification passed", flush=True)
