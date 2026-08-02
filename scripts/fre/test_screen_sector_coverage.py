"""Standalone assertion-script tests for screen_sector_coverage.py
(FSI Phase 25), validated against real production data. Invokes the
CLI script as a real subprocess (matching how an actual user would run
it) and compares against calling coverage_by_sector() directly.

  PYTHONPATH=src python scripts/fre/test_screen_sector_coverage.py
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.sector_coverage import coverage_by_sector  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

SCRIPT = ROOT / "scripts" / "fre" / "screen_sector_coverage.py"

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )


def _render_like_cli(rows) -> str:
    if not rows:
        return "No sectors found."
    return "\n".join(
        f"{r.sector_ngx}: total={r.total_tickers} fsi_covered={r.fsi_covered_tickers} "
        f"watchlist={r.watchlist_tickers}"
        for r in rows
    )


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(con)

    # --- 1. CLI output matches calling coverage_by_sector() directly -------
    direct = _render_like_cli(coverage_by_sector(con, "2026-08-02"))
    result = run_cli("--as-of", "2026-08-02")
    check("the CLI's stdout is identical to calling coverage_by_sector() "
          "directly, for the real production database",
          result.returncode == 0 and result.stdout.strip() == direct.strip())

    # --- 2. Real output includes the known CONSUMER GOODS row and the
    # UNKNOWN row last --------------------------------------------------------
    lines = result.stdout.strip().splitlines()
    check("CONSUMER GOODS appears with fsi_covered=3 (NASCON, NESTLE, "
          "BUAFOODS)",
          any(line.startswith("CONSUMER GOODS: ") and "fsi_covered=3" in line for line in lines))
    check("UNKNOWN is the last line printed (forced last, never buried "
          "mid-alphabet)",
          lines[-1].startswith("UNKNOWN: "))

    # --- 3. Malformed date produces a clear error, not a crash --------------
    bad_date_result = run_cli("--as-of", "not-a-date")
    check("a malformed --as-of date produces a clear error message and "
          "exit code 1, never a raw traceback",
          bad_date_result.returncode == 1 and "not a valid date" in bad_date_result.stderr
          and "Traceback" not in bad_date_result.stderr)

    # --- 4. Missing required argument produces argparse's own usage error --
    missing_args_result = run_cli()
    check("a missing required argument (--as-of) produces argparse's own "
          "clear usage error, exit code != 0",
          missing_args_result.returncode != 0)

    # --- 5. zero database writes, including across every subprocess --------
    after_counts = snapshot_all_table_counts(con)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run, "
          "including every real CLI subprocess invocation (zero database "
          "writes)", diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])

    con.close()
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
