"""Extensible diagnostic engine.

Every diagnostic is a class with a ``run(ctx) -> DiagnosticResult``; adding a
new check = writing a new class with the ``@register`` decorator (or calling
``register`` from any module, including user code) — existing diagnostics are
never modified. ``run_all`` executes the registry against a DiagContext and
persists outcomes to data_quality_log.

Severity semantics:
  ERROR   — data cannot be trusted for research until resolved (e.g. an
            unexplained -30% day is probably an unadjusted corporate action:
            using it fabricates momentum).
  WARNING — degrades quality/realism; research may proceed with the caveat
            recorded in the experiment's validation_flags.
  INFO    — worth knowing, no action forced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SEVERITIES = ("INFO", "WARNING", "ERROR")


@dataclass
class DiagContext:
    con: object                       # sqlite3 connection (market-data DB)
    start: str
    end: str
    params: dict = field(default_factory=dict)   # per-diagnostic thresholds

    def equity(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT ticker, trade_date, close, volume, value_traded, deals "
            "FROM v_equity_prices_latest WHERE trade_date BETWEEN ? AND ? "
            "ORDER BY ticker, trade_date", self.con, params=(self.start, self.end))

    def index_levels(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT index_code, trade_date, close_value FROM v_index_levels_latest "
            "WHERE trade_date BETWEEN ? AND ? ORDER BY index_code, trade_date",
            self.con, params=(self.start, self.end))


@dataclass
class DiagnosticResult:
    name: str
    severity: str                     # severity IF failed; INFO results pass
    passed: bool
    summary: str
    evidence: pd.DataFrame            # supporting rows (possibly empty)
    recommended_action: str

    def __str__(self) -> str:
        flag = "PASS" if self.passed else f"FAIL[{self.severity}]"
        return f"{flag:14s} {self.name}: {self.summary}"


_REGISTRY: dict[str, type] = {}


def register(cls):
    _REGISTRY[cls.name] = cls
    return cls


def run_all(ctx: DiagContext, names: list[str] | None = None,
            persist: bool = True) -> list[DiagnosticResult]:
    results = [_REGISTRY[n]().run(ctx) for n in (names or sorted(_REGISTRY))]
    if persist:
        for r in results:
            for _, row in r.evidence.head(50).iterrows():
                ctx.con.execute(
                    "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
                    "trade_date, severity, detail) VALUES (?,?,?,?,?,?)",
                    (r.name,
                     "ticker" if "ticker" in r.evidence.columns else "index",
                     str(row.get("ticker") or row.get("index_code") or "?"),
                     str(row.get("trade_date", "")),
                     r.severity.lower() if r.severity != "WARNING" else "warn",
                     r.summary[:200]))
        ctx.con.commit()
    return results


# ---------------------------------------------------------------------------
# Built-in diagnostics
# ---------------------------------------------------------------------------

@register
class UnexplainedJump:
    """Large single-day move with no corporate action nearby: probably an
    unadjusted split/rights/bonus markdown, not a real return."""
    name = "unexplained_jump"
    severity = "ERROR"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        thr = ctx.params.get("jump_threshold", 0.25)
        window = ctx.params.get("jump_ca_window_days", 5)
        eq = ctx.equity()
        eq["ret"] = eq.groupby("ticker").close.pct_change()
        jumps = eq[eq.ret.abs() >= thr].copy()
        ca = pd.read_sql("SELECT ticker, markdown_date, action_type FROM corporate_actions",
                         ctx.con)
        ca["markdown_date"] = pd.to_datetime(ca.markdown_date)
        unexplained = []
        for _, j in jumps.iterrows():
            d = pd.Timestamp(j.trade_date)
            near = ca[(ca.ticker == j.ticker) &
                      (ca.markdown_date.notna()) &
                      (abs((ca.markdown_date - d).dt.days) <= window)]
            if near.empty:
                unexplained.append(j)
        ev = pd.DataFrame(unexplained)[["ticker", "trade_date", "close", "ret"]] \
            if unexplained else pd.DataFrame(columns=["ticker", "trade_date", "close", "ret"])
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            f"{len(ev)} moves >= {thr:.0%} with no corporate action within "
            f"{window} days" if not ev.empty else
            f"no unexplained moves >= {thr:.0%}",
            ev, "verify against corporate-action records / news; if a markdown, "
                "record the action and rebuild the total-return series — do NOT "
                "trade or research on this series until resolved")


@register
class StalePrice:
    """Long runs of identical closes: price floor, suspension, or dead feed.
    Momentum computed over a frozen price is fiction."""
    name = "stale_price"
    severity = "WARNING"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        min_run = ctx.params.get("stale_min_sessions", 20)
        eq = ctx.equity()
        rows = []
        for tkr, g in eq.groupby("ticker"):
            runs = (g.close != g.close.shift()).cumsum()
            counts = g.groupby(runs).agg(n=("close", "size"),
                                         start=("trade_date", "min"),
                                         end=("trade_date", "max"),
                                         close=("close", "first"))
            for _, r in counts[counts.n >= min_run].iterrows():
                rows.append(dict(ticker=tkr, trade_date=r.start, run_end=r.end,
                                 sessions=int(r.n), close=r.close))
        ev = pd.DataFrame(rows)
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            (f"{len(ev)} stale stretches >= {min_run} sessions"
             if len(ev) else f"no stale stretches >= {min_run} sessions"),
            ev, "treat stale stretches as non-tradeable: exclude from momentum "
                "lookbacks or mark liquidity zero; check suspension records")


@register
class MissingData:
    """Series missing a material share of the union trading calendar."""
    name = "missing_data"
    severity = "WARNING"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        max_missing = ctx.params.get("max_missing_pct", 5.0)
        rows = []
        for df, col in ((ctx.equity(), "ticker"), (ctx.index_levels(), "index_code")):
            if df.empty:
                continue
            calendar = df.trade_date.nunique()
            counts = df.groupby(col).trade_date.nunique()
            for code, n in counts.items():
                miss = 100 * (1 - n / calendar)
                if miss > max_missing:
                    rows.append({col: code, "days_present": n,
                                 "calendar_days": calendar,
                                 "missing_pct": round(miss, 1)})
        ev = pd.DataFrame(rows)
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            (f"{len(ev)} series missing > {max_missing}% of calendar"
             if len(ev) else "no series with material gaps"),
            ev, "check listing/delisting dates vs window; fill from an "
                "alternative source or exclude the series with a note")


@register
class DuplicateObservation:
    """Same (entity, date) with materially different values across sources."""
    name = "duplicate_observation"
    severity = "WARNING"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        tol = ctx.params.get("cross_source_tolerance_pct", 1.0)
        df = pd.read_sql(
            "SELECT index_code, trade_date, COUNT(DISTINCT source_id) AS n_src, "
            "MIN(close_value) AS lo, MAX(close_value) AS hi FROM index_levels "
            "WHERE trade_date BETWEEN ? AND ? GROUP BY index_code, trade_date "
            "HAVING n_src > 1", ctx.con, params=(ctx.start, ctx.end))
        if not df.empty:
            df["spread_pct"] = 100 * (df.hi - df.lo) / df.lo
            df = df[df.spread_pct > tol]
        return DiagnosticResult(
            self.name, self.severity, df.empty,
            (f"{len(df)} entity-dates where sources disagree > {tol}%"
             if len(df) else "no material cross-source disagreements"),
            df, "prefer the higher-confidence source; record the loser's row "
                "as suspect in data_quality_log")


@register
class ExtremeIndexReturn:
    """Sector-index daily moves beyond plausibility for a diversified basket."""
    name = "extreme_index_return"
    severity = "WARNING"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        thr = ctx.params.get("index_return_threshold", 0.10)
        lv = ctx.index_levels()
        lv["ret"] = lv.groupby("index_code").close_value.pct_change()
        ev = lv[lv.ret.abs() >= thr][["index_code", "trade_date", "ret"]]
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            (f"{len(ev)} index moves >= {thr:.0%} in a day" if len(ev)
             else f"no index moves >= {thr:.0%}"),
            ev, "cross-check against a second source and the constituent-level "
                "data for the same day")


@register
class MembershipConsistency:
    """Interval overlaps, inverted intervals, members with no price data."""
    name = "membership_consistency"
    severity = "ERROR"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        m = pd.read_sql("SELECT index_code, ticker, effective_from, effective_to "
                        "FROM index_membership", ctx.con)
        rows = []
        inverted = m[m.effective_to.notna() & (m.effective_to < m.effective_from)]
        for _, r in inverted.iterrows():
            rows.append(dict(index_code=r.index_code, ticker=r.ticker,
                             issue="effective_to before effective_from"))
        for (idx, tkr), g in m.groupby(["index_code", "ticker"]):
            g = g.sort_values("effective_from")
            ends = g.effective_to.fillna("9999-12-31")
            if (g.effective_from.iloc[1:].values < ends.iloc[:-1].values).any():
                rows.append(dict(index_code=idx, ticker=tkr,
                                 issue="overlapping membership intervals"))
        priced = set(pd.read_sql("SELECT DISTINCT ticker FROM equity_prices",
                                 ctx.con).ticker)
        for _, r in m[~m.ticker.isin(priced)].iterrows():
            rows.append(dict(index_code=r.index_code, ticker=r.ticker,
                             issue="member has no price data at all"))
        ev = pd.DataFrame(rows)
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            (f"{len(ev)} membership inconsistencies" if len(ev)
             else "membership intervals consistent"),
            ev, "fix intervals from review circulars; a member without prices "
                "silently biases sector return construction")


@register
class LiquidityAnomaly:
    """Volume/value/price contradictions that corrupt ADTV-based sizing."""
    name = "liquidity_anomaly"
    severity = "WARNING"

    def run(self, ctx: DiagContext) -> DiagnosticResult:
        eq = ctx.equity()
        eq["ret"] = eq.groupby("ticker").close.pct_change()
        bad_value = eq[(eq.volume > 0) & (eq.value_traded <= 0)]
        ghost_move = eq[(eq.ret.abs() > 1e-9) & (eq.volume == 0)]
        ev = pd.concat([
            bad_value.assign(issue="volume>0 but value_traded<=0"),
            ghost_move.assign(issue="price moved on zero volume"),
        ])[["ticker", "trade_date", "volume", "value_traded", "issue"]]
        return DiagnosticResult(
            self.name, self.severity, ev.empty,
            (f"{len(ev)} liquidity contradictions" if len(ev)
             else "no volume/value/price contradictions"),
            ev, "exclude affected days from ADTV windows; if systematic for a "
                "source, downgrade that source's confidence")
