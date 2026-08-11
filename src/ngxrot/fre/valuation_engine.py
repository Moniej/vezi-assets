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
boundary this module otherwise refuses to cross). **Updated 2026-08-02,
FSI Phase 26**: `classify_company_type()` now DOES consult `sector_ngx`
(via `sector_company_type_mapping.derive_company_type_for_ticker()`) as a
new middle precedence tier, between the owner-override config (still
highest) and the `"general"` default (still the final fallback) -- a
deterministic translation, never inference, and confirmed to change zero
readiness/valuation output for any of the 10 real FSI tickers (none
resolve to `"bank"`/`"insurance"` under the new mapping; see Phase 26's
own pre-registration for the real-data check). `compute()` itself is
untouched and still unconditionally refuses on every adapter -- this
remains architecture, not activation.

**Updated 2026-08-09, FRE-7 (owner-authorized activation)**: real
`compute()` formulas now exist for `pb`, `pe`, and `dcf` -- the three
methods real data can genuinely support, verified by direct inspection
before any formula was written (not assumed). `ev_ebitda` stays
permanently `NOT_READY` for every ticker: Enterprise Value needs
`total_debt`/`cash_and_equivalents`, and no such `fact_type` has ever been
extracted on this platform (checked directly against the full known
`fact_type` list) -- fabricating a debt/cash proxy was explicitly
forbidden by the owner's authorization, so this stays a disclosed,
permanent data gap, not a workaround. `ddm`/`residual_income` are
untouched -- still correctly gated on the missing cost-of-equity ontology.
Every new formula still passes through `is_ready()` first, still refuses
to guess a missing input (returns a `ValuationResult` with
`point_estimate=None` and a named reason instead), still requires the
caller to supply `dcf`'s `wacc`/`terminal_growth` explicitly (never
defaulted), and still applies the accounting core's own currency-exact
and PIT-filing-date disciplines (re-implemented locally in this module,
since `financial_ratios.py`/`pit_financial_memory.py` were not modified
-- see `docs/fre_runs/fre7_valuation_activation_report.md` for the full
data-availability audit and test results).

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

import pandas as pd

from ngxrot.fre.financial_ratios import list_tickers
from ngxrot.fre.period_normalization import classify_period_type
from ngxrot.fre.sector_company_type_mapping import derive_company_type_for_ticker

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"
MARKET_CAP_PANEL_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "market_cap_panel.csv"

# fact_type sets used to assemble a normalized statement (FRE-7). "Flow"
# items cover a reporting SPAN (need an exact FY period match, same
# discipline as financial_ratios.py); "stock" items are a snapshot as of
# a single date (period_start is often legitimately NULL for these --
# a balance sheet is "as of" one day, not a flow over a range).
FLOW_FACT_TYPES = ("revenue", "gross_profit", "cogs", "ebit", "ebitda", "net_profit",
                    "cfo", "cfi", "cff", "capex", "fcf")
STOCK_FACT_TYPES = ("assets", "liabilities", "equity")


@dataclass
class ReadinessResult:
    ready: bool
    reason: str  # always populated -- "ready" is never bare, matching this
                 # platform's NOT-NULL-explanation discipline elsewhere


@dataclass
class ValuationResult:
    method_name: str
    point_estimate: float | None  # None IS the DATA_GAP/UNKNOWN state -- never a guessed number
    range_low: float | None
    range_high: float | None
    assumptions_used: dict
    data_vintage: str | None
    confidence_note: str
    # FRE-7 additions (additive, backward compatible -- all default to empty):
    input_fact_ids: list[tuple[int, str]] = field(default_factory=list)  # (fact_id, role) -- full provenance
    peers_used: list[str] = field(default_factory=list)
    scenario_estimates: dict[str, float] = field(default_factory=dict)  # e.g. {'bear':..,'base':..,'bull':..}


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


@dataclass
class LineItem:
    fact_type: str
    status: str  # 'known' | 'DATA_GAP'
    value: float | None
    fact_id: int | None
    period_start: str | None
    period_end: str | None
    period_type: str | None
    currency: str | None
    confidence_tier: str | None
    filing_date: str | None


@dataclass
class NormalizedStatement:
    ticker: str
    as_of_date: str
    fy_period_end: str | None  # None if no FY period is knowable as of this date
    line_items: dict[str, LineItem]


def _latest_fy_period(con: sqlite3.Connection, ticker: str, as_of_date: str
                       ) -> tuple[str, str] | None:
    """Most recent (period_start, period_end) pair classified as 'FY' by
    period_normalization.classify_period_type() -- from actual calendar
    span, never a filing's own headline -- among facts knowable (filing
    date <= as_of_date, same PIT discipline as pit_financial_memory.py,
    re-implemented here rather than imported since that module's own
    public surface is conclusion-level, not fact-level)."""
    rows = con.execute(
        "SELECT DISTINCT f.period_start, f.period_end FROM extracted_facts f "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.period_start IS NOT NULL AND f.period_end IS NOT NULL "
        "AND d.filing_date <= ?",
        (ticker, as_of_date),
    ).fetchall()
    fy_periods = [(ps, pe) for ps, pe in rows if classify_period_type(ps, pe) == "FY"]
    if not fy_periods:
        return None
    return max(fy_periods, key=lambda p: p[1])


def _fact_for_exact_period(con: sqlite3.Connection, ticker: str, fact_type: str,
                            period_start: str, period_end: str, as_of_date: str
                            ) -> tuple[int, float, str | None, str | None, str] | None:
    """(fact_id, numeric_value, confidence_tier, currency, filing_date) for
    the unique ticker/fact_type/exact-period fact knowable as of
    as_of_date, or None. Mirrors financial_ratios._fact_for()'s exact-period
    discipline (same reason: mixing a half-year figure with a full-year
    figure is meaningless, not merely imprecise) plus a PIT filing-date
    gate financial_ratios.py itself does not need (it has no as_of concept).
    Re-implemented locally rather than importing the private helper --
    the accounting core's internals stay untouched."""
    rows = con.execute(
        "SELECT f.fact_id, f.numeric_value, f.confidence_tier, f.currency, d.filing_date "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = ? AND f.period_start = ? AND f.period_end = ? "
        "AND f.numeric_value IS NOT NULL AND d.filing_date <= ? ORDER BY f.fact_id",
        (ticker, fact_type, period_start, period_end, as_of_date),
    ).fetchall()
    return rows[0] if rows else None


def _latest_stock_fact(con: sqlite3.Connection, ticker: str, fact_type: str, as_of_date: str
                        ) -> tuple[int, float, str | None, str | None, str, str] | None:
    """(fact_id, numeric_value, confidence_tier, currency, period_end,
    filing_date) for the most recent knowable snapshot fact (assets/
    liabilities/equity) -- period_start is NOT required (a balance-sheet
    line item is as-of one date, not a flow over a range)."""
    row = con.execute(
        "SELECT f.fact_id, f.numeric_value, f.confidence_tier, f.currency, f.period_end, d.filing_date "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = ? AND f.numeric_value IS NOT NULL "
        "AND f.period_end IS NOT NULL AND d.filing_date <= ? "
        "ORDER BY f.period_end DESC, f.fact_id ASC LIMIT 1",
        (ticker, fact_type, as_of_date),
    ).fetchone()
    return row


def get_normalized_statement(con: sqlite3.Connection, ticker: str, as_of_date: str
                              ) -> NormalizedStatement:
    """FRE-7 deliverable: a normalized financial-statement snapshot,
    knowable as of as_of_date. Flow items (revenue/net_profit/etc.) are
    pinned to the single most recent knowable FY period (exact-period
    match, never mixed with an interim figure); stock items (assets/
    liabilities/equity) use the most recent knowable snapshot independent
    of that FY period. Every line item is either 'known' with a real
    fact_id, or an explicit 'DATA_GAP' -- never inferred or defaulted."""
    fy = _latest_fy_period(con, ticker, as_of_date)
    line_items: dict[str, LineItem] = {}
    for ft in FLOW_FACT_TYPES:
        if fy is None:
            line_items[ft] = LineItem(ft, "DATA_GAP", None, None, None, None, None, None, None, None)
            continue
        f = _fact_for_exact_period(con, ticker, ft, fy[0], fy[1], as_of_date)
        if f is None:
            line_items[ft] = LineItem(ft, "DATA_GAP", None, None, fy[0], fy[1], "FY", None, None, None)
        else:
            fact_id, value, tier, ccy, filing_date = f
            line_items[ft] = LineItem(ft, "known", value, fact_id, fy[0], fy[1], "FY", ccy, tier, filing_date)
    for ft in STOCK_FACT_TYPES:
        s = _latest_stock_fact(con, ticker, ft, as_of_date)
        if s is None:
            line_items[ft] = LineItem(ft, "DATA_GAP", None, None, None, None, None, None, None, None)
        else:
            fact_id, value, tier, ccy, period_end, filing_date = s
            line_items[ft] = LineItem(ft, "known", value, fact_id, None, period_end, None, ccy, tier, filing_date)
    return NormalizedStatement(ticker=ticker, as_of_date=as_of_date,
                                fy_period_end=fy[1] if fy else None, line_items=line_items)


_market_cap_panel_cache: pd.DataFrame | None = None


def _load_market_cap_panel() -> pd.DataFrame:
    global _market_cap_panel_cache
    if _market_cap_panel_cache is None:
        df = pd.read_csv(MARKET_CAP_PANEL_PATH, parse_dates=["trade_date"])
        _market_cap_panel_cache = df
    return _market_cap_panel_cache


def _shares_outstanding_millions(ticker: str, as_of_date: str) -> tuple[float, str] | None:
    """(implied_shares_m, panel_row_date) as of the latest panel row on or
    before as_of_date, from data/reference/market_cap_panel.csv -- the
    platform's existing, previously-validated shares-outstanding proxy
    (no direct 'shares_outstanding' fact_type exists in extracted_facts).
    Read-only; this file is never written to by this module."""
    df = _load_market_cap_panel()
    sub = df[(df["symbol"] == ticker) & (df["trade_date"] <= pd.Timestamp(as_of_date))]
    if sub.empty:
        return None
    row = sub.sort_values("trade_date").iloc[-1]
    shares = row["implied_shares_m"]
    if pd.isna(shares) or shares <= 0:
        return None
    return float(shares), str(row["trade_date"].date())


def _latest_price(con: sqlite3.Connection, ticker: str, as_of_date: str) -> tuple[str, float] | None:
    """(trade_date, close) as of the latest equity_prices row on or before
    as_of_date. equity_prices has no currency column -- every NGX-traded
    close is implicitly NGN (confirmed: fx_rates has 0 rows platform-wide,
    so no other currency could ever have been converted into this table)."""
    row = con.execute(
        "SELECT trade_date, close FROM equity_prices WHERE ticker = ? AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1", (ticker, as_of_date),
    ).fetchone()
    return row


def _peer_tickers(con: sqlite3.Connection, ticker: str, company_type: str) -> list[str]:
    """Every other real, fact-bearing ticker (financial_ratios.list_tickers())
    that resolves to the same company_type -- the only peer-grouping axis
    this platform's existing architecture provides (classify_company_type()).
    A coarser proxy for 'comparable company' than sector-level matching
    would be, disclosed as such in every result that uses it."""
    return [t for t in list_tickers(con) if t != ticker and classify_company_type(con, t) == company_type]


def _usable_fcf_fact(con: sqlite3.Connection, ticker: str, as_of_date: str
                      ) -> tuple[int, float, str | None, str | None, str, str] | None:
    """(fact_id, value, tier, currency, period_end, filing_date) for the
    most recent knowable, currency-clean (NGN only) direct 'fcf' fact.
    Confirmed by direct query (2026-08-09): zero tickers, ever, have both
    a cfo and a capex fact sharing the exact same period -- so a CFO-minus-
    CapEx derivation yields nothing on real data today and is not
    attempted; only the 3 direct 'fcf' facts platform-wide (CAP, GEREGU,
    AIRTELAFRI) are candidates, and this function still applies the
    currency guard per-call (AIRTELAFRI's is USD -- excluded, since
    fx_rates has 0 rows and no conversion is possible without fabricating
    a rate)."""
    row = con.execute(
        "SELECT f.fact_id, f.numeric_value, f.confidence_tier, f.currency, f.period_end, d.filing_date "
        "FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE d.ticker = ? AND f.fact_type = 'fcf' AND f.numeric_value IS NOT NULL "
        "AND f.period_end IS NOT NULL AND f.currency = 'NGN' AND d.filing_date <= ? "
        "ORDER BY f.period_end DESC, f.fact_id ASC LIMIT 1",
        (ticker, as_of_date),
    ).fetchone()
    return row


class DCFAdapter(ValuationMethodAdapter):
    method_name = "dcf"
    required_inputs = ("fcf_fact", "wacc_assumption", "terminal_growth_assumption", "shares_outstanding")

    def is_ready(self, con, ticker):
        row = con.execute(
            "SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
            "WHERE d.ticker = ? AND f.fact_type = 'fcf' AND f.numeric_value IS NOT NULL", (ticker,)
        ).fetchone()[0]
        if row == 0:
            return ReadinessResult(False, "no direct 'fcf' fact exists for this ticker, and no "
                                           "ticker on this platform has ever had a 'cfo' and 'capex' "
                                           "fact sharing the exact same period (confirmed by direct "
                                           "query), so a CFO-minus-CapEx FCF derivation is also "
                                           "unavailable")
        return ReadinessResult(True, f"{row} direct 'fcf' fact(s) exist for this ticker -- "
                                      f"currency/PIT/assumption checks happen at compute() time")

    def compute(self, con, ticker, as_of_date, assumptions):
        readiness = self.is_ready(con, ticker)
        if not readiness.ready:
            raise RuntimeError(f"{self.method_name} refuses to compute for {ticker}: {readiness.reason}")

        def gap(reason: str) -> ValuationResult:
            return ValuationResult(
                method_name=self.method_name, point_estimate=None, range_low=None, range_high=None,
                assumptions_used=dict(assumptions), data_vintage=None,
                confidence_note=f"DATA_GAP: {reason}",
            )

        wacc = assumptions.get("wacc")
        g = assumptions.get("terminal_growth")
        if wacc is None or g is None:
            return gap("caller must explicitly supply both 'wacc' and 'terminal_growth' in "
                        "assumptions -- this adapter never defaults or infers a discount rate "
                        "or growth rate")
        if not (0 < wacc < 1):
            return gap(f"wacc={wacc!r} is not a valid discount rate (must be strictly between 0 and 1)")
        if wacc <= g:
            return gap(f"wacc ({wacc}) must exceed terminal_growth ({g}) for a Gordon Growth "
                        f"perpetuity to be defined -- refusing rather than returning an "
                        f"unbounded/negative 'value'")

        fcf_fact = _usable_fcf_fact(con, ticker, as_of_date)
        if fcf_fact is None:
            return gap("no currency-clean (NGN), knowable 'fcf' fact exists for this ticker as of "
                        "this date (a USD-denominated fact may exist but is excluded -- no fx_rates "
                        "data exists on this platform to convert it, and no fabricated rate is used)")
        fact_id, fcf_value, tier, ccy, period_end, filing_date = fcf_fact

        shares = _shares_outstanding_millions(ticker, as_of_date)
        if shares is None:
            return gap("no shares-outstanding data exists in market_cap_panel.csv for this ticker "
                        "as of this date -- cannot convert an aggregate FCF figure to a per-share value")
        shares_m, shares_date = shares

        def perpetuity_value_per_share(w: float, growth: float) -> float | None:
            if w <= growth:
                return None
            ev = fcf_value * (1 + growth) / (w - growth)
            return ev / (shares_m * 1_000_000)

        base = perpetuity_value_per_share(wacc, g)
        bear = perpetuity_value_per_share(wacc + 0.015, g - 0.005)
        bull = perpetuity_value_per_share(wacc - 0.015, g + 0.005)
        scenario_estimates = {k: v for k, v in
                               {"bear": bear, "base": base, "bull": bull}.items() if v is not None}
        values = list(scenario_estimates.values())

        return ValuationResult(
            method_name=self.method_name,
            point_estimate=base,
            range_low=min(values) if values else None,
            range_high=max(values) if values else None,
            assumptions_used={"wacc": wacc, "terminal_growth": g,
                               "sensitivity_band": "wacc +/-1.5pp, terminal_growth +/-0.5pp "
                                                    "(fixed, disclosed convention, not tuned per ticker)"},
            data_vintage=f"fcf period_end={period_end}, filed={filing_date}; "
                         f"shares as of {shares_date}",
            confidence_note=(
                f"Single-period Gordon Growth perpetuity on ONE observed FCF data point "
                f"(fact_id={fact_id}, confidence_tier={tier!r}) -- NOT a multi-year DCF "
                f"projection: real per-ticker FCF time series do not exist on this platform "
                f"today (confirmed: only 3 direct 'fcf' facts exist platform-wide, and zero "
                f"tickers have a same-period cfo/capex pair to derive more). wacc/terminal_growth "
                f"were supplied by the caller, never defaulted or inferred. "
                + ("Confidence tier is unknown (a pre-confidence_tier-column legacy fact)." if tier is None else "")
            ),
            input_fact_ids=[(fact_id, "fcf")],
            scenario_estimates=scenario_estimates,
        )


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
    required_inputs = ("ebitda_ts", "total_debt", "cash_and_equivalents", "peer_multiples")

    def is_ready(self, con, ticker):
        # FRE-7 (2026-08-09): EBITDA itself often DOES exist for a given
        # ticker -- the real, permanent blocker is Enterprise Value's
        # debt/cash components. Checked directly against the full known
        # extracted_facts.fact_type list: dividend, rights_issue,
        # bonus_issue, share_reconstruction, assets, equity, liabilities,
        # net_profit, revenue, ebit, ebitda, cfo, gross_profit, cogs, cff,
        # capex, cfi, fcf -- no 'debt' or 'cash'/'cash_and_equivalents'
        # concept has ever been extracted on this platform. Fabricating a
        # proxy (e.g. treating total liabilities as debt) was explicitly
        # forbidden by the owner's FRE-7 authorization, so this stays a
        # disclosed, permanent DATA_GAP, not a workaround.
        return ReadinessResult(False, "Enterprise Value requires 'total_debt' and "
                                       "'cash_and_equivalents' fact_types; neither has ever been "
                                       "extracted on this platform (checked directly against the "
                                       "full known fact_type list). EBITDA facts may exist for this "
                                       "ticker, but EV cannot be computed without fabricating a "
                                       "debt/cash proxy, which is not permitted.")


def _percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (no numpy dependency needed for this
    small a use). p in [0,1]."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    idx = p * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] + (s[hi] - s[lo]) * frac


class PEAdapter(ValuationMethodAdapter):
    method_name = "pe"
    required_inputs = ("net_profit_fy", "shares_outstanding", "peer_pe_multiples")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no EPS time series exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found -- currency/positive-"
                                      "earnings/peer-count checks happen at compute() time")

    def compute(self, con, ticker, as_of_date, assumptions):
        readiness = self.is_ready(con, ticker)
        if not readiness.ready:
            raise RuntimeError(f"{self.method_name} refuses to compute for {ticker}: {readiness.reason}")

        def gap(reason: str) -> ValuationResult:
            return ValuationResult(
                method_name=self.method_name, point_estimate=None, range_low=None, range_high=None,
                assumptions_used=dict(assumptions), data_vintage=None, confidence_note=f"DATA_GAP: {reason}",
            )

        subj = _eps(con, ticker, as_of_date)
        if subj is None:
            return gap("no currency-clean (NGN), knowable FY 'net_profit' fact and/or shares-"
                        "outstanding figure exists for this ticker as of this date")
        subj_eps, subj_fact_id, subj_period_end, subj_filing_date, subj_tier, subj_shares_date = subj
        if subj_eps <= 0:
            return gap(f"net_profit for the most recent knowable FY period ({subj_period_end}) is "
                        f"not positive (fact_id={subj_fact_id}) -- a P/E multiple is undefined for "
                        f"negative or zero earnings, and this adapter refuses rather than reporting "
                        f"a meaningless ratio")

        company_type = classify_company_type(con, ticker)
        peer_pes: list[float] = []
        peers_used: list[str] = []
        for peer in _peer_tickers(con, ticker, company_type):
            p = _eps(con, peer, as_of_date)
            if p is None or p[0] <= 0:
                continue
            price = _latest_price(con, peer, as_of_date)
            if price is None:
                continue
            pe = price[1] / p[0]
            if pe > 0:
                peer_pes.append(pe)
                peers_used.append(peer)
        if len(peer_pes) < 2:
            return gap(f"fewer than 2 comparable peers (same company_type={company_type!r}) have "
                        f"a computable, positive P/E as of this date ({len(peer_pes)} found) -- "
                        f"refusing to triangulate off an insufficient comparable set")

        median_pe = _percentile(peer_pes, 0.5)
        p25, p75 = _percentile(peer_pes, 0.25), _percentile(peer_pes, 0.75)
        point = median_pe * subj_eps
        scenario_estimates = {"bear_p25_peer_pe": p25 * subj_eps, "base_median_peer_pe": point,
                               "bull_p75_peer_pe": p75 * subj_eps}

        subj_price = _latest_price(con, ticker, as_of_date)
        subj_pe_note = (f" Subject's own current P/E (cross-check only, not the valuation): "
                         f"{subj_price[1] / subj_eps:.2f}x." if subj_price else "")

        return ValuationResult(
            method_name=self.method_name,
            point_estimate=point, range_low=min(p25, p75) * subj_eps, range_high=max(p25, p75) * subj_eps,
            assumptions_used={"peer_group": f"same company_type ({company_type!r}) via "
                                             f"classify_company_type() -- a coarse proxy for "
                                             f"'comparable company', not sector-level matching"},
            data_vintage=f"subject FY net_profit period_end={subj_period_end}, filed={subj_filing_date}",
            confidence_note=(
                f"EPS = net_profit (FY, fact_id={subj_fact_id}, tier={subj_tier!r}) / implied shares "
                f"outstanding. Peer multiple = median of {len(peer_pes)} peer P/E ratios "
                f"({', '.join(peers_used)}); range reflects peer 25th/75th percentile dispersion, "
                f"not a statistical confidence interval." + subj_pe_note
            ),
            input_fact_ids=[(subj_fact_id, "subject_net_profit")],
            peers_used=peers_used,
            scenario_estimates=scenario_estimates,
        )


class PBAdapter(ValuationMethodAdapter):
    method_name = "pb"
    required_inputs = ("book_equity", "shares_outstanding", "peer_pb_multiples")

    def is_ready(self, con, ticker):
        if not _financial_statement_line_items_exist(con, ticker):
            return ReadinessResult(False, "no book-equity data exists for this ticker "
                                           "(no financial-statements dataset acquired)")
        return ReadinessResult(True, "financial-statement line items found -- currency/positive-"
                                      "equity/peer-count checks happen at compute() time")

    def compute(self, con, ticker, as_of_date, assumptions):
        readiness = self.is_ready(con, ticker)
        if not readiness.ready:
            raise RuntimeError(f"{self.method_name} refuses to compute for {ticker}: {readiness.reason}")

        def gap(reason: str) -> ValuationResult:
            return ValuationResult(
                method_name=self.method_name, point_estimate=None, range_low=None, range_high=None,
                assumptions_used=dict(assumptions), data_vintage=None, confidence_note=f"DATA_GAP: {reason}",
            )

        subj = _bvps(con, ticker, as_of_date)
        if subj is None:
            return gap("no currency-clean (NGN), knowable 'equity' fact and/or shares-outstanding "
                        "figure exists for this ticker as of this date")
        subj_bvps, subj_fact_id, subj_period_end, subj_filing_date, subj_tier, subj_shares_date = subj
        if subj_bvps <= 0:
            return gap(f"book equity is not positive as of period_end={subj_period_end} "
                        f"(fact_id={subj_fact_id}) -- a P/B multiple is undefined for negative or "
                        f"zero book equity")

        company_type = classify_company_type(con, ticker)
        peer_pbs: list[float] = []
        peers_used: list[str] = []
        for peer in _peer_tickers(con, ticker, company_type):
            p = _bvps(con, peer, as_of_date)
            if p is None or p[0] <= 0:
                continue
            price = _latest_price(con, peer, as_of_date)
            if price is None:
                continue
            pb = price[1] / p[0]
            if pb > 0:
                peer_pbs.append(pb)
                peers_used.append(peer)
        if len(peer_pbs) < 2:
            return gap(f"fewer than 2 comparable peers (same company_type={company_type!r}) have "
                        f"a computable, positive P/B as of this date ({len(peer_pbs)} found) -- "
                        f"refusing to triangulate off an insufficient comparable set")

        median_pb = _percentile(peer_pbs, 0.5)
        p25, p75 = _percentile(peer_pbs, 0.25), _percentile(peer_pbs, 0.75)
        point = median_pb * subj_bvps
        scenario_estimates = {"bear_p25_peer_pb": p25 * subj_bvps, "base_median_peer_pb": point,
                               "bull_p75_peer_pb": p75 * subj_bvps}

        subj_price = _latest_price(con, ticker, as_of_date)
        subj_pb_note = (f" Subject's own current P/B (cross-check only, not the valuation): "
                         f"{subj_price[1] / subj_bvps:.2f}x." if subj_price else "")

        return ValuationResult(
            method_name=self.method_name,
            point_estimate=point, range_low=min(p25, p75) * subj_bvps, range_high=max(p25, p75) * subj_bvps,
            assumptions_used={"peer_group": f"same company_type ({company_type!r}) via "
                                             f"classify_company_type() -- a coarse proxy for "
                                             f"'comparable company', not sector-level matching"},
            data_vintage=f"subject equity period_end={subj_period_end}, filed={subj_filing_date}",
            confidence_note=(
                f"BVPS = equity (fact_id={subj_fact_id}, tier={subj_tier!r}) / implied shares "
                f"outstanding. Peer multiple = median of {len(peer_pbs)} peer P/B ratios "
                f"({', '.join(peers_used)}); range reflects peer 25th/75th percentile dispersion, "
                f"not a statistical confidence interval." + subj_pb_note
            ),
            input_fact_ids=[(subj_fact_id, "subject_equity")],
            peers_used=peers_used,
            scenario_estimates=scenario_estimates,
        )


def _eps(con: sqlite3.Connection, ticker: str, as_of_date: str
          ) -> tuple[float, int, str, str, str | None, str] | None:
    """(eps, fact_id, period_end, filing_date, confidence_tier, shares_date)
    from the most recent knowable FY net_profit fact (NGN only) divided by
    implied shares outstanding, or None if either input is unavailable."""
    fy = _latest_fy_period(con, ticker, as_of_date)
    if fy is None:
        return None
    f = _fact_for_exact_period(con, ticker, "net_profit", fy[0], fy[1], as_of_date)
    if f is None or f[3] != "NGN":
        return None
    fact_id, value, tier, ccy, filing_date = f
    shares = _shares_outstanding_millions(ticker, as_of_date)
    if shares is None:
        return None
    shares_m, shares_date = shares
    return value / (shares_m * 1_000_000), fact_id, fy[1], filing_date, tier, shares_date


def _bvps(con: sqlite3.Connection, ticker: str, as_of_date: str
          ) -> tuple[float, int, str, str, str | None, str] | None:
    """(bvps, fact_id, period_end, filing_date, confidence_tier, shares_date)
    from the most recent knowable equity fact (NGN only) divided by implied
    shares outstanding, or None if either input is unavailable."""
    s = _latest_stock_fact(con, ticker, "equity", as_of_date)
    if s is None or s[3] != "NGN":
        return None
    fact_id, value, tier, ccy, period_end, filing_date = s
    shares = _shares_outstanding_millions(ticker, as_of_date)
    if shares is None:
        return None
    shares_m, shares_date = shares
    return value / (shares_m * 1_000_000), fact_id, period_end, filing_date, tier, shares_date


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


def classify_company_type(con: sqlite3.Connection, ticker: str) -> str:
    """Three-tier precedence, FSI Phase 26: (1) owner-judged override
    list (`configs/company_type_overrides.toml`, currently empty,
    disclosed) -- still highest precedence, unchanged; (2) NEW:
    sector-derived mapping (`sector_company_type_mapping.
    derive_company_type_for_ticker()`, from NGX's own official
    `sector_ngx`, FSI Phase 23) -- only when unambiguously resolvable,
    never a guess; (3) `"general"` -- unchanged final fallback, reached
    whenever neither (1) nor (2) resolves (unknown ticker, NULL
    sector_ngx, or a deliberately-unresolved sub-industry). This is a
    deterministic translation layer, never inference -- confirmed to
    change zero readiness/valuation output for any of the 10 real FSI
    tickers (see docs/fre_runs/fsi_phase26_preregistration.md)."""
    overrides = _load_company_type_overrides()
    if ticker in overrides:
        return overrides[ticker]
    derived = derive_company_type_for_ticker(con, ticker)
    return derived if derived is not None else "general"


@dataclass
class TriangulatedValuation:
    ticker: str
    as_of_date: str
    company_type: str
    eligible_methods: list[str]
    readiness_by_method: dict[str, ReadinessResult]
    results: list[ValuationResult] = field(default_factory=list)  # may include DATA_GAP results
    disagreement_note: str = ""
    intrinsic_value_range: tuple[float, float] | None = None  # spans all numeric methods' own ranges
    valuation_confidence: str = "no_data"  # 'no_data'|'single_method'|'low'|'medium'|'high' -- a disclosed heuristic, not a statistical measure


def value_company(con: sqlite3.Connection, ticker: str, as_of_date: str) -> TriangulatedValuation:
    """Runs every eligible adapter's is_ready() check (never compute()
    unless ready) and returns a fully honest, disclosed readiness report.
    On the real database today, `results` is always empty -- every real
    adapter is NOT_READY for every real ticker, verified, not assumed."""
    company_type = classify_company_type(con, ticker)
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

    numeric_results = [r for r in results if r.point_estimate is not None]

    if not results:
        disagreement_note = "No methods are ready -- nothing to triangulate or disagree about."
    elif not numeric_results:
        disagreement_note = (
            f"{len(results)} method(s) are ready and ran, but each reported an explicit "
            f"DATA_GAP for {ticker} as of {as_of_date} (see each result's confidence_note) -- "
            f"zero numeric valuations produced."
        )
    elif len(numeric_results) == 1:
        r = numeric_results[0]
        disagreement_note = (
            f"Only one method ({r.method_name}) produced a numeric result "
            f"(point estimate {r.point_estimate:,.4f}); nothing to triangulate against."
        )
    else:
        estimates = [r.point_estimate for r in numeric_results]
        lo, hi = min(estimates), max(estimates)
        spread = (hi - lo) / lo if lo else None
        disagreement_note = (
            f"{len(numeric_results)} methods produced numeric results "
            f"({', '.join(r.method_name for r in numeric_results)}); point estimates range "
            f"{lo:,.4f} to {hi:,.4f}"
            + (f" ({spread:.0%} spread from the lowest)" if spread is not None else "")
            + " -- disagreement is disclosed here, never resolved into a single blended number."
        )

    intrinsic_value_range: tuple[float, float] | None = None
    if numeric_results:
        los = [r.range_low for r in numeric_results if r.range_low is not None]
        his = [r.range_high for r in numeric_results if r.range_high is not None]
        if los and his:
            intrinsic_value_range = (min(los), max(his))

    if not numeric_results:
        valuation_confidence = "no_data"
    elif len(numeric_results) == 1:
        valuation_confidence = "single_method"
    else:
        estimates = [r.point_estimate for r in numeric_results]
        lo, hi = min(estimates), max(estimates)
        spread = (hi - lo) / lo if lo else float("inf")
        if spread < 0.20:
            valuation_confidence = "high"
        elif spread < 0.50:
            valuation_confidence = "medium"
        else:
            valuation_confidence = "low"

    return TriangulatedValuation(
        ticker=ticker, as_of_date=as_of_date, company_type=company_type,
        eligible_methods=eligible_methods, readiness_by_method=readiness_by_method,
        results=results, disagreement_note=disagreement_note,
        intrinsic_value_range=intrinsic_value_range, valuation_confidence=valuation_confidence,
    )
