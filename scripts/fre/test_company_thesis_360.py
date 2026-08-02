"""Standalone assertion-script tests for company_thesis_360.py, validated
against real production data (read-only, zero write path anywhere in
this module).

  PYTHONPATH=src python scripts/fre/test_company_thesis_360.py
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre import company_memory_360 as cm360  # noqa: E402
from ngxrot.fre import company_thesis_360 as ct360  # noqa: E402
from ngxrot.fre.company_thesis import build_company_thesis  # noqa: E402
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


# Real, known-fired concern flags per ticker (confirmed via direct query
# against the frozen fsi-phase3-baseline-2026-08-01 data) -- used to prove
# CORRECT integration, not just "runs without crashing."
EXPECTED_FIRED_CONCERNS = {
    "NASCON": {"leverage_increasing"},
    "AFRIPRUD": {"margin_compression"},
    "UCAP": set(),
    "CAP": set(),
    "BUAFOODS": set(),
    # FSI Phase 13's 5 new tickers -- ground truth confirmed via direct
    # query of financial_reasoning_conclusions (added FSI Phase 16, which
    # extended this test's ticker coverage from 5 to all 10 real tickers).
    "MTNN": {"margin_compression"},
    "DANGCEM": set(),
    "UBN": set(),
    "OANDO": {"margin_compression"},
    "NESTLE": {"margin_compression"},
}


def main() -> int:
    con = ro()
    before_counts = snapshot_all_table_counts(con)

    # FSI Phase 16: dynamic ticker discovery (was a hardcoded 5-ticker list
    # that silently stopped covering Phase 13's 5 new tickers).
    tickers = list_tickers(con)
    latest_dates = {}
    for ticker in tickers:
        latest_dates[ticker] = con.execute(
            "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id "
            "WHERE d.ticker=?", (ticker,),
        ).fetchone()[0]

    snapshots = {t: ct360.as_of(con, t, latest_dates[t]) for t in tickers}

    # --- 1. Output equivalence: the 'thesis' sub-result must be exactly
    # equal to calling build_company_thesis() directly, for all 5 tickers,
    # regardless of whether FSI concern evidence exists for that ticker ---
    equivalence_ok = True
    for ticker in tickers:
        direct = build_company_thesis(con, ticker, latest_dates[ticker])
        if snapshots[ticker].thesis != direct:
            equivalence_ok = False
    zero_concern_count = sum(1 for t in tickers if not EXPECTED_FIRED_CONCERNS[t])
    check(f"CompanyThesis360's 'thesis' sub-result is exactly equivalent to "
          f"calling build_company_thesis() directly, for all {len(tickers)} "
          f"tickers -- true regardless of whether FSI concern evidence "
          f"exists for that ticker (proves the composition never alters "
          f"the underlying thesis, satisfying the 'output equivalence "
          f"where no FSI evidence exists' requirement by construction: "
          f"{zero_concern_count} of {len(tickers)} tickers here have zero "
          f"concern evidence and still match exactly)",
          equivalence_ok)

    memory_equivalence_ok = True
    for ticker in tickers:
        direct_memory = cm360.as_of(con, ticker, latest_dates[ticker])
        if snapshots[ticker].memory != direct_memory:
            memory_equivalence_ok = False
    check(f"CompanyThesis360's 'memory' sub-result is exactly equivalent to "
          f"calling company_memory_360.as_of() directly, for all "
          f"{len(tickers)} tickers", memory_equivalence_ok)

    # --- 2. Correct integration on all real tickers: concern evidence must
    # match the REAL, known-fired flags exactly, neither more nor fewer -----
    integration_ok = True
    for ticker in tickers:
        fired_metrics = {e.metric for e in snapshots[ticker].concern_evidence}
        if fired_metrics != EXPECTED_FIRED_CONCERNS[ticker]:
            integration_ok = False
            print(f"  MISMATCH for {ticker}: expected {EXPECTED_FIRED_CONCERNS[ticker]}, "
                  f"got {fired_metrics}")
    check(f"concern_evidence exactly matches the real, known-fired financial "
          f"health flags for all {len(tickers)} real tickers (NASCON: "
          f"leverage_increasing; AFRIPRUD/MTNN/OANDO/NESTLE: margin_"
          f"compression; UCAP/CAP/BUAFOODS/DANGCEM/UBN: none)",
          integration_ok)

    # --- 3. Completeness + non-overlap: every financial conclusion in the
    # memory snapshot appears in EXACTLY ONE of concern_evidence/
    # supplementary_evidence -- nothing dropped, nothing duplicated ---------
    partition_ok = True
    for ticker in tickers:
        snap = snapshots[ticker]
        all_ids = {c.conclusion_id for c in snap.memory.financial.conclusions}
        concern_ids = {e.conclusion_id for e in snap.concern_evidence}
        supplementary_ids = {e.conclusion_id for e in snap.supplementary_evidence}
        if concern_ids & supplementary_ids:
            partition_ok = False  # overlap
        if (concern_ids | supplementary_ids) != all_ids:
            partition_ok = False  # missing or extra
    check("every financial-reasoning conclusion is categorized into EXACTLY "
          "ONE of concern_evidence/supplementary_evidence -- no conclusion "
          "dropped, none duplicated, none double-counted",
          partition_ok)

    # --- 4. Trends are NEVER assigned to concern_evidence (the Entry 0
    # design refinement: no polarity judgment for trends) -------------------
    no_trend_in_concern = all(
        e.conclusion_type != "trend"
        for snap in snapshots.values() for e in snap.concern_evidence
    )
    check("concern_evidence NEVER contains a trend conclusion (trends are "
          "never assigned a bull/bear polarity in this module, per Entry 0's "
          "deliberate design refinement)", no_trend_in_concern)
    check("only fired flags (never ratios, never trends, never not-fired "
          "flags) ever appear in concern_evidence",
          all(e.conclusion_type == "flag" and e.value_text == "fired"
              for snap in snapshots.values() for e in snap.concern_evidence))

    # --- 5. No synthesized 'overall thesis strength' field anywhere ---------
    field_names = set(ct360.CompanyThesis360.__dataclass_fields__.keys())
    check("CompanyThesis360's own dataclass fields are exactly {ticker, "
          "as_of_date, thesis, memory, concern_evidence, supplementary_"
          "evidence} -- no strength/score/weight/rank/vote/balance field "
          "of any kind",
          field_names == {"ticker", "as_of_date", "thesis", "memory",
                           "concern_evidence", "supplementary_evidence"})
    evidence_field_names = set(ct360.FSIEvidenceItem.__dataclass_fields__.keys())
    check("FSIEvidenceItem carries no numeric weight/score field beyond the "
          "already-existing value_numeric/confidence_tier inherited verbatim "
          "from the source conclusion",
          not any(bad in name.lower() for name in evidence_field_names
                  for bad in ("weight", "score", "rank", "vote", "strength", "balance")))

    # --- 6. Every evidence item is individually auditable: references its
    # own conclusion_id and carries its own method/limitations verbatim -----
    auditable_ok = True
    for ticker in tickers:
        snap = snapshots[ticker]
        for item in snap.concern_evidence + snap.supplementary_evidence:
            source = next(c for c in snap.memory.financial.conclusions if c.conclusion_id == item.conclusion_id)
            if item.method != source.method or item.limitations != source.limitations \
               or item.confidence_tier != source.confidence_tier:
                auditable_ok = False
    check("every folded evidence item's method/limitations/confidence_tier "
          "match its source conclusion exactly (verbatim, not re-derived)",
          auditable_ok)

    # --- 7. Mechanical single-ticker-scope guardrail, same style as Phases 3-7
    public_funcs = [f for name, f in inspect.getmembers(ct360, inspect.isfunction)
                    if not name.startswith("_")]
    check("every public function in company_thesis_360.py accepts at most "
          "ONE 'ticker'-named parameter",
          all(len([p for p in inspect.signature(f).parameters if "ticker" in p.lower()]) <= 1
              for f in public_funcs))

    con.close()

    # --- database immutability -----------------------------------------------
    con = sqlite3.connect(db.DEFAULT_DB)
    after_counts = snapshot_all_table_counts(con)
    table_diffs = diff_table_counts(before_counts, after_counts)
    check("ALL tables' row counts unchanged after this entire test run "
          "(zero database writes)", table_diffs == [])
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
