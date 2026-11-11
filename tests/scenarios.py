"""Destructive regression scenarios for an isolated synthetic verification database."""

import os
import subprocess
import sys
from contextlib import closing
from etl.common import pg_connect, staging_connect, ch_connect, project_lock, save_json, utc_now
from etl.pipeline import pipeline
from etl.watermark import published


def sql(text, parameters=None):
    with closing(pg_connect()) as connection, connection, connection.cursor() as cursor:
        cursor.execute(text, parameters)


def scalar(text):
    with closing(ch_connect()) as client:
        return client.query(text).first_row[0]


def run(mode="incremental"):
    with project_lock():
        return pipeline(mode)


def scenarios():
    if os.environ.get("DW_ALLOW_SCENARIOS") != "1":
        raise RuntimeError("Use only with an isolated database and DW_ALLOW_SCENARIOS=1")
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print("PASS " + name, flush=True)

    before = published()["fingerprints"]
    empty = run()
    check(
        "empty run preserves every Gold fingerprint",
        empty["gold_reused"] and empty["fingerprints"] == before,
    )
    with project_lock(shared=True):
        try:
            with project_lock():
                raise AssertionError("writer acquired lock with reader active")
        except RuntimeError:
            check("reader lock blocks publication writer", True)
    first_value = scalar(
        "SELECT time_spent_seconds FROM gold.fact_quiz_attempts WHERE attempt_id=1"
    )
    second_value = scalar(
        "SELECT time_spent_seconds FROM gold.fact_quiz_attempts WHERE attempt_id=2"
    )
    with closing(pg_connect()) as late:
        with late.cursor() as cursor:
            cursor.execute(
                "UPDATE oltp.quiz_attempts SET time_spent_seconds=time_spent_seconds+1 WHERE attempt_id=1"
            )
        sql(
            "UPDATE oltp.quiz_attempts SET time_spent_seconds=time_spent_seconds+1 WHERE attempt_id=2"
        )
        run()
        check(
            "open earlier transaction defers a later committed transaction",
            scalar("SELECT time_spent_seconds FROM gold.fact_quiz_attempts WHERE attempt_id=2")
            == second_value,
        )
        late.commit()
    run()
    check(
        "late commit and later commit both arrive exactly once",
        scalar("SELECT time_spent_seconds FROM gold.fact_quiz_attempts WHERE attempt_id=1")
        == first_value + 1
        and scalar("SELECT time_spent_seconds FROM gold.fact_quiz_attempts WHERE attempt_id=2")
        == second_value + 1,
    )
    sql("UPDATE oltp.users SET email='broken-email' WHERE user_id=1")
    run()
    with closing(staging_connect()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT email FROM silver.users WHERE user_id=1")
        check(
            "invalid update preserves last known clean row",
            cursor.fetchone()[0] == "student1@example.invalid",
        )
        cursor.execute(
            "SELECT count(*) FROM quarantine.quarantine_records WHERE table_name='users' AND source_id=1 AND resolved_at IS NULL"
        )
        check("invalid update is quarantined", cursor.fetchone()[0] == 1)
    sql("UPDATE oltp.users SET email='student1@example.invalid' WHERE user_id=1")
    run()
    with closing(staging_connect()) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM quarantine.quarantine_records WHERE table_name='users' AND source_id=1 AND resolved_at IS NULL"
        )
        check("corrected source resolves quarantine", cursor.fetchone()[0] == 0)
    count = scalar("SELECT count() FROM gold.fact_quiz_attempts")
    sql(
        "DELETE FROM oltp.quiz_attempts WHERE attempt_id=(SELECT min(attempt_id) FROM oltp.quiz_attempts WHERE attempt_id>2)"
    )
    removed = run()
    check(
        "physical delete reaches Silver and Gold",
        scalar("SELECT count() FROM gold.fact_quiz_attempts") == count - 1
        and removed["fact_actions"]["fact_quiz_attempts"] == "rebuilt",
    )
    sql("UPDATE oltp.payments SET refunded=1-refunded WHERE payment_id=1")
    from unittest.mock import patch

    try:
        with patch(
            "etl.validate.validate", side_effect=RuntimeError("intentional validation failure")
        ):
            run()
    except RuntimeError as error:
        check(
            "failed quality gate leaves published Gold unchanged",
            str(error) == "intentional validation failure",
        )
    retried = run()
    check(
        "committed staging delta survives failure before publication",
        retried["fact_actions"]["fact_payments"] == "rebuilt",
    )
    sql("UPDATE oltp.payments SET refunded=1-refunded WHERE payment_id=2")
    code = """import os
from etl.common import project_lock
import etl.load_clickhouse as loader
def interrupted(ch,plan):
    loader.drop_feeds(ch)
    name=plan[0]['table']
    ch.command(f'EXCHANGE TABLES gold.{name} AND gold_build.{name}')
    os._exit(86)
loader.publish=interrupted
from etl.pipeline import pipeline
with project_lock(): pipeline('incremental')
"""
    process = subprocess.run([sys.executable, "-c", code], check=False)
    check("process stops after an actual table exchange", process.returncode == 86)
    restored = run()
    check(
        "restart recovers partial publication and completes retry",
        len(restored["recovered_runs"]) == 1,
    )
    check(
        "retry consumes pending changes without duplicate facts",
        run()["fingerprints"] == restored["fingerprints"],
    )
    sql("UPDATE oltp.payments SET refunded=1-refunded WHERE payment_id=3")
    try:
        with patch("etl.validate.validate", side_effect=RuntimeError("intentional full failure")):
            run("full")
    except RuntimeError:
        pass
    resumed = run()
    check(
        "failed full snapshot forces complete rebuild on incremental retry",
        all(action == "rebuilt" for action in resumed["fact_actions"].values())
        and len(resumed["fact_actions"]) == 4,
    )
    # Full sees the delete, but a subsequent conservative checkpoint sees only
    # an older UPDATE while another transaction remains open.
    with closing(pg_connect()) as first, closing(pg_connect()) as middle:
        with first.cursor() as cursor:
            cursor.execute("SELECT pg_current_xact_id()")
        with closing(pg_connect()) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT min(attempt_id) FROM oltp.quiz_attempts WHERE attempt_id>2")
            deleted_id = cursor.fetchone()[0]
        sql(
            "UPDATE oltp.quiz_attempts SET time_spent_seconds=time_spent_seconds+1 WHERE attempt_id=%s",
            (deleted_id,),
        )
        with middle.cursor() as cursor:
            cursor.execute("SELECT pg_current_xact_id()")
        sql("DELETE FROM oltp.quiz_attempts WHERE attempt_id=%s", (deleted_id,))
        run("full")
        first.commit()
        run()
        check(
            "full snapshot tombstone prevents resurrection by older journal update",
            scalar(f"SELECT count() FROM gold.fact_quiz_attempts WHERE attempt_id={deleted_id}")
            == 0,
        )
        middle.commit()
    run()
    result = dict(
        status="success",
        checked_at=utc_now(),
        checks=checks,
        count=len(checks),
        scope="isolated synthetic smoke database",
    )
    save_json("regression.json", result)
    return result


if __name__ == "__main__":
    print(scenarios())
