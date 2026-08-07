"""FSI Phase 3, Step 1: deterministic financial metric calculations
(docs/fre_runs/fsi_phase3_preregistration.md Area 1).

Computes a small, fixed set of ratios from already-validated
`extracted_facts` (FSI Phase 1-2) -- no new fact_type, no new document, no
LLM call, no valuation output. Every ratio is computed only from a
numerator and denominator fact sharing the EXACT SAME (ticker, fact_type,
period_start, period_end) -- the same "equivalent reporting spans"
discipline the restatement-detection fix established (Phase 2 Entry 5):
a ratio computed across two different-length periods (e.g. a half-year
numerator over a full-year denominator) would be meaningless, not merely
imprecise.

Where a required input fact does not exist for a ticker/period, this is
recorded as an explicit `status='insufficient_data'` conclusion -- never
silently skipped, never substituted with a different period's value or a
sector-typical default (the same "no inferred financial facts" rule that
governed every FSI Phase 1-2 extraction script applies identically here).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ngxrot.fre.confidence_propagation import propagate_confidence_tier

RULE_VERSION = "ratios_v1"

CORP_ACTION_FACT_TYPES = ("dividend", "rights_issue", "bonus_issue")

# metric -> (numerator fact_type, denominator fact_type)
RATIO_DEFINITIONS: dict[str, tuple[str, str]] = {
    "debt_to_equity": ("liabilities", "equity"),
    "ebitda_margin": ("ebitda", "revenue"),
    "ebit_margin": ("ebit", "revenue"),
    "net_margin": ("net_profit", "revenue"),
    "cfo_to_net_profit": ("cfo", "net_profit"),
}


@dataclass
class RatioResult:
    ticker: str
    metric: str
    status: str  # 'computed' | 'insufficient_data'
    period_start: str
    period_end: str
    value_numeric: float | None
    confidence_tier: str | None
    method: str
    limitations: str
    input_fact_ids: list[tuple[int, str]] = field(default_factory=list)  # (fact_id, role)


def list_tickers(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT d.ticker FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE f.fact_type NOT IN (?,?,?) AND d.ticker IS NOT NULL ORDER BY d.ticker",
        CORP_ACTION_FACT_TYPES,
    ).fetchall()
    return [r[0] for r in rows]


def _periods_for_ticker(con: sqlite3.Connection, ticker: str) -> list[tuple[str, str]]:
    rows = con.execute(
        "SELECT DISTINCT f.period_start, f.period_end FROM extracted_facts f "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type NOT IN (?,?,?) "
        "AND f.period_start IS NOT NULL AND f.period_end IS NOT NULL "
        "ORDER BY f.period_end",
        (ticker, *CORP_ACTION_FACT_TYPES),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _fact_for(con: sqlite3.Connection, ticker: str, fact_type: str,
              period_start: str, period_end: str
              ) -> tuple[int, float, str | None, str | None] | None:
    """Returns (fact_id, numeric_value, confidence_tier, currency) for the
    unique fact matching ticker/fact_type/exact-period, or None if it
    doesn't exist. `currency` added MC-001 (2026-08-04,
    docs/MULTI_CURRENCY_FINANCIAL_ARCHITECTURE_REVIEW_2026-08-04.md
    Section 7 rule 2) -- every existing fact backfilled to 'NGN'; may be
    NULL only for a fact written before this column existed and never
    backfilled, which the same-currency guard below treats as unknown,
    not as a silent match."""
    rows = con.execute(
        "SELECT f.fact_id, f.numeric_value, f.confidence_tier, f.currency "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = ? AND f.period_start = ? AND f.period_end = ? "
        "AND f.numeric_value IS NOT NULL",
        (ticker, fact_type, period_start, period_end),
    ).fetchall()
    if not rows:
        return None
    # Multiple facts for the same exact ticker/fact_type/period would itself be
    # a real, disclosable finding (e.g. a genuine restatement of the SAME
    # period) -- not expected on this dataset (confirmed: 0 such cases as of
    # Phase 2), but never silently averaged if it occurred; the first (lowest
    # fact_id, i.e. earliest-written) is used and the ambiguity is not hidden.
    return rows[0]


def compute_ratios_for_ticker(con: sqlite3.Connection, ticker: str) -> list[RatioResult]:
    results: list[RatioResult] = []
    for period_start, period_end in _periods_for_ticker(con, ticker):
        for metric, (num_type, den_type) in RATIO_DEFINITIONS.items():
            method = f"{metric} = {num_type} / {den_type} (same ticker, exact reporting period)"
            numerator = _fact_for(con, ticker, num_type, period_start, period_end)
            denominator = _fact_for(con, ticker, den_type, period_start, period_end)
            input_fact_ids: list[tuple[int, str]] = []
            if numerator is not None:
                input_fact_ids.append((numerator[0], "numerator"))
            if denominator is not None:
                input_fact_ids.append((denominator[0], "denominator"))

            if numerator is None or denominator is None:
                missing = []
                if numerator is None:
                    missing.append(num_type)
                if denominator is None:
                    missing.append(den_type)
                results.append(RatioResult(
                    ticker=ticker, metric=metric, status="insufficient_data",
                    period_start=period_start, period_end=period_end,
                    value_numeric=None,
                    confidence_tier=None,  # insufficient_data never reports a confidence -- there is no value to be confident about
                    method=method,
                    limitations=f"Missing required fact_type(s) for this exact period: {', '.join(missing)}. "
                                 f"No substitute period or sector-typical value was used.",
                    input_fact_ids=input_fact_ids,
                ))
                continue

            num_id, num_value, num_tier, num_ccy = numerator
            den_id, den_value, den_tier, den_ccy = denominator

            # MC-001 (2026-08-04): same-currency guard. A single ticker's
            # own filing is always one currency, so this has never fired on
            # real data -- added as a defensive invariant now that a
            # foreign-currency reporter (AIRTELAFRI) exists on the
            # platform, per docs/MULTI_CURRENCY_FINANCIAL_ARCHITECTURE_
            # REVIEW_2026-08-04.md Section 7 rule 2. NULL currency (a fact
            # written before this column existed and never backfilled) is
            # treated as unknown, not as an implicit match.
            if num_ccy is None or den_ccy is None or num_ccy != den_ccy:
                results.append(RatioResult(
                    ticker=ticker, metric=metric, status="insufficient_data",
                    period_start=period_start, period_end=period_end,
                    value_numeric=None, confidence_tier=None, method=method,
                    limitations=(
                        f"Numerator ({num_type}, currency={num_ccy!r}) and denominator "
                        f"({den_type}, currency={den_ccy!r}) do not share a confirmed "
                        f"common currency -- ratio would be meaningless without an "
                        f"explicit conversion, which this module does not perform. "
                        f"Not computed."
                    ),
                    input_fact_ids=input_fact_ids,
                ))
                continue

            if den_value == 0:
                results.append(RatioResult(
                    ticker=ticker, metric=metric, status="insufficient_data",
                    period_start=period_start, period_end=period_end,
                    value_numeric=None, confidence_tier=None, method=method,
                    limitations=f"Denominator ({den_type}) is exactly zero for this period -- ratio is undefined.",
                    input_fact_ids=input_fact_ids,
                ))
                continue

            value = num_value / den_value
            tier = propagate_confidence_tier([num_tier, den_tier])
            limitations = (
                "Computed from a single reporting period; not independently cross-checked against "
                "a second source." + (
                    " At least one input fact predates the confidence_tier column and was never "
                    "backfilled (Phase 1 legacy fact) -- this conclusion's confidence floor is unknown, "
                    "not merely low." if tier is None else ""
                )
            )
            results.append(RatioResult(
                ticker=ticker, metric=metric, status="computed",
                period_start=period_start, period_end=period_end,
                value_numeric=value, confidence_tier=tier, method=method,
                limitations=limitations, input_fact_ids=input_fact_ids,
            ))
    return results


def write_ratio_results(con: sqlite3.Connection, results: list[RatioResult]) -> int:
    """Writes RatioResult rows to financial_reasoning_conclusions +
    financial_reasoning_conclusion_facts. Returns the number of conclusions written."""
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for r in results:
        cur = con.execute(
            "INSERT INTO financial_reasoning_conclusions "
            "(ticker, conclusion_type, metric, status, value_numeric, value_text, confidence_tier, "
            "method, limitations, rule_version, period_start, period_end, computed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.ticker, "ratio", r.metric, r.status, r.value_numeric, None, r.confidence_tier,
             r.method, r.limitations, RULE_VERSION, r.period_start, r.period_end, now),
        )
        conclusion_id = cur.lastrowid
        for fact_id, role in r.input_fact_ids:
            con.execute(
                "INSERT INTO financial_reasoning_conclusion_facts (conclusion_id, fact_id, role) "
                "VALUES (?,?,?)",
                (conclusion_id, fact_id, role),
            )
        written += 1
    return written
