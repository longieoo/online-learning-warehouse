"""Single entry point for setup, data, ETL, analytics and diagnostics."""

import argparse
import json
import sys
from contextlib import closing
from etl.common import project_lock, source_connect


def main():
    parser = argparse.ArgumentParser(description="Online Learning DW · synthetic data 2022–2024")
    parser.add_argument(
        "command",
        choices=[
            "setup",
            "generate",
            "pipeline",
            "validate",
            "reports",
            "benchmark",
            "doctor",
            "all",
        ],
    )
    parser.add_argument("--enrollments", type=int, default=500000)
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--reuse-mirror",
        action="store_true",
        help="Verify and reuse the existing PostgreSQL Gold mirror",
    )
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    args = parser.parse_args()
    if args.command in ("setup", "all"):
        from etl.bootstrap import setup

        setup()
        if args.command == "setup":
            print("Setup complete. Source reader and staging roles are ready.")
            return
    if args.command == "doctor":
        from etl.doctor import doctor

        print(json.dumps(doctor(), indent=2, ensure_ascii=False, default=str))
        return
    with project_lock(shared=args.command == "reports"):
        if args.command in ("generate", "all"):
            with closing(source_connect()) as source, source.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM oltp.enrollments")
                populated = cursor.fetchone()[0] > 0
            if args.command == "generate" or not populated:
                from oltp.generate_data import generate

                generate(args.enrollments, args.seed)
            else:
                print("Source already populated. Reusing source data.")
        if args.command in ("pipeline", "all"):
            from etl.pipeline import pipeline

            pipeline(args.mode)
        if args.command == "validate":
            from etl.validate import validate

            validate()
        if args.command in ("reports", "all"):
            from analytics.reports import reports

            reports()
        if args.command in ("benchmark", "all"):
            from benchmark.run_benchmark import benchmark

            benchmark(args.runs, reuse_mirror=args.reuse_mirror)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, AssertionError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
