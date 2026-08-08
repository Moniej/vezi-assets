"""Stage 1 / A-1 — participation-capped execution realism test.

NOT a hypothesis, NOT a change to any confirmed hypothesis's signal or
portfolio construction. This module adds exactly one new simulation path
— ``constrained_simulate`` — that consumes the SAME ``targets`` dict a
frozen hypothesis's own scoring/selection pipeline already produces
(``size_scores`` + ``targets_from_scores`` for H-011, unchanged) and asks
a different, additive question: what return would have been REALIZED if
every rebalance leg had been capped at the same ADTV participation limit
the platform's own ``capacity_report`` already uses to grade capacity,
instead of assuming an unconstrained fill?

``backtest_xs.simulate`` is untouched. This is a parallel path, not a
replacement — every existing hypothesis's evidence trail is unaffected.

Fill mechanics (stated explicitly, not left implicit):
  - At each execution date, for each ticker with a nonzero desired weight
    change (buy or sell, including a full exit), the executable change is
    clipped to +/- (participation_pct/100 * ADTV_60d / aum_ngn) — the same
    capacity formula ``backtest_xs.capacity_report`` already uses, just
    applied as a FILL constraint instead of a post-hoc report.
  - Missing/zero ADTV on an execution date = zero executable capacity for
    that leg that day (a real leg cannot be sized without a liquidity
    estimate) — recorded as a rejected leg, not silently skipped.
  - Unfilled capital does NOT get deployed elsewhere and does NOT earn the
    benchmark's return: it sits as explicit zero-return cash. This is the
    conservative assumption (never invents return), stated here so it
    cannot be silently reinterpreted later.
  - No renormalization of drifted weights to sum to 1 (unlike
    ``backtest_xs.simulate``, which assumes full investment) — the cash
    residual left by under-fills is real and persists until a later
    rebalance can (partially) close it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .backtest_xs import XSResult


@dataclass
class LegFill:
    date: pd.Timestamp
    ticker: str
    desired_dw: float
    executed_dw: float
    adtv: float
    cap_weight: float
    fill_frac: float
    status: str   # "filled" | "partial" | "rejected"


@dataclass
class ConstrainedResult:
    xs: XSResult
    legs: list[LegFill] = field(default_factory=list)

    def leg_frame(self) -> pd.DataFrame:
        if not self.legs:
            return pd.DataFrame(columns=["date", "ticker", "desired_dw",
                                         "executed_dw", "adtv", "cap_weight",
                                         "fill_frac", "status"])
        return pd.DataFrame([vars(l) for l in self.legs])


def constrained_simulate(close_ff: pd.DataFrame, targets: dict,
                          adtv60: pd.DataFrame, buy_rate: float,
                          sell_rate: float, sim_start: str, sim_end: str,
                          aum_ngn: float, participation_pct: float,
                          fill_epsilon: float = 1e-6) -> ConstrainedResult:
    """Same signature shape as ``backtest_xs.simulate`` plus the two
    capacity inputs (``adtv60``, ``aum_ngn``, ``participation_pct``) that
    ``capacity_report`` already uses for its own (report-only) grading.
    ``targets`` must come from the frozen hypothesis's own
    ``targets_from_scores`` output, unmodified."""
    cap_frac = participation_pct / 100.0
    daily = close_ff.loc[sim_start:sim_end]
    R = daily.pct_change().fillna(0.0)
    dates = R.index
    exec_dates = {pd.Timestamp(k): v for k, v in targets.items()}

    w = pd.Series(dtype=float)  # invested weights only; (1 - w.sum()) is cash
    net, gross, tos, csts = [], [], [], []
    contrib: dict[str, float] = {}
    wrows: dict = {}
    legs: list[LegFill] = []

    for dt in dates:
        r_assets = R.loc[dt]
        day_gross = float((w * r_assets.reindex(w.index).fillna(0.0)).sum()) \
            if len(w) else 0.0
        for t_, wt in w.items():
            contrib[t_] = contrib.get(t_, 0.0) + wt * float(r_assets.get(t_, 0.0))
        day_net = day_gross
        if len(w):
            # drift only — NO renormalization: unfilled cash stays at 0%,
            # it is never implicitly redeployed into existing holdings
            w = w * (1 + r_assets.reindex(w.index).fillna(0.0))

        if dt in exec_dates:
            tgt = exec_dates[dt].astype(float)
            tgt = tgt[tgt > 0]
            all_ix = w.index.union(tgt.index)
            old = w.reindex(all_ix).fillna(0.0)
            desired = tgt.reindex(all_ix).fillna(0.0) - old
            executed = pd.Series(0.0, index=all_ix)
            for tick in all_ix:
                dd = float(desired[tick])
                if abs(dd) < fill_epsilon:
                    continue
                adtv = (adtv60[tick].asof(dt) if tick in adtv60.columns
                        else np.nan)
                if pd.isna(adtv) or adtv <= 0:
                    cap = 0.0
                else:
                    cap = cap_frac * float(adtv) / aum_ngn
                ed = max(-cap, min(cap, dd))
                executed[tick] = ed
                fill_frac = abs(ed) / abs(dd)
                status = ("rejected" if fill_frac < fill_epsilon
                          else "filled" if fill_frac > 1 - 1e-4
                          else "partial")
                legs.append(LegFill(dt, tick, dd, ed,
                                    float(adtv) if not pd.isna(adtv) else float("nan"),
                                    cap, round(fill_frac, 4), status))
            new_w = (old + executed).clip(lower=0.0)
            buys = executed.clip(lower=0).sum()
            sells = (-executed.clip(upper=0)).sum()
            cost = buys * buy_rate + sells * sell_rate
            day_net -= cost
            tos.append(pd.Series({dt: buys}))
            csts.append(pd.Series({dt: cost}))
            wrows[dt] = new_w[new_w > 0]
            w = new_w
        net.append(day_net)
        gross.append(day_gross)

    turnover = pd.concat(tos) if tos else pd.Series(dtype=float)
    costs_s = pd.concat(csts) if csts else pd.Series(dtype=float)
    weights = pd.DataFrame(wrows).T.fillna(0.0) if wrows \
        else pd.DataFrame(index=pd.DatetimeIndex([]))
    xs = XSResult(
        net_returns=pd.Series(net, index=dates),
        gross_returns=pd.Series(gross, index=dates),
        weights=weights, turnover=turnover, costs=costs_s,
        sector_contribution={k: round(v, 5) for k, v in
                             sorted(contrib.items(), key=lambda kv: -kv[1])})
    return ConstrainedResult(xs=xs, legs=legs)


def leg_fill_summary(legs: list[LegFill]) -> dict:
    if not legs:
        return {}
    df = pd.DataFrame([vars(l) for l in legs])
    return {
        "n_legs": len(df),
        "pct_rejected": round(100.0 * (df.status == "rejected").mean(), 1),
        "pct_partial": round(100.0 * (df.status == "partial").mean(), 1),
        "pct_filled": round(100.0 * (df.status == "filled").mean(), 1),
        "mean_fill_frac": round(float(df.fill_frac.mean()), 4),
    }
