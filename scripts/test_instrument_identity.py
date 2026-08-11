"""Tests for src/ngxrot/instrument_identity.py.

  PYTHONPATH=src python scripts/test_instrument_identity.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from ngxrot import db  # noqa: E402
from ngxrot.instrument_identity import full_price_history_query, resolve_ticker_history_symbols  # noqa: E402

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
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- real rename chains, confirmed against entity_relationships -------
    for ticker, expected_symbols, expected_transition in [
        ("GTCO", ["GUARANTY", "GTCO"], "2021-06-24"),
        ("ACCESSCORP", ["ACCESS", "ACCESSCORP"], "2022-03-28"),
        ("FIRSTHOLDCO", ["FBNH", "FIRSTHOLDCO"], "2025-03-10"),
    ]:
        eras = resolve_ticker_history_symbols(con, ticker)
        check(f"{ticker}: resolves to the real 2-symbol chain {expected_symbols}",
              [e.ticker for e in eras] == expected_symbols)
        check(f"{ticker}: transition date matches the real entity_relationships.valid_from",
              eras[0].valid_to == expected_transition and eras[1].valid_from == expected_transition)
        check(f"{ticker}: oldest era has valid_from=None (no earlier bound known)",
              eras[0].valid_from is None)
        check(f"{ticker}: newest (current) era has valid_to=None (still current)",
              eras[-1].valid_to is None)

    # --- a ticker with no rename history returns a single, honest era -----
    eras_cap = resolve_ticker_history_symbols(con, "CAP")
    check("CAP (no known rename): resolves to exactly one era, itself",
          len(eras_cap) == 1 and eras_cap[0].ticker == "CAP"
          and eras_cap[0].valid_from is None and eras_cap[0].valid_to is None)

    # --- a nonexistent ticker never crashes or fabricates a chain ---------
    eras_fake = resolve_ticker_history_symbols(con, "NOTAREALTICKER")
    check("NOTAREALTICKER: resolves to a single, unmodified era (no entity-graph "
          "presence found, never guessed)",
          len(eras_fake) == 1 and eras_fake[0].ticker == "NOTAREALTICKER")

    # --- full_price_history_query: real, bridged, MORE complete than
    # querying either symbol alone ------------------------------------------
    ref_sid = con.execute("SELECT source_id FROM sources WHERE name='ngx_pricelist_v2'").fetchone()[0]
    bridged = pd.read_sql(full_price_history_query(con, "GTCO", ref_sid), con)
    gtco_only = pd.read_sql(
        "SELECT trade_date FROM equity_prices WHERE source_id=? AND ticker='GTCO'", con, params=(ref_sid,))
    check("GTCO bridged history has MORE rows than querying 'GTCO' alone "
          "(real pre-rename GUARANTY history is included)",
          len(bridged) > len(gtco_only))
    check("GTCO bridged history's earliest date is well before the 2021 rename "
          "(real GUARANTY-era history reached)",
          bridged["trade_date"].min() < "2021-06-24")
    check("GTCO bridged history preserves the ORIGINAL ticker each row was stored "
          "under (never silently relabels GUARANTY-era rows as 'GTCO')",
          set(bridged["original_ticker"]) == {"GUARANTY", "GTCO"})
    check("GTCO bridged history tags every row with canonical_ticker='GTCO'",
          (bridged["canonical_ticker"] == "GTCO").all())
    check("GTCO bridged history has zero duplicate (original_ticker, trade_date) rows",
          not bridged.duplicated(subset=["original_ticker", "trade_date"]).any())

    con.close()
    con = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    check("production documents count unchanged (this module has no write path at all)",
          doc_count_after == doc_count_before)
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
