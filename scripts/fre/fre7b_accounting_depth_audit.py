"""FRE-7B: Accounting Data Depth Audit (docs/fre_runs/fre7b_accounting_data_depth_audit.md).

Infrastructure/data-quality assessment ONLY. Read-only against the real
production database. No valuation is computed, no formula is run, no
parameter is tuned, no hypothesis is registered, no backtest runs.

For every real fact-bearing ticker, measures availability and PIT coverage
of the facts a peer-based P/E/P/B valuation needs (net_profit, equity,
revenue, shares_outstanding via market_cap_panel.csv), broken down by
FRE-7A's own frozen economic taxonomy (unmodified, imported read-only),
and traces every gap back to whether the underlying document already
exists on the platform (an extraction gap) or not (a genuine acquisition
gap). Every ABSENT/UNUSABLE label below is a direct, live query result --
nothing is inferred, defaulted, or fabricated.

  PYTHONPATH=src python scripts/fre/fre7b_accounting_data_depth_audit.py
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
from ngxrot.fre.period_normalization import classify_period_type  # noqa: E402

AS_OF = "2026-08-09"
FINANCIAL_STATEMENT_FACT_TYPES = (
    "net_profit", "equity", "revenue", "assets", "liabilities", "ebit", "ebitda",
    "cfo", "cfi", "cff", "capex", "fcf", "gross_profit", "cogs",
)


def usable_fy_fact(con, ticker, fact_type):
    """Real FY-period, NGN, non-null, PIT-knowable fact -- or None. Mirrors
    valuation_engine.py's own _fact_for_exact_period/_latest_fy_period,
    reused read-only, not reimplemented differently."""
    fy = ve._latest_fy_period(con, ticker, AS_OF)
    if fy is None:
        return None
    f = ve._fact_for_exact_period(con, ticker, fact_type, fy[0], fy[1], AS_OF)
    if f is None or f[3] != "NGN":
        return None
    return f


def usable_stock_fact(con, ticker, fact_type):
    s = ve._latest_stock_fact(con, ticker, fact_type, AS_OF)
    if s is None or s[3] != "NGN":
        return None
    return s


def main() -> int:
    con = sqlite3.connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    tickers = list_tickers(con)

    print("=" * 100)
    print("PART A -- per-ticker raw fact inventory (all financial-statement fact types)")
    print("=" * 100)
    per_ticker = {}
    for t in tickers:
        row = {}
        for ft in FINANCIAL_STATEMENT_FACT_TYPES:
            n = con.execute(
                "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
                "WHERE d.ticker=? AND f.fact_type=?", (t, ft)
            ).fetchone()[0]
            row[ft] = n
        n_results_notice = con.execute(
            "SELECT COUNT(*) FROM documents WHERE ticker=? AND doc_type='results_notice'", (t,)
        ).fetchone()[0]
        n_total_docs = con.execute("SELECT COUNT(*) FROM documents WHERE ticker=?", (t,)).fetchone()[0]
        usable_np = usable_fy_fact(con, t, "net_profit")
        usable_eq = usable_stock_fact(con, t, "equity")
        usable_rev = usable_fy_fact(con, t, "revenue")
        c = ept.classify_ticker(con, t, AS_OF)
        per_ticker[t] = {
            "raw": row, "results_notice_docs": n_results_notice, "total_docs": n_total_docs,
            "usable_net_profit": usable_np is not None, "usable_equity": usable_eq is not None,
            "usable_revenue": usable_rev is not None,
            "level1": c.level1, "level2": c.level2,
        }
        print(f"{t:12s} L1={str(c.level1):12s} L2={str(c.level2):32s} "
              f"NP={row['net_profit']}(usable={usable_np is not None}) "
              f"EQ={row['equity']}(usable={usable_eq is not None}) "
              f"REV={row['revenue']}(usable={usable_rev is not None}) "
              f"results_notice_docs={n_results_notice} total_docs={n_total_docs}")

    print()
    print("=" * 100)
    print("PART B -- peer-group bottleneck table (grouped by FRE-7A level1)")
    print("=" * 100)
    from collections import defaultdict
    by_l1 = defaultdict(list)
    for t, d in per_ticker.items():
        by_l1[d["level1"]].append(t)

    for l1, members in sorted(by_l1.items(), key=lambda kv: str(kv[0])):
        n = len(members)
        n_np = sum(1 for t in members if per_ticker[t]["usable_net_profit"])
        n_eq = sum(1 for t in members if per_ticker[t]["usable_equity"])
        n_both = sum(1 for t in members if per_ticker[t]["usable_net_profit"] and per_ticker[t]["usable_equity"])
        obs_counts = sorted(per_ticker[t]["raw"]["net_profit"] for t in members)
        median_obs = obs_counts[len(obs_counts) // 2] if obs_counts else 0
        print(f"L1={str(l1):14s} n={n:2d} usable_net_profit={n_np:2d} ({n_np/n:.0%})  "
              f"usable_equity={n_eq:2d} ({n_eq/n:.0%})  both={n_both:2d} ({n_both/n:.0%})  "
              f"median_net_profit_obs_per_ticker={median_obs}  members={members}")

    print()
    print("=" * 100)
    print("PART C -- source-coverage audit: results_notice documents that exist vs. "
          "documents that actually contributed an extracted financial-statement fact")
    print("=" * 100)
    total_results_notice = con.execute("SELECT COUNT(*) FROM documents WHERE doc_type='results_notice'").fetchone()[0]
    extracted_from_results_notice = con.execute(
        "SELECT COUNT(DISTINCT d.doc_id) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.doc_type='results_notice'"
    ).fetchone()[0]
    print(f"Total results_notice documents platform-wide: {total_results_notice}")
    print(f"Distinct results_notice documents with >=1 extracted financial-statement fact: {extracted_from_results_notice}")
    print(f"Un-extracted results_notice documents (source exists, extraction not yet run): "
          f"{total_results_notice - extracted_from_results_notice}")
    print()
    print("Per-ticker: results_notice docs vs. distinct results_notice docs actually mined "
          "(for the 26 fact-bearing tickers only):")
    for t in tickers:
        total_rn = con.execute(
            "SELECT COUNT(*) FROM documents WHERE ticker=? AND doc_type='results_notice'", (t,)
        ).fetchone()[0]
        mined_rn = con.execute(
            "SELECT COUNT(DISTINCT d.doc_id) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=? AND d.doc_type='results_notice'", (t,)
        ).fetchone()[0]
        if total_rn > 0:
            print(f"  {t:12s} results_notice_docs={total_rn:3d}  mined={mined_rn:3d}  "
                  f"un-mined={total_rn - mined_rn:3d}")

    print()
    print("=" * 100)
    print("PART D -- fact source / extraction-method / grounding breakdown "
          "(financial-statement fact types only)")
    print("=" * 100)
    print("By source doc_type:")
    for r in con.execute(
        "SELECT d.doc_type, COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE f.fact_type IN (?,?,?,?,?,?,?,?,?,?,?,?,?,?) GROUP BY d.doc_type ORDER BY 2 DESC",
        FINANCIAL_STATEMENT_FACT_TYPES,
    ).fetchall():
        print(" ", r)
    print("By confidence_tier:")
    for r in con.execute(
        "SELECT confidence_tier, COUNT(*) FROM extracted_facts "
        "WHERE fact_type IN (?,?,?,?,?,?,?,?,?,?,?,?,?,?) GROUP BY confidence_tier ORDER BY 2 DESC",
        FINANCIAL_STATEMENT_FACT_TYPES,
    ).fetchall():
        print(" ", r)
    print("By grounding_check:")
    for r in con.execute(
        "SELECT grounding_check, COUNT(*) FROM extracted_facts "
        "WHERE fact_type IN (?,?,?,?,?,?,?,?,?,?,?,?,?,?) GROUP BY grounding_check ORDER BY 2 DESC",
        FINANCIAL_STATEMENT_FACT_TYPES,
    ).fetchall():
        print(" ", r)

    print()
    print("=" * 100)
    print("PART E -- PIT / lookahead mechanical check + conflict scan")
    print("=" * 100)
    lookahead = con.execute(
        "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE f.period_end IS NOT NULL AND d.filing_date < f.period_end "
        "AND f.fact_type IN (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        FINANCIAL_STATEMENT_FACT_TYPES,
    ).fetchone()[0]
    print(f"Facts filed BEFORE their own period ended (lookahead violation): {lookahead}")
    conflicts = con.execute(
        "SELECT d.ticker, f.fact_type, f.period_start, f.period_end, COUNT(*), GROUP_CONCAT(f.numeric_value) "
        "FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE f.fact_type IN ('net_profit','equity','revenue','assets','liabilities') "
        "GROUP BY d.ticker, f.fact_type, f.period_start, f.period_end HAVING COUNT(*) > 1"
    ).fetchall()
    print(f"Exact (ticker, fact_type, period_start, period_end) groups with >1 value: {len(conflicts)}")
    for c in conflicts:
        print(" ", c)

    print()
    print("=" * 100)
    print("PART F -- shares-outstanding (market_cap_panel.csv) coverage")
    print("=" * 100)
    for t in tickers:
        s = ve._shares_outstanding_millions(t, AS_OF)
        print(f"  {t:12s} shares_outstanding_available={s is not None}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
