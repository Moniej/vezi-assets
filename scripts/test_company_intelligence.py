"""Standalone assertion-script tests for src/ngxrot/company_intelligence.py's
Industry Exposure integration (FSI Phase 27), validated against real
production data. Read-only -- company_intelligence.py has no write path.

  PYTHONPATH=src python scripts/test_company_intelligence.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot import company_intelligence as ci  # noqa: E402

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
    before_doc_count = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- 1. Real data: a ticker with a known sector ------------------------
    nascon = ci.build_profile(con, "NASCON", as_of="2026-08-02")
    check("NASCON: industry_exposure == 'CONSUMER GOODS' (real sector_ngx, "
          "FSI Phase 23)", nascon.industry_exposure == "CONSUMER GOODS")
    check("NASCON: 'Industry Exposure' is correctly REMOVED from unavailable "
          "once populated", "Industry Exposure" not in nascon.unavailable)

    # --- 2. Real data: a ticker with NO known sector (UBN, the one FSI
    # ticker absent from Phase 23's source document) ------------------------
    ubn = ci.build_profile(con, "UBN", as_of="2026-08-02")
    check("UBN: industry_exposure stays None (sector_ngx is NULL, never "
          "guessed)", ubn.industry_exposure is None)
    check("UBN: 'Industry Exposure' correctly REMAINS in unavailable, "
          "disclosed", "Industry Exposure" in ubn.unavailable)

    # --- 3. Isolation: one profile's unavailable mutation never leaks into
    # another, even when built with a shared cache in the same batch run ---
    cache: dict = {}
    p_known = ci.build_profile(con, "NASCON", as_of="2026-08-02", cache=cache)
    p_unknown = ci.build_profile(con, "UBN", as_of="2026-08-02", cache=cache)
    check("shared-cache batch run: NASCON's Industry Exposure removal does "
          "NOT leak into UBN's own unavailable dict (each profile's own "
          "fresh copy, via default_factory)",
          "Industry Exposure" not in p_known.unavailable
          and "Industry Exposure" in p_unknown.unavailable)
    check("the module-level UNAVAILABLE_FIELDS dict itself is never mutated "
          "by any profile build (confirmed after two builds touching it)",
          "Industry Exposure" in ci.UNAVAILABLE_FIELDS)

    # --- 4. Unknown ticker: no crash, industry_exposure stays None ---------
    unknown_ticker = ci.build_profile(con, "NOTAREALTICKER", as_of="2026-08-02")
    check("an unknown ticker (no securities row) does not crash, and "
          "industry_exposure stays None",
          unknown_ticker.industry_exposure is None
          and "Industry Exposure" in unknown_ticker.unavailable)

    # --- 5. No other field is disturbed by this phase's change --------------
    check("NASCON's name field is still populated correctly (unrelated field, "
          "confirms the SELECT change didn't break anything else)",
          nascon.name == "NASCON")

    # --- 6. the REAL production database was never touched ---------------------
    after_doc_count = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write "
          "path at all)", after_doc_count == before_doc_count)
    check("real database integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])

    con.close()
    print(f"\n{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
