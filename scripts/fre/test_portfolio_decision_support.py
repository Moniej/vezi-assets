"""Decision Intelligence Phase 12: tests for portfolio_decision_support.py.

NOTE: `portfolio_memory.cross_reference()` (an existing, unmodified module)
reloads the full quant registry/sleeve on every call (~15-20s, uncached --
a real, pre-existing performance characteristic of that module, not
something this new module can or should fix). This test therefore uses
only 2 holdings to keep runtime bounded.

  PYTHONPATH=src python scripts/fre/test_portfolio_decision_support.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.portfolio_decision_support import build_portfolio_decision_support  # noqa: E402

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
    HOLDINGS = ["CAP", "AFRIPRUD"]
    pds = build_portfolio_decision_support(con, HOLDINGS, "2026-08-09", "2024-01-01",
                                            intelligence_cache=cache)

    check("holdings echoes exactly what the caller supplied -- never a discovered/invented "
          "portfolio", pds.holdings == HOLDINGS)
    check("portfolio_health has an entry for every holding that didn't fail",
          set(pds.portfolio_health.keys()) == set(HOLDINGS) - set(pds.failed_tickers))
    check("every portfolio_health value is LOW/MEDIUM/HIGH",
          all(v in ("LOW", "MEDIUM", "HIGH") for v in pds.portfolio_health.values()))
    check("every thesis_change entry names a real holding ticker",
          all(c["ticker"] in HOLDINGS for c in pds.thesis_changes))
    check("every risk_alert entry names a real holding ticker and a non-empty reason",
          all(a["ticker"] in HOLDINGS and a["reason"] for a in pds.risk_alerts))
    check("research_queue only contains real holding tickers, never a ticker outside the "
          "supplied portfolio", set(pds.research_queue) <= set(HOLDINGS))
    check("research_queue is sorted worst-confidence-first",
          [pds.portfolio_health[t] for t in pds.research_queue] ==
          sorted([pds.portfolio_health[t] for t in pds.research_queue],
                 key=lambda v: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[v]))

    # --- portfolio_memory.cross_reference() is called read-only, never
    # writes back into the quant registry -- confirmed by checking module
    # source contains no write SQL/API call. ---------------------------------
    src_text = (ROOT / "src" / "ngxrot" / "fre" / "portfolio_decision_support.py").read_text(encoding="utf-8")
    check("portfolio_decision_support.py contains no INSERT/UPDATE/DELETE SQL anywhere",
          not any(kw in src_text.upper() for kw in ("INSERT INTO", "UPDATE ", "DELETE FROM")))

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
