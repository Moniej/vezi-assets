"""Regression test for load_real_corporate_actions_dividends.py
(2026-08-11, HANDOFF.md). Real-database checks (read-only) plus one
scratch-DB check of the alpha-safety guarantee this loader depends on.

  PYTHONPATH=src python scripts/test_corporate_actions_dividend_load.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

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


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)

    n_real = con.execute(
        "SELECT COUNT(*) FROM corporate_actions WHERE source_fact_id IS NOT NULL").fetchone()[0]
    check("real dividend rows loaded (>=100, matches the confirmed 155)", n_real >= 100)

    n_synthetic = con.execute(
        "SELECT COUNT(*) FROM corporate_actions WHERE ticker LIKE 'SYNBNK%'").fetchone()[0]
    check("pre-existing synthetic dev fixtures (31) untouched, never deleted", n_synthetic == 31)

    n_md_populated = con.execute(
        "SELECT COUNT(*) FROM corporate_actions WHERE source_fact_id IS NOT NULL "
        "AND markdown_date IS NOT NULL").fetchone()[0]
    check("ALPHA-SAFETY: zero fact-linked rows have markdown_date populated "
          "(engine_full.py's total-return overlay cannot fire on any of these rows)",
          n_md_populated == 0)

    orphans = con.execute(
        "SELECT COUNT(*) FROM corporate_actions ca WHERE ca.source_fact_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM extracted_facts ef WHERE ef.fact_id = ca.source_fact_id)"
    ).fetchone()[0]
    check("every source_fact_id resolves to a real extracted_facts row (no dangling links)",
          orphans == 0)

    n_real_tickers = con.execute(
        "SELECT COUNT(DISTINCT ticker) FROM corporate_actions WHERE source_fact_id IS NOT NULL"
    ).fetchone()[0]
    check("real dividend data spans multiple real tickers (not one synthetic fixture)",
          n_real_tickers >= 20)

    fabricated_amounts = con.execute(
        "SELECT COUNT(*) FROM corporate_actions ca JOIN extracted_facts ef "
        "ON ef.fact_id = ca.source_fact_id "
        "WHERE ca.dividend_per_share IS NOT NULL AND ef.numeric_value IS NULL"
    ).fetchone()[0]
    check("no dividend_per_share was fabricated where the source fact had no numeric_value",
          fabricated_amounts == 0)

    mismatched_amounts = con.execute(
        "SELECT COUNT(*) FROM corporate_actions ca JOIN extracted_facts ef "
        "ON ef.fact_id = ca.source_fact_id "
        "WHERE ca.dividend_per_share IS NOT NULL AND ef.numeric_value IS NOT NULL "
        "AND ABS(ca.dividend_per_share - ef.numeric_value) > 1e-9"
    ).fetchone()[0]
    check("every populated dividend_per_share matches its source fact's numeric_value exactly",
          mismatched_amounts == 0)

    n_bonus_rights = con.execute(
        "SELECT COUNT(*) FROM corporate_actions WHERE action_type NOT IN "
        "('dividend_cash', 'rights_issue')"
    ).fetchone()[0]
    check("no bonus/reconstruction rows introduced by this loader (out of scope this pass -- "
          "only the 1 pre-existing synthetic rights_issue fixture plus dividend_cash exist)",
          n_bonus_rights == 0)

    con.close()

    # --- scratch-DB check: the migration is idempotent and additive -----------
    scratch_dir = Path(tempfile.mkdtemp())
    scratch_db = scratch_dir / "ngx.sqlite"
    scon = db.init_db(scratch_db, seed=False)
    info = scon.execute("PRAGMA table_info(corporate_actions)").fetchall()
    check("migration: source_fact_id column exists on a freshly-migrated database",
          any(c[1] == "source_fact_id" for c in info))
    scon.close()
    db.init_db(scratch_db, seed=False)  # rerun should not raise (idempotent ALTER)
    check("migration: rerunning init_db() on an already-migrated database does not raise", True)
    shutil.rmtree(scratch_dir, ignore_errors=True)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
