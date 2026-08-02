"""Standalone assertion-script tests for company_memory_360.py, validated
against real production data (read-only, no write path exists anywhere
in this module).

  PYTHONPATH=src python scripts/fre/test_company_memory_360.py
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import company_memory_360 as cm360  # noqa: E402
from ngxrot.fre.company_memory import build_company_memory  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402
from ngxrot.fre.pit_financial_memory import as_of as financial_as_of  # noqa: E402

ANCHOR_DOC_IDS = (4248, 6911, 10772, 6664, 8009, 9357, 4245, 6349, 7540,
                   4508, 5911, 10115, 8801, 9460, 10929)

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
    before_counts = snapshot_all_table_counts(con)

    # FSI Phase 16: derived dynamically (was a hardcoded 5-ticker list that
    # silently stopped covering the 5 tickers Phase 13 added) -- always the
    # real, current roster, so a future coverage-expansion phase is
    # automatically exercised here without a manual edit.
    tickers = list_tickers(con)
    test_dates = ["2020-01-01", "2022-06-01", "2024-07-31", "2026-08-01"]

    # --- output equivalence: CompanyMemory360 must exactly match calling
    # both underlying modules directly, for every ticker and every test date
    equivalence_ok = True
    for ticker in tickers:
        for as_of_date in test_dates:
            combined = cm360.as_of(con, ticker, as_of_date)
            direct_corporate = build_company_memory(con, ticker, as_of_date)
            direct_financial = financial_as_of(con, ticker, as_of_date)
            if combined.corporate != direct_corporate or combined.financial != direct_financial:
                equivalence_ok = False
    check(f"CompanyMemory360.as_of() is exactly equivalent to calling "
          f"build_company_memory() and pit_financial_memory.as_of() directly, "
          f"for all {len(tickers)} real tickers across 4 real/representative "
          f"as_of_dates ({len(tickers) * 4} combinations, 0 discrepancies)",
          equivalence_ok)

    # --- PIT leakage: reuse the 15 real anchor documents' own filing dates --
    # both the 'corporate' (filing_history) and 'financial' sub-results must
    # never include anything from a not-yet-public filing
    leakage_violations = []
    for doc_id in ANCHOR_DOC_IDS:
        ticker, filing_date = con.execute(
            "SELECT ticker, filing_date FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        day_before = (date.fromisoformat(filing_date) - timedelta(days=1)).isoformat()
        snapshot = cm360.as_of(con, ticker, day_before)
        for f in snapshot.corporate.filing_history:
            if f.filing_date > day_before:
                leakage_violations.append(
                    f"{ticker}/{day_before}: corporate.filing_history leaked doc_id={f.doc_id} "
                    f"filed {f.filing_date}"
                )
        for c in snapshot.financial.conclusions:
            for sf in c.source_facts:
                if sf.filing_date > day_before:
                    leakage_violations.append(
                        f"{ticker}/{day_before}: financial conclusion {c.conclusion_id} leaked "
                        f"fact from doc_id={sf.doc_id} filed {sf.filing_date}"
                    )
    check("PIT leakage test: 0 violations across all 15 real anchor filings' "
          "own 'day before' dates, in BOTH the corporate and financial "
          "sub-results", leakage_violations == [])

    # --- mechanical single-ticker-scope guardrail (same style as Phases 3-5) --
    public_funcs = [f for name, f in inspect.getmembers(cm360, inspect.isfunction)
                    if not name.startswith("_")]
    check("every public function in company_memory_360.py accepts at most "
          "ONE 'ticker'-named parameter",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))
    dataclass_field_names = set(cm360.CompanyMemory360.__dataclass_fields__.keys())
    check("CompanyMemory360's own dataclass fields are exactly {ticker, as_of_date, "
          "corporate, financial} -- no synthesized field (no score/rating/summary/"
          "recommendation of any kind)",
          dataclass_field_names == {"ticker", "as_of_date", "corporate", "financial"})

    con.close()

    # --- database immutability: all 29 tables' row counts unchanged, plus
    # integrity/FK checks, before and after this entire test run ---
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run "
          "(this module has no write path of any kind)", table_diffs == [])
    check("integrity_check reports 'ok' after this test run",
          con.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
    check("foreign_key_check reports clean after this test run",
          con.execute("PRAGMA foreign_key_check").fetchall() == [])
    con.close()

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
