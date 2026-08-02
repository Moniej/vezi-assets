"""Standalone assertion-script tests for screen_companies.py (FSI Phase
15), validated against real production data. Invokes the CLI script as a
real subprocess (matching how an actual user would run it).

  PYTHONPATH=src python scripts/fre/test_screen_companies.py
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
from ngxrot.fre.screening import screen_by_flag, screen_by_trend  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

SCRIPT = ROOT / "scripts" / "fre" / "screen_companies.py"

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
    # encoding="utf-8" explicitly, same real lesson as Phase 12's own test
    # (subprocess.run(text=True) without it decodes using the OS locale
    # default, producing mojibake even when the child's own bytes are
    # correct UTF-8).
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )


def _render_matches_like_cli(matches) -> str:
    """Reproduces screen_companies.py's own _print_matches() formatting,
    to compare against real CLI stdout without importing a private
    function from another script."""
    if not matches:
        return "No matches."
    lines = []
    for m in matches:
        period = f"{m.period_start}..{m.period_end}" if m.period_start else "(no period)"
        tier = m.confidence_tier if m.confidence_tier is not None else "NOT RECORDED"
        lines.append(f"{m.ticker}: {m.metric}={m.value_text} period={period} "
                     f"confidence_tier={tier} conclusion_id={m.conclusion_id}")
        lines.append(f"    method: {m.method}")
        lines.append(f"    limitations: {m.limitations}")
    return "\n".join(lines)


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(con)

    far_future = "2030-01-01"

    # --- 1. flag subcommand equivalence -----------------------------------
    direct_flag = _render_matches_like_cli(
        screen_by_flag(con, "leverage_increasing", True, far_future))
    result = run_cli("flag", "--metric", "leverage_increasing", "--fired", "true", "--as-of", far_future)
    check("the CLI's 'flag' subcommand stdout is identical to calling "
          "screen_by_flag() directly, for a real fired flag",
          result.returncode == 0 and result.stdout.strip() == direct_flag.strip())

    # --- 2. trend subcommand equivalence -----------------------------------
    direct_trend = _render_matches_like_cli(
        screen_by_trend(con, "net_profit", "decreasing", far_future))
    result = run_cli("trend", "--metric", "net_profit", "--direction", "decreasing", "--as-of", far_future)
    check("the CLI's 'trend' subcommand stdout is identical to calling "
          "screen_by_trend() directly, for a real decreasing trend",
          result.returncode == 0 and result.stdout.strip() == direct_trend.strip())

    # --- 3. an empty result set prints "No matches." not a blank/crash ----
    result = run_cli("flag", "--metric", "cash_flow_earnings_divergence", "--fired", "true", "--as-of", "2020-01-01")
    check("a real, correctly-empty result set (far too early for any conclusion "
          "to be knowable) prints 'No matches.', not a blank output or a crash",
          result.returncode == 0 and result.stdout.strip() == "No matches.")

    # --- 4. invalid categorical values are rejected by argparse, exit code != 0
    result = run_cli("flag", "--metric", "not_a_real_flag", "--fired", "true", "--as-of", far_future)
    check("an unrecognized --metric produces argparse's own clear usage error, "
          "exit code != 0, never a raw traceback",
          result.returncode != 0 and "Traceback" not in result.stderr)

    result = run_cli("trend", "--metric", "revenue", "--direction", "improving", "--as-of", far_future)
    check("an unrecognized --direction produces argparse's own clear usage error",
          result.returncode != 0 and "Traceback" not in result.stderr)

    # --- 5. malformed --as-of produces a clear error, not a crash ----------
    result = run_cli("flag", "--metric", "leverage_increasing", "--fired", "true", "--as-of", "not-a-date")
    check("a malformed --as-of date produces a clear error message and exit "
          "code 1, never a raw traceback",
          result.returncode == 1 and "not a valid date" in result.stderr and "Traceback" not in result.stderr)

    # --- 6. missing required argument produces argparse's own usage error --
    result = run_cli("flag", "--metric", "leverage_increasing", "--as-of", far_future)
    check("a missing required argument (--fired) produces argparse's own "
          "clear usage error, exit code != 0",
          result.returncode != 0 and "Traceback" not in result.stderr)

    # --- 7. zero database writes, including across every subprocess invocation
    after_counts = snapshot_all_table_counts(con)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run, "
          "including every real CLI subprocess invocation (zero database writes)",
          diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])

    con.close()
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
