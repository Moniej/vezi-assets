"""Decision Intelligence Phase 1: tests for company_state.py.

Same no-pytest, script-based, read-only-against-production convention as
every other FRE test script.

  PYTHONPATH=src python scripts/fre/test_company_state.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.company_state import KNOWN, UNKNOWN, build_company_state  # noqa: E402

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
    AS_OF = "2026-08-09"

    # Shared cache -- company_intelligence.build_profile() is ~15-20s cold,
    # ~0.4s warm; every state built in this test reuses ONE cache dict so
    # the whole suite runs in a reasonable time, matching build_company_
    # state()'s own documented intended usage.
    cache: dict = {}

    dealing_tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM documents WHERE doc_type='dealing' AND ticker IS NOT NULL LIMIT 3"
    ).fetchall()]

    tickers = ["CAP", "AFRIPRUD", "TOTAL", "GTCO", "NOTAREALTICKER"] + dealing_tickers
    states = {t: build_company_state(con, t, AS_OF, intelligence_cache=cache) for t in dict.fromkeys(tickers)}
    s_cap, s_total = states["CAP"], states["TOTAL"]

    # --- every DataPoint status is one of the 4 allowed values --------------
    for t, s in states.items():
        all_points = (list(s.business.values()) + list(s.financial.values())
                      + list(s.market.values()) + [s.corporate_events, s.regulatory, s.insider_activity])
        check(f"{t}: every DataPoint status is KNOWN/UNKNOWN/CONFLICTING/STALE",
              all(p.status in ("KNOWN", "UNKNOWN", "CONFLICTING", "STALE") for p in all_points))
        check(f"{t}: every DataPoint names a real source string (never blank)",
              all(p.source for p in all_points))
        check(f"{t}: data_completeness is a real fraction in [0,1]", 0.0 <= s.data_completeness <= 1.0)

    # --- confirmed real, honest data-richness gradient across the pilot ----
    check("CAP (real FSI coverage) has HIGHER data_completeness than TOTAL "
          "(no FSI facts) -- the state engine reflects real coverage, not a fabricated floor",
          s_cap.data_completeness > s_total.data_completeness)
    check("CAP's financial line items are all KNOWN with real fact_id provenance",
          all(s_cap.financial[k].status == KNOWN and "fact_id=" in s_cap.financial[k].source
              for k in ("revenue", "net_profit", "equity", "assets", "liabilities")))
    check("TOTAL's financial line items are all UNKNOWN (no FSI extraction exists for it) -- "
          "never inferred or defaulted", all(s_total.financial[k].status == UNKNOWN
              for k in ("revenue", "net_profit", "equity", "assets", "liabilities")))

    # --- business_description/segments/geography are UNKNOWN for EVERY
    # ticker, including the richest one --------------------------------------
    for t in ["CAP", "AFRIPRUD"]:
        s = states[t]
        check(f"{t}: business_description/segments/geography are UNKNOWN (no such data "
              f"exists anywhere on this platform)",
              s.business["business_description"].status == UNKNOWN
              and s.business["segments"].status == UNKNOWN
              and s.business["geography"].status == UNKNOWN)

    # --- valuation_confidence passthrough -----------------------------------
    from ngxrot.fre.valuation_engine import value_company  # noqa: E402
    for t in ["CAP", "TOTAL"]:
        tv = value_company(con, t, AS_OF)
        check(f"{t}: financial['valuation_confidence'] exactly matches "
              f"value_company().valuation_confidence (no recomputation)",
              states[t].financial["valuation_confidence"].value == tv.valuation_confidence)

    # --- insider activity: vesting-only tickers must never be misread as a
    # purchase/sale -----------------------------------------------------------
    for t in dealing_tickers:
        s = states[t]
        check(f"{t}: insider_activity status is KNOWN or UNKNOWN, never a crash, for a "
              f"real ticker with 'dealing' filings on record",
              s.insider_activity.status in ("KNOWN", "UNKNOWN"))
        if s.insider_activity.status == "KNOWN":
            check(f"{t}: every classified insider transaction has nature in "
                  f"{{PURCHASE, SALE}} only (vesting already excluded at classification)",
                  all(txn.nature in ("PURCHASE", "SALE") for txn in s.insider_activity.value))

    # --- PIT: a later as_of_date can only reveal MORE or EQUAL corporate
    # events than an earlier one for the same ticker -------------------------
    s_early = build_company_state(con, "CAP", "2020-01-01", intelligence_cache=cache)
    s_late = states["CAP"]
    n_early = len(s_early.corporate_events.value) if s_early.corporate_events.status == "KNOWN" else 0
    n_late = len(s_late.corporate_events.value) if s_late.corporate_events.status == "KNOWN" else 0
    check("CAP: corporate_events count as of 2020-01-01 <= count as of 2026-08-09 "
          "(monotonic PIT growth, never fewer events revealed by an earlier date)",
          n_early <= n_late)

    # --- architectural isolation: read-only, no write path anywhere --------
    src_text = (ROOT / "src" / "ngxrot" / "fre" / "company_state.py").read_text(encoding="utf-8")
    check("company_state.py contains no INSERT/UPDATE/DELETE SQL anywhere (read-only module)",
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
