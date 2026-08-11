"""FRE-7A: rerun of the ORIGINAL FRE-7 pilot with the taxonomy frozen
(docs/fre_runs/fre7a_peer_taxonomy_report.md).

CRITICAL SEPARATION (per the FRE-7A brief): identical tickers, identical
financial inputs, identical valuation formulas, identical WACC/terminal-
growth assumptions, identical activation criterion (bracket the real
market close price) as the original FRE-7 pilot
(docs/fre_runs/fre7_valuation_activation_report.md Section 5). The ONLY
changed component is the peer-selection layer: `economic_peer_taxonomy.
select_peers()` replaces `valuation_engine._peer_tickers()` (which was
built from the coarse `classify_company_type()`).

This script does not modify valuation_engine.py -- it imports its private
EPS/price/percentile helpers unchanged (`_eps`, `_latest_price`,
`_percentile`) and re-applies the EXACT SAME arithmetic PEAdapter.compute()
uses (median peer multiple x subject metric; range = [p25, p75] x subject
metric) to a different peer set. DCF has no peer dependency at all, so
CAP's dcf result is recomputed with the ORIGINAL adapter directly,
unchanged, for completeness.

No parameter is retuned after seeing the result -- this script is run
exactly once per invocation and prints its own output as the final answer.

  PYTHONPATH=src python scripts/fre/fre7a_rerun_pilot.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import economic_peer_taxonomy as ept  # noqa: E402
from ngxrot.fre import valuation_engine as ve  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402

AS_OF = "2026-08-09"

# Identical to the original FRE-7 pilot's own pe cases.
PE_PILOT_TICKERS = ["UCAP", "BUAFOODS", "NASCON", "CAP", "OANDO", "UBN"]
# Identical to the original FRE-7 pilot's own dcf case and assumptions.
DCF_PILOT_TICKER = "CAP"
DCF_ASSUMPTIONS = {"wacc": 0.22, "terminal_growth": 0.06}

ORIGINAL_RESULT = {
    "UCAP": {"point": 24.58, "range": (10.61, 86.51), "ref": 18.00, "brackets": True},
    "NASCON": {"point": 142.82, "range": (84.20, 686.46), "ref": 195.00, "brackets": True},
    "BUAFOODS": {"point": 175.83, "range": (103.66, 240.07), "ref": 845.10, "brackets": False},
    "CAP_pe": {"point": 15.87, "range": (9.35, 21.66), "ref": 115.45, "brackets": False},
    "OANDO": {"point": 82.80, "range": (60.64, 291.46), "ref": 35.75, "brackets": False},
    "UBN": {"point": 21.16, "range": (15.50, 74.48), "ref": 6.65, "brackets": False},
    "CAP_dcf": {"point": 8.33, "range": (7.37, 9.57), "ref": 115.45, "brackets": False},
}


def rerun_pe(con: sqlite3.Connection, ticker: str, candidate_tickers: list[str]) -> dict:
    subj = ve._eps(con, ticker, AS_OF)
    if subj is None or subj[0] <= 0:
        return {"ticker": ticker, "method": "pe", "status": "DATA_GAP",
                "reason": "subject EPS unavailable or non-positive (identical to original FRE-7 "
                          "extraction -- unaffected by peer taxonomy)"}
    subj_eps = subj[0]

    peer_selection = ept.select_peers(con, ticker, AS_OF, candidate_tickers, min_peers=2)
    if peer_selection.tier == "none":
        return {"ticker": ticker, "method": "pe", "status": "DATA_GAP",
                "reason": f"FRE-7A taxonomy: {peer_selection.reason}",
                "taxonomy_tier": "none"}

    peer_pes: list[float] = []
    peers_used: list[str] = []
    for peer in peer_selection.peers:
        p = ve._eps(con, peer, AS_OF)
        if p is None or p[0] <= 0:
            continue
        price = ve._latest_price(con, peer, AS_OF)
        if price is None:
            continue
        pe = price[1] / p[0]
        if pe > 0:
            peer_pes.append(pe)
            peers_used.append(peer)

    if len(peer_pes) < 2:
        return {"ticker": ticker, "method": "pe", "status": "DATA_GAP",
                "reason": f"FRE-7A taxonomy selected {len(peer_selection.peers)} candidate peer(s) "
                          f"at tier={peer_selection.tier!r}, but only {len(peer_pes)} have a "
                          f"computable positive P/E as of {AS_OF} (< 2 required)",
                "taxonomy_tier": peer_selection.tier}

    median_pe = ve._percentile(peer_pes, 0.5)
    p25, p75 = ve._percentile(peer_pes, 0.25), ve._percentile(peer_pes, 0.75)
    point = median_pe * subj_eps
    range_low, range_high = min(p25, p75) * subj_eps, max(p25, p75) * subj_eps

    price_row = ve._latest_price(con, ticker, AS_OF)
    ref = price_row[1] if price_row else None
    brackets = (range_low <= ref <= range_high) if ref is not None else None

    return {
        "ticker": ticker, "method": "pe", "status": "computed",
        "point": point, "range": (range_low, range_high), "ref": ref, "brackets": brackets,
        "taxonomy_tier": peer_selection.tier, "peers_used": peers_used,
        "n_candidate_peers": len(peer_selection.peers),
    }


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    doc_count_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    tickers = list_tickers(con)

    print("=" * 100)
    print("FRE-7A PILOT RERUN -- identical tickers/inputs/formulas/assumptions/criterion;")
    print("ONLY the peer-selection layer changed (economic_peer_taxonomy vs classify_company_type)")
    print("=" * 100)
    print()

    results = []
    for t in PE_PILOT_TICKERS:
        r = rerun_pe(con, t, tickers)
        results.append(r)
        orig = ORIGINAL_RESULT["CAP_pe" if t == "CAP" else t]
        print(f"{t}:")
        print(f"  ORIGINAL (FRE-7, company_type peers): point={orig['point']}, "
              f"range={orig['range']}, ref={orig['ref']}, brackets={orig['brackets']}")
        if r["status"] == "DATA_GAP":
            print(f"  FRE-7A   (economic-taxonomy peers): DATA_GAP -- {r['reason']}")
        else:
            print(f"  FRE-7A   (economic-taxonomy peers): point={r['point']:.2f}, "
                  f"range=({r['range'][0]:.2f}, {r['range'][1]:.2f}), ref={r['ref']}, "
                  f"brackets={r['brackets']}, tier={r['taxonomy_tier']}, "
                  f"peers={r['peers_used']} (of {r['n_candidate_peers']} candidates)")
        print()

    # DCF has no peer dependency -- rerun via the ORIGINAL, unmodified adapter directly.
    dcf_result = ve.DCFAdapter().compute(con, DCF_PILOT_TICKER, AS_OF, DCF_ASSUMPTIONS)
    price_row = ve._latest_price(con, DCF_PILOT_TICKER, AS_OF)
    ref = price_row[1] if price_row else None
    dcf_brackets = (dcf_result.range_low <= ref <= dcf_result.range_high) if (dcf_result.point_estimate and ref) else None
    print(f"{DCF_PILOT_TICKER} (dcf, no peer dependency -- original adapter, unchanged):")
    orig = ORIGINAL_RESULT["CAP_dcf"]
    print(f"  ORIGINAL (FRE-7): point={orig['point']}, range={orig['range']}, ref={orig['ref']}, brackets={orig['brackets']}")
    print(f"  FRE-7A   (identical -- dcf uses no peer group): point={dcf_result.point_estimate:.2f}, "
          f"range=({dcf_result.range_low:.2f}, {dcf_result.range_high:.2f}), ref={ref}, brackets={dcf_brackets}")
    print()

    numeric_results = [r for r in results if r["status"] == "computed"]
    n_bracket = sum(1 for r in numeric_results if r["brackets"]) + (1 if dcf_brackets else 0)
    n_total_computed = len(numeric_results) + 1  # + dcf
    n_data_gap = sum(1 for r in results if r["status"] == "DATA_GAP")

    print("=" * 100)
    print(f"FRE-7A PILOT RESULT: {n_bracket}/{n_total_computed} COMPUTED cases bracket the "
          f"independent reference value ({n_bracket/n_total_computed:.0%})")
    print(f"({n_data_gap} of the original 6 pe cases now report an explicit DATA_GAP under the "
          f"finer-grained taxonomy -- insufficient real comparable peers, not silently dropped)")
    print(f"Gate requires a MAJORITY (> 50%) of pilot cases to bracket.")
    gate_passes = n_bracket / n_total_computed > 0.5 if n_total_computed else False
    print(f"GATE: {'PASSES' if gate_passes else 'FAILS'}")
    print("=" * 100)

    con2 = sqlite3.connect(db.DEFAULT_DB)
    doc_count_after = con2.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert doc_count_after == doc_count_before, "production database was written to -- this must never happen"
    con2.close()
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
