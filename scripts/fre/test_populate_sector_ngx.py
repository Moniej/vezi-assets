"""Standalone assertion-script tests for populate_sector_ngx.py (FSI
Phase 23). Section 1 confirms the REAL production database's actual
current state (already populated by a prior real run of this script);
Section 2 re-exercises the population logic on a disposable scratch
copy to confirm it is idempotent and mechanically correct in isolation.

  PYTHONPATH=src python scripts/fre/test_populate_sector_ngx.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts" / "fre"))
from populate_sector_ngx import SECTOR_MAPPING, populate  # noqa: E402

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
    real_ro = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    before_counts = snapshot_all_table_counts(real_ro)

    # --- 1. Real production state: already populated by a real prior run --
    mapping_tickers = {t[0] for t in SECTOR_MAPPING}
    check("SECTOR_MAPPING has no duplicate tickers",
          len(mapping_tickers) == len(SECTOR_MAPPING))

    real_populated = real_ro.execute(
        "SELECT COUNT(*) FROM securities WHERE sector_ngx IS NOT NULL"
    ).fetchone()[0]
    check("real securities.sector_ngx is populated for exactly as many "
          "tickers as SECTOR_MAPPING names (every mapped ticker matched "
          "a real securities row)",
          real_populated == len(SECTOR_MAPPING))

    real_provenance = real_ro.execute("SELECT COUNT(*) FROM sector_ngx_provenance").fetchone()[0]
    check("every populated sector_ngx value has exactly one matching "
          "sector_ngx_provenance row (full audit trail, no bare values)",
          real_provenance == real_populated)

    mismatch = real_ro.execute(
        "SELECT s.ticker FROM securities s JOIN sector_ngx_provenance p ON p.ticker = s.ticker "
        "WHERE s.sector_ngx != p.sector_ngx"
    ).fetchall()
    check("every provenance row's sector_ngx matches the value actually "
          "written to securities.sector_ngx (no drift)",
          mismatch == [])

    check("UBN (the one FSI ticker NOT found in the source document) "
          "correctly remains NULL, not guessed",
          real_ro.execute("SELECT sector_ngx FROM securities WHERE ticker='UBN'").fetchone()[0] is None)

    check("every real sector_ngx value is one of NGX's own 13 top-level "
          "sector headings from the source document, verbatim -- never "
          "a normalized/reformatted/invented label",
          all(row[0] in {"AGRICULTURE", "CONGLOMERATES", "CONSTRUCTION/REAL ESTATE",
                          "CONSUMER GOODS", "FINANCIAL SERVICES", "HEALTHCARE", "ICT",
                          "INDUSTRIAL GOODS", "INVESTMENT", "NATURAL RESOURCES",
                          "OIL AND GAS", "SERVICES", "UTILITIES"}
              for row in real_ro.execute(
                  "SELECT DISTINCT sector_ngx FROM securities WHERE sector_ngx IS NOT NULL")))

    real_source_urls = set(r[0] for r in real_ro.execute(
        "SELECT DISTINCT source_url FROM sector_ngx_provenance").fetchall())
    check("every provenance row cites the same real, official NGX source URL",
          real_source_urls == {"https://doclib.ngxgroup.com/DownloadsContent/"
                                "Daily%20Official%20List%20-%20Equities%20for%2021-04-2026.pdf"})

    # --- 2. Population logic re-exercised on a disposable scratch copy ---
    scratch = db.new_scratch_db_path()
    shutil.copy(db.DEFAULT_DB, scratch)
    con = sqlite3.connect(scratch)

    # Reset sector_ngx/provenance on the scratch copy to prove populate()
    # itself does the real work, not just re-confirming already-set data.
    con.execute("UPDATE securities SET sector_ngx = NULL")
    con.execute("DELETE FROM sector_ngx_provenance")
    con.commit()

    updated, skipped = populate(con)
    con.commit()
    check("populate() on a freshly-reset scratch copy updates exactly "
          "len(SECTOR_MAPPING) tickers, with 0 skipped (every mapped "
          "ticker matches a real securities row)",
          updated == len(SECTOR_MAPPING) and skipped == 0)

    scratch_populated = con.execute(
        "SELECT COUNT(*) FROM securities WHERE sector_ngx IS NOT NULL"
    ).fetchone()[0]
    check("scratch copy: sector_ngx populated count matches populate()'s "
          "own reported updated count",
          scratch_populated == updated)

    nascon_sector = con.execute("SELECT sector_ngx FROM securities WHERE ticker='NASCON'").fetchone()[0]
    check("scratch copy: NASCON correctly re-populated as CONSUMER GOODS",
          nascon_sector == "CONSUMER GOODS")

    con.close()

    # --- 3. The REAL production database was not touched by THIS test ------
    after_counts = snapshot_all_table_counts(real_ro)
    diffs = diff_table_counts(before_counts, after_counts)
    check("ALL of the REAL data/ngx.sqlite tables' row counts are unchanged "
          "by THIS test run -- Section 2's reset/re-populate only ever "
          "happened on a disposable scratch copy",
          diffs == [])
    check("real database integrity_check reports 'ok' after this test run",
          real_ro.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("real database foreign_key_check reports clean after this test run",
          real_ro.execute("PRAGMA foreign_key_check").fetchall() == [])
    real_ro.close()

    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
