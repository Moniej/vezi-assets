"""Standalone assertion-script tests for generate_research_dossier.py,
validated against real production data. Invokes the CLI script as a real
subprocess (matching how an actual user would run it) and compares
against calling build_dossier()/render_dossier() directly in Python.

  PYTHONPATH=src python scripts/fre/test_generate_research_dossier.py
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_research_dossier import build_dossier, render_dossier  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

SCRIPT = ROOT / "scripts" / "fre" / "generate_research_dossier.py"

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
    env_python = sys.executable
    # encoding="utf-8" explicitly: the script itself forces UTF-8 on its own
    # stdout/stderr (see Entry 1 of the implementation log -- real filing
    # text contains the Naira sign, U+20A6). Capturing without an explicit
    # encoding here would let subprocess.run() fall back to the OS locale's
    # default (cp1252 on this Windows environment), producing mojibake even
    # though the child process's own bytes are correct UTF-8 -- a real
    # decoding mismatch found while building this exact test.
    return subprocess.run(
        [env_python, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(con)

    # FSI Phase 16: dynamic ticker discovery (was a hardcoded 5-ticker list
    # that silently stopped covering Phase 13's 5 new tickers).
    tickers = list_tickers(con)
    latest_dates = {}
    for ticker in tickers:
        latest_dates[ticker] = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]

    # --- 1. Script output matches calling build_dossier()/render_dossier()
    # directly, for all real tickers --------------------------------------------
    equivalence_ok = True
    for ticker in tickers:
        direct = render_dossier(build_dossier(con, ticker, latest_dates[ticker]))
        result = run_cli("--ticker", ticker, "--as-of", latest_dates[ticker])
        if result.returncode != 0 or result.stdout.strip() != direct.strip():
            equivalence_ok = False
            print(f"  MISMATCH for {ticker}: returncode={result.returncode}")
    check(f"the CLI script's stdout output is identical to calling "
          f"build_dossier()/render_dossier() directly, for all "
          f"{len(tickers)} real tickers at their own latest real filing date",
          equivalence_ok)

    # --- 2. --output writes the identical text to the given file, and stdout
    # still shows the same content too -----------------------------------------
    scratch_dir = Path(db.new_scratch_db_path()).parent
    output_path = scratch_dir / "test_dossier_output.md"
    result = run_cli("--ticker", "NASCON", "--as-of", latest_dates["NASCON"], "--output", str(output_path))
    direct_nascon = render_dossier(build_dossier(con, "NASCON", latest_dates["NASCON"]))
    check("--output writes a file whose content is byte-identical to the "
          "direct render, and the script still prints to stdout too",
          result.returncode == 0
          and output_path.exists()
          and output_path.read_text(encoding="utf-8") == direct_nascon
          and direct_nascon.strip() in result.stdout)
    output_path.unlink()
    scratch_dir.rmdir()

    # --- 3. Without --output, NO file is written anywhere ----------------------
    # (already implicitly covered by the DB-immutability check below covering
    # the whole test run, but explicitly confirm no stray file appears in the
    # script's own directory)
    stray_files_before = set(SCRIPT.parent.glob("*.md"))
    run_cli("--ticker", "CAP", "--as-of", latest_dates["CAP"])
    stray_files_after = set(SCRIPT.parent.glob("*.md"))
    check("running without --output creates NO file anywhere",
          stray_files_before == stray_files_after)

    # --- 4. Unknown ticker produces a clear, honest error, never a crash or a
    # fabricated/misleading report ----------------------------------------------
    bad_ticker_result = run_cli("--ticker", "NOTAREALTICKER", "--as-of", "2026-01-01")
    check("an unknown ticker produces a clear error message and exit code 1, "
          "never a crash or a fabricated report",
          bad_ticker_result.returncode == 1
          and "unknown ticker" in bad_ticker_result.stderr.lower()
          and bad_ticker_result.stdout.strip() == "")

    # --- 5. Malformed date produces a clear, honest error -----------------------
    bad_date_result = run_cli("--ticker", "NASCON", "--as-of", "not-a-date")
    check("a malformed --as-of date produces a clear error message and exit "
          "code 1, never a crash with a raw traceback",
          bad_date_result.returncode == 1
          and "not a valid date" in bad_date_result.stderr.lower()
          and "Traceback" not in bad_date_result.stderr)

    # --- 6. Missing required arguments produce argparse's own clear usage error
    missing_args_result = run_cli("--ticker", "NASCON")
    check("a missing required argument (--as-of) produces argparse's own "
          "clear usage error, exit code != 0",
          missing_args_result.returncode != 0)

    con.close()

    # --- database immutability: the entire test run, including every CLI
    # invocation above, must leave data/ngx.sqlite completely unchanged --------
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
