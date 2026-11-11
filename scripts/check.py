"""Run lint, formatting and the existing warehouse unit/integration suite."""

import subprocess
import sys
import unittest
from etl.common import save_json, utc_now

paths = [
    "cli.py",
    "etl",
    "analytics",
    "benchmark",
    "demo",
    "oltp",
    "tests",
    "scripts",
    "docs/generate_dictionary.py",
]
for arguments in [["check", *paths], ["format", "--check", *paths]]:
    subprocess.run([sys.executable, "-m", "ruff", *arguments], check=True)
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover("tests"))
receipt = dict(
    status="success" if result.wasSuccessful() else "failed",
    checked_at=utc_now(),
    lint="passed",
    format="passed",
    tests=result.testsRun,
    failures=len(result.failures),
    errors=len(result.errors),
    scope="unit tests and integration against current main Gold",
)
save_json("code-checks.json", receipt)
if not result.wasSuccessful():
    sys.exit(1)
