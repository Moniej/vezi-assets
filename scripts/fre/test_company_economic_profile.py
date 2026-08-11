"""Decision Intelligence Phase 14: tests for company_economic_profile.py.

  PYTHONPATH=src python scripts/fre/test_company_economic_profile.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_economic_profile import _FIELD_NAMES, build_economic_profile  # noqa: E402

REAL_DB = db.DEFAULT_DB
passed = 0
failed = 0

_CONFIRMED_ABSENT_FIELDS = {
    "business_description", "products_services", "revenue_segments", "geographic_exposure",
    "customer_concentration", "supplier_dependencies", "management_ownership",
    "material_subsidiaries", "strategic_priorities",
}


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
    AS_OF = "2026-08-09"

    check("exactly 15 fields are defined (matches the task's own numbered list)",
          len(_FIELD_NAMES) == 15)

    for t in ["CAP", "AFRIPRUD", "TOTAL", "NOTAREALTICKER"]:
        p = build_economic_profile(con, t, AS_OF, intelligence_cache=cache)
        check(f"{t}: profile has exactly the 15 documented fields, no more, no less",
              set(p.fields.keys()) == set(_FIELD_NAMES))
        check(f"{t}: every field status is KNOWN/UNKNOWN/CONFLICTING/STALE",
              all(dp.status in ("KNOWN", "UNKNOWN", "CONFLICTING", "STALE") for dp in p.fields.values()))
        check(f"{t}: every field names a real, non-empty source", all(dp.source for dp in p.fields.values()))
        check(f"{t}: coverage is a real fraction in [0,1]", 0.0 <= p.coverage <= 1.0)

        # --- the 9 confirmed-platform-wide-absent fields are UNKNOWN for
        # EVERY ticker, including the richest one -- never fabricated even
        # for a data-rich company. -------------------------------------------
        check(f"{t}: all 9 confirmed-absent fields are UNKNOWN",
              all(p.fields[f].status == "UNKNOWN" for f in _CONFIRMED_ABSENT_FIELDS))

    # --- CAP (rich, classified) has strictly higher coverage than TOTAL
    # (unclassified/thin) -- reflects real evidence, not a fabricated floor -
    p_cap = build_economic_profile(con, "CAP", AS_OF, intelligence_cache=cache)
    p_total = build_economic_profile(con, "TOTAL", AS_OF, intelligence_cache=cache)
    check("CAP has higher coverage than TOTAL", p_cap.coverage > p_total.coverage)
    check("CAP: business_model/industry_sub_industry/competitive_peer_context/capital_structure "
          "are all KNOWN (real economic_peer_taxonomy + financial data)",
          all(p_cap.fields[f].status == "KNOWN" for f in
              ("business_model", "industry_sub_industry", "competitive_peer_context", "capital_structure")))

    # --- competitive_peer_context is explicitly disclosed as a SECTOR
    # PROXY, never presented as a real disclosed competitor list --------------
    check("CAP: competitive_peer_context source explicitly discloses it is a sector/subsector "
          "proxy, not a real disclosed competitor list",
          "proxy" in p_cap.fields["competitive_peer_context"].source)

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
