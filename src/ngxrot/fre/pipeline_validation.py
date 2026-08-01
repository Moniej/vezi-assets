"""FSI Phase 5: Regression & Consistency Validation Harness
(docs/fre_runs/fsi_phase5_preregistration.md).

Read-only against production. Validates that the frozen FSI Phase 1-4
pipeline (`fsi-phase4-baseline-2026-08-01`) stays exactly reproducible
over time -- this module adds NO reasoning capability, NO new fact, NO
valuation, NO ranking, NO scoring: it is infrastructure ABOUT the
existing frozen phases, comparing them only against themselves (a
frozen golden snapshot, or a deliberately-corrupted scratch copy in the
test suite) -- never against a new external ground truth.

Three components, per the pre-registration:
  1. Golden-snapshot reproducibility (`compute_live_snapshot`,
     `compare_snapshots`).
  2. Cross-phase consistency (`verify_cross_phase_consistency`).
  3. Database immutability verification (`snapshot_all_table_counts`,
     `diff_table_counts`) -- the owner's additional requirement.

Historical defect-injection tests (the third pre-registered component)
live in `scripts/fre/test_historical_defect_detection.py`, not here,
since they deliberately construct BROKEN logic for testing purposes --
this module must never contain a broken code path, even for illustration.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from ngxrot.fre.pit_financial_memory import as_of

# ---------------------------------------------------------------------------
# 1. Golden-snapshot reproducibility
# ---------------------------------------------------------------------------

FACT_TYPES_ORDER = (
    "revenue", "net_profit", "assets", "liabilities", "equity",
    "cfo", "cfi", "cff", "capex", "fcf", "ebit", "ebitda",
)
CORP_ACTION_FACT_TYPES = ("dividend", "rights_issue", "bonus_issue")


def compute_live_snapshot(con: sqlite3.Connection) -> dict:
    """A canonical, deterministically-ordered dict of everything Phase 5
    checks for byte-level reproducibility. Every list is sorted so two
    calls against unchanged data are guaranteed identical regardless of
    SQLite's own row-return order."""
    fact_type_counts = dict(con.execute(
        "SELECT fact_type, COUNT(*) FROM extracted_facts "
        "WHERE fact_type NOT IN (?,?,?) GROUP BY fact_type",
        CORP_ACTION_FACT_TYPES,
    ).fetchall())
    total_financial_facts = sum(fact_type_counts.values())

    conclusion_type_counts = dict(con.execute(
        "SELECT conclusion_type, COUNT(*) FROM financial_reasoning_conclusions "
        "GROUP BY conclusion_type"
    ).fetchall())
    total_conclusions = sum(conclusion_type_counts.values())

    conclusions = con.execute(
        "SELECT conclusion_id, ticker, conclusion_type, metric, status, value_numeric, "
        "value_text, confidence_tier, period_start, period_end "
        "FROM financial_reasoning_conclusions ORDER BY conclusion_id"
    ).fetchall()
    conclusion_rows = [
        {
            "conclusion_id": r[0], "ticker": r[1], "conclusion_type": r[2], "metric": r[3],
            "status": r[4], "value_numeric": r[5], "value_text": r[6],
            "confidence_tier": r[7], "period_start": r[8], "period_end": r[9],
        }
        for r in conclusions
    ]

    return {
        "extracted_facts_total_financial": total_financial_facts,
        "extracted_facts_by_type": dict(sorted(fact_type_counts.items())),
        "conclusions_total": total_conclusions,
        "conclusions_by_type": dict(sorted(conclusion_type_counts.items())),
        "conclusions": conclusion_rows,
    }


def compare_snapshots(golden: dict, live: dict) -> list[str]:
    """Returns a list of human-readable diffs; empty = byte-identical
    (once both are canonically ordered, a plain `==` on the two dicts is
    already a byte-level comparison -- this function exists to produce
    a readable diff, not a looser check)."""
    if golden == live:
        return []
    diffs = []
    for key in ("extracted_facts_total_financial", "conclusions_total",
                "extracted_facts_by_type", "conclusions_by_type"):
        if golden.get(key) != live.get(key):
            diffs.append(f"{key}: golden={golden.get(key)!r} != live={live.get(key)!r}")
    golden_by_id = {c["conclusion_id"]: c for c in golden.get("conclusions", [])}
    live_by_id = {c["conclusion_id"]: c for c in live.get("conclusions", [])}
    for cid in sorted(set(golden_by_id) | set(live_by_id)):
        if golden_by_id.get(cid) != live_by_id.get(cid):
            diffs.append(f"conclusion_id={cid}: golden={golden_by_id.get(cid)!r} "
                         f"!= live={live_by_id.get(cid)!r}")
    return diffs


# ---------------------------------------------------------------------------
# 2. Cross-phase consistency (Phase 3 <-> Phase 4)
# ---------------------------------------------------------------------------

def _tickers(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM financial_reasoning_conclusions ORDER BY ticker"
    ).fetchall()]


def _latest_filing_for_ticker(con: sqlite3.Connection, ticker: str) -> str:
    row = con.execute(
        "SELECT MAX(d.filing_date) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ?",
        (ticker,),
    ).fetchone()
    return row[0]


def verify_cross_phase_consistency(con: sqlite3.Connection) -> list[str]:
    """Returns a list of violation descriptions (empty = consistent):

    (a) full knowability: as_of(ticker, ticker's own latest real filing
        date) must return EXACTLY Phase 3's full, unfiltered conclusion
        set for that ticker -- nothing withheld once everything a ticker
        has ever filed is public.
    (b) monotonicity: the knowable set at a LATER as_of_date must be a
        SUPERSET of the knowable set at an EARLIER as_of_date, for every
        real filing-date boundary -- once a conclusion becomes knowable
        it must never become "unknowable" again, confirming PIT cutoff
        behavior preserves valid historical conclusions rather than
        silently dropping them as later dates are queried.
    """
    violations: list[str] = []
    for ticker in _tickers(con):
        full_set = set(r[0] for r in con.execute(
            "SELECT conclusion_id FROM financial_reasoning_conclusions WHERE ticker = ?",
            (ticker,),
        ).fetchall())
        latest_filing = _latest_filing_for_ticker(con, ticker)
        snapshot_at_latest = as_of(con, ticker, latest_filing)
        knowable_at_latest = set(c.conclusion_id for c in snapshot_at_latest.conclusions)
        if knowable_at_latest != full_set:
            missing = full_set - knowable_at_latest
            extra = knowable_at_latest - full_set
            violations.append(
                f"{ticker}: as_of(latest_filing={latest_filing}) does not match the full "
                f"conclusion set -- missing={sorted(missing)}, unexpected_extra={sorted(extra)}"
            )

        # monotonicity across each real filing_date boundary for this ticker
        filing_dates = sorted(r[0] for r in con.execute(
            "SELECT DISTINCT d.filing_date FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
            "WHERE d.ticker = ?", (ticker,),
        ).fetchall())
        prior_knowable: set[int] = set()
        for filing_date in filing_dates:
            current_knowable = set(c.conclusion_id for c in as_of(con, ticker, filing_date).conclusions)
            if not prior_knowable.issubset(current_knowable):
                lost = prior_knowable - current_knowable
                violations.append(
                    f"{ticker}: monotonicity violated at as_of={filing_date} -- "
                    f"conclusion_ids {sorted(lost)} were knowable at an earlier date and are "
                    f"no longer knowable now (a PIT cutoff must never make a previously-valid "
                    f"historical conclusion disappear)"
                )
            prior_knowable = current_knowable
    return violations


# ---------------------------------------------------------------------------
# 3. Database immutability verification
# ---------------------------------------------------------------------------

def snapshot_all_table_counts(con: sqlite3.Connection) -> dict[str, int]:
    """Row count for every real table in the database -- used to prove a
    validation run touches nothing, across ALL 29 tables, not just the
    ones this phase's own logic happens to read."""
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def diff_table_counts(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Returns a list of table names whose row count changed (empty =
    fully immutable)."""
    all_tables = sorted(set(before) | set(after))
    return [t for t in all_tables if before.get(t) != after.get(t)]
