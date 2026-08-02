"""Standalone assertion-script tests for manage_watchlist.py (FSI Phase
21). Invokes the CLI as a real subprocess (matching how an actual user
would run it). CRITICAL: every subprocess invocation in this test sets
NGXROT_DB_PATH to a disposable scratch copy of the real database (the
sanctioned override db.py's own DEFAULT_DB honors) -- this is the
platform's FIRST write-capable CLI, so this test never once invokes
`add`/`remove` against the real production database. `list`/`history`
are additionally exercised once, read-only, against the real database.

  PYTHONPATH=src python scripts/fre/test_manage_watchlist.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.watchlist import get_history_for_ticker, list_active  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

SCRIPT = ROOT / "scripts" / "fre" / "manage_watchlist.py"

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


def run_cli(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "NGXROT_DB_PATH": str(db_path)},
    )


def main() -> int:
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)

    con = sqlite3.connect(scratch)
    latest_nascon = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='NASCON'"
    ).fetchone()[0]
    con.close()

    # --- 1. add: succeeds, prints the new watchlist_entry_id ---------------
    result = run_cli(
        scratch, "add", "--ticker", "NASCON", "--rationale", "CLI test rationale.",
        "--source-thesis-as-of", latest_nascon, "--entry-criteria", "CLI test criteria.",
        "--review-cadence", "on-next-filing",
    )
    check("add: exit code 0, prints the new watchlist_entry_id",
          result.returncode == 0 and "Added watchlist_entry_id=" in result.stdout)

    con = sqlite3.connect(scratch)
    entry_id = int(result.stdout.strip().split("watchlist_entry_id=")[1].split(" ")[0])
    check("add: the row is really present in the scratch database "
          "(the CLI subprocess actually committed the write)",
          con.execute("SELECT ticker FROM watchlist_entries WHERE watchlist_entry_id=?",
                      (entry_id,)).fetchone() == ("NASCON",))
    con.close()

    # --- 2. add: a real validation error (unknown ticker) surfaces cleanly -
    result = run_cli(
        scratch, "add", "--ticker", "NOTAREALTICKER", "--rationale", "x",
        "--source-thesis-as-of", latest_nascon, "--entry-criteria", "x",
    )
    check("add: an unknown ticker produces watchlist.add_entry()'s own "
          "ValueError message via stderr, exit code 1, never a raw traceback",
          result.returncode == 1 and "unknown ticker" in result.stderr and "Traceback" not in result.stderr)

    # --- 3. add: malformed date produces a clear error, not a crash --------
    result = run_cli(
        scratch, "add", "--ticker", "NASCON", "--rationale", "x",
        "--source-thesis-as-of", "not-a-date", "--entry-criteria", "x",
    )
    check("add: a malformed --source-thesis-as-of date produces a clear "
          "error message and exit code 1",
          result.returncode == 1 and "not a valid date" in result.stderr and "Traceback" not in result.stderr)

    # --- 4. list: the new entry shows up as active --------------------------
    result = run_cli(scratch, "list", "--as-of", "2026-08-05")
    check("list: the newly-added NASCON entry appears in the active list",
          result.returncode == 0 and "NASCON" in result.stdout and f"[{entry_id}]" in result.stdout)

    # --- 5. remove: succeeds, entry no longer active -------------------------
    result = run_cli(scratch, "remove", "--watchlist-entry-id", str(entry_id),
                      "--removed-at", "2026-08-06", "--removal-reason", "CLI test removal.")
    check("remove: exit code 0, prints confirmation",
          result.returncode == 0 and f"Removed watchlist_entry_id={entry_id}" in result.stdout)

    result = run_cli(scratch, "list", "--as-of", "2026-08-07")
    check("list: the now-removed NASCON entry no longer appears as active",
          result.returncode == 0 and "NASCON" not in result.stdout)

    result = run_cli(scratch, "history", "--ticker", "NASCON")
    check("history: the removed entry still appears in full history, "
          "showing its removal reason",
          result.returncode == 0 and "CLI test removal." in result.stdout)

    # --- 6. remove: double-removal is rejected cleanly -----------------------
    result = run_cli(scratch, "remove", "--watchlist-entry-id", str(entry_id),
                      "--removed-at", "2026-08-08", "--removal-reason", "second attempt")
    check("remove: a double-removal attempt produces watchlist.remove_entry()'s "
          "own ValueError message via stderr, exit code 1",
          result.returncode == 1 and "already removed" in result.stderr and "Traceback" not in result.stderr)

    # --- 7. equivalence: list/history CLI output matches calling the "list_active()"/
    # "get_history_for_ticker()" functions directly against the same scratch DB -----
    con = sqlite3.connect(scratch)
    direct_history = get_history_for_ticker(con, "NASCON")
    con.close()
    result = run_cli(scratch, "history", "--ticker", "NASCON")
    check("history: CLI output mentions every real watchlist_entry_id from "
          "calling get_history_for_ticker() directly against the same data",
          all(f"[{e.watchlist_entry_id}]" in result.stdout for e in direct_history))

    # --- 8. list/history against the REAL production database, read-only ----
    result = run_cli(db.DEFAULT_DB, "list", "--as-of", "2026-08-02")
    direct_active = list_active(real_ro, as_of_date="2026-08-02")
    check("list against the REAL database: CLI output matches list_active() "
          "called directly (read-only, no write attempted)",
          result.returncode == 0
          and (result.stdout.strip() == "No entries." if not direct_active
               else all(f"[{e.watchlist_entry_id}]" in result.stdout for e in direct_active)))

    # --- 9. the REAL production database was never touched -------------------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged -- "
          "every add/remove subprocess in this test targeted only the scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
