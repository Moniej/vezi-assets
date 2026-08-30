"""FRE data-quality monitoring (2026-08-13, Investment OS end-to-end
build). Converts the failure classes discovered across the FRE scale-
validation program (magnitude anomalies, tabular unit conventions,
period mismatches, quarantine bypass) plus additional classes named in
this build assignment (duplicate/conflicting facts, entity mismatches,
PIT violations, evidence mismatches, coverage swings) into deterministic,
re-runnable checks.

REAL ENFORCEMENT, not just logging: `factor_eligible_tickers()` excludes
any ticker with an OPEN CRITICAL alert from factor-ready coverage --
a downstream consumer (the coverage matrix, a future paper-cycle ticker
selection) that calls this function instead of a raw "does this ticker
have any computed conclusion" check gets the enforcement automatically.
This is the same discipline as the quarantine-at-extraction-time fix
(numeric_consistency.py) applied at the coverage-measurement layer
instead of the extraction layer -- a second, independent backstop.

Read-only against extracted_facts/financial_reasoning_conclusions.
Writes ONLY to the new data_quality_alerts table -- never touches
extracted_facts, financial_reasoning_conclusions, or any Alpha Engine
table.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DataQualityAlert:
    check_name: str
    severity: str          # 'info' | 'warning' | 'critical'
    ticker: str | None
    fact_id: int | None
    message: str
    details: dict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Individual checks -- each pure, read-only, returns a list of alerts.
# ---------------------------------------------------------------------------

def check_magnitude_anomalies(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """10x/100x/1000x errors already caught at extraction time
    (numeric_consistency_check='flag') -- this check confirms none have
    slipped past into a COMPUTED conclusion (the quarantine-bypass check
    below is the general case; this one is specifically the magnitude
    failure mode, reported separately because it is the highest-severity,
    best-understood one -- see docs/alpha/AUTONOMOUS_FRE_PROGRESS_
    2026-08-13.md)."""
    if not _has_column(con, "numeric_consistency_check"):
        return []
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.numeric_consistency_check = 'flag'").fetchall()
    return [DataQualityAlert("magnitude_anomaly", "warning", ticker, fact_id,
                             f"fact {fact_id} flagged by numeric_consistency_check "
                             f"(round-factor magnitude mismatch) -- review before trusting",
                             {"fact_id": fact_id}) for fact_id, ticker in rows]


def check_tabular_unit_declarations(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """Table-header scale conventions (₦'000/million/billion) flagged or
    ambiguous -- the defect class found on ELLAHLAKES."""
    if not _has_column(con, "tabular_unit_check"):
        return []
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker, ef.tabular_unit_check FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.tabular_unit_check IN ('flag', 'ambiguous')").fetchall()
    return [DataQualityAlert("tabular_unit_declaration", "critical", ticker, fact_id,
                             f"fact {fact_id} tabular_unit_check={status} -- likely-unscaled "
                             f"or ambiguously-scaled table figure", {"fact_id": fact_id, "status": status})
           for fact_id, ticker, status in rows]


def check_period_mismatches(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """A flow fact with only one of period_start/period_end populated --
    structurally impossible via validate_period() going forward, but
    checked directly against real data rather than assumed impossible."""
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker, ef.fact_type FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.fact_type NOT IN ('assets','liabilities','equity') "
        "AND ((ef.period_start IS NULL) != (ef.period_end IS NULL))").fetchall()
    return [DataQualityAlert("period_mismatch", "critical", ticker, fact_id,
                             f"flow fact {fact_id} ({fact_type}) has only one of "
                             f"period_start/period_end populated", {"fact_id": fact_id})
           for fact_id, ticker, fact_type in rows]


def check_missing_periods(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """Facts with a numeric_value but no period at all -- not itself
    wrong (a genuinely period-unstated fact should have null periods per
    validate_period()), but worth surfacing as coverage information, not
    an error -- 'info' severity, never blocks anything."""
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.fact_type NOT IN ('assets','liabilities','equity') "
        "AND ef.numeric_value IS NOT NULL AND ef.period_end IS NULL").fetchall()
    return [DataQualityAlert("missing_period", "info", ticker, fact_id,
                             f"fact {fact_id} has a numeric value but no stated period -- "
                             f"correctly excluded from ratio/trend computation, not an error",
                             {"fact_id": fact_id}) for fact_id, ticker in rows]


def check_duplicate_facts(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """More than one fact for the EXACT SAME (ticker, fact_type,
    period_start, period_end) -- financial_ratios._fact_for() already
    silently picks the first (lowest fact_id) without erroring, per its
    own documented, deliberate policy -- this check surfaces the
    ambiguity that policy is quietly resolving, so it's visible."""
    rows = con.execute(
        "SELECT d.ticker, ef.fact_type, ef.period_start, ef.period_end, COUNT(*) n, "
        "GROUP_CONCAT(ef.fact_id) fact_ids "
        "FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.period_end IS NOT NULL AND ef.numeric_value IS NOT NULL "
        "GROUP BY d.ticker, ef.fact_type, ef.period_start, ef.period_end "
        "HAVING COUNT(*) > 1").fetchall()
    return [DataQualityAlert("duplicate_facts", "warning", ticker, None,
                             f"{ticker}/{fact_type} has {n} facts for the same period "
                             f"({period_start}..{period_end}) -- fact_ids={fact_ids}, "
                             f"the lowest is used, the rest are silently unused",
                             {"fact_ids": fact_ids, "fact_type": fact_type})
           for ticker, fact_type, period_start, period_end, n, fact_ids in rows]


def check_conflicting_facts(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """Same (ticker, fact_type, period) but genuinely DIFFERENT values
    (not just duplicated rows) -- a real restatement or a real extraction
    disagreement, either way worth a critical flag since financial_
    ratios.py has no restatement-aware resolution logic for this case."""
    rows = con.execute(
        "SELECT d.ticker, ef.fact_type, ef.period_start, ef.period_end, "
        "COUNT(DISTINCT ef.numeric_value) n_distinct, GROUP_CONCAT(DISTINCT ef.numeric_value) values_ "
        "FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.period_end IS NOT NULL AND ef.numeric_value IS NOT NULL "
        "GROUP BY d.ticker, ef.fact_type, ef.period_start, ef.period_end "
        "HAVING COUNT(DISTINCT ef.numeric_value) > 1").fetchall()
    return [DataQualityAlert("conflicting_facts", "critical", ticker, None,
                             f"{ticker}/{fact_type} has {n} DIFFERENT values for the same "
                             f"period ({period_start}..{period_end}): {values_}",
                             {"values": values_, "fact_type": fact_type})
           for ticker, fact_type, period_start, period_end, n, values_ in rows]


def check_entity_mismatches(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """A document's resolved ticker is NULL while its raw_symbol is
    populated -- entity resolution never completed for this document, so
    every fact on it is effectively invisible to any ticker-keyed query
    (list_tickers, compute_ratios_for_ticker, etc.) without anyone being
    told why."""
    rows = con.execute(
        "SELECT d.doc_id, d.raw_symbol, COUNT(ef.fact_id) n_facts "
        "FROM documents d JOIN extracted_facts ef ON ef.doc_id = d.doc_id "
        "WHERE d.ticker IS NULL AND d.raw_symbol IS NOT NULL "
        "GROUP BY d.doc_id, d.raw_symbol").fetchall()
    return [DataQualityAlert("entity_mismatch", "warning", None, None,
                             f"doc_id {doc_id} (raw_symbol={raw_symbol!r}) has {n_facts} "
                             f"extracted fact(s) but no resolved ticker -- invisible to "
                             f"every ticker-keyed query", {"doc_id": doc_id, "raw_symbol": raw_symbol})
           for doc_id, raw_symbol, n_facts in rows]


def check_pit_violations(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """A fact's period_end AFTER its own document's filing_date -- the
    document would be claiming knowledge of a period that hadn't ended
    yet as of its own filing (impossible for a real filing; a real,
    disclosed PIT integrity failure if found)."""
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker, ef.period_end, d.filing_date FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.period_end IS NOT NULL AND ef.period_end > d.filing_date").fetchall()
    return [DataQualityAlert("pit_violation", "critical", ticker, fact_id,
                             f"fact {fact_id} has period_end={period_end} AFTER its own "
                             f"document's filing_date={filing_date} -- impossible, a real "
                             f"PIT integrity defect if confirmed",
                             {"fact_id": fact_id, "period_end": period_end, "filing_date": filing_date})
           for fact_id, ticker, period_end, filing_date in rows]


def check_evidence_mismatches(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """grounding_check='failed' facts -- already forced to
    extraction_confidence=0.0 at write time (extract.py); this check
    confirms none have nonetheless fed a COMPUTED conclusion (the general
    quarantine-bypass check below covers this too, but grounding failures
    are reported by name since they're the platform's original, most-
    audited quality gate)."""
    rows = con.execute(
        "SELECT ef.fact_id, d.ticker FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "WHERE ef.grounding_check = 'failed'").fetchall()
    return [DataQualityAlert("evidence_mismatch", "warning", ticker, fact_id,
                             f"fact {fact_id} has grounding_check='failed' -- quoted evidence "
                             f"not found verbatim in source text", {"fact_id": fact_id})
           for fact_id, ticker in rows]


def check_quarantine_bypass(con: sqlite3.Connection) -> list[DataQualityAlert]:
    """THE audit-of-the-enforcement check: verifies no fact with
    numeric_consistency_check='flag' or tabular_unit_check IN
    ('flag','ambiguous') has nonetheless fed a COMPUTED conclusion via
    financial_reasoning_conclusion_facts -- i.e. that the quarantine
    fix built into financial_ratios._fact_for()/trend_classification.
    _base_fact_points() is actually holding on real data, not just in
    the unit tests. Any hit here is critical by construction -- it would
    mean the enforcement itself has a gap."""
    if not (_has_column(con, "numeric_consistency_check") and _has_column(con, "tabular_unit_check")):
        return []
    rows = con.execute(
        "SELECT DISTINCT ef.fact_id, d.ticker, ef.numeric_consistency_check, ef.tabular_unit_check "
        "FROM extracted_facts ef "
        "JOIN documents d ON d.doc_id = ef.doc_id "
        "JOIN financial_reasoning_conclusion_facts crf ON crf.fact_id = ef.fact_id "
        "JOIN financial_reasoning_conclusions c ON c.conclusion_id = crf.conclusion_id "
        "WHERE c.status = 'computed' "
        "AND (ef.numeric_consistency_check = 'flag' OR ef.tabular_unit_check IN ('flag','ambiguous'))"
    ).fetchall()
    return [DataQualityAlert("quarantine_bypass", "critical", ticker, fact_id,
                             f"fact {fact_id} is flagged (numeric={nc}, tabular={tc}) but "
                             f"FED A COMPUTED CONCLUSION ANYWAY -- the quarantine enforcement "
                             f"has a real gap, not a theoretical one", {"fact_id": fact_id})
           for fact_id, ticker, nc, tc in rows]


def check_coverage_swings(con: sqlite3.Connection, baseline_tickers: set[str] | None = None
                          ) -> list[DataQualityAlert]:
    """A ticker that previously had computed conclusions and now has
    none (or vice versa, a large unexplained jump) -- requires an
    external baseline snapshot since a single query has no "before" to
    compare against; caller supplies one (e.g. from the last report's
    recorded ticker set). Returns nothing (not a false 'no alerts') if
    no baseline is supplied -- this check is opt-in, not silently
    skipped without saying so."""
    if baseline_tickers is None:
        return []
    current = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM financial_reasoning_conclusions WHERE status='computed'").fetchall()}
    dropped = baseline_tickers - current
    return [DataQualityAlert("coverage_swing", "warning", ticker, None,
                             f"{ticker} had computed coverage in the baseline snapshot but "
                             f"has none now -- investigate before treating this as expected",
                             {"baseline_size": len(baseline_tickers), "current_size": len(current)})
           for ticker in sorted(dropped)]


def _has_column(con: sqlite3.Connection, column: str) -> bool:
    cols = {r[1] for r in con.execute("PRAGMA table_info(extracted_facts)").fetchall()}
    return column in cols


ALL_CHECKS = (
    check_magnitude_anomalies, check_tabular_unit_declarations, check_period_mismatches,
    check_missing_periods, check_duplicate_facts, check_conflicting_facts,
    check_entity_mismatches, check_pit_violations, check_evidence_mismatches,
    check_quarantine_bypass,
)


def run_all_checks(con: sqlite3.Connection, baseline_tickers: set[str] | None = None
                   ) -> list[DataQualityAlert]:
    alerts: list[DataQualityAlert] = []
    for check_fn in ALL_CHECKS:
        alerts.extend(check_fn(con))
    alerts.extend(check_coverage_swings(con, baseline_tickers))
    return alerts


def write_alerts(con: sqlite3.Connection, alerts: list[DataQualityAlert]) -> int:
    """Writes to data_quality_alerts ONLY -- never touches extracted_facts
    or financial_reasoning_conclusions. Idempotent-ish: does not dedupe
    against prior runs (each run is its own audit trail, same convention
    as `alerts`/`portfolio_alerts`), a caller wanting dedup should filter
    on (check_name, ticker, fact_id, status='open') before calling this."""
    import json
    now = _now()
    for a in alerts:
        con.execute(
            "INSERT INTO data_quality_alerts (alert_id, check_name, severity, ticker, fact_id, "
            "message, details_json, status, detected_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (f"DQ-{uuid.uuid4()}", a.check_name, a.severity, a.ticker, a.fact_id, a.message,
             json.dumps(a.details), "open", now))
    con.commit()
    return len(alerts)


def factor_eligible_tickers(con: sqlite3.Connection) -> list[str]:
    """THE enforcement point: every ticker with >=1 COMPUTED conclusion,
    EXCLUDING any ticker with an OPEN CRITICAL data_quality_alert. A
    caller building a coverage matrix or selecting tickers for a paper
    cycle should call THIS, not a raw query against financial_reasoning_
    conclusions, to get the enforcement automatically. Degrades
    gracefully (no exclusion) if data_quality_alerts doesn't exist yet
    on this database (an unmigrated/production database), matching the
    same backward-compatibility pattern as financial_ratios.py's own
    tabular_unit_check guard."""
    computed = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM financial_reasoning_conclusions WHERE status='computed'").fetchall()}
    has_table = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='data_quality_alerts'"
    ).fetchone() is not None
    if not has_table:
        return sorted(computed)
    flagged = {r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM data_quality_alerts WHERE severity='critical' AND status='open' "
        "AND ticker IS NOT NULL").fetchall()}
    return sorted(computed - flagged)
