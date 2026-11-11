import csv
import hashlib
import json
import platform
import statistics
import time
from datetime import date, datetime
from decimal import Decimal
import pandas as pd
from benchmark.queries import QUERIES
from etl.common import (
    ROOT,
    ARTIFACTS,
    ch_connect,
    staging_connect,
    copy_frame,
    require_success,
    save_json,
    utc_now,
)


def canonical(rows):
    def norm(v):
        if isinstance(v, Decimal):
            return int(v) if v == v.to_integral_value() else str(v.normalize())
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    # Compare multisets: include duplicates; ignore only DB-specific NULL ordering.
    return sorted(
        json.dumps([norm(v) for v in row], ensure_ascii=False, separators=(",", ":"))
        for row in rows
    )


def digest(rows):
    return hashlib.sha256("\n".join(canonical(rows)).encode()).hexdigest()


def row_bytes(row):
    # The source convention is UTC; PG stores UTC-naive and CH returns UTC-aware.
    normalized = [
        v.replace(tzinfo=None).isoformat()
        if isinstance(v, datetime)
        else v.isoformat()
        if isinstance(v, date)
        else v
        for v in row
    ]
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"


def mirror(ch, pg, tables):
    with pg.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS benchmark")
    counts = {}
    ddl = []
    for table in tables:
        columns = ch.query(f"DESCRIBE TABLE gold.{table}").result_rows
        definitions = []
        for c, t, *_ in columns:
            sql_type = (
                "TIMESTAMP"
                if "DateTime" in t
                else "DATE"
                if t == "Date"
                else "TEXT"
                if "String" in t
                else "BIGINT"
            )
            definitions.append(
                f'"{c}" {sql_type}' + ("" if t.startswith("Nullable") else " NOT NULL")
            )
        key = columns[0][0]
        create = f"CREATE TABLE benchmark.{table} ({','.join(definitions)}, PRIMARY KEY ({key}))"
        with pg.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS benchmark.{table}")
            cur.execute(create)
        ddl.append(create + ";")
        n = 0
        with ch.query_row_block_stream(
            f"SELECT * FROM gold.{table}", settings={"max_block_size": 50000}
        ) as stream:
            for rows in stream:
                copy_frame(
                    pg, "benchmark." + table, pd.DataFrame(rows, columns=[r[0] for r in columns])
                )
                n += len(rows)
        if table.startswith("fact_"):
            with pg.cursor() as cur:
                for col in ("date_sk", "enrolled_date_sk", "course_sk", "user_sk"):
                    if col in [r[0] for r in columns]:
                        cur.execute(f"CREATE INDEX ON benchmark.{table} ({col})")
        counts[table] = n
        print(f"Benchmark mirror {table}: {n:,}", flush=True)
    pg.commit()
    with pg.cursor() as cur:
        for table in tables:
            cur.execute(f"ANALYZE benchmark.{table}")
    pg.commit()
    (ROOT / "benchmark/postgres_schema.sql").write_text("\n".join(ddl) + "\n", encoding="utf-8")
    return counts


def benchmark(runs=5, reuse_mirror=False):
    if runs < 3:
        raise ValueError("At least 3 measured runs are required")
    manifest = require_success()
    save_json(
        "benchmark/metadata.json",
        dict(status="running", pipeline_run=manifest["run_id"], started_at=utc_now()),
    )
    ch, pg = ch_connect(), staging_connect()
    warmups = 2
    try:
        tables = sorted(manifest["fingerprints"])
        begin = time.perf_counter()
        if reuse_mirror:
            with pg.cursor() as cur:
                counts = {}
                for table in tables:
                    cur.execute(f"SELECT count(*) FROM benchmark.{table}")
                    counts[table] = cur.fetchone()[0]
        else:
            counts = mirror(ch, pg, tables)
        mirror_seconds = round(time.perf_counter() - begin, 3)
        for t, n in counts.items():
            if n != manifest["fingerprints"][t][0]:
                raise AssertionError("Mirror count mismatch: " + t)
        # Full row SHA256 comparison, sorted by primary key, before any timing.
        equality = {}
        for table in tables:
            key = ch.query(f"DESCRIBE TABLE gold.{table}").first_row[0]
            ch_hash, pg_hash = hashlib.sha256(), hashlib.sha256()
            with ch.query_row_block_stream(
                f"SELECT * FROM gold.{table} ORDER BY {key}", settings={"max_block_size": 50000}
            ) as stream:
                for rows in stream:
                    # Each block is already ordered; preserve order across blocks.
                    for row in rows:
                        ch_hash.update(row_bytes(row))
            with pg.cursor(name="hash_" + table) as cur:
                cur.itersize = 50000
                cur.execute(f"SELECT * FROM benchmark.{table} ORDER BY {key}")
                while rows := cur.fetchmany(50000):
                    for row in rows:
                        pg_hash.update(row_bytes(row))
            # CH datetime may carry UTC tzinfo while PG is UTC-naive; normalized below if needed.
            equality[table] = dict(clickhouse=ch_hash.hexdigest(), postgres=pg_hash.hexdigest())
            if ch_hash.digest() != pg_hash.digest():
                raise AssertionError("Full row mirror hash mismatch: " + table)
            print("Full-row hash equal: " + table, flush=True)
        pg.commit()
        query_dir = ROOT / "benchmark/sql"
        query_dir.mkdir(parents=True, exist_ok=True)
        raw, summary, parity = [], [], {}

        def execute(engine, sql):
            start = time.perf_counter_ns()
            if engine == "clickhouse":
                rows = ch.query(
                    sql, settings={"group_by_use_nulls": 1, "use_query_cache": 0}
                ).result_rows
            else:
                with pg.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
            return (time.perf_counter_ns() - start) / 1e6, rows

        for name, template in QUERIES.items():
            queries = {
                "postgres": template.format(db="benchmark"),
                "clickhouse": template.format(db="gold"),
            }
            for engine, sql in queries.items():
                (query_dir / f"{name}.{engine}.sql").write_text(sql + ";\n", encoding="utf-8")
            baseline = {}
            for engine in queries:
                for _ in range(warmups):
                    _, rows = execute(engine, queries[engine])
                baseline[engine] = canonical(rows)
            if baseline["postgres"] != baseline["clickhouse"]:
                save_json("benchmark/mismatch.json", dict(query=name, results=baseline))
                raise AssertionError("Query result mismatch: " + name)
            parity[name] = dict(
                equal=True,
                rows=len(baseline["postgres"]),
                sha256=hashlib.sha256("\n".join(baseline["postgres"]).encode()).hexdigest(),
            )
            times = {"postgres": [], "clickhouse": []}
            for run in range(runs):
                order = ["postgres", "clickhouse"] if run % 2 == 0 else ["clickhouse", "postgres"]
                for engine in order:
                    elapsed, rows = execute(engine, queries[engine])
                    if canonical(rows) != baseline[engine]:
                        raise AssertionError("Unstable results during timing: " + name)
                    times[engine].append(elapsed)
                    raw.append(
                        dict(
                            query=name,
                            engine=engine,
                            run=run + 1,
                            milliseconds=round(elapsed, 4),
                            rows=len(rows),
                        )
                    )
            pg_ms, ch_ms = (
                statistics.median(times["postgres"]),
                statistics.median(times["clickhouse"]),
            )
            summary.append(
                dict(
                    query=name,
                    postgres_median_ms=round(pg_ms, 3),
                    clickhouse_median_ms=round(ch_ms, 3),
                    speedup_pg_over_ch=round(pg_ms / ch_ms, 3),
                    postgres_min_ms=round(min(times["postgres"]), 3),
                    postgres_max_ms=round(max(times["postgres"]), 3),
                    clickhouse_min_ms=round(min(times["clickhouse"]), 3),
                    clickhouse_max_ms=round(max(times["clickhouse"]), 3),
                    result_rows=parity[name]["rows"],
                )
            )
            print(
                f"{name}: PG {pg_ms:.2f} ms / CH {ch_ms:.2f} ms = {pg_ms / ch_ms:.2f}x (equal)",
                flush=True,
            )
        pg.commit()
        with pg.cursor() as cur:
            cur.execute("SELECT version()")
            pg_version = cur.fetchone()[0]
            cur.execute(
                "SELECT name,setting,unit FROM pg_settings WHERE name IN ('work_mem','shared_buffers','max_parallel_workers_per_gather')"
            )
            pg_settings = cur.fetchall()
            cur.execute(
                "SELECT sum(pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename))) FROM pg_tables WHERE schemaname='benchmark'"
            )
            pg_bytes = int(cur.fetchone()[0])
        storage = ch.query(
            "SELECT sum(bytes_on_disk),sum(data_uncompressed_bytes) FROM system.parts WHERE database='gold' AND active"
        ).first_row
        metadata = dict(
            status="success",
            measured_at=utc_now(),
            pipeline_run=manifest["run_id"],
            warmup_runs=warmups,
            measured_runs=runs,
            timing="client wall-clock execute+fetch, serial, warm cache; CH query cache disabled",
            postgres_version=pg_version,
            clickhouse_version=ch.query("SELECT version()").first_row[0],
            python_version=platform.python_version(),
            postgres_settings=pg_settings,
            resources=dict(
                postgres_cpu=4,
                clickhouse_cpu=4,
                postgres_memory="2 GiB",
                clickhouse_memory="3 GiB",
                runner_memory="1500 MiB",
            ),
            limitations=[
                "Single host Docker/WSL; no cold-cache control",
                "Memory budgets differ; not an equal-memory engine isolation test",
                "Network/client latency included",
                "CPU, query peak memory and IO are not measured",
                "Synthetic data; cannot generalize to production",
            ],
            mirror_counts=counts,
            mirror_seconds=mirror_seconds,
            mirror_reused=reuse_mirror,
            mirror_hashes=equality,
            query_parity=parity,
            storage=dict(
                postgres_gold_with_indexes_bytes=pg_bytes,
                clickhouse_gold_bytes_on_disk=storage[0],
                clickhouse_gold_uncompressed_column_bytes=storage[1],
            ),
        )
        save_json("benchmark/metadata.json", metadata)
        save_json("benchmark/summary.json", summary)
        for filename, records in [("runs.csv", raw), ("summary.csv", summary)]:
            with (ARTIFACTS / "benchmark" / filename).open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
        lines = [
            "# Benchmark — measured results",
            "",
            f"Pipeline: `{manifest['run_id']}`. {warmups} warm-ups + {runs} measured runs per engine/query.",
            "",
            "Same Gold rows and columns; full row hashes and all query outputs matched. Timings include client execute + fetch.",
            "",
            "| Query | PostgreSQL median ms | ClickHouse median ms | PG / CH |",
            "|---|---:|---:|---:|",
        ]
        lines += [
            f"| {r['query']} | {r['postgres_median_ms']} | {r['clickhouse_median_ms']} | {r['speedup_pg_over_ch']}x |"
            for r in summary
        ]
        lines += ["", "## Limitations", ""] + ["- " + v for v in metadata["limitations"]]
        (ARTIFACTS / "benchmark/results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        save_json(
            "benchmark/metadata.json",
            dict(
                status="failed",
                pipeline_run=manifest["run_id"],
                error=str(exc),
                finished_at=utc_now(),
            ),
        )
        raise
    finally:
        ch.close()
        pg.close()
