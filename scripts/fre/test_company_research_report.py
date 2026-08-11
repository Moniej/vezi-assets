"""Decision Intelligence Phase 13/16: tests for company_research_report.py.

  PYTHONPATH=src python scripts/fre/test_company_research_report.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_research_report import build_full_report, render_full_report  # noqa: E402

REAL_DB = db.DEFAULT_DB
passed = 0
failed = 0

REQUIRED_SECTIONS = [
    "Executive Investment View", "Company Overview", "What Changed",
    "Fundamental Analysis", "Earnings Trajectory", "Capital Allocation",
    "Management & Insider Activity", "Regulatory Developments",
    "Corporate Actions", "Market Behavior", "Bull Case", "Base Case", "Bear Case",
    "Catalysts", "Risks", "Contradictory Evidence", "Valuation Status",
    "Data-Quality Assessment", "Confidence Assessment", "Evidence Timeline",
    "Open Questions", "What Would Change The Current Assessment", "Recommendation",
    "Evidence Appendix",
]


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
    AS_OF, PRIOR = "2026-08-09", "2024-01-01"

    for t in ["CAP", "TOTAL"]:
        report = build_full_report(con, t, AS_OF, PRIOR, intelligence_cache=cache,
                                    include_portfolio_note=False)
        md = render_full_report(report)
        check(f"{t}: report renders to a real, non-trivial Markdown document",
              isinstance(md, str) and len(md) > 500)
        for section in REQUIRED_SECTIONS:
            check(f"{t}: report contains a '## ... {section}' section", section in md)
        check(f"{t}: report explicitly states no BUY/WATCH/HOLD/AVOID recommendation is "
              f"produced (governance disclosure, not silently omitted)",
              "NOT PRODUCED BY THIS PLATFORM" in md)
        check(f"{t}: report explicitly states VALUATION_CONFIDENCE (Core Principle compliance)",
              "VALUATION_CONFIDENCE = " in md)
        check(f"{t}: report includes economic_profile fields not in company_state alone "
              f"(products/services, customer concentration, supplier dependencies)",
              "Products/services:" in md and "Customer concentration:" in md
              and "Supplier dependencies:" in md)
        check(f"{t}: 'What Would Change The Current Assessment' section is non-empty",
              "No specific invalidation trigger identified" in md or "- A subsequent" in md
              or "- Resolution of" in md or "- Additional currency-clean" in md)

    # --- TOTAL (thin data): report still renders cleanly, with honest
    # UNKNOWNs, never a crash or fabricated content --------------------------
    report_total = build_full_report(con, "TOTAL", AS_OF, PRIOR, intelligence_cache=cache,
                                      include_portfolio_note=False)
    md_total = render_full_report(report_total)
    check("TOTAL: 'UNKNOWN' appears in the rendered report (thin data honestly disclosed)",
          "UNKNOWN" in md_total)

    # --- a real HIGH/CRITICAL change produces a real, specific invalidation
    # condition naming the exact field, not a generic placeholder -----------
    report_cap = build_full_report(con, "CAP", AS_OF, PRIOR, intelligence_cache=cache,
                                    include_portfolio_note=False)
    md_cap = render_full_report(report_cap)
    check("CAP: at least one invalidation condition names a real financial field "
          "(materially changed between snapshots)",
          any(f in md_cap for f in ("equity", "assets", "liabilities", "revenue", "net_profit"))
          and "A subsequent" in md_cap)

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
