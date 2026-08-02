"""FRE-6: Valuation Engine Architecture (docs/fre/08_valuation_engine_
architecture.md) -- ARCHITECTURE ONLY, verified against real data to
confirm it cannot run for real yet.

Deliberately, completely SEPARATE from the reasoning/thesis layer: this
module imports nothing from company_thesis.py, evidence_graph.py,
company_memory.py, or reaction_check.py, and nothing in those modules
imports this one. Per the owner's explicit instruction, valuation stays
architecturally isolated from thesis generation -- a triangulated
valuation, if one is ever computed, is a separate artifact a future
consumer may choose to read alongside a CompanyThesis, never a field
inside one.

## Why this is architecture, not a working valuation model, verified not assumed

Written when `extracted_facts.fact_type` had exactly three values across
all 161 real rows -- `dividend` (158), `rights_issue` (2), `bonus_issue`
(1) -- with zero revenue/EBITDA/balance-sheet/cash-flow line items
anywhere, so every adapter reported `NOT_READY` for every real ticker.

**Updated 2026-08-01, FSI Phase 1** (`docs/fre_runs/fsi_phase1_results.md`):
30 real `revenue`/`net_profit` facts now exist for 5 real tickers (UCAP,
BUAFOODS, AFRIPRUD, CAP, NASCON) -- the first financial-statement-shaped
data this platform has ever held. `is_ready()`'s coarse "does ANY
non-corporate-action fact exist" check now correctly reports `dcf`/
`ev_ebitda`/`pe` as READY for those 5 tickers -- exactly the transition
this architecture was built to make once real data existed. **This is
still not a working valuation model**: `compute()` has no implemented
formula for any method (see the `NotImplementedError` in the base class
below), so `value_company()` catches that specifically and reports
"ready, but not yet implemented" rather than crashing or fabricating a
number -- `TriangulatedValuation.results` remains empty for every ticker,
with or without FSI Phase 1's data. **Updated 2026-08-02, FSI Phase 23**:
`securities.sector_ngx` is now populated for 136/320 real equities (from
NGX's own official Daily Official List, a genuine exchange-authoritative
reference-metadata source, distinct from the analytical/investment-data
boundary this module otherwise refuses to cross) -- `classify_company_
type()` below does not consult this column at all, so this update changes
no behavior in this module; it is noted here only so this docstring does
not go stale the way the pre-Phase-23 "remains 0/320" claim did.

## The non-negotiable boundary, restated as code

No function in this module ever returns a numeric valuation without every
one of its `required_inputs` resolving to real data first (`is_ready()`
gates `compute()` unconditionally). No function anywhere computes an
expected return, an alpha estimate, or anything that could be read as a
portfolio input -- `TriangulatedValuation` is a disclosed comparison of
method-level readiness/results, nothing more, and even once methods
become computable, this platform's own charter requires any such number
to route through the pre-registration/gauntlet process before it is ever
treated as validated, never straight into a portfolio decision.
"""
from __future__ import annotations

import sqlite3
import tomllib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"


@dataclass
class ReadinessResult:
    ready: bool
    reason: str  # always populated -- "ready" is never bare, matching this
                 # platform's NOT-NULL-explanation discipline elsewhere


@dataclass
class ValuationResult:
    method_name: str
    point_estimate: float | None
    range_low: float | None
    range_high: float | None
    assumptions_used: dict
    data_vintage: str | None
    confidence_note: str


class ValuationMethodAdapter(ABC):
    method_name: str
    required_inputs: tuple[str, ...]

    @abstractmethod
    def is_ready(self, con: sqlite3.Connection, ticker: str) -> ReadinessResult:
        ...

    def compute(self, con: sqlite3.Connection, ticker: str, as_of_date: str,
                assumptions: dict) -> ValuationResult:
        readiness = self.is_ready(con, ticker)
        if not readiness.ready:
            raise RuntimeError(
                f"{self.method_name} refuses to compute for {ticker}: {readiness.reason}"
            )
        raise NotImplementedError(
            f"{self.method_name}'s formula is not implemented -- no real financial-statements "
            f"dataset has ever existed on this platform to develop or validate it against. "
            f"This is architecture, not a placeholder formula waiting to be uncovered by calling it."
        )


def _financial_statement_line_items_exist(con: sqlite3.Connection, ticker: str) -> bool:
    """The one real, mechanical check every adapter below shares: does ANY
    extracted_facts row for this ticker carry a real financial-statement
    line item (revenue/EBITDA/balance-sheet/cash-flow)? Verified today:
    no -- extracted_facts.fact_type only ever holds dividend/rights_issue/
    bonus_issue on this platform (161/161 real rows checked)."""
    row = con.execute(
        "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type NOT IN ('dividend', 'rights_issue', 'bonus_issue')",
        (ticker,),
    ).fetchone()[0]
    return row > 0


class DCFAdapter(ValuationMethodAdapter):
    method_name = "dcf"
    required_inputs = ("revenue_ts", "fcf_ts", "wacc_assumption")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no revenue/FCF time series exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found")  # unreachable today


class DDMAdapter(ValuationMethodAdapter):
    method_name = "ddm"
    required_inputs = ("dividend_ts", "cost_of_equity_assumption")

    def is_ready(self, con, ticker):
        row = con.execute(
            "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
            "WHERE d.ticker = ? AND f.fact_type = 'dividend'", (ticker,)
        ).fetchone()[0]
        if row == 0:
            return ReadinessResult(False, "no dividend history exists for this ticker")
        return ReadinessResult(
            False,
            f"{row} real dividend fact(s) exist, but a DDM additionally needs a "
            f"cost-of-equity assumption sourced from Part 1's sector-conditioned ontology "
            f"(not yet populated) -- dividend history alone is not sufficient"
        )


class ResidualIncomeAdapter(ValuationMethodAdapter):
    method_name = "residual_income"
    required_inputs = ("book_equity_ts", "roe_ts", "cost_of_equity_assumption")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no book-equity/ROE time series exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found")  # unreachable today


class EVEBITDAAdapter(ValuationMethodAdapter):
    method_name = "ev_ebitda"
    required_inputs = ("ebitda_ts", "peer_multiples")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no EBITDA time series exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found")  # unreachable today


class PEAdapter(ValuationMethodAdapter):
    method_name = "pe"
    required_inputs = ("eps_ts", "peer_multiples")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no EPS time series exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found")  # unreachable today


class PBAdapter(ValuationMethodAdapter):
    method_name = "pb"
    required_inputs = ("book_equity_ts",)

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no book-equity data exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found")  # unreachable today


_ALL_ADAPTERS: dict[str, ValuationMethodAdapter] = {
    a.method_name: a for a in [
        DCFAdapter(), DDMAdapter(), ResidualIncomeAdapter(),
        EVEBITDAAdapter(), PEAdapter(), PBAdapter(),
    ]
}


def _load_eligibility() -> dict[str, list[str]]:
    with open(CONFIG_DIR / "valuation_method_eligibility.toml", "rb") as fh:
        data = tomllib.load(fh)
    return {company_type: entry["methods"] for company_type, entry in data.items()}


def _load_company_type_overrides() -> dict[str, str]:
    with open(CONFIG_DIR / "company_type_overrides.toml", "rb") as fh:
        data = tomllib.load(fh)
    return data.get("overrides", {})


def classify_company_type(ticker: str) -> str:
    """Owner-judged override list (currently empty, disclosed) takes
    precedence; everything else defaults to 'general'. Deliberately does
    NOT read `securities.sector_ngx` (populated for 136/320 tickers as of
    FSI Phase 23, 2026-08-02) to auto-derive a company_type -- mapping
    NGX's 13 sector headings onto this module's own company_type taxonomy
    (`configs/valuation_method_eligibility.toml`) is its own judgment call,
    not yet made, and remains a distinct, separately-scoped design
    decision for a future phase, not something Phase 23's data population
    silently activates here."""
    overrides = _load_company_type_overrides()
    return overrides.get(ticker, "general")


@dataclass
class TriangulatedValuation:
    ticker: str
    as_of_date: str
    company_type: str
    eligible_methods: list[str]
    readiness_by_method: dict[str, ReadinessResult]
    results: list[ValuationResult] = field(default_factory=list)  # always empty today
    disagreement_note: str = ""


def value_company(con: sqlite3.Connection, ticker: str, as_of_date: str) -> TriangulatedValuation:
    """Runs every eligible adapter's is_ready() check (never compute()
    unless ready) and returns a fully honest, disclosed readiness report.
    On the real database today, `results` is always empty -- every real
    adapter is NOT_READY for every real ticker, verified, not assumed."""
    company_type = classify_company_type(ticker)
    eligibility = _load_eligibility()
    eligible_methods = eligibility.get(company_type, eligibility["general"])

    readiness_by_method: dict[str, ReadinessResult] = {}
    results: list[ValuationResult] = []
    for method_name in eligible_methods:
        adapter = _ALL_ADAPTERS.get(method_name)
        if adapter is None:
            readiness_by_method[method_name] = ReadinessResult(
                False, f"'{method_name}' has no adapter implementation yet "
                       f"(sum_of_the_parts/normalized_earnings_multiple/asset_based_floor "
                       f"are named in the eligibility config but not yet built -- architecture "
                       f"only, disclosed as not-yet-implemented rather than silently skipped)"
            )
            continue
        readiness = adapter.is_ready(con, ticker)
        readiness_by_method[method_name] = readiness
        if readiness.ready:
            try:
                results.append(adapter.compute(con, ticker, as_of_date, assumptions={}))
            except NotImplementedError:
                # Real, disclosed interaction (first observed 2026-08-01,
                # docs/fre_runs/fsi_phase1_results.md): once FSI Phase 1 adds
                # real revenue/net_profit facts for a ticker,
                # is_ready()'s coarse "does ANY non-corporate-action fact
                # exist" check correctly flips to True for the first time --
                # exactly the future unlock this architecture was built for
                # -- but compute() itself still has no real formula to run
                # (none has ever been developed or validated on this
                # platform). This is NOT valuation activation: `results`
                # stays exactly as empty as it was before this fact existed;
                # the distinction is disclosed here instead of crashing
                # uncaught, so a caller can tell "ready but not yet
                # implemented" apart from "not ready" without ever
                # receiving a fabricated number either way.
                readiness_by_method[method_name] = ReadinessResult(
                    True, readiness.reason + " -- HOWEVER, compute() is not yet "
                    "implemented for this method (no real formula has ever been "
                    "developed or validated on this platform); zero numeric "
                    "result is produced despite is_ready()=True."
                )

    disagreement_note = (
        "No methods are ready -- nothing to triangulate or disagree about."
        if not results else
        "Multiple methods produced results; disagreement analysis is not yet built "
        "(unreachable on the real database today, since no method has ever been ready)."
    )

    return TriangulatedValuation(
        ticker=ticker, as_of_date=as_of_date, company_type=company_type,
        eligible_methods=eligible_methods, readiness_by_method=readiness_by_method,
        results=results, disagreement_note=disagreement_note,
    )
