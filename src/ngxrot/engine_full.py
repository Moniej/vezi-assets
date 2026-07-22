"""Phase 3 backtest engine: constituent-level, liquidity-constrained.

Realism upgrades over backtest_lite:
  - trades CONSTITUENTS, not index levels: sector targets are pushed down to
    member stocks using point-in-time membership and within-sector weights;
  - total-return: cash dividends reinvested on their markdown date. Other
    action types (rights, bonuses, splits) are NOT auto-adjusted — a wrong
    auto-adjustment fabricates returns; the unexplained_jump diagnostic
    exists to catch unadjusted markdowns and force an explicit fix;
  - ADTV participation cap: no trade may exceed cap_pct of a stock's
    trailing ADTV. Excess is REJECTED (not deferred), logged, and reported;
  - line-item costs: brokerage/SEC/NGX/CSCS/stamp/VAT from the effective-
    dated schedule, plus slippage (fixed bps, assumed) and market impact
    (impact_coeff_bps * sqrt(participation), assumed) — each accumulated
    separately for cost attribution;
  - capacity: at every rebalance, the max AUM at which every desired trade
    would still fit its ADTV cap, plus the name that binds (bottleneck).
    Reported as a distribution, never a single number.

Honest limitation (flagged in every record): within-sector weights are a
trailing-ADTV-share PROXY because no float-adjusted weights exist yet. This
overweights liquid names, which flatters capacity; real index weights from
NGX review documents will typically be HARSHER (cap-weighted into less
liquid names). Treat capacity numbers as upper bounds until real weights land.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import db
from . import signal as sig

COST_COMPONENTS = ("brokerage", "sec_fee", "ngx_fee", "cscs_fee", "stamp_duty",
                   "vat", "slippage", "market_impact")
VATABLE = {"brokerage", "cscs_fee"}


@dataclass
class FullResult:
    net_returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame                 # sector-level targets per execution date
    turnover: pd.Series                   # executed one-way (buys) per rebalance
    costs: pd.Series                      # total cost per rebalance (fraction of NAV)
    benchmark_returns: pd.Series
    attribution: dict = field(default_factory=dict)     # component -> cumulative frac
    capacity_records: list = field(default_factory=list)
    clip_stats: dict = field(default_factory=dict)
    sector_contribution: dict = field(default_factory=dict)
    exclusions: dict = field(default_factory=dict)
    tr_adjustments: int = 0
    unadjusted_action_types: list = field(default_factory=list)


def _fee_rates(schedule: pd.DataFrame, brokerage_override_pct: float) -> dict:
    sch = schedule.copy()
    if brokerage_override_pct >= 0:
        sch.loc[sch.fee_name == "brokerage", "rate_pct"] = brokerage_override_pct
    rates = {}
    for _, r in sch[sch.applies_to == "trade_value"].iterrows():
        rates[r.fee_name] = {"rate": r.rate_pct / 100.0, "side": r.side}
    vat = sch.loc[sch.fee_name == "vat", "rate_pct"]
    rates["vat_pct"] = float(vat.iloc[0]) / 100.0 if len(vat) else 0.0
    return rates


def _line_item_costs(buys: pd.Series, sells: pd.Series, rates: dict) -> dict:
    """Per-component cost (fractions of NAV) for one rebalance."""
    out = dict.fromkeys(COST_COMPONENTS, 0.0)
    b, s = float(buys.sum()), float(sells.sum())
    for fee, spec in rates.items():
        if fee == "vat_pct":
            continue
        notional = (b if spec["side"] == "buy" else
                    s if spec["side"] == "sell" else b + s)
        out[fee] = notional * spec["rate"]
    out["vat"] = rates["vat_pct"] * sum(out[f] for f in VATABLE)
    return out


def run_full(con, cfg: dict) -> FullResult:
    d, s, p, c = cfg["data"], cfg["signal"], cfg["portfolio"], cfg["costs"]
    eng = cfg["engine"]
    aum = float(eng["aum_ngn"])
    cap = cfg["liquidity"]["adtv_participation_cap_pct"] / 100.0
    adtv_win = cfg["liquidity"]["adtv_window_days"]
    slip_rate = eng["slippage_bps"] / 1e4
    impact_coeff = eng["impact_coeff_bps"] / 1e4

    # ---- constituent data ------------------------------------------------
    eq = db.equity_prices_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                               vintage=d["vintage"] or None)
    px = eq.pivot(index="trade_date", columns="ticker", values="close")
    px.index = pd.to_datetime(px.index)
    val = eq.pivot(index="trade_date", columns="ticker", values="value_traded")
    val.index = pd.to_datetime(val.index)
    val = val.reindex(px.index).fillna(0.0)
    if float(val.to_numpy().sum()) <= 0:
        raise RuntimeError("value_traded is all zero — ADTV constraint would "
                           "silently zero out every trade; refusing to run")
    ret = px.pct_change().fillna(0.0)

    # ---- total-return overlay: cash dividends on markdown date ------------
    ca = db.corporate_actions_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                                   vintage=d["vintage"] or None)
    n_adj, unadjusted = 0, set()
    for _, a in ca.iterrows():
        if a.action_type in ("dividend_cash", "dividend_interim") and \
                pd.notna(a.dividend_per_share) and a.ticker in px.columns:
            md = pd.Timestamp(a.markdown_date)
            if md in px.index:
                i = px.index.get_loc(md)
                if i > 0:
                    prev = px[a.ticker].iloc[i - 1]
                    if prev > 0:
                        ret.loc[md, a.ticker] += a.dividend_per_share / prev
                        n_adj += 1
        elif a.action_type not in ("dividend_cash", "dividend_interim"):
            unadjusted.add(a.action_type)

    # ---- PIT membership and within-sector ADTV-share proxy weights --------
    mem = db.membership_intervals(con, d["universe"],
                                  min_confidence=d["min_confidence"],
                                  vintage=d["vintage"] or None)
    adtv = val.rolling(adtv_win, min_periods=max(20, adtv_win // 3)).mean().shift(1)

    _member_cache: dict = {}

    def members(sector: str, day: pd.Timestamp) -> list[str]:
        # membership changes are announced-dated and rare; caching per
        # (sector, month) is exact unless a change lands mid-month, which the
        # monthly weight refresh already treats as the granularity of truth
        key = (sector, day.strftime("%Y-%m"))
        if key in _member_cache:
            return _member_cache[key]
        g = mem[mem.index_code == sector]
        ds = day.strftime("%Y-%m-%d")
        ok = g[(g.effective_from <= ds)
               & (g.effective_to.isna() | (g.effective_to > ds))
               & (g.announced_date.fillna(g.effective_from) <= ds)]
        out = [t for t in ok.ticker if t in px.columns]
        _member_cache[key] = out
        return out

    def within_weights(sector: str, day: pd.Timestamp) -> pd.Series:
        ms = members(sector, day)
        w = adtv.loc[day, ms].clip(lower=0.0) if ms else pd.Series(dtype=float)
        tot = w.sum()
        return (w / tot) if tot > 0 else pd.Series(1 / len(ms), index=ms) if ms else w

    # ---- sector TR series (for the signal) --------------------------------
    sector_ret = {}
    for sec in d["universe"]:
        wts = pd.DataFrame(0.0, index=px.index, columns=px.columns)
        # membership changes are rare; recompute weights monthly, hold between
        month_starts = px.index.to_series().groupby(px.index.to_period("M")).min()
        for ms_day in month_starts:
            w = within_weights(sec, ms_day)
            wts.loc[ms_day:, w.index] = 0.0
            wts.loc[ms_day:, w.index] = w.values
        sector_ret[sec] = (wts * ret).sum(axis=1)
    sector_ret = pd.DataFrame(sector_ret)
    sector_tr_index = (1 + sector_ret).cumprod() * 100.0

    scores = sig.momentum_scores(sector_tr_index, s["lookbacks_months"],
                                 s["lookback_weights"])
    ev = db.events_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                        vintage=d["vintage"] or None)

    # ---- benchmark ---------------------------------------------------------
    lv = db.index_levels_asof(con, d["sim_end"], [d["benchmark"]],
                              min_confidence=d["min_confidence"],
                              vintage=d["vintage"] or None, sources=d["sources"])
    bench = lv.pivot(index="trade_date", columns="index_code",
                     values="close_value")[d["benchmark"]]
    bench.index = pd.to_datetime(bench.index)

    # ---- rebalance schedule ------------------------------------------------
    window = px.loc[d["sim_start"]:d["sim_end"]].index
    fee_rates = _fee_rates(db.cost_schedule_asof(con, d["sim_end"]),
                           c["brokerage_override_pct"])
    sig_dates = [t for t in scores.index if t in window]
    if p["rebalance"] == "quarterly":
        sig_dates = sig_dates[::3]
    pos = {t: i for i, t in enumerate(window)}
    exec_map, exclusions = {}, {}
    for sd in sig_dates:
        i = pos[sd] + p["execution_lag_days"]
        if i >= len(window):
            continue
        excl = (sig.excluded_sectors(ev, sd, p["impairment_window_months"])
                if p["catalyst_filter"] else set())
        exec_map[window[i]] = sig.select_top_n(scores.loc[sd], p["top_n"], excl,
                                               p["construction"])
        if excl:
            exclusions[str(window[i].date())] = sorted(excl)
    if not exec_map:
        raise ValueError("no executable rebalances in window")
    first_exec = min(exec_map)

    # ---- daily loop ---------------------------------------------------------
    h = pd.Series(0.0, index=px.columns)          # holdings, fractions of NAV
    attribution = dict.fromkeys(COST_COMPONENTS, 0.0)
    sector_contrib = dict.fromkeys(d["universe"], 0.0)
    cap_records, wrows, turn, cost_rows = [], [], [], []
    net, gross = [], []
    n_legs = n_clipped = 0
    max_participation = 0.0

    for t in window:
        if t < first_exec:
            continue
        r_today = ret.loc[t].fillna(0.0)
        r_gross = float((h * r_today).sum())
        for sec in d["universe"]:
            ms = members(sec, t)
            sector_contrib[sec] += float((h[ms] * r_today[ms]).sum()) if ms else 0.0
        h = h * (1 + r_today)
        nav_growth = 1 + r_gross
        h = h / nav_growth if nav_growth > 0 else h * 0.0

        cost_total = 0.0
        if t in exec_map:
            sec_tgt = exec_map[t]
            tgt = pd.Series(0.0, index=px.columns)
            for sec, wsec in sec_tgt[sec_tgt > 0].items():
                ww = within_weights(sec, t)
                tgt[ww.index] += wsec * ww
            desired = tgt - h
            traded = desired[desired.abs() > 1e-9]

            # capacity: max AUM at which every DESIRED trade fits its cap
            adtv_t = adtv.loc[t].reindex(traded.index).fillna(0.0)
            with np.errstate(divide="ignore"):
                per_name_cap_aum = (cap * adtv_t / traded.abs()).replace(0.0, np.nan)
            if per_name_cap_aum.notna().any():
                bottleneck = per_name_cap_aum.idxmin()
                cap_records.append(dict(
                    date=str(t.date()), max_aum_ngn=float(per_name_cap_aum.min()),
                    bottleneck=bottleneck,
                    n_violations_at_aum=int((per_name_cap_aum < aum).sum())))

            # execute with participation cap; excess is rejected
            cap_frac = (cap * adtv_t / aum)
            executed = desired.copy()
            executed[traded.index] = traded.clip(lower=-cap_frac, upper=cap_frac)
            clipped = traded.index[traded.abs() > cap_frac + 1e-12]
            n_legs += len(traded)
            n_clipped += len(clipped)
            part = (executed[traded.index].abs() * aum /
                    adtv_t.replace(0.0, np.nan)).dropna()
            if len(part):
                max_participation = max(max_participation, float(part.max()))

            buys = executed.clip(lower=0.0)
            sells = (-executed).clip(lower=0.0)
            items = _line_item_costs(buys, sells, fee_rates)
            items["slippage"] = slip_rate * float(executed.abs().sum())
            impact = impact_coeff * np.sqrt(part.clip(lower=0.0)) * \
                executed[part.index].abs()
            items["market_impact"] = float(impact.sum())
            for k, v in items.items():
                attribution[k] += v
            cost_total = sum(items.values())
            h = h + executed
            wrows.append(sec_tgt.rename(t))
            turn.append(pd.Series(float(buys.sum()), index=[t]))
            cost_rows.append(pd.Series(cost_total, index=[t]))

        gross.append(r_gross)
        net.append(r_gross - cost_total)

    idx = window[window >= first_exec]
    return FullResult(
        net_returns=pd.Series(net, index=idx),
        gross_returns=pd.Series(gross, index=idx),
        weights=pd.DataFrame(wrows),
        turnover=pd.concat(turn),
        costs=pd.concat(cost_rows),
        benchmark_returns=bench.reindex(idx).pct_change().fillna(0.0),
        attribution=attribution,
        capacity_records=cap_records,
        clip_stats={"trade_legs": n_legs, "legs_rejected_for_liquidity": n_clipped,
                    "pct_legs_rejected": round(100 * n_clipped / n_legs, 2) if n_legs else 0.0,
                    "max_participation_pct": round(100 * max_participation, 2)},
        sector_contribution={k: round(v, 4) for k, v in sector_contrib.items()},
        exclusions=exclusions,
        tr_adjustments=n_adj,
        unadjusted_action_types=sorted(unadjusted),
    )


def capacity_report(result: FullResult, aum: float) -> dict:
    """Capacity as a distribution — a first-class research output."""
    if not result.capacity_records:
        return {"n_rebalances": 0}
    df = pd.DataFrame(result.capacity_records)
    bn = df.bottleneck.value_counts()
    return {
        "median_capacity_ngn": float(df.max_aum_ngn.median()),
        "worst_capacity_ngn": float(df.max_aum_ngn.min()),
        "worst_capacity_date": df.loc[df.max_aum_ngn.idxmin(), "date"],
        "p25_capacity_ngn": float(df.max_aum_ngn.quantile(0.25)),
        "bottleneck_constituents": bn.head(5).to_dict(),
        "n_rebalances_with_violations_at_aum": int((df.n_violations_at_aum > 0).sum()),
        "configured_aum_ngn": aum,
        **result.clip_stats,
    }
