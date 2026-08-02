"""Company Intelligence Engine — v0 scaffolding.

Unlocked 2026-07-22 by H-011 reaching `confirmed` (the platform's first
validated factor) — per docs/PLATFORM_MATURITY_AND_3YEAR_ROADMAP.md's
Year-1 exit condition, this module may now be scaffolded. "Scaffolding"
is the operative word: the schema below carries every field the platform
vision eventually wants (Financial Quality, Valuation, Growth, Momentum,
Risk, Corporate Events, Competitive Position, Macro Sensitivity, Industry
Exposure, Ownership, Historical Factor Exposures, Expected Return, Risk
Score, Confidence Score) — but each field is populated ONLY from evidence
that actually exists today. Fields with no evidence-grade dataset behind
them return an explicit reason via `unavailable`, never a fabricated
value. This is the same "unknown stays unknown" discipline the parsers
and the alpha engine already follow — Company Intelligence generates
evidence, not opinions.

Architecture note: this does NOT replace or redesign anything. It reads
from the existing PIT database, the existing validated `xs_size`
construction (unchanged), the existing event calendars, and the existing
data_quality_log — all Production Ready per the maturity assessment.

Extensibility pattern, deliberately mirrored from alpha_engine.py's
MODEL_ADAPTERS: FACTOR_EXPOSURE_ADAPTERS is keyed by family name; a new
validated factor is wired in by adding one function here, not by
redesigning the schema. REJECTED_FAMILIES is the honest counterpart —
citing what was tested and did NOT validate is itself evidence, per the
charter ("a rejected hypothesis increases knowledge").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from . import universe

PKG_ROOT = Path(__file__).resolve().parents[2]

# Fields the eventual platform vision wants that have NO evidence-grade
# dataset behind them today. Mapped to the SPECIFIC blocking reason, not
# a generic "TODO" — matches docs/EXECUTION_BACKLOG.md's own Data-category
# items so a reader can trace exactly what would need to land first.
UNAVAILABLE_FIELDS = {
    "Financial Quality": "no financial-statement/fundamentals dataset acquired",
    "Valuation": "EPS/P.E. parser failed validation twice — "
                "reports/eps_pe_extraction_status.md",
    "Growth": "no financial-statement dataset acquired (same blocker as "
             "Financial Quality)",
    "Competitive Position": "no qualitative/analyst/news dataset acquired",
    "Macro Sensitivity": "H-004 (oil lead-lag) and H-005 (MPC windows) "
                         "both rejected; no validated macro-conditioning "
                         "exists yet (Wave 3 candidate C2, not yet built)",
    "Industry Exposure": "securities.sector_ngx is now populated for 136/320 "
                         "rows (FSI Phase 23, 2026-08-02, from NGX's own "
                         "official Daily Official List) -- still listed as "
                         "unavailable here because coverage remains partial "
                         "and build_profile() has no logic wired to consume "
                         "it yet; not activated by this disclosure update",
    "Ownership": "no ownership/shareholding dataset acquired",
}

# Factor families tested and REJECTED — citing this is evidence, not a
# gap. Format: family -> (hypothesis_ids, one-line finding).
REJECTED_FAMILIES = {
    "Momentum": ("H-007, H-009, H-010",
                "gross effect real in places but did not survive "
                "placebo/statistical-power tests across three designs "
                "(quarterly, annual, pooled cohorts)"),
    "Low Volatility": ("H-008",
                       "statistically ROBUST NEGATIVE tilt — not merely "
                       "absent, the opposite sign; NGX's regime-shock "
                       "history does not match the anomaly's precondition"),
    "PEAD": ("H-006",
            "the earnings-reaction effect itself is real and large, but "
            "reaction-magnitude ranking carried zero selection skill"),
}


@dataclass
class FactorExposure:
    hypothesis_id: str
    family: str
    status: str                     # "validated" | "rejected"
    value: float | None             # cross-sectional percentile [0,1]
    in_current_sleeve: bool = False
    note: str = ""


@dataclass
class CompanyProfile:
    ticker: str
    as_of: str
    name: str | None = None

    # --- Factual snapshot: validated price/data layer, never fabricated ---
    close: float | None = None
    close_date: str | None = None          # actual date of the close used
                                           # (may lag as_of on non-trading days)
    adtv_60d_ngn: float | None = None
    market_cap_ngn_m: float | None = None  # full-issue, NOT float-adjusted
    in_iru: bool = False
    iru_liquidity_rank: int | None = None

    # --- Descriptive risk: observed history, NOT a factor claim ---
    # (Low-Vol was tested as an alpha claim and rejected, H-008 — these
    # fields describe realized behavior, they do not predict it)
    realized_vol_ann_12m: float | None = None
    max_drawdown_3y: float | None = None
    data_quality_flags: list[str] = field(default_factory=list)

    # --- Validated factor exposures: the ONLY alpha-adjacent content ---
    factor_exposures: dict[str, FactorExposure] = field(default_factory=dict)

    # --- Corporate events: factual, from validated calendars ---
    last_dividend_closure: str | None = None
    last_earnings_filing: str | None = None
    recent_corporate_actions: list[dict] = field(default_factory=list)

    # --- Composite: populated ONLY if in a currently actionable sleeve ---
    expected_return_ann: float | None = None
    confidence_rating: str | None = None

    # --- Explicit inventory of what this profile cannot say yet, and why ---
    unavailable: dict[str, str] = field(
        default_factory=lambda: dict(UNAVAILABLE_FIELDS))


def _size_exposure(con, cache: dict, ticker: str, as_of: str) -> FactorExposure:
    """H-011 (confirmed). Reuses backtest_xs.size_scores/load_panel/
    load_market_cap_panel UNCHANGED — descriptive for EVERY company, not
    just the current top-20 sleeve (alpha_engine.H011SizeAdapter only
    emits the actionable picks; reporting where every company stands is
    Company Intelligence's job, not the trading engine's). Populates
    `cache["mcap_wide"]`/`cache["close_ff"]` so build_profile's market-cap
    field reuses this same computation instead of redoing it."""
    from . import backtest_xs
    from .alpha_engine import H011SizeAdapter

    if "size_scores" not in cache:
        cfg = {
            "data": {"sim_start": "2016-01-02", "sim_end": as_of,
                     "min_confidence": 0.9, "vintage": ""},
            "signal": {"method": "xs_size", "min_obs_formation": 120,
                      "lookback_months": 12},
            "portfolio": {"top_n": H011SizeAdapter.TOP_N,
                         "rebalance": H011SizeAdapter.REBALANCE},
        }
        panel = backtest_xs.load_panel(con, cfg)
        panel["mcap"] = backtest_xs.load_market_cap_panel(panel["close_ff"])
        cache["close_ff"] = panel["close_ff"]
        cache["mcap_wide"] = panel["mcap"]
        cache["size_scores"] = backtest_xs.size_scores(con, panel, cfg)
        cache["size_top_n"] = H011SizeAdapter.TOP_N

    scores = cache["size_scores"]
    top_n = cache["size_top_n"]
    if not scores:
        return FactorExposure("H-011", "Size", "validated", None, False,
                              "No eligible formation available at this date.")
    latest = max(scores)
    sc = scores[latest]
    if ticker not in sc.index:
        return FactorExposure(
            "H-011", "Size", "validated", None, False,
            f"Not IRU-eligible or missing market-cap data at the "
            f"{latest.date()} formation.")
    pct = float((sc <= sc[ticker]).mean())   # higher score = smaller cap
    sleeve = set(sc.nlargest(min(top_n, len(sc))).index)
    in_sleeve = ticker in sleeve
    note = (f"Small-cap percentile {pct:.0%} at the {latest.date()} "
           f"formation (higher = smaller)." +
           (" Currently in the validated top-20 sleeve."
            if in_sleeve else " Not in the current top-20 sleeve."))
    return FactorExposure("H-011", "Size", "validated", round(pct, 4),
                          in_sleeve, note)


FACTOR_EXPOSURE_ADAPTERS = {"Size": _size_exposure}


def _realized_stats(close: pd.Series, as_of: pd.Timestamp, vol_months: int,
                    dd_years: int) -> tuple[float | None, float | None]:
    """Vol/drawdown from ACTUAL close observations only (no forward-fill —
    a ffilled series would understate vol for stale names, same discipline
    backtest_xs.vol_scores already established)."""
    window = close.loc[as_of - pd.DateOffset(months=vol_months):as_of].dropna()
    ret = window.pct_change()
    vol = float(ret.std() * (252 ** 0.5)) if ret.notna().sum() > 20 else None

    dd_window = close.loc[as_of - pd.DateOffset(years=dd_years):as_of].dropna()
    if len(dd_window) > 20:
        nav = dd_window / dd_window.iloc[0]
        dd = float((nav / nav.cummax() - 1).min())
    else:
        dd = None
    return vol, dd


def _latest_event(csv_path: Path, date_col: str, symbol_col: str,
                  ticker: str, as_of: str) -> str | None:
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, usecols=[symbol_col, date_col])
    hit = df[df[symbol_col] == ticker].copy()
    if hit.empty:
        return None
    hit["ev_date"] = pd.to_datetime(hit[date_col].astype(str).str[:10], errors="coerce")
    hit = hit[hit.ev_date <= pd.Timestamp(as_of)].dropna(subset=["ev_date"])
    if hit.empty:
        return None
    return str(hit.ev_date.max().date())


def _recent_corporate_actions(ticker: str, as_of: str, n: int = 5) -> list[dict]:
    path = PKG_ROOT / "data/staging/xissuer/corporate_actions_calendar_classified.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, usecols=["symbol", "created", "submission_type", "doc_class"])
    hit = df[df.symbol == ticker].copy()
    if hit.empty:
        return []
    hit["ev_date"] = pd.to_datetime(hit.created.astype(str).str[:10], errors="coerce")
    hit = hit[hit.ev_date <= pd.Timestamp(as_of)].dropna(subset=["ev_date"])
    hit = hit.sort_values("ev_date", ascending=False).head(n)
    return [{"date": str(r.ev_date.date()), "submission_type": r.submission_type,
            "doc_class": r.doc_class} for r in hit.itertuples()]


def build_profile(con, ticker: str, as_of: str | None = None,
                  cache: dict | None = None) -> CompanyProfile:
    """Build one company's profile as of `as_of` (default: today).
    `cache` lets a caller building profiles for many tickers reuse the
    (expensive) panel loads and factor-exposure computation across calls
    instead of recomputing them per ticker — pass the SAME dict across a
    batch run (see scripts/company_profile.py)."""
    from . import db

    as_of = as_of or date.today().isoformat()
    cache = cache if cache is not None else {}

    row = con.execute("SELECT name FROM securities WHERE ticker = ?",
                      (ticker,)).fetchone()
    profile = CompanyProfile(ticker=ticker, as_of=as_of,
                             name=row[0] if row else None)

    px = db.equity_prices_asof(con, as_of, tickers=[ticker], min_confidence=0.9)
    if not px.empty:
        px = px.sort_values("trade_date")
        profile.close = float(px.close.iloc[-1])
        profile.close_date = px.trade_date.iloc[-1]
        close_s = px.set_index(pd.to_datetime(px.trade_date)).close
        profile.realized_vol_ann_12m, profile.max_drawdown_3y = _realized_stats(
            close_s, pd.Timestamp(as_of), 12, 3)
        val_s = px.set_index(pd.to_datetime(px.trade_date)).value_traded.dropna()
        if len(val_s) >= 10:
            profile.adtv_60d_ngn = float(val_s.tail(60).mean())

    iru_rules = universe.load_rules()
    mem = universe.iru_members(con, as_of, iru_rules)
    hit = mem[mem.ticker == ticker]
    if len(hit):
        profile.in_iru = True
        profile.iru_liquidity_rank = int(hit.liq_rank.iloc[0])

    flags = pd.read_sql(
        "SELECT DISTINCT check_name FROM data_quality_log WHERE "
        "entity_type = 'ticker' AND entity_code = ?", con, params=(ticker,))
    profile.data_quality_flags = sorted(flags.check_name.tolist())

    for family, fn in FACTOR_EXPOSURE_ADAPTERS.items():
        profile.factor_exposures[family] = fn(con, cache, ticker, as_of)
    for family, (hyp, finding) in REJECTED_FAMILIES.items():
        profile.factor_exposures[family] = FactorExposure(
            hyp, family, "rejected", None, False, finding)

    # Market cap — reuse the panel _size_exposure already built (cheap);
    # never recomputed a second time.
    mcap_wide = cache.get("mcap_wide")
    if mcap_wide is not None and ticker in mcap_wide.columns:
        s = mcap_wide[ticker].dropna()
        if len(s):
            profile.market_cap_ngn_m = float(s.iloc[-1])

    size_exp = profile.factor_exposures.get("Size")
    if size_exp and size_exp.in_current_sleeve:
        from .alpha_engine import H011SizeAdapter
        profile.expected_return_ann = H011SizeAdapter.EXPECTED_EXCESS_ANN
        profile.confidence_rating = "High"

    profile.last_dividend_closure = _latest_event(
        PKG_ROOT / "data/reference/exdiv_closure_calendar.csv",
        "closure_date", "symbol", ticker, as_of)
    profile.last_earnings_filing = _latest_event(
        PKG_ROOT / "data/staging/xissuer/earnings_calendar.csv",
        "created_date", "symbol", ticker, as_of)
    profile.recent_corporate_actions = _recent_corporate_actions(ticker, as_of)

    return profile
