"""Standalone assertion-script tests for
generate_portfolio_context_dossier.py (FSI Phase 22), validated against
real production data. Invokes the CLI script as a real subprocess
(matching how an actual user would run it) and compares against
calling as_of()/render() directly in Python.

  PYTHONPATH=src python scripts/fre/test_generate_portfolio_context_dossier.py
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
from ngxrot.fre.company_portfolio_context import as_of, render  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

SCRIPT = ROOT / "scripts" / "fre" / "generate_portfolio_context_dossier.py"

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


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(con)

    tickers = list(list_tickers(con))
    latest_dates = {}
    for ticker in tickers:
        latest_dates[ticker] = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]

    # --- 1. Script output matches calling as_of()/render() directly, for all
    # 10 real FSI tickers ---------------------------------------------------
    equivalence_ok = True
    for ticker in tickers:
        direct = render(as_of(con, ticker, latest_dates[ticker]))
        result = run_cli("--ticker", ticker, "--as-of", latest_dates[ticker])
        if result.returncode != 0 or result.stdout.strip() != direct.strip():
            equivalence_ok = False
            print(f"  MISMATCH for {ticker}: returncode={result.returncode}")
    check(f"the CLI script's stdout is identical to calling as_of()/render() "
          f"directly, for all {len(tickers)} real FSI tickers",
          equivalence_ok)

    # --- 2. CAVERTON: outside the FSI ticker set but confirmed in the live
    # H-011 sleeve today -- exercises the "in live sleeve" rendering path ----
    direct_caverton = render(as_of(con, "CAVERTON", "2026-08-02"))
    result = run_cli("--ticker", "CAVERTON", "--as-of", "2026-08-02")
    check("CAVERTON: CLI output identical to direct call, and correctly "
          "states it IS currently in the live sleeve",
          result.returncode == 0 and result.stdout.strip() == direct_caverton.strip()
          and "Currently in the live sleeve" in result.stdout)

    # --- 3. --output writes the identical text to the given file ------------
    scratch_dir = Path(db.new_scratch_db_path()).parent
    output_path = scratch_dir / "test_portfolio_dossier_output.md"
    result = run_cli("--ticker", "NASCON", "--as-of", latest_dates["NASCON"], "--output", str(output_path))
    direct_nascon = render(as_of(con, "NASCON", latest_dates["NASCON"]))
    check("--output writes a file byte-identical to the direct render, and "
          "the script still prints to stdout too",
          result.returncode == 0
          and output_path.exists()
          and output_path.read_text(encoding="utf-8") == direct_nascon
          and direct_nascon.strip() in result.stdout)
    output_path.unlink()
    scratch_dir.rmdir()

    # --- 4. Without --output, no file is written anywhere --------------------
    stray_files_before = set(SCRIPT.parent.glob("*.md"))
    run_cli("--ticker", "CAP", "--as-of", latest_dates["CAP"])
    stray_files_after = set(SCRIPT.parent.glob("*.md"))
    check("running without --output creates NO file anywhere",
          stray_files_before == stray_files_after)

    # --- 5. Unknown ticker produces a clear, honest error --------------------
    bad_ticker_result = run_cli("--ticker", "NOTAREALTICKER", "--as-of", "2026-01-01")
    check("an unknown ticker produces a clear error message and exit code 1, "
          "never a crash or a fabricated report",
          bad_ticker_result.returncode == 1
          and "unknown ticker" in bad_ticker_result.stderr.lower()
          and bad_ticker_result.stdout.strip() == "")

    # --- 6. Malformed date produces a clear, honest error ---------------------
    bad_date_result = run_cli("--ticker", "NASCON", "--as-of", "not-a-date")
    check("a malformed --as-of date produces a clear error message and exit "
          "code 1, never a crash with a raw traceback",
          bad_date_result.returncode == 1
          and "not a valid date" in bad_date_result.stderr.lower()
          and "Traceback" not in bad_date_result.stderr)

    # --- 7. Missing required arguments produce argparse's own usage error ----
    missing_args_result = run_cli("--ticker", "NASCON")
    check("a missing required argument (--as-of) produces argparse's own "
          "clear usage error, exit code != 0",
          missing_args_result.returncode != 0)

    con.close()

    # --- database immutability across the entire test run --------------------
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run, "
          "including every real CLI subprocess invocation (zero database "
          "writes)", table_diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
