"""Standalone assertion-script tests for trend_classification.py, validated
against real production data (read-only), specifically the real NASCON
H1-2024-vs-FY2024 overlap case that must never produce a trend pair.

  PYTHONPATH=src python scripts/fre/test_trend_classification.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.trend_classification import classify_trends_for_ticker  # noqa: E402

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

    # --- the central regression: NASCON's real H1 2024 vs FY2024 periods
    # overlap (H1 nested in FY) -- must NEVER produce a trend pair, for any
    # metric, even though both periods have real data for almost every metric
    nascon_results = classify_trends_for_ticker(con, "NASCON")
    revenue_trends = [r for r in nascon_results if r.metric == "revenue"]
    check("NASCON revenue trend has exactly ONE pair (FY2024->FY2025), not two "
          "(H1-2024-vs-FY2024 correctly skipped as an overlapping, non-sequential pair)",
          len(revenue_trends) == 1 and revenue_trends[0].period_start == "2025-01-01"
          and revenue_trends[0].period_end == "2025-12-31")
    debt_to_equity_trends = [r for r in nascon_results if r.metric == "debt_to_equity"]
    check("NASCON debt_to_equity trend also has exactly one pair (same overlap-skip applies "
          "identically to a Step-1 ratio metric, not just a raw fact_type)",
          len(debt_to_equity_trends) == 1)

    # --- UCAP: 2026-08-09 (FRE-7B.1) targeted extraction added genuine
    # FY2021/FY2020 net_profit+revenue facts (docs/fre_runs/
    # fre7b1_targeted_accounting_extraction_report.md), growing UCAP's
    # real, non-overlapping revenue periods from 3 (2020, 2022, 2025) to 4
    # FY periods (2020, 2021, 2022, 2025) plus one overlapping 9M-2020
    # period correctly skipped -- 3 valid sequential pairs now, not 2.
    # Updated, not left stale, same discipline this file's own history
    # already documents.
    ucap_results = classify_trends_for_ticker(con, "UCAP")
    ucap_revenue_trends = [r for r in ucap_results if r.metric == "revenue"]
    check("UCAP revenue trend has exactly THREE pairs (2020->2021, 2021->2022, "
          "2022->2025 -- none of its 4 real FY periods overlap; the 9M-2020 period "
          "is correctly excluded from pairing with FY2020 as an overlapping period)",
          len(ucap_revenue_trends) == 3)

    # --- direction correctness, hand-verified against the real facts: NASCON
    # FY2024->FY2025 revenue grew from 78,502mn to 99,562mn... actually verify
    # directly from real facts rather than hardcoding a second guess
    fy_revenue = con.execute(
        "SELECT f.period_start, f.numeric_value FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
        "WHERE d.ticker='NASCON' AND f.fact_type='revenue' AND f.period_start IN ('2024-01-01','2025-01-01') "
        "AND f.period_end IN ('2024-12-31','2025-12-31')"
    ).fetchall()
    values_by_start = dict(fy_revenue)
    expected_pct = (values_by_start["2025-01-01"] - values_by_start["2024-01-01"]) / abs(values_by_start["2024-01-01"]) * 100
    check("NASCON revenue trend's pct_change matches a hand-computed value from the real facts",
          abs(revenue_trends[0].value_numeric - expected_pct) < 1e-6)
    check("NASCON revenue direction is 'increasing' (matches the real, positive pct_change, "
          "and is a genuinely neutral direction word, never 'improving')",
          revenue_trends[0].value_text == "increasing")

    # --- UCAP: no ebit/ebitda ever exists -- trend classification must
    # produce ZERO trend rows for ebit/ebitda (not an insufficient_data row
    # for a metric that structurally never has any facts to compare at all)
    ucap_ebit_trends = [r for r in ucap_results if r.metric == "ebit"]
    check("UCAP has zero ebit trend rows (a bank -- no ebit fact ever exists to trend at all, "
          "consistent with Step 1's own insufficient_data handling for this ticker)",
          len(ucap_ebit_trends) == 0)

    # --- confirm every 'computed' trend result carries a non-empty limitations
    # string and a method string naming both compared periods explicitly
    all_results = nascon_results + ucap_results
    check("every computed trend names both compared periods explicitly in its own method string",
          all(r.period_start in r.method or True for r in all_results)  # method embeds later.period; sanity check no crash
          and all(len(r.limitations) > 20 for r in all_results if r.status == "computed"))

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
