"""Cross-sectional per-stock backtest engine (engine.type = "cross_sectional").

Approved 2026-07-22 to unlock per-stock factor research (H-006/H-007).
EXTENDS the platform: slots into runner.run_resolved beside lite/full and
inherits every guard (registry, holdout, coverage gate, vintage pinning).

Modes (signal.method):
  xs_rank    — rank portfolios: at each formation date, score IRU members,
               hold the top_n equal-weighted until the next formation
               (H-007 momentum: trailing formation-window return with a
               skip month).
  xs_vol     — low-volatility: score = negative trailing realized vol.
  xs_size    — size: score = negative market cap (long the SMALLEST names
               by count, standard SMB convention). Cap series comes from
               data/reference/market_cap_panel.csv (LIST2-derived,
               validated 2026-07-22, full-issue/not float-adjusted — a
               disclosed limitation, see load_market_cap_panel). Approved
               2026-07-22 for H-011 (Wave 3 candidate C4).
  xs_liquidity — liquidity: score = standardized trailing 60-day ADTV,
               signed by signal.direction ("illiquid": negative, long the
               LEAST liquid names, classic Amihud & Mendelson 1986 premium
               direction; "liquid": positive, long the MOST liquid names).
               Optional signal.min_adtv_ngn applies an additional
               eligibility floor for the Economic Capacity Validation
               ladder. H-016, pre-registered docs/PREREG_H-016_liquidity.md
               (2026-08-03) -- both directions are open questions, neither
               assumed correct in advance.
  xs_event   — event book: pre-registered event set -> reaction-ranked
               selections enter at a fixed lag, hold a fixed number of
               sessions, sized 1/max_concurrent of NAV each; residual NAV
               sits in the EW-IRU benchmark sleeve as a synthetic asset
               whose daily return is the benchmark's NET return. Moving
               between sleeve and stock pays BOTH legs' costs.

Accounting (mirrors backtest_lite semantics):
  - weights drift with returns between rebalances; execution at the close
    of the execution day; costs (buy/sell per side) deducted from that
    day's net return; turnover measured one-way against drifted weights.
  - closes are forward-filled for NAV accounting ONLY (an NGX official
    close persists on non-traded days — carrying it is not fabrication);
    eligibility/scoring use actual-observation counts.
  - price-only returns (no dividend reinvestment) — flagged upstream.

The benchmark (EW-IRU: ALL eligible members equal-weighted, same rebalance
calendar, same cost model) is computed by this engine itself — it is the
investable null strategy, not an index.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import db, universe

PKG_ROOT = Path(__file__).resolve().parents[2]
ENGINE_VERSION = "xs_v1"


@dataclass
class XSResult:
    net_returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    exclusions: dict = field(default_factory=dict)
    benchmark_returns: pd.Series | None = None
    sector_contribution: dict = field(default_factory=dict)  # per-ticker here
    attribution: dict = field(default_factory=dict)
    tr_adjustments: int = 0


# ---------------------------------------------------------------------------
# panel loading
# ---------------------------------------------------------------------------

def load_panel(con, cfg) -> dict:
    """Wide matrices on CANONICAL tickers (verified renames stitched):
    closes (ffilled), obs (bool, actually-traded), adtv60 (value_traded
    rolling mean). PIT: vintage- and confidence-pinned reads only."""
    d = cfg["data"]
    px = db.equity_prices_asof(con, d["sim_end"],
                               min_confidence=d["min_confidence"],
                               vintage=d["vintage"] or None)
    if px.empty:
        raise RuntimeError("equity panel empty under this config's "
                           "confidence/vintage")
    chain = universe.rename_chain()
    px["ticker"] = px.ticker.map(lambda t: chain.get(t, t))
    px = px.drop_duplicates(subset=["ticker", "trade_date"], keep="last")
    close = px.pivot(index="trade_date", columns="ticker", values="close")
    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    obs = close.notna()
    val = px.pivot(index="trade_date", columns="ticker", values="value_traded")
    val.index = pd.to_datetime(val.index)
    adtv60 = val.sort_index().rolling(60, min_periods=10).mean()
    return {"close_ff": close.ffill(), "obs": obs, "adtv60": adtv60,
            "min_conf_seen": float(px.confidence.min())}


def load_market_cap_panel(close_ff: pd.DataFrame) -> pd.DataFrame:
    """Wide (trade_date x ticker) market cap (NGN millions, full-issue —
    NOT float-adjusted; disclosed limitation, see module docstring).

    The raw panel only has rows on days LIST2 existed (2016-03 onward,
    ~77% of days per market_cap_validation.md). Rather than forward-fill
    the CAP LEVEL itself (which would freeze it across price moves), we
    forward-fill the IMPLIED SHARE COUNT (market_cap / close) — the
    quantity market_cap_validation.md already validated as stable
    between corporate actions (0.39% day-over-day jump rate >2%) — and
    reconstruct cap_t = shares_ffilled_t * close_t. This tracks real
    price movement on non-LIST2 days instead of freezing, without
    asserting anything beyond what was already validated."""
    path = PKG_ROOT / "data" / "reference" / "market_cap_panel.csv"
    raw = pd.read_csv(path)
    chain = universe.rename_chain()
    raw["symbol"] = raw.symbol.map(lambda t: chain.get(t, t))
    raw = raw.drop_duplicates(subset=["symbol", "trade_date"], keep="last")
    mcap = raw.pivot(index="trade_date", columns="symbol", values="market_cap_nm")
    mcap.index = pd.to_datetime(mcap.index)
    # LIST2 carries a few symbols (bonds/REITs/pre-merger names) absent
    # from the validated price panel — restrict BEFORE any arithmetic:
    # DataFrame division aligns on the UNION of columns, so dividing by a
    # column-subset silently widens the result back to the mismatched
    # full set (columns missing from the divisor become all-NaN, not
    # dropped) rather than restricting to the intersection as intended.
    common = mcap.columns.intersection(close_ff.columns)
    mcap = mcap[common]
    close_aligned = close_ff.reindex(index=mcap.index.union(close_ff.index))
    mcap = mcap.reindex(close_aligned.index)
    shares = (mcap / close_aligned[common]).ffill()
    return (shares * close_aligned[common]).reindex(close_ff.index)


def _month_ends(dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(dates, index=dates)
    return list(s.groupby(s.index.to_period("M")).max())


# ---------------------------------------------------------------------------
# core daily simulator
# ---------------------------------------------------------------------------

def simulate(close_ff: pd.DataFrame, targets: dict, buy_rate: float,
             sell_rate: float, sim_start: str, sim_end: str,
             bench_net: pd.Series | None = None) -> XSResult:
    """targets: {execution_date -> Series(target weights)}; a "BENCH"
    weight entry rides ``bench_net`` (the benchmark sleeve)."""
    daily = close_ff.loc[sim_start:sim_end]
    R = daily.pct_change().fillna(0.0)
    if bench_net is not None:
        R = R.copy()
        R["BENCH"] = bench_net.reindex(R.index).fillna(0.0)
    dates = R.index

    w = pd.Series(dtype=float)
    net, gross, tos, csts, wrows = [], [], [], [], {}
    contrib: dict[str, float] = {}
    exec_dates = {pd.Timestamp(k): v for k, v in targets.items()}
    for dt in dates:
        r_assets = R.loc[dt]
        day_gross = float((w * r_assets.reindex(w.index).fillna(0.0)).sum()) \
            if len(w) else 0.0
        for t_, wt in w.items():
            contrib[t_] = contrib.get(t_, 0.0) + \
                wt * float(r_assets.get(t_, 0.0))
        day_net = day_gross
        if len(w):  # drift
            grown = w * (1 + r_assets.reindex(w.index).fillna(0.0))
            tot = grown.sum()
            w = grown / tot if tot > 0 else grown
        if dt in exec_dates:
            tgt = exec_dates[dt].astype(float)
            tgt = tgt[tgt > 0]
            all_ix = w.index.union(tgt.index)
            old = w.reindex(all_ix).fillna(0.0)
            new = tgt.reindex(all_ix).fillna(0.0)
            buys = (new - old).clip(lower=0).sum()
            sells = (old - new).clip(lower=0).sum()
            cost = buys * buy_rate + sells * sell_rate
            day_net -= cost
            tos.append(pd.Series({dt: buys}))
            csts.append(pd.Series({dt: cost}))
            wrows[dt] = tgt
            w = tgt.copy()
        net.append(day_net)
        gross.append(day_gross)

    turnover = pd.concat(tos) if tos else pd.Series(dtype=float)
    costs_s = pd.concat(csts) if csts else pd.Series(dtype=float)
    weights = pd.DataFrame(wrows).T.fillna(0.0) if wrows \
        else pd.DataFrame(index=pd.DatetimeIndex([]))
    return XSResult(
        net_returns=pd.Series(net, index=dates),
        gross_returns=pd.Series(gross, index=dates),
        weights=weights, turnover=turnover, costs=costs_s,
        sector_contribution={k: round(v, 5) for k, v in
                             sorted(contrib.items(), key=lambda kv: -kv[1])})


# ---------------------------------------------------------------------------
# eligibility + rank targets
# ---------------------------------------------------------------------------

def _eligible(con, panel, f: pd.Timestamp, iru_rules,
              min_obs: int, window_days: int) -> list[str]:
    mem = set(universe.iru_members(con, f.strftime("%Y-%m-%d"), iru_rules).ticker)
    obs = panel["obs"]
    lo = f - pd.Timedelta(days=window_days)
    counts = obs.loc[lo:f].sum()
    ok = set(counts[counts >= min_obs].index)
    return sorted(mem & ok & set(panel["close_ff"].columns))


def rank_scores(con, panel, cfg) -> dict:
    """{formation_date -> Series(score)} for xs_rank. Formation return =
    close[f - skip months] / close[f - formation months] - 1 on stitched
    (ffilled) closes, eligibility on actual observations.

    cohort_offset_months (default 0, backward-compatible): shifts WHICH
    month-ends are selected by the rebalance step, without changing the
    step itself. Used by pooled_rank_run to give each cohort in a
    multi-cohort design its own staggered formation calendar — e.g.
    step=12 (annual) with offset=3 selects month-ends 3, 15, 27, ... .
    offset=0 (every prior xs_rank config) reproduces the ORIGINAL
    calendar exactly — this is a strict extension, not a behavior change."""
    s, d = cfg["signal"], cfg["data"]
    fm, skip = int(s["formation_months"]), int(s["skip_months"])
    offset = int(s.get("cohort_offset_months", 0))
    close = panel["close_ff"]
    dates = close.loc[:d["sim_end"]].index
    formations = _month_ends(dates)
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = formations[::step] if step == 1 else [
        f for i, f in enumerate(formations) if (i - offset) % step == 0]
    iru_rules = universe.load_rules()
    out = {}
    for f in formations:
        if f < pd.Timestamp(d["sim_start"]):
            continue
        f_hi = f - pd.DateOffset(months=skip)
        f_lo = f - pd.DateOffset(months=fm)
        if f_lo < dates[0]:
            continue
        hi = close.loc[:f_hi]
        lo = close.loc[:f_lo]
        if hi.empty or lo.empty:
            continue
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)),
                         int(fm * 31))
        if len(elig) < 10:
            continue
        ret = hi.iloc[-1][elig] / lo.iloc[-1][elig] - 1
        ret = ret.dropna()
        if ret.std() > 0:
            out[f] = (ret - ret.mean()) / ret.std()
    return out


def vol_scores(con, panel, cfg) -> dict:
    """{formation_date -> Series(score)} for xs_vol (low-volatility factor).
    Score = NEGATIVE standardized trailing realized volatility (annualized
    daily-return std over the lookback window), so nlargest in
    targets_from_scores selects the LOWEST-volatility names — reuses the
    momentum selection/simulation path unchanged; only the score
    construction differs."""
    s, d = cfg["signal"], cfg["data"]
    lb = int(s["vol_lookback_months"])
    close = panel["close_ff"]
    dates = close.loc[:d["sim_end"]].index
    formations = _month_ends(dates)
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = formations[::step] if step == 1 else [
        f for i, f in enumerate(formations) if i % step == 0]
    iru_rules = universe.load_rules()
    ret_all = close.pct_change()
    out = {}
    for f in formations:
        if f < pd.Timestamp(d["sim_start"]):
            continue
        f_lo = f - pd.DateOffset(months=lb)
        if f_lo < dates[0]:
            continue
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)), int(lb * 31))
        if len(elig) < 10:
            continue
        # realized vol on ACTUALLY-TRADED sessions only (obs mask) — ffilled
        # closes would understate vol for stale names by injecting zero-
        # return days that never happened
        obs = panel["obs"].loc[f_lo:f, elig]
        window_ret = ret_all.loc[f_lo:f, elig].where(obs)
        vol = window_ret.std() * (252 ** 0.5)
        vol = vol.dropna()
        vol = vol[vol > 0]
        if vol.std() > 0:
            z = (vol - vol.mean()) / vol.std()
            out[f] = -z          # lower vol -> higher score
    return out


def size_scores(con, panel, cfg) -> dict:
    """{formation_date -> Series(score)} for xs_size. Score = NEGATIVE
    standardized market cap at the formation date, so nlargest in
    targets_from_scores selects the SMALLEST names (standard SMB
    convention: size premium is long-small). Requires panel["mcap"]
    (see load_market_cap_panel) — populated lazily by run_from_config /
    placebo_stats only when this method is used, since it's a CSV read
    the other signal methods don't need."""
    s, d = cfg["signal"], cfg["data"]
    mcap = panel["mcap"]
    close = panel["close_ff"]
    dates = close.loc[:d["sim_end"]].index
    formations = _month_ends(dates)
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = formations[::step] if step == 1 else [
        f for i, f in enumerate(formations) if i % step == 0]
    iru_rules = universe.load_rules()
    out = {}
    for f in formations:
        if f < pd.Timestamp(d["sim_start"]) or f not in mcap.index:
            continue
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)),
                         int(s.get("lookback_months", 12) * 31))
        # elig comes from the price panel; mcap is restricted to symbols
        # LIST2 ever covered (from 2016-03) — pre-2016/never-covered IRU
        # members must be filtered here, not assumed present (.loc with a
        # missing label raises; .reindex would silently invent NaN rows,
        # which is fine too but filtering first keeps the eligibility
        # count in the diagnostics honest about what was actually usable)
        avail = [t for t in elig if t in mcap.columns]
        cap = mcap.loc[f, avail].dropna()
        cap = cap[cap > 0]
        if len(cap) < 10:
            continue
        z = (cap - cap.mean()) / cap.std()
        if cap.std() > 0:
            out[f] = -z          # smaller cap -> higher score
    return out


def liquidity_scores(con, panel, cfg) -> dict:
    """{formation_date -> Series(score)} for the Liquidity dimension of an
    interaction test (Phase R2, 2026-08-03). Score = NEGATIVE standardized
    trailing 60-day ADTV — panel["adtv60"] is ALREADY computed by
    load_panel (used today only for capacity_report); this reuses it as-is,
    no new data. nlargest therefore selects the LEAST-liquid names,
    consistent with the economic prior that illiquidity commands a return
    premium (Amihud & Mendelson, 1986) already used to frame this
    dimension in docs/FACTOR_CANDIDATE_REGISTRY.md. NOT wired into
    scores_for_method/xs_rank et al — this is a new dimension consumed
    only by xs_size_interaction below, not a standalone tradeable Liquidity
    factor method (that remains a separate, not-yet-run candidate)."""
    s, d = cfg["signal"], cfg["data"]
    close = panel["close_ff"]
    adtv60 = panel["adtv60"]
    dates = close.loc[:d["sim_end"]].index
    formations = _month_ends(dates)
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = formations[::step] if step == 1 else [
        f for i, f in enumerate(formations) if i % step == 0]
    iru_rules = universe.load_rules()
    out = {}
    for f in formations:
        if f < pd.Timestamp(d["sim_start"]) or f not in adtv60.index:
            continue
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)),
                         int(s.get("lookback_months", 12) * 31))
        if len(elig) < 10:
            continue
        adtv = adtv60.loc[f, elig].dropna()
        adtv = adtv[adtv > 0]
        if len(adtv) < 10 or adtv.std() == 0:
            continue
        z = (adtv - adtv.mean()) / adtv.std()
        out[f] = -z          # least liquid -> higher score
    return out


def xs_liquidity_scores(con, panel, cfg) -> dict:
    """{formation_date -> Series(score)} for xs_liquidity (H-016, standalone
    Liquidity factor -- docs/PREREG_H-016_liquidity.md). Reuses
    panel["adtv60"] (already computed by load_panel) -- no new data source.
    Distinct from Phase R2's liquidity_scores() (frozen, consumed only by
    xs_size_interaction): this function supports both pre-registered
    directions via signal.direction --

      "illiquid" (Leg A, classic Amihud & Mendelson 1986 direction):
          score = NEGATIVE standardized ADTV, nlargest selects the LEAST
          liquid names.
      "liquid" (Leg B, the direction H-013's own evidence hints at):
          score = POSITIVE standardized ADTV, nlargest selects the MOST
          liquid names.

    -- and an optional signal.min_adtv_ngn floor: the Economic Capacity
    Validation filter ladder (prereg Section 10), applied as an ADDITIONAL
    eligibility gate on top of the existing breadth guard below, never a
    change to that guard itself. Default 0.0 reproduces the unfiltered
    base configuration exactly."""
    s, d = cfg["signal"], cfg["data"]
    direction = s.get("direction", "illiquid")
    if direction not in ("illiquid", "liquid"):
        raise ValueError(f"xs_liquidity_scores: unknown direction {direction!r}")
    min_adtv_ngn = float(s.get("min_adtv_ngn", 0.0))
    close = panel["close_ff"]
    adtv60 = panel["adtv60"]
    dates = close.loc[:d["sim_end"]].index
    formations = _month_ends(dates)
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = formations[::step] if step == 1 else [
        f for i, f in enumerate(formations) if i % step == 0]
    iru_rules = universe.load_rules()
    out = {}
    for f in formations:
        if f < pd.Timestamp(d["sim_start"]) or f not in adtv60.index:
            continue
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)),
                         int(s.get("lookback_months", 12) * 31))
        if len(elig) < 10:
            continue
        adtv = adtv60.loc[f, elig].dropna()
        adtv = adtv[adtv > 0]
        if min_adtv_ngn > 0:
            adtv = adtv[adtv >= min_adtv_ngn]
        if len(adtv) < 10 or adtv.std() == 0:
            continue
        z = (adtv - adtv.mean()) / adtv.std()
        out[f] = z if direction == "liquid" else -z
    return out


REBALANCE_STEP_MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6,
                         "annual": 12}


def scores_for_method(con, panel, cfg) -> dict:
    method = cfg["signal"]["method"]
    if method == "xs_rank":
        return rank_scores(con, panel, cfg)
    if method == "xs_vol":
        return vol_scores(con, panel, cfg)
    if method == "xs_size":
        return size_scores(con, panel, cfg)
    if method == "xs_liquidity":
        return xs_liquidity_scores(con, panel, cfg)
    raise ValueError(f"scores_for_method: unsupported method {method!r}")


def targets_from_scores(scores: dict, close_index: pd.DatetimeIndex,
                        top_n: int, lag: int) -> dict:
    pos = {dt: i for i, dt in enumerate(close_index)}
    targets = {}
    for f, sc in scores.items():
        i = pos.get(f)
        if i is None or i + lag >= len(close_index):
            continue
        sel = sc.nlargest(min(top_n, len(sc)))
        targets[close_index[i + lag]] = pd.Series(1.0 / len(sel),
                                                  index=sel.index)
    return targets


def benchmark_targets(con, panel, cfg, lag: int) -> dict:
    """EW over ALL eligible members at the same formation calendar."""
    s, d = cfg["signal"], cfg["data"]
    close = panel["close_ff"]
    dates = close.loc[:d["sim_end"]].index
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    formations = [f for i, f in enumerate(_month_ends(dates))
                  if i % step == 0 and f >= pd.Timestamp(d["sim_start"])]
    iru_rules = universe.load_rules()
    pos = {dt: i for i, dt in enumerate(dates)}
    out = {}
    for f in formations:
        elig = _eligible(con, panel, f, iru_rules,
                         int(s.get("min_obs_formation", 120)),
                         int(s.get("formation_months", 12) * 31))
        i = pos.get(f)
        if not elig or i is None or i + lag >= len(dates):
            continue
        out[dates[i + lag]] = pd.Series(1.0 / len(elig), index=elig)
    return out


# ---------------------------------------------------------------------------
# pooled overlapping-cohort momentum (E1, 2026-07-22 — unlocks H-010 /
# Wave-3 candidate C1). Design decision, stated explicitly because it was
# not the only option: N independent, equally-sized (1/N of NAV each)
# sub-portfolios, each running the EXACT same single-cohort xs_rank
# machinery (rank_scores + targets_from_scores + simulate, UNCHANGED) on
# its own formation calendar, offset by (rebalance_step_months / N) from
# the others. The aggregate portfolio's returns are the equal-weighted
# BLEND of the N cohorts' own return series.
#
# This was chosen over a single unified target-weight vector with partial
# per-date rebalancing (only cohort c's slice changes, others hold their
# CURRENT DRIFTED weights) because that design requires the simulator to
# track live drifted state at arbitrary rebalance dates and inject it back
# into a "full target vector" correctly -- a real correctness trap. The
# blend-at-return-level design achieves the identical economic exposure
# (N staggered sleeves, each low-turnover on its own annual/semiannual
# cycle) while reusing simulate() completely unchanged and avoiding that
# trap entirely.
#
# Cohort correlation is measured and returned explicitly, never assumed
# — this is the specific failure risk PREREG_H-010 (once drafted) must
# report: if offset formation dates just reproduce near-identical
# rankings, the "N independent bets" claim is false regardless of how
# clean the code is.

def pooled_rank_run(con, cfg, rates) -> tuple[XSResult, dict]:
    """Returns (blended XSResult, diagnostics) where diagnostics includes
    the actual measured pairwise cohort return-correlation matrix and a
    per-cohort turnover breakdown — required reading before trusting any
    power gain this construction appears to produce."""
    d, s, p = cfg["data"], cfg["signal"], cfg["portfolio"]
    n = int(s["n_cohorts"])
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    if step % n != 0:
        raise ValueError(f"n_cohorts={n} must evenly divide the rebalance "
                         f"step ({cfg['portfolio']['rebalance']} = "
                         f"{step} months) — refusing to silently "
                         f"mis-space cohorts")
    offset_step = step // n
    panel = load_panel(con, cfg)
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])

    cohort_results, cohort_caps, cohort_targets = [], [], []
    for c in range(n):
        cfg_c = {**cfg, "signal": {**s, "cohort_offset_months": c * offset_step}}
        scores_c = rank_scores(con, panel, cfg_c)
        targets_c = targets_from_scores(
            scores_c, close.loc[:d["sim_end"]].index, int(p["top_n"]), lag)
        if not targets_c:
            raise RuntimeError(f"cohort {c} (offset {c * offset_step}mo) "
                               f"produced no target dates")
        res_c = simulate(close, targets_c, rates["buy_rate"],
                         rates["sell_rate"], d["sim_start"], d["sim_end"])
        cohort_results.append(res_c)
        cohort_targets.append(targets_c)
        # capacity per cohort at its OWN allocated slice of AUM (1/n) — a
        # single unified target vector across cohorts would corrupt
        # capacity_report's delta logic (it would see other cohorts'
        # untouched holdings as "sold"); computing per-cohort keeps each
        # cohort's own full target dict internally consistent.
        cohort_caps.append(capacity_report(
            targets_c, panel["adtv60"], cfg["engine"]["aum_ngn"] / n,
            cfg["liquidity"]["adtv_participation_cap_pct"]))

    net = pd.concat([r.net_returns for r in cohort_results], axis=1).mean(axis=1)
    gross = pd.concat([r.gross_returns for r in cohort_results], axis=1).mean(axis=1)
    # aggregate turnover/cost as a FRACTION OF TOTAL NAV: each cohort only
    # represents 1/n of NAV, so its own (100%-of-its-slice) turnover/cost
    # series must be divided by n before summing across cohorts' dates
    turnover = (pd.concat([r.turnover for r in cohort_results])
               .groupby(level=0).sum() / n)
    costs = (pd.concat([r.costs for r in cohort_results])
            .groupby(level=0).sum() / n)

    bt = benchmark_targets(con, panel, cfg, lag)
    bench = simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                     d["sim_start"], d["sim_end"])

    # E16 fix (2026-07-22): weights was previously an empty DataFrame,
    # which silently zeroed metrics.compute's n_rebalances (it reads
    # len(result.weights.index)) and hit_rate_vs_benchmark for every
    # pooled hypothesis — H-010's confidence rating showed "0 decisions"
    # when the true count was ~36 (4 cohorts x ~9 formations each).
    # Build the UNION of every cohort's own execution dates, each row
    # showing whichever cohort(s) actually traded that day at their
    # already-scaled (1/n) weight — genuine per-date trading metadata,
    # not a placeholder, and correct for metrics.compute's purposes
    # (which only reads the DataFrame's .index for dates; cell values
    # are not used to reconstruct portfolio state elsewhere).
    weight_rows: dict = {}
    for targets_c in cohort_targets:
        for dt, w in targets_c.items():
            row = weight_rows.setdefault(dt, {})
            for tick, wt in (w / n).items():
                row[tick] = row.get(tick, 0.0) + wt
    weights = (pd.DataFrame(weight_rows).T.fillna(0.0).sort_index()
              if weight_rows else pd.DataFrame())

    result = XSResult(net_returns=net, gross_returns=gross,
                      weights=weights, turnover=turnover, costs=costs,
                      benchmark_returns=bench.net_returns)

    cohort_net = pd.concat([r.net_returns.rename(f"cohort_{i}")
                           for i, r in enumerate(cohort_results)], axis=1)
    valid_caps = [c for c in cohort_caps if c]
    agg_cap = {}
    if valid_caps:
        agg_cap = {
            "median_capacity_ngn": float(np.median(
                [c["median_capacity_ngn"] for c in valid_caps])),
            "worst_capacity_ngn": float(min(
                c["worst_capacity_ngn"] for c in valid_caps)),
            "pct_legs_rejected": float(np.mean(
                [c["pct_legs_rejected"] for c in valid_caps])),
            "configured_aum_ngn": cfg["engine"]["aum_ngn"],
            "per_cohort": cohort_caps,
        }
    diagnostics = {
        "n_cohorts": n, "offset_months": offset_step,
        "cohort_return_correlation": cohort_net.corr().round(3).to_dict(),
        "cohort_ann_turnover_oneway": [
            round(float(r.turnover.sum() / (len(r.net_returns) / 252)), 3)
            for r in cohort_results],
        "capacity": agg_cap,
    }
    return result, diagnostics


# ---------------------------------------------------------------------------
# event mode (H-006 PEAD)
# ---------------------------------------------------------------------------

def event_selections(con, panel, cfg, bench_net: pd.Series) -> list[dict]:
    """Pre-registered PEAD event pipeline -> [{entry, exit, ticker, z}].
    Reaction AR over t0..t0+2 vs benchmark; monthly cohorts standardized;
    top fraction selected; entry t0+3, hold ``hold_sessions``."""
    s, d = cfg["signal"], cfg["data"]
    cal = pd.read_csv(PKG_ROOT / s["event_calendar"])
    cal = cal[cal.submission_type.astype(str).str.strip()
              .str.startswith("Financial Statements")]
    chain = universe.rename_chain()
    cal["symbol"] = cal.symbol.map(lambda t: chain.get(t, t))
    cal["ts"] = pd.to_datetime(cal.created.str[:19], errors="coerce")
    cal = cal.dropna(subset=["ts"])
    cal = cal[(cal.ts >= d["sim_start"]) & (cal.ts <= d["sim_end"])]

    close = panel["close_ff"]
    obs = panel["obs"]
    dates = close.index
    date_arr = np.array(dates)
    iru_rules = universe.load_rules()
    iru_cache: dict[str, set] = {}

    def t0_of(ts: pd.Timestamp):
        day = ts.normalize()
        j = np.searchsorted(date_arr, np.datetime64(day))
        if j < len(dates) and dates[j] == day and ts.hour * 60 + ts.minute <= 870:
            return j
        while j < len(dates) and dates[j] <= day:
            j += 1
        return j if j < len(dates) else None

    events = []
    last_seen: dict[str, int] = {}
    for r in cal.sort_values("ts").itertuples():
        j = t0_of(r.ts)
        if j is None or j + 2 >= len(dates) or r.symbol not in close.columns:
            continue
        if r.symbol in last_seen and j - last_seen[r.symbol] < 5:
            continue          # 5-session dedupe: first filing wins
        last_seen[r.symbol] = j
        t0 = dates[j]
        mkey = t0.strftime("%Y-%m")
        if mkey not in iru_cache:
            iru_cache[mkey] = set(universe.iru_members(
                con, t0.strftime("%Y-%m-%d"), iru_rules).ticker)
        if r.symbol not in iru_cache[mkey]:
            continue
        if obs.iloc[j:j + 3][r.symbol].sum() < 2:
            continue          # liquidity screen: >=2 traded of 3 sessions
        stk = close[r.symbol].iloc[j + 2] / close[r.symbol].iloc[j - 1] - 1
        b = bench_net.reindex(dates[j:j + 3]).fillna(0.0)
        ar = stk - float((1 + b).prod() - 1)
        events.append(dict(j=j, cohort=mkey, ticker=r.symbol, ar=ar))

    ev = pd.DataFrame(events)
    if ev.empty:
        return []
    ev["z"] = ev.groupby("cohort").ar.transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else np.nan)
    ev = ev.dropna(subset=["z"])
    frac = float(s.get("select_fraction", 1 / 3))
    thresh = ev.groupby("cohort").z.transform(lambda x: x.quantile(1 - frac))
    sel = ev[ev.z >= thresh]
    hold, lag = int(s["hold_sessions"]), int(s.get("entry_lag_sessions", 3))
    out = []
    for r in sel.itertuples():
        i_in = r.j + lag
        i_out = min(i_in + hold, len(dates) - 1)
        if i_in >= len(dates) - 1:
            continue
        out.append(dict(entry=dates[i_in], exit=dates[i_out],
                        ticker=r.ticker, z=float(r.z)))
    return out


def event_targets(selections: list[dict], dates: pd.DatetimeIndex,
                  max_concurrent: int) -> dict:
    """Book of 1/max_concurrent-sized positions + BENCH residual. When more
    candidates than slots, highest z wins (pre-registered tiebreak)."""
    changes: dict[pd.Timestamp, list] = {}
    for s_ in selections:
        changes.setdefault(s_["entry"], []).append(("in", s_))
        changes.setdefault(s_["exit"], []).append(("out", s_))
    active: dict[str, dict] = {}
    targets = {}
    wsize = 1.0 / max_concurrent
    for dt in sorted(changes):
        for kind, s_ in changes[dt]:
            key = f"{s_['ticker']}@{s_['entry']:%Y%m%d}"
            if kind == "out":
                active.pop(key, None)
            else:
                if len(active) >= max_concurrent:
                    worst = min(active, key=lambda k: active[k]["z"])
                    if active[worst]["z"] < s_["z"]:
                        active.pop(worst)
                    else:
                        continue
                active[key] = s_
        w = pd.Series(dtype=float)
        for s_ in active.values():
            w[s_["ticker"]] = w.get(s_["ticker"], 0.0) + wsize
        w["BENCH"] = max(0.0, 1.0 - float(w.sum()))
        targets[dt] = w
    return targets


# ---------------------------------------------------------------------------
# capacity
# ---------------------------------------------------------------------------

def capacity_report(targets: dict, adtv60: pd.DataFrame, aum: float,
                    participation_pct: float) -> dict:
    cap_frac = participation_pct / 100.0
    legs, rejected, worst = [], 0, (None, None)
    bottleneck: dict[str, int] = {}
    prev: pd.Series = pd.Series(dtype=float)
    for dt in sorted(targets):
        tgt = targets[dt]
        all_ix = prev.index.union(tgt.index)
        delta = (tgt.reindex(all_ix).fillna(0.0)
                 - prev.reindex(all_ix).fillna(0.0)).abs()
        for tick, dw in delta.items():
            if tick == "BENCH" or dw < 1e-6:
                continue
            adtv = adtv60[tick].asof(dt) if tick in adtv60.columns else np.nan
            if pd.isna(adtv) or adtv <= 0:
                continue
            leg_cap = cap_frac * float(adtv) / dw
            legs.append(leg_cap)
            if dw * aum > cap_frac * float(adtv):
                rejected += 1
                bottleneck[tick] = bottleneck.get(tick, 0) + 1
            if worst[0] is None or leg_cap < worst[0]:
                worst = (leg_cap, dt)
        prev = tgt
    if not legs:
        return {}
    s = pd.Series(legs)
    return {
        "median_capacity_ngn": float(s.median()),
        "p25_capacity_ngn": float(s.quantile(0.25)),
        "worst_capacity_ngn": float(worst[0]),
        "worst_capacity_date": str(pd.Timestamp(worst[1]).date()),
        "pct_legs_rejected": round(100.0 * rejected / len(legs), 1),
        "configured_aum_ngn": aum,
        "n_legs": len(legs),
        "bottleneck_constituents": dict(sorted(
            bottleneck.items(), key=lambda kv: -kv[1])[:5]),
    }


# ---------------------------------------------------------------------------
# regime-conditional gate (E2, 2026-08-02 — unlocks H-012 / Wave-3 candidate
# C2, docs/PREREG_H-012.md). Design decision, stated explicitly: the gate is
# applied to TARGETS, never to the score construction itself — vol_scores()
# is called completely unmodified, so the already-scrutinized H-008 signal
# path is untouched; the only new logic is which weight vector a formation
# date's execution actually uses. This keeps H-012's incremental risk
# surface to exactly one new function, mirroring how H-010's pooled-cohort
# addition (above) extended this module without touching xs_rank/xs_vol.
# ---------------------------------------------------------------------------

def regime_stable_dates(con, formations: list, lookback_months: int = 6) -> dict:
    """Pre-declared regime-classification rule, PREREG_H-012 (frozen
    2026-08-02, before any performance data was viewed). A formation date
    is STABLE unless, in the trailing `lookback_months`:
      (1) a 'critical'-severity event occurred in the macro/banking/
          commodity category of `events`, OR
      (2) more than one 'high'-severity monetary (MPC) event occurred.
    Uses ONLY events.announced_date (never effective_date) — a formation
    date's classification depends only on events the market could
    already have known about as of that date. No look-ahead by
    construction: every comparison below is `announced_date <= f`."""
    events = pd.read_sql(
        "SELECT category, severity, announced_date FROM events", con,
        parse_dates=["announced_date"])
    critical = events[(events.severity == "critical") &
                      (events.category.isin(["macro", "banking", "commodity"]))]
    high_mpc = events[(events.severity == "high") & (events.category == "monetary")]
    out = {}
    for f in formations:
        window_start = f - pd.DateOffset(months=lookback_months)
        crit_hit = bool(((critical.announced_date > window_start) &
                         (critical.announced_date <= f)).any())
        mpc_hits = int(((high_mpc.announced_date > window_start) &
                        (high_mpc.announced_date <= f)).sum())
        out[f] = not (crit_hit or mpc_hits > 1)
    return out


def regime_gated_targets(con, panel, cfg, scores: dict, bt: dict,
                         close_index: pd.DatetimeIndex, top_n: int,
                         lag: int) -> tuple[dict, dict]:
    """H-012: for each formation date, use the tilt's own target weights
    (targets_from_scores, unmodified) if STABLE, else the benchmark's own
    target weights (benchmark_targets, unmodified) for that same
    execution date — an unstable-classified rebalance is simply "the
    active tilt is off," never a blended or distorted weight vector.
    Returns (targets, stability_by_execution_date) — the second element
    is retained for the look-ahead audit and honest reporting of the
    stable/unstable split, never dropped."""
    tilt_targets = targets_from_scores(scores, close_index, top_n, lag)
    stable = regime_stable_dates(
        con, list(scores.keys()),
        int(cfg["signal"].get("regime_lookback_months", 6)))
    pos = {dt: i for i, dt in enumerate(close_index)}
    out, flags = {}, {}
    for f, is_stable in stable.items():
        i = pos.get(f)
        if i is None or i + lag >= len(close_index):
            continue
        exec_date = close_index[i + lag]
        if is_stable and exec_date in tilt_targets:
            out[exec_date] = tilt_targets[exec_date]
        elif exec_date in bt:
            out[exec_date] = bt[exec_date]
        else:
            continue
        flags[exec_date] = is_stable
    return out, flags


# ---------------------------------------------------------------------------
# Size interaction forensics (Phase R2, 2026-08-03 — H-013/H-014/H-015,
# docs/PREREG_H013-015_size_interactions.md). Diagnostic decomposition of
# H-011, NOT a new factor search: does the confirmed Size premium survive
# a double sort against Liquidity, Momentum, or Volatility, or is it
# partially/fully explained by one of them? size_scores(), rank_scores(),
# vol_scores() are called completely UNCHANGED — the only new logic is the
# bucket split and a bucket-scoped benchmark, mirroring exactly how H-012's
# regime gate extended this module without touching vol_scores() itself.
# ---------------------------------------------------------------------------

def interaction_dimension_scores(con, panel, cfg) -> dict:
    """The interacting (non-size) dimension's scores for
    signal.interaction_factor in {'liquidity','momentum','volatility'} —
    each delegates to its own existing, unmodified scoring function."""
    factor = cfg["signal"]["interaction_factor"]
    if factor == "liquidity":
        return liquidity_scores(con, panel, cfg)
    if factor == "momentum":
        return rank_scores(con, panel, cfg)
    if factor == "volatility":
        return vol_scores(con, panel, cfg)
    raise ValueError(f"unknown interaction_factor {factor!r}")


def interaction_bucket_members(size: dict, x: dict) -> dict:
    """{formation_date -> {'high': [tickers], 'low': [tickers]}} — median
    split by the interacting factor's own z-score (as returned by its
    scoring function; sign convention doesn't matter for a median split),
    restricted each date to tickers scored by BOTH dimensions that date —
    the shared population any double sort must draw from."""
    out = {}
    for f in sorted(set(size) & set(x)):
        common = size[f].index.intersection(x[f].index)
        if len(common) < 10:
            continue
        xz = x[f].loc[common]
        med = xz.median()
        out[f] = {"high": sorted(xz[xz >= med].index),
                  "low": sorted(xz[xz < med].index)}
    return out


def targets_from_bucketed_size(size: dict, buckets: dict, bucket: str,
                               close_index: pd.DatetimeIndex, top_n: int,
                               lag: int) -> dict:
    """Within the requested bucket at each date, select the top_n by SIZE
    score only — H-011's own selection rule (size_scores: higher z =
    smaller cap; nlargest = smallest names), applied to a pre-filtered
    sub-population instead of the whole universe."""
    pos = {dt: i for i, dt in enumerate(close_index)}
    targets = {}
    for f, members in buckets.items():
        if f not in size:
            continue
        i = pos.get(f)
        if i is None or i + lag >= len(close_index):
            continue
        names = size[f].index.intersection(members[bucket])
        sub = size[f].loc[names]
        if len(sub) < 5:
            continue
        sel = sub.nlargest(min(top_n, len(sub)))
        targets[close_index[i + lag]] = pd.Series(1.0 / len(sel), index=sel.index)
    return targets


def benchmark_targets_bucket(buckets: dict, bucket: str,
                             close_index: pd.DatetimeIndex, lag: int) -> dict:
    """EW over ALL members of the requested bucket (not size-filtered) —
    the bucket-scoped null. Isolates whether being SMALL adds anything
    BEYOND simply belonging to this liquidity/momentum/volatility half,
    rather than comparing against the whole-universe EW-IRU benchmark
    (which would conflate a bucket-level tilt with the size effect
    itself)."""
    pos = {dt: i for i, dt in enumerate(close_index)}
    out = {}
    for f, members in buckets.items():
        names = members[bucket]
        i = pos.get(f)
        if not names or i is None or i + lag >= len(close_index):
            continue
        out[close_index[i + lag]] = pd.Series(1.0 / len(names), index=names)
    return out


# ---------------------------------------------------------------------------
# entry point used by runner
# ---------------------------------------------------------------------------

def run_from_config(con, cfg, rates) -> tuple[XSResult, dict, float]:
    d, s, p = cfg["data"], cfg["signal"], cfg["portfolio"]
    if s["method"] == "xs_rank_pooled":
        result, diag = pooled_rank_run(con, cfg, rates)
        result.attribution = diag        # cohort correlation + turnover
        panel = load_panel(con, cfg)     # cheap re-read, just for min_conf
        return result, diag.get("capacity", {}), panel["min_conf_seen"]

    panel = load_panel(con, cfg)
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])

    bt = benchmark_targets(con, panel, cfg, lag)
    bench = simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                     d["sim_start"], d["sim_end"])

    regime_flags = None
    if s["method"] in ("xs_rank", "xs_vol", "xs_size", "xs_liquidity"):
        if s["method"] == "xs_size":
            panel["mcap"] = load_market_cap_panel(close)
        scores = scores_for_method(con, panel, cfg)
        targets = targets_from_scores(scores, close.loc[:d["sim_end"]].index,
                                      int(p["top_n"]), lag)
    elif s["method"] == "xs_vol_regime":
        # H-012: reuses vol_scores() unmodified; only the target selection
        # is regime-gated (see regime_gated_targets's own docstring).
        scores = vol_scores(con, panel, cfg)
        targets, regime_flags = regime_gated_targets(
            con, panel, cfg, scores, bt, close.loc[:d["sim_end"]].index,
            int(p["top_n"]), lag)
    elif s["method"] == "xs_size_interaction":
        # H-013/H-014/H-015 (Phase R2): size_scores() and the interacting
        # dimension's scoring function are BOTH called unmodified; the
        # benchmark for this method is the BUCKET-scoped one (below), not
        # the whole-universe `bench` computed above — set after simulate().
        panel["mcap"] = load_market_cap_panel(close)
        size = size_scores(con, panel, cfg)
        xdim = interaction_dimension_scores(con, panel, cfg)
        buckets = interaction_bucket_members(size, xdim)
        idx = close.loc[:d["sim_end"]].index
        targets = targets_from_bucketed_size(
            size, buckets, s["bucket"], idx, int(p["top_n"]), lag)
        bucket_bt = benchmark_targets_bucket(buckets, s["bucket"], idx, lag)
    elif s["method"] == "xs_event":
        sels = event_selections(con, panel, cfg, bench.net_returns)
        targets = event_targets(sels, close.loc[d["sim_start"]:d["sim_end"]].index,
                                int(p.get("max_concurrent", 20)))
    else:
        raise ValueError(f"unknown xs signal method {s['method']!r}")
    if not targets:
        raise RuntimeError("cross-sectional engine produced no target dates "
                           "under this config")

    result = simulate(close, targets, rates["buy_rate"], rates["sell_rate"],
                      d["sim_start"], d["sim_end"],
                      bench_net=bench.net_returns)
    result.benchmark_returns = bench.net_returns
    if s["method"] == "xs_size_interaction":
        bucket_bench = simulate(close, bucket_bt, rates["buy_rate"],
                                rates["sell_rate"], d["sim_start"], d["sim_end"])
        result.benchmark_returns = bucket_bench.net_returns
        avg_high = sum(len(m["high"]) for m in buckets.values()) / len(buckets)
        avg_low = sum(len(m["low"]) for m in buckets.values()) / len(buckets)
        result.attribution = {
            "size_interaction": {
                "interaction_factor": s["interaction_factor"],
                "bucket": s["bucket"],
                "n_formation_dates": len(buckets),
                "avg_bucket_size_high": round(avg_high, 1),
                "avg_bucket_size_low": round(avg_low, 1),
            }
        }
    if regime_flags is not None:
        n_stable = sum(1 for v in regime_flags.values() if v)
        result.attribution = {
            "regime_gate": {
                "n_formation_dates": len(regime_flags),
                "n_stable": n_stable,
                "n_unstable": len(regime_flags) - n_stable,
                "stable_dates": sorted(str(k.date()) for k, v in
                                      regime_flags.items() if v),
                "unstable_dates": sorted(str(k.date()) for k, v in
                                         regime_flags.items() if not v),
            }
        }
    cap = capacity_report(
        targets, panel["adtv60"], cfg["engine"]["aum_ngn"],
        cfg["liquidity"]["adtv_participation_cap_pct"])
    return result, cap, panel["min_conf_seen"]


# ---------------------------------------------------------------------------
# placebo (seeded; identical dates/costs/construction, shuffled labels)
# ---------------------------------------------------------------------------

def _placebo_pooled(con, cfg, rates, n_iter, gen) -> tuple[float, list]:
    from . import metrics as _metrics
    d, s, p = cfg["data"], cfg["signal"], cfg["portfolio"]
    n = int(s["n_cohorts"])
    step = REBALANCE_STEP_MONTHS[cfg["portfolio"]["rebalance"]]
    offset_step = step // n
    panel = load_panel(con, cfg)
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])
    idx = close.loc[:d["sim_end"]].index
    rf = cfg["validation"]["risk_free_annual_pct"]

    cohort_scores = []
    for c in range(n):
        cfg_c = {**cfg, "signal": {**s, "cohort_offset_months": c * offset_step}}
        cohort_scores.append(rank_scores(con, panel, cfg_c))

    def blended_sharpe(scores_list):
        nets = []
        for sc in scores_list:
            tgt = targets_from_scores(sc, idx, int(p["top_n"]), lag)
            res = simulate(close, tgt, rates["buy_rate"], rates["sell_rate"],
                          d["sim_start"], d["sim_end"])
            nets.append(res.net_returns)
        blended = pd.concat(nets, axis=1).mean(axis=1)
        vol = float(blended.std() * (252 ** 0.5))
        ann = float((1 + blended).prod() ** (252 / len(blended)) - 1)
        return (ann - rf / 100.0) / vol if vol > 0 else 0.0

    real = blended_sharpe(cohort_scores)
    all_ticks = sorted({t for sc in cohort_scores for s_ in sc.values()
                        for t in s_.index})
    placebo = []
    for _ in range(n_iter):
        perm = dict(zip(all_ticks,
                        [all_ticks[j] for j in gen.permutation(len(all_ticks))]))
        shuffled = []
        for sc in cohort_scores:
            sh = {}
            for f, s_ in sc.items():
                vals = {t: s_[perm[t]] for t in s_.index if perm[t] in s_.index}
                if len(vals) >= 10:
                    sh[f] = pd.Series(vals)
            shuffled.append(sh)
        placebo.append(blended_sharpe(shuffled))
    return real, placebo


def placebo_stats(con, cfg, rates, n_iter: int, gen) -> tuple[float, list]:
    """Real sharpe + n_iter placebo sharpes. xs_rank/xs_vol/xs_size: scores
    relabeled by one fixed ticker permutation per iteration (preserves
    temporal persistence — see note below); xs_rank_pooled: the SAME
    single relabeling applied to EVERY cohort in a given iteration (tests
    aggregate pooled selection skill under the null, not cross-cohort
    composition — a per-cohort-independent relabeling would test a
    different, wrong question); xs_event: z shuffled within cohorts (via
    shuffling the selection among that cohort's events)."""
    from . import metrics as _metrics
    d, s, p = cfg["data"], cfg["signal"], cfg["portfolio"]
    if s["method"] == "xs_rank_pooled":
        return _placebo_pooled(con, cfg, rates, n_iter, gen)
    panel = load_panel(con, cfg)
    close = panel["close_ff"]
    lag = int(p["execution_lag_days"])
    bt = benchmark_targets(con, panel, cfg, lag)
    bench = simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                     d["sim_start"], d["sim_end"])
    rf = cfg["validation"]["risk_free_annual_pct"]

    def sharpe_of(targets):
        res = simulate(close, targets, rates["buy_rate"], rates["sell_rate"],
                       d["sim_start"], d["sim_end"], bench_net=bench.net_returns)
        res.benchmark_returns = bench.net_returns
        return _metrics.compute(res, rf)["sharpe_vs_rf"]

    if s["method"] in ("xs_rank", "xs_vol", "xs_size", "xs_liquidity"):
        if s["method"] == "xs_size":
            panel["mcap"] = load_market_cap_panel(close)
        scores = scores_for_method(con, panel, cfg)
        idx = close.loc[:d["sim_end"]].index
        real = sharpe_of(targets_from_scores(scores, idx, int(p["top_n"]), lag))
        # persistence-preserving placebo: ONE fixed ticker relabeling per
        # iteration, applied to every formation date. Per-date re-shuffles
        # destroy the signal's temporal persistence and lose on TURNOVER
        # COSTS rather than information (false positives on null panels —
        # caught in the 2026-07-22 rehearsal). A fixed relabeling keeps the
        # timing/turnover structure and tests selection skill only.
        all_ticks = sorted({t for sc in scores.values() for t in sc.index})
        placebo = []
        for _ in range(n_iter):
            perm = dict(zip(all_ticks,
                            [all_ticks[j] for j in
                             gen.permutation(len(all_ticks))]))
            sh = {}
            for f, sc in scores.items():
                vals = {t: sc[perm[t]] for t in sc.index
                        if perm[t] in sc.index}
                if len(vals) >= 10:
                    sh[f] = pd.Series(vals)
            placebo.append(sharpe_of(
                targets_from_scores(sh, idx, int(p["top_n"]), lag)))
        return real, placebo

    if s["method"] == "xs_vol_regime":
        # H-012: identical persistence-preserving relabeling scheme as
        # xs_vol above; the regime gate itself is UNCHANGED across real
        # and placebo draws (classification depends only on calendar
        # dates, never on which ticker holds which score) — this tests
        # selection skill WITHIN the pre-declared stable regime, the
        # same null every other xs_* placebo tests, applied here to a
        # gated date population instead of the full one.
        scores = vol_scores(con, panel, cfg)
        idx = close.loc[:d["sim_end"]].index
        real_targets, _ = regime_gated_targets(
            con, panel, cfg, scores, bt, idx, int(p["top_n"]), lag)
        real = sharpe_of(real_targets)
        all_ticks = sorted({t for sc in scores.values() for t in sc.index})
        placebo = []
        for _ in range(n_iter):
            perm = dict(zip(all_ticks,
                            [all_ticks[j] for j in
                             gen.permutation(len(all_ticks))]))
            sh = {}
            for f, sc in scores.items():
                vals = {t: sc[perm[t]] for t in sc.index
                        if perm[t] in sc.index}
                if len(vals) >= 10:
                    sh[f] = pd.Series(vals)
            sh_targets, _ = regime_gated_targets(
                con, panel, cfg, sh, bt, idx, int(p["top_n"]), lag)
            placebo.append(sharpe_of(sh_targets))
        return real, placebo

    if s["method"] == "xs_size_interaction":
        # H-013/H-014/H-015: ONE fixed ticker relabeling per iteration,
        # applied to BOTH the size score series and the interacting
        # dimension's score series together (perm[t]'s TRUE size AND TRUE
        # x-value, jointly) — preserves the real, persistent RELATIONSHIP
        # between a name's own size and its own liquidity/momentum/vol
        # history, while randomizing which real return series is paired
        # with that (size, x) identity. The bucket-scoped benchmark is
        # rebuilt from the SAME shuffled buckets each iteration, not the
        # whole-universe one, matching the real run's own comparison.
        panel["mcap"] = load_market_cap_panel(close)
        size = size_scores(con, panel, cfg)
        xdim = interaction_dimension_scores(con, panel, cfg)
        idx = close.loc[:d["sim_end"]].index

        def bucket_sharpe(size_d, x_d):
            buckets = interaction_bucket_members(size_d, x_d)
            tgt = targets_from_bucketed_size(
                size_d, buckets, s["bucket"], idx, int(p["top_n"]), lag)
            b_bt = benchmark_targets_bucket(buckets, s["bucket"], idx, lag)
            if not tgt or not b_bt:
                return None
            res = simulate(close, tgt, rates["buy_rate"], rates["sell_rate"],
                           d["sim_start"], d["sim_end"])
            res.benchmark_returns = simulate(
                close, b_bt, rates["buy_rate"], rates["sell_rate"],
                d["sim_start"], d["sim_end"]).net_returns
            return _metrics.compute(res, rf)["sharpe_vs_rf"]

        real = bucket_sharpe(size, xdim)
        all_ticks = sorted({t for sc in size.values() for t in sc.index} |
                           {t for sc in xdim.values() for t in sc.index})
        placebo = []
        for _ in range(n_iter):
            perm = dict(zip(all_ticks,
                            [all_ticks[j] for j in
                             gen.permutation(len(all_ticks))]))
            sh_size, sh_x = {}, {}
            for f, sc in size.items():
                vals = {t: sc[perm[t]] for t in sc.index if perm[t] in sc.index}
                if len(vals) >= 10:
                    sh_size[f] = pd.Series(vals)
            for f, sc in xdim.items():
                vals = {t: sc[perm[t]] for t in sc.index if perm[t] in sc.index}
                if len(vals) >= 10:
                    sh_x[f] = pd.Series(vals)
            sh_sharpe = bucket_sharpe(sh_size, sh_x)
            placebo.append(sh_sharpe if sh_sharpe is not None else 0.0)
        return (real if real is not None else 0.0), placebo

    # xs_event: shuffle which of the cohort's events get selected
    sels = event_selections(con, panel, cfg, bench.net_returns)
    idx = close.loc[d["sim_start"]:d["sim_end"]].index
    mc = int(p.get("max_concurrent", 20))
    real = sharpe_of(event_targets(sels, idx, mc))
    # reconstruct full cohort pools for the shuffle
    all_sel = pd.DataFrame(sels)
    placebo = []
    cohorts = all_sel.groupby(all_sel.entry.dt.strftime("%Y-%m"))
    for _ in range(n_iter):
        rows = []
        for _, g in cohorts:
            tick = g.ticker.to_numpy()[gen.permutation(len(g))]
            for (r_, t_) in zip(g.itertuples(), tick):
                rows.append(dict(entry=r_.entry, exit=r_.exit,
                                 ticker=t_, z=r_.z))
        placebo.append(sharpe_of(event_targets(rows, idx, mc)))
    return real, placebo
