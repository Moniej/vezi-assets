"""Stage 1 / A-1 — H-011 realistic participation-cap execution test.

Reads configs/h011_size.toml READ-ONLY. Does not modify it, does not
modify docs/PREREG_H-011.md, does not change H-011's signal or portfolio
construction. Builds the IDENTICAL targets the confirmed H-011 run used
(backtest_xs.size_scores + targets_from_scores, unchanged) and runs them
through two execution paths:

  1. UNCONSTRAINED — backtest_xs.simulate, byte-identical to the code path
     that produced the registered, confirmed H-011 numbers. Run here again
     as a reproduction/sanity check, not a new claim.
  2. CONSTRAINED — execution_realism.constrained_simulate, which caps every
     rebalance leg's fill at the same ADTV participation limit
     (adtv_participation_cap_pct=10.0, adtv_window_days=60) H-011's own
     frozen liquidity config already declares, applied to actual fills
     instead of only reported after the fact.

Two windows, matching the platform's own regime definitions in
configs/h011_size.toml's [[phase4.regimes]] (not invented here):
  - "dev": 2016-01-02 to 2024-12-31 (H-011's base configured window)
  - "oos_2025_26": 2025-01-02 to 2026-06-30 (the untouched final-OOS regime)
Both windows keep vintage="2026-07-21" (H-011's own frozen data snapshot),
exactly as every prior Phase 4 walk-forward run for this hypothesis did —
no new data leaks into this test that H-011's own validation did not use.

Output: prints a comparison table and writes
reports/H011_STAGE1_A1_EXECUTION_REALISM_2026-08-08.json (raw numbers) for
the write-up. Not registered in data/registry.sqlite: this is an
implementation-realism diagnostic on an already-confirmed hypothesis, not
a new or modified hypothesis test.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import backtest_xs, costs, db, execution_realism, metrics, runner  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "h011_size.toml"


def build_targets(con, cfg):
    """Exact reproduction of backtest_xs.run_from_config's xs_size path
    up to target construction — no behavior added, no parameter touched."""
    panel = backtest_xs.load_panel(con, cfg)
    panel["mcap"] = backtest_xs.load_market_cap_panel(panel["close_ff"])
    close = panel["close_ff"]
    lag = int(cfg["portfolio"]["execution_lag_days"])
    scores = backtest_xs.size_scores(con, panel, cfg)
    targets = backtest_xs.targets_from_scores(
        scores, close.loc[:cfg["data"]["sim_end"]].index,
        int(cfg["portfolio"]["top_n"]), lag)
    bt = backtest_xs.benchmark_targets(con, panel, cfg, lag)
    return panel, targets, bt


def run_window(con, base_cfg, window_start, window_end, label, aum_override=None):
    cfg = copy.deepcopy(base_cfg)
    cfg["data"]["sim_start"] = window_start
    cfg["data"]["sim_end"] = window_end
    if aum_override is not None:
        cfg["engine"]["aum_ngn"] = aum_override
    d = cfg["data"]

    panel, targets, bt = build_targets(con, cfg)
    close = panel["close_ff"]
    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                             cfg["costs"]["brokerage_override_pct"])

    bench = backtest_xs.simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                                 d["sim_start"], d["sim_end"])

    unconstrained = backtest_xs.simulate(close, targets, rates["buy_rate"],
                                         rates["sell_rate"], d["sim_start"],
                                         d["sim_end"])
    unconstrained.benchmark_returns = bench.net_returns

    liq = cfg["liquidity"]
    constrained = execution_realism.constrained_simulate(
        close, targets, panel["adtv60"], rates["buy_rate"], rates["sell_rate"],
        d["sim_start"], d["sim_end"], aum_ngn=float(cfg["engine"]["aum_ngn"]),
        participation_pct=float(liq["adtv_participation_cap_pct"]))
    constrained.xs.benchmark_returns = bench.net_returns

    rf = cfg["validation"]["risk_free_annual_pct"]
    m_unc = metrics.compute(unconstrained, rf)
    m_con = metrics.compute(constrained.xs, rf)

    fills = execution_realism.leg_fill_summary(constrained.legs)
    leg_df = constrained.leg_frame()
    aum = float(cfg["engine"]["aum_ngn"])
    leg_cap_ngn = (leg_df.cap_weight * aum / leg_df.desired_dw.abs()
                  if len(leg_df) else None)

    cap_report_unc = backtest_xs.capacity_report(
        targets, panel["adtv60"], aum, float(liq["adtv_participation_cap_pct"]))

    return {
        "label": label, "window": [window_start, window_end],
        "unconstrained": m_unc, "constrained": m_con,
        "fills": fills,
        "executable_capacity_ngn": {
            "median": float(leg_cap_ngn.median()) if leg_cap_ngn is not None and len(leg_cap_ngn) else None,
            "min": float(leg_cap_ngn.min()) if leg_cap_ngn is not None and len(leg_cap_ngn) else None,
            "max": float(leg_cap_ngn.max()) if leg_cap_ngn is not None and len(leg_cap_ngn) else None,
        },
        "unconstrained_capacity_report": cap_report_unc,
        "n_legs": len(leg_df),
    }


AUM_SWEEP_NGN = [5e6, 10e6, 15e6, 20e6, 30e6, 50e6, 75e6, 100e6,
                 150e6, 200e6, 300e6, 500e6, 1e9]


def run_aum_sweep(con, base_cfg):
    """Not a parameter optimization of the SIGNAL (top_n/rebalance/score are
    untouched throughout) — sweeps only the EXECUTION-SIDE aum_ngn input to
    find where constrained net excess crosses zero, i.e. the realistic
    capacity ceiling implied by H-011's own already-frozen liquidity
    parameters. Reported regardless of outcome, not selected after seeing
    the result."""
    windows = [("2016-01-02", "2024-12-31", "dev"),
              ("2025-01-02", "2026-06-30", "oos_2025_26")]
    rows = []
    for w_start, w_end, label in windows:
        for aum in AUM_SWEEP_NGN:
            r = run_window(con, base_cfg, w_start, w_end, label, aum_override=aum)
            rows.append({
                "window": label, "aum_ngn": aum,
                "constrained_excess": r["constrained"]["excess_return_ann"],
                "constrained_net_return": r["constrained"]["ann_return"],
                "constrained_sharpe": r["constrained"]["sharpe_vs_rf"],
                "mean_fill_frac": r["fills"].get("mean_fill_frac"),
                "pct_partial": r["fills"].get("pct_partial"),
            })
    return rows


def main():
    base_cfg = runner.load_config(CONFIG_PATH)
    con = db.init_db(ROOT / "data" / "ngx.sqlite")

    results = []
    results.append(run_window(con, base_cfg, "2016-01-02", "2024-12-31", "dev"))
    results.append(run_window(con, base_cfg, "2025-01-02", "2026-06-30", "oos_2025_26"))

    print(f"{'window':<12}{'metric':<28}{'unconstrained':>16}{'constrained':>16}")
    for r in results:
        for k in ("gross_ann_return", "ann_return", "ann_return_benchmark",
                  "excess_return_ann", "sharpe_vs_rf", "max_drawdown",
                  "ann_turnover_oneway", "ann_cost_drag"):
            print(f"{r['label']:<12}{k:<28}{r['unconstrained'].get(k):>16}"
                  f"{r['constrained'].get(k):>16}")
        print(f"{r['label']:<12}{'--- fills ---':<28}")
        print(f"  {r['fills']}")
        print(f"  executable_capacity_ngn: {r['executable_capacity_ngn']}")
        print()

    print("=== AUM sweep (execution-side only; signal/construction untouched) ===")
    sweep = run_aum_sweep(con, base_cfg)
    print(f"{'window':<14}{'aum_ngn':>14}{'constr_excess':>16}{'mean_fill':>12}")
    for r in sweep:
        print(f"{r['window']:<14}{r['aum_ngn']:>14,.0f}{r['constrained_excess']:>16}"
              f"{r['mean_fill_frac']:>12}")

    out_path = ROOT / "reports" / "H011_STAGE1_A1_EXECUTION_REALISM_2026-08-08.json"
    out_path.write_text(json.dumps({"windows": results, "aum_sweep": sweep},
                                   indent=2, default=str), encoding="utf-8")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
