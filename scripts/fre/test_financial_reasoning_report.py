"""Standalone assertion-script tests for financial_reasoning_report.py,
validated against real production data (read-only, zero write path
anywhere in this module).

  PYTHONPATH=src python scripts/fre/test_financial_reasoning_report.py
"""
from __future__ import annotations

import inspect
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import company_memory_360 as cm360  # noqa: E402
from ngxrot.fre import financial_reasoning_report as report_mod  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402
from ngxrot.fre.pipeline_validation import snapshot_all_table_counts, diff_table_counts  # noqa: E402

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

    # FSI Phase 16: dynamic ticker discovery (was a hardcoded 5-ticker list
    # that silently stopped covering Phase 13's 5 new tickers).
    tickers = list_tickers(con)

    # --- 1. Renders without exception for all real tickers at their own
    # latest real filing date, and never crashes -----------------------------
    snapshots = {}
    reports = {}
    render_ok = True
    for ticker in tickers:
        latest = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]
        try:
            snap = cm360.as_of(con, ticker, latest)
            rpt = report_mod.render_report(snap)
            snapshots[ticker] = snap
            reports[ticker] = rpt
        except Exception as e:  # noqa: BLE001
            print(f"  EXCEPTION for {ticker}: {e}")
            render_ok = False
    check(f"renders without exception for all {len(tickers)} real tickers at "
          f"their own latest real filing date", render_ok)

    # --- 2. Determinism: identical input -> byte-identical output ----------
    ticker, snap = "NASCON", snapshots["NASCON"]
    rendered_twice = [report_mod.render_report(snap) for _ in range(3)]
    check("render_report() produces byte-identical output across 3 calls "
          "on the SAME snapshot object (pure function, no hidden state)",
          rendered_twice[0] == rendered_twice[1] == rendered_twice[2])

    fresh_snap_1 = cm360.as_of(con, "NASCON", "2026-03-03")
    fresh_snap_2 = cm360.as_of(con, "NASCON", "2026-03-03")
    check("render_report() produces byte-identical output for two INDEPENDENTLY "
          "built snapshots of the same (ticker, as_of_date) -- full pipeline "
          "determinism, not just the renderer in isolation",
          report_mod.render_report(fresh_snap_1) == report_mod.render_report(fresh_snap_2))

    # --- 3. NULL confidence tier is rendered explicitly, never silently
    # omitted or presented as a real tier ------------------------------------
    null_tier_present_somewhere = any(
        report_mod._NULL_CONFIDENCE_LABEL in rpt for rpt in reports.values()
    )
    check("the explicit 'confidence tier NOT RECORDED' phrase appears in at "
          "least one real report (Phase 1's legacy revenue/net_profit facts "
          "have NULL confidence_tier and must never be silently upgraded)",
          null_tier_present_somewhere)

    # --- 4. insufficient_data conclusions are never hidden ------------------
    for ticker, snap in snapshots.items():
        insufficient_in_snapshot = sum(1 for c in snap.financial.conclusions if c.status == "insufficient_data")
        insufficient_in_report = reports[ticker].count("- Status: insufficient_data")
        if insufficient_in_snapshot != insufficient_in_report:
            check(f"{ticker}: every insufficient_data conclusion in the snapshot "
                  f"appears in the rendered report ({insufficient_in_snapshot} in "
                  f"snapshot vs {insufficient_in_report} in report)", False)
            break
    else:
        check("every insufficient_data conclusion in each snapshot appears "
              "exactly once in its own rendered report (never hidden)", True)

    # --- 5. Sentence-to-field traceability: sample one conclusion of each
    # confidence tier + both statuses, confirm its exact stored values appear
    # verbatim in the rendered text ------------------------------------------
    sample_ok = True
    for ticker, snap in snapshots.items():
        rpt = reports[ticker]
        for c in snap.financial.conclusions:
            if c.method not in rpt or c.limitations not in rpt:
                sample_ok = False
                print(f"  MISMATCH: {ticker} conclusion_id={c.conclusion_id} "
                      f"method/limitations not found verbatim in report")
    check("every conclusion's own 'method' and 'limitations' text appears "
          "VERBATIM in its ticker's rendered report (sentence-to-field "
          "traceability, not just presence of some placeholder text)",
          sample_ok)

    # --- 6. Field coverage: every populated field across all 5 real
    # snapshots appears somewhere in the corresponding rendered report -------
    coverage_ok = True
    for ticker, snap in snapshots.items():
        rpt = reports[ticker]
        for fact_id_container in (snap.corporate.dividend_history, snap.corporate.corporate_action_history):
            for f in fact_id_container:
                if str(f.fact_id) not in rpt:
                    coverage_ok = False
        for f in snap.corporate.filing_history:
            if str(f.doc_id) not in rpt:
                coverage_ok = False
        for c in snap.financial.conclusions:
            if str(c.conclusion_id) not in rpt and not c.source_facts:
                pass  # conclusion_id itself isn't rendered by design; checked via method/limitations above
    check("every real filing (doc_id) and every real dividend/corporate-action "
          "fact (fact_id) in each snapshot appears in its own rendered report",
          coverage_ok)

    # --- 7. Ordering discipline: financial conclusions are alphabetical by
    # metric then chronological by period_end -- never by value/status -----
    ratios = [c for c in snapshots["NASCON"].financial.conclusions if c.conclusion_type == "ratio"]
    sorted_ratios = report_mod._sorted_conclusions(ratios)
    check("_sorted_conclusions() orders strictly by (metric, period_end) -- "
          "a neutral, disclosed, non-importance-based order",
          [(c.metric, c.period_end) for c in sorted_ratios] ==
          sorted([(c.metric, c.period_end) for c in ratios]))

    # --- 8. Mechanical single-ticker-scope guardrail (same style as Phases 3-6)
    public_funcs = [f for name, f in inspect.getmembers(report_mod, inspect.isfunction)
                    if not name.startswith("_")]
    check("every public function in financial_reasoning_report.py accepts at "
          "most ONE 'ticker'-named parameter (none accept 'tickers' plural "
          "or a list)",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))

    # --- 9. No forbidden vocabulary: the report must never contain a
    # ranking/scoring/recommendation word OUTSIDE the fixed disclaimer
    # paragraph itself (which legitimately NAMES these excluded categories
    # to state what the report does NOT do -- that disclaimer sentence is
    # excluded from the scan, everything else is not) ------------------------
    forbidden_terms = ("buy", "sell", "recommend", "target price", "expected return",
                       "undervalued", "overvalued")
    # "rank"/"score"/"rating" are checked as whole words, since "rank" and
    # "score" are also substrings of legitimate report vocabulary the
    # disclaimer itself uses ("ranking", "health score") and "rating" is a
    # substring of the real financial term "Operating Profit" -- a
    # substring match would produce false positives on the module's own
    # required disclaimer text and on real, approved financial terminology.
    forbidden_whole_words = ("rank", "score", "rating")
    forbidden_found = []
    for ticker, rpt in reports.items():
        body = rpt
        # exclude the one known disclaimer sentence, then scan the rest
        disclaimer_start = body.find("*This is a deterministic")
        disclaimer_end = body.find("*", disclaimer_start + 1) + 1 if disclaimer_start != -1 else -1
        scanned = body[:disclaimer_start] + body[disclaimer_end:] if disclaimer_start != -1 else body
        lower_scanned = scanned.lower()
        for term in forbidden_terms:
            if term in lower_scanned:
                forbidden_found.append((ticker, term))
        for word in forbidden_whole_words:
            if re.search(rf"\b{word}\w*\b", lower_scanned):
                forbidden_found.append((ticker, word))
    check(f"no forbidden ranking/scoring/recommendation vocabulary appears "
          f"anywhere in the {len(tickers)} real rendered reports OUTSIDE the "
          f"module's own fixed disclaimer sentence (which legitimately names "
          f"these excluded categories)", forbidden_found == [])

    con.close()

    # --- database immutability -----------------------------------------------
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run "
          "(this module has zero write path)", table_diffs == [])
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
