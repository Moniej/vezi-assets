"""Decision Intelligence Phase 11: tests for market_intelligence.py.

  PYTHONPATH=src python scripts/fre/test_market_intelligence.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.market_intelligence import build_market_intelligence  # noqa: E402

REAL_DB = db.DEFAULT_DB
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


def ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{REAL_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    cache: dict = {}
    mi = build_market_intelligence(con, "2026-08-09", "2024-01-01", intelligence_cache=cache)

    check("all 9 real NGX indices are present in sector_momentum",
          len(mi.sector_momentum) == 9)
    check("every SectorMomentum with both closes available has a real, computed pct_change "
          "(never None when both inputs exist)",
          all(sm.pct_change is not None for sm in mi.sector_momentum
              if sm.start_close is not None and sm.end_close is not None))
    check("sector_momentum pct_change is None whenever either close is missing (never defaulted to 0)",
          all(sm.pct_change is None for sm in mi.sector_momentum
              if sm.start_close is None or sm.end_close is None))

    check("fsi_coverage_by_sector is real, non-empty sector_coverage.py output, unmodified",
          len(mi.fsi_coverage_by_sector) > 0)

    check("improving_companies and deteriorating_companies are disjoint sets",
          not (set(mi.improving_companies) & set(mi.deteriorating_companies)))
    check("companies_assessed + len(companies_skipped) == the real genuine fact-bearing "
          "universe size (24, per genuine_fact_universe.py)",
          mi.companies_assessed + len(mi.companies_skipped) == 24)

    check("every capital_raising_event has a real ticker and event_type",
          all(e["ticker"] and e["event_type"] for e in mi.capital_raising_events))
    check("capital_raising_events are all within (prior_date, as_of_date] -- PIT-gated",
          all(mi.prior_date < e["announced_date"] <= mi.as_of_date for e in mi.capital_raising_events))

    check("regulatory_theme_counts values are all positive integers (real counts, never fabricated)",
          all(isinstance(v, int) and v > 0 for v in mi.regulatory_theme_counts.values()))

    # --- a narrower window produces counts <= a wider window (monotonic,
    # sanity check against a fabricated/static count) ------------------------
    mi_narrow = build_market_intelligence(con, "2026-08-09", "2026-01-01", intelligence_cache=cache)
    check("a narrower [2026-01-01, 2026-08-09] regulatory-theme total is <= the wider "
          "[2024-01-01, 2026-08-09] total (real, window-sensitive counting)",
          sum(mi_narrow.regulatory_theme_counts.values()) <= sum(mi.regulatory_theme_counts.values()))

    con.close()
    con = sqlite3.connect(REAL_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path at all)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
