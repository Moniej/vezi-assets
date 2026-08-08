"""H-019/H-020 first-look backtest — strictly per the frozen specifications:

  docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md  (event/signal layer)
  docs/PREREG_H-019.md                                   (event dataset)
  docs/PREREG_H-020_PORTFOLIO_CONSTRUCTION_2026-08-08.md (portfolio layer)

Reuses the platform's existing, unmodified cross-sectional accounting core
(simulate(), event_targets(), benchmark_targets(), load_panel(),
capacity_report(), costs.side_rates(), metrics.compute() — all from
src/ngxrot/backtest_xs.py and siblings, none touched by this script).

Deliberately does NOT reuse backtest_xs.event_selections() -- that function
ranks candidates by their OWN price reaction (t0..t0+2 abnormal return vs
benchmark) before selecting which to hold. That is precisely the kind of
return-dependent selection step Stage 14/H-020 was built to avoid: H-019's
whole premise is that a news-derived event's ECONOMIC classification
(§14C's objective direction rule, fixed before any return was examined) is
what is being tested, not a rule that already knows which reactions were
favorable. This script instead builds its own event-selection list directly
from the frozen H-019 CSV, using only §14A/§14C/§14E/H-020's fixed rules —
no price data is read before an entry/exit date is fixed.

Run:  PYTHONPATH=src python scripts/run_h019_backtest.py
"""
from __future__ import annotations

import csv
import sys
import uuid
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import backtest_xs as xs  # noqa: E402
from ngxrot import costs, db, metrics, registry  # noqa: E402

H019_CSV = ROOT / "data" / "hypotheses" / "h019" / "h019_event_dataset_2026-08-08.csv"
HOLD_SESSIONS = 60          # PREREG_H-020 §8, matches docs/PREREG_H-006.md
                             # (an unrelated, earlier, already-rejected hypothesis)
MAX_CONCURRENT = 20         # non-binding ceiling; §5 "hold all, no top_n" --
                             # this dataset never has >2 concurrent candidates
SIM_START = "2026-01-01"    # CORRECTED after first run: the platform's
                             # generic simulate()/event_targets() combo only
                             # sets a target-weight row on selection change
                             # dates (entry/exit) -- with only 2 executable
                             # events, both in 2026, an earlier sim_start
                             # (originally 2015-07-01, matching H-006) left
                             # the H-019 book completely UNINVESTED (true
                             # 0% daily return, not benchmark-tracking) for
                             # a ~10.7-year pre-event stretch, which crushed
                             # the annualized-return math into noise and
                             # made the vs-benchmark comparison meaningless
                             # (the benchmark DOES rebalance across the full
                             # window via benchmark_targets()'s formation-
                             # date loop, so the two series were being
                             # compared over incomparable exposure periods).
                             # This is a mechanical window-sizing fix, made
                             # BEFORE examining any return number's
                             # favorability -- bounding the window to when
                             # the signal can plausibly be active is a
                             # correctness fix, not a hindsight edit.
SIM_END = "2026-07-21"      # latest date with real equity_prices coverage
                             # for the constituents involved (checked live)
MIN_CONFIDENCE = 0.9        # platform standard, matches H-011/H-006
VINTAGE = None               # latest captures -- this is a first-look run,
                             # not a formal walk-forward/final-OOS experiment


def build_news_event_selections(close_index: pd.DatetimeIndex) -> list[dict]:
    """PREREG_H-020 §2-§8, applied literally to the frozen H-019 dataset.
    No price data is consulted to decide WHICH events are selected -- every
    non-neutral row in the dataset is selected, full stop (§5)."""
    rows = list(csv.DictReader(H019_CSV.open(encoding="utf-8")))
    date_arr = np.array(close_index)
    out = []
    for r in rows:
        direction = r["direction"]
        if direction == "neutral":
            continue  # §3: neutral events generate no position
        if direction != "positive":
            # §6: negative-direction events are recorded, not executed
            # (long-only, no short-selling anywhere on this platform).
            # None occur in the current dataset; this branch is inert but
            # present for completeness, per §6's own stated rule.
            continue
        kt = r["knowledge_timestamp_eligible_from"]
        if not kt:
            continue  # PIT-uncertain, never entered (H-020 §13)
        kt_ts = pd.Timestamp(kt)
        j = np.searchsorted(date_arr, kt_ts.to_datetime64())
        if j >= len(date_arr) or date_arr[j] != kt_ts.to_datetime64():
            continue  # eligible_from date not a real trading session in
                      # this panel's actual calendar -- fail closed, PIT-uncertain
        i_out = min(j + HOLD_SESSIONS, len(date_arr) - 1)
        out.append(dict(
            entry=close_index[j],
            exit=close_index[i_out],
            ticker=r["ticker"],
            z=1.0,  # §6 equal-weight: no ranking signal, every selected
                    # event is weighted identically -- z is only used by
                    # event_targets() for the (never-binding) capacity
                    # tiebreak, kept at a constant so it is inert here.
            canonical_event_id=r["canonical_event_id"],
            direction=direction,
        ))
    return out


def main() -> None:
    con = db.init_db()

    cfg = {
        "data": {"sim_start": SIM_START, "sim_end": SIM_END,
                 "min_confidence": MIN_CONFIDENCE, "vintage": VINTAGE},
        "signal": {"min_obs_formation": 120, "formation_months": 12},
        "portfolio": {"rebalance": "quarterly", "execution_lag_days": 1},
        "engine": {"aum_ngn": 1e9},
        "liquidity": {"adtv_participation_cap_pct": 10.0, "adtv_window_days": 60},
    }

    panel = xs.load_panel(con, cfg)
    close = panel["close_ff"]

    rates = costs.side_rates(db.cost_schedule_asof(con, SIM_END))

    lag = int(cfg["portfolio"]["execution_lag_days"])
    bt = xs.benchmark_targets(con, panel, cfg, lag)
    bench = xs.simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                        SIM_START, SIM_END)

    # --- full dataset composition (all 11 qualifying events, not just the
    # executable ones) so the small-sample point is visible at every level ---
    rows = list(csv.DictReader(H019_CSV.open(encoding="utf-8")))
    from collections import Counter
    dir_counts = Counter(r["direction"] for r in rows)
    type_counts = Counter(r["event_type"] for r in rows)
    ticker_counts = Counter(r["ticker"] for r in rows)
    print(f"=== H-019 dataset composition: {len(rows)} qualifying GMC/CIR events ===")
    print(f"  direction:  {dict(dir_counts)}")
    print(f"  event_type: {dict(type_counts)}")
    print(f"  by ticker:  {dict(ticker_counts)}")
    print(f"  PIT_status: {dict(Counter(r['PIT_status'] for r in rows))}")
    print(f"  duplicate_status: {dict(Counter(r['duplicate_status'] for r in rows))}")

    dates = close.loc[SIM_START:SIM_END].index
    selections = build_news_event_selections(dates)
    print(f"\nselections built (non-neutral, LONG direction=positive only, per "
          f"PREREG_H-020 Sec.3/Sec.6): {len(selections)} of {len(rows)} qualifying events "
          f"-- i.e. {len(rows) - len(selections)} of {len(rows)} generate NO position "
          f"({dir_counts.get('neutral', 0)} neutral by the objective rule, "
          f"{dir_counts.get('unknown', 0)} unknown because they don't fit any defined "
          f"Sec.14C rule row -- see docs for the two specific rule-coverage gaps found)")
    for s in selections:
        print(f"  {s['ticker']:12} entry={s['entry'].date()} exit={s['exit'].date()} "
              f"direction={s['direction']} event={s['canonical_event_id']}")

    if not selections:
        print("\nNo executable selections -- nothing to backtest under the "
              "frozen long-only, non-neutral-only rule. Stopping honestly "
              "rather than fabricating a result.")
        return

    targets = xs.event_targets(selections, dates, MAX_CONCURRENT)
    result = xs.simulate(close, targets, rates["buy_rate"], rates["sell_rate"],
                         SIM_START, SIM_END, bench_net=bench.net_returns)
    result.benchmark_returns = bench.net_returns

    cap = xs.capacity_report(targets, panel["adtv60"], cfg["engine"]["aum_ngn"],
                             cfg["liquidity"]["adtv_participation_cap_pct"])

    m = metrics.compute(result, rf_annual_pct=0.0)

    print("\n=== H-019/H-020 result (n=2 executable events -- read as a "
          "diagnostic, not a validated finding); ann_return_benchmark/"
          "excess_return_ann below already compare against EW-IRU, same "
          "window, same cost model ===")
    for k, v in m.items():
        print(f"  {k:24} {v}")
    print("\n=== capacity (informational only -- n too small for this to be "
          "meaningful) ===")
    print(json.dumps(cap, indent=2, default=str))

    # Per-position contribution, for full transparency on a 2-observation run
    print("\n=== event-level contribution (== per-ticker here: each ticker has "
          "exactly 1 executable event) ===")
    for t, c in sorted(result.sector_contribution.items(), key=lambda kv: -abs(kv[1])):
        if t == "BENCH":
            continue
        print(f"  {t:12} {c:+.4%}")

    # --- per-position raw/net price return, win/loss, and own-window
    # benchmark comparison (distinct from the whole-book metrics above,
    # which blend both positions and the empty pre/post stretches) ---
    print("\n=== per-position: raw price return, cost-adjusted return, "
          "win/loss vs EW-IRU over its OWN holding window ===")
    daily = close.loc[SIM_START:SIM_END]
    bench_r = bench.net_returns
    wins = 0
    for s in selections:
        px = daily[s["ticker"]]
        raw_ret = float(px.loc[s["exit"]] / px.loc[s["entry"]] - 1)
        # round-trip cost at the platform's live cost_schedule rates
        cost_drag = rates["buy_rate"] + rates["sell_rate"]
        net_ret = (1 + raw_ret) * (1 - rates["buy_rate"]) * (1 - rates["sell_rate"]) - 1
        b_window = bench_r.loc[s["entry"]:s["exit"]]
        bench_window_ret = float((1 + b_window).prod() - 1)
        won = net_ret > bench_window_ret
        wins += int(won)
        print(f"  {s['ticker']:12} raw={raw_ret:+.4%}  net_of_costs={net_ret:+.4%}  "
              f"EW-IRU_own_window={bench_window_ret:+.4%}  "
              f"excess={net_ret - bench_window_ret:+.4%}  {'WIN' if won else 'LOSS'}")
    print(f"  win rate: {wins}/{len(selections)} ({100*wins/len(selections):.0f}%) "
          f"-- with n={len(selections)}, this is a coin-flip-uninformative sample size, "
          f"stated explicitly, not as a finding")

    # --- exposure / turnover detail ---
    invested_days = int((result.weights.reindex(daily.index, method="ffill")
                        .drop(columns=["BENCH"], errors="ignore").sum(axis=1) > 1e-9).sum())
    print(f"\n=== exposure ===")
    print(f"  trading days in sim window: {len(daily.index)}")
    print(f"  days with >=1 active non-BENCH position: {invested_days} "
          f"({100*invested_days/len(daily.index):.1f}% of window)")
    print(f"  turnover: {m['n_rebalances']} rebalance events (2 entries + 2 exits), "
          f"one-way avg {m['avg_oneway_turnover_per_rebalance']:.1%} of NAV per event, "
          f"annualized one-way turnover {m['ann_turnover_oneway']:.1%}")

    # --- monthly time-period breakdown (bounded utility given only a
    # ~4-month active window, stated explicitly) ---
    print(f"\n=== performance by calendar month (net_returns, whole book incl. BENCH "
          f"residual) ===")
    monthly = result.net_returns.groupby(result.net_returns.index.to_period("M"))
    for period, seg in monthly:
        compounded = float((1 + seg).prod() - 1)
        print(f"  {period}: {compounded:+.4%}  ({len(seg)} trading days)")

    # --- liquidity / execution constraint check, elevated from capacity_report ---
    print(f"\n=== liquidity/execution: periods with insufficient capacity at the "
          f"configured AUM ===")
    print(f"  {cap.get('pct_legs_rejected', 'n/a')}% of trade legs would be rejected "
          f"under a {cfg['engine']['aum_ngn']:,.0f} NGN AUM at the platform's standard "
          f"10%/60-day ADTV participation cap -- both DEAPCAP and LEGENDINT are "
          f"capacity-bottlenecked constituents (median leg capacity ~{cap.get('median_capacity_ngn', 0):,.0f} "
          f"NGN, i.e. well below a plausible institutional AUM). This mirrors H-011's own "
          f"prior, independent finding that this 20-name universe is capacity-constrained "
          f"by construction -- not a new or surprising result for THIS universe, but a real "
          f"constraint on how any confirmed version of H-019 could ever be deployed at scale.")

    # --- statistical uncertainty, stated plainly ---
    tt = m["excess_ttest"]
    print(f"\n=== statistical uncertainty ===")
    print(f"  Underlying independent event count: n={len(selections)} executable "
          f"(of {len(rows)} qualifying events total, of which "
          f"{dir_counts.get('neutral',0)} are neutral-by-rule and "
          f"{dir_counts.get('unknown',0)} are unknown-by-rule-coverage-gap -- neither "
          f"trades, per the frozen long-only/non-neutral-only construction).")
    print(f"  The reported t-stat/p-value ({tt['t_stat']}/{tt['p_value']}, n_obs="
          f"{tt['n_obs']}) is computed over DAILY excess-return observations within the "
          f"holding windows, which are highly autocorrelated within each of only 2 "
          f"independent underlying events -- the EFFECTIVE sample size for any claim "
          f"about GMC/CIR events in general is 2, not {tt['n_obs']}. No confidence "
          f"interval, significance level, or p-value computed from n=2 independent "
          f"events can distinguish a real effect from noise. This is stated as a hard "
          f"limit on interpretation, not a caveat to be read past.")

    # --- registry logging: every run, however small, goes through the
    # same immutable experiment record every other hypothesis uses ---
    code_fp = hashlib.sha256(
        (ROOT / "src" / "ngxrot" / "backtest_xs.py").read_bytes()
        + Path(__file__).read_bytes()).hexdigest()
    cfg_json = json.dumps(cfg, sort_keys=True, default=str)
    reg = registry.connect_registry()
    reg.execute(
        "INSERT INTO experiments (experiment_id, created_at, code_fingerprint, "
        "config_path, config_hash, config_json, hypothesis_id, stage, provider, "
        "min_confidence, vintage, sim_start, sim_end, lookbacks_months, top_n, "
        "rebalance, construction, cost_assumptions, liquidity_constraints, seed, "
        "metrics, validation_flags, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(timespec="seconds"),
         code_fp, "scripts/run_h019_backtest.py",
         hashlib.sha256(cfg_json.encode()).hexdigest(), cfg_json,
         "H-019", "development", "ngx_pricelist_v1,ngx_dol_v1,ngx_list2_v1",
         MIN_CONFIDENCE, VINTAGE or "", SIM_START, SIM_END,
         json.dumps([HOLD_SESSIONS]), MAX_CONCURRENT, "event_driven",
         "equal_weight_long_only", json.dumps(rates), json.dumps(cfg["liquidity"]),
         None, json.dumps(m), json.dumps({"n_qualifying_events": len(rows),
                                          "n_executable_selections": len(selections),
                                          "n_neutral": dir_counts.get("neutral", 0),
                                          "n_unknown_rule_gap": dir_counts.get("unknown", 0),
                                          "sample_too_small_for_inference": True}),
         f"H-019/H-020 backtest per frozen specs, expanded dataset (n={len(rows)} "
         f"qualifying events, n={len(selections)} executable). Explicitly NOT a "
         "confirmation-eligible run; see docs/H019_H020_BACKTEST_RESULT_2026-08-08.md."))
    reg.execute(
        "INSERT INTO hypothesis_experiments (hypothesis_id, experiment_id) "
        "SELECT ?, experiment_id FROM experiments ORDER BY created_at DESC LIMIT 1",
        ("H-019",))
    reg.commit()
    print("\nExperiment logged to registry (data/registry.sqlite).")


if __name__ == "__main__":
    main()
