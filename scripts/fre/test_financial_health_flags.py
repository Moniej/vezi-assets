"""Standalone assertion-script tests for financial_health_flags.py,
validated against real production data (read-only).

  PYTHONPATH=src python scripts/fre/test_financial_health_flags.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.financial_health_flags import compute_flags_for_ticker  # noqa: E402

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
    return sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)


def main() -> int:
    con = ro()
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    all_flags = {t: {f.flag_name: f for f in compute_flags_for_ticker(con, t)}
                 for t in ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON")}

    check("every ticker gets exactly the 3 named flags, never more or fewer",
          all(set(flags.keys()) == {"leverage_increasing", "cash_flow_earnings_divergence",
                                     "margin_compression"} for flags in all_flags.values()))

    # --- cash_flow_earnings_divergence: insufficient_data for the 3 tickers
    # confirmed (Stage 3 of Phase 2) to never have a cfo fact at all
    for ticker in ("AFRIPRUD", "CAP", "UCAP"):
        check(f"{ticker} cash_flow_earnings_divergence is insufficient_data (no cfo ever extracted)",
              all_flags[ticker]["cash_flow_earnings_divergence"].status == "insufficient_data")

    # --- NASCON leverage_increasing: real debt_to_equity rose from 0.823
    # (FY2024) to 0.900 (FY2025), a genuine +9.36% increase -- must FIRE
    nascon_leverage = all_flags["NASCON"]["leverage_increasing"]
    check("NASCON leverage_increasing correctly FIRES (real debt_to_equity trend is 'increasing')",
          nascon_leverage.status == "computed" and nascon_leverage.fired is True)

    # --- BUAFOODS cash_flow_earnings_divergence: the one real period with
    # both cfo and net_profit gives cfo_to_net_profit ~1.51 (>= 1.0) -- must
    # NOT fire
    buafoods_divergence = all_flags["BUAFOODS"]["cash_flow_earnings_divergence"]
    check("BUAFOODS cash_flow_earnings_divergence does NOT fire (real ratio ~1.51 >= 1.0 threshold)",
          buafoods_divergence.status == "computed" and buafoods_divergence.fired is False
          and buafoods_divergence.triggering_value > 1.0)

    # --- every 'computed' flag has a non-empty method string naming its own
    # exact trigger condition, and a non-empty limitations string -- no flag
    # is ever silently mysterious about why it fired or didn't
    all_results = [f for flags in all_flags.values() for f in flags.values()]
    check("every flag result has a non-empty, specific method string (its own trigger condition)",
          all(len(f.method) > 20 for f in all_results))
    check("every flag result has a non-empty limitations string",
          all(len(f.limitations) > 10 for f in all_results))
    check("insufficient_data flags never claim fired True/False (fired is None)",
          all(f.fired is None for f in all_results if f.status == "insufficient_data"))
    check("computed flags always have a definite fired True/False (never None)",
          all(f.fired is not None for f in all_results if f.status == "computed"))

    con.close()

    # --- confirm the real production database was never touched by this test ---
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this test only reads)", doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
