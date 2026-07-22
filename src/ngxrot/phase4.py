"""Phase 4 validation orchestrator.

Answers, for one hypothesis: does the signal survive (a) the full parameter
space, (b) multiple-testing correction, (c) a shuffled-label placebo,
(d) walk-forward across regimes with an untouched final OOS window — and at
what deployable AUM? Ends by generating the Investment Committee memo.

Every run goes through runner.run_resolved, so everything lands in the
immutable registry; the placebo suite registers once with its iteration
count and seed.
"""

from __future__ import annotations

import copy
import json
import tomllib
from datetime import date
from pathlib import Path

import pandas as pd

from . import (backtest_lite, costs, db, failure_conditions, ic_report,
               metrics, registry, rng, runner, stats)
from . import signal as sig
from . import confidence_rating

PKG_ROOT = Path(__file__).resolve().parents[2]


def _cell_cfg(base: dict, **overrides) -> dict:
    cfg = copy.deepcopy(base)
    for dotted, val in overrides.items():
        section, key = dotted.split("__")
        cfg[section][key] = val
    return cfg


# ---------------------------------------------------------------------------
# 1. Parameter stability map (lite engine: this is a SIGNAL question)
# ---------------------------------------------------------------------------

def stability_map(base: dict, grid: dict) -> tuple[pd.DataFrame, dict]:
    rows = []
    for lb in grid["lookbacks"]:
        for tn in grid["top_n"]:
            for rb in grid["rebalance"]:
                cfg = _cell_cfg(
                    base, signal__lookbacks_months=list(lb),
                    signal__lookback_weights=[1.0 / len(lb)] * len(lb),
                    portfolio__top_n=tn, portfolio__rebalance=rb,
                    engine__type="lite")
                cfg["experiment"]["name"] = f"p4_stability_lb{lb}_n{tn}_{rb}"
                r = runner.run_resolved(cfg, label=f"lb={lb} N={tn} {rb}")
                rows.append({"lookbacks": str(lb), "top_n": tn, "rebalance": rb,
                             "excess": r["row"]["excess_return_ann"],
                             "sharpe": r["row"]["sharpe_vs_rf"],
                             "p_raw": r["row"]["p_raw"],
                             "exp_id": r["exp_id"][:8]})
    df = pd.DataFrame(rows)
    plateau = {
        "n_cells": len(df),
        "frac_positive_excess": round(float((df.excess > 0).mean()), 3),
        "best_cell_excess": float(df.excess.max()),
        "median_cell_excess": float(df.excess.median()),
        "best_minus_median": round(float(df.excess.max() - df.excess.median()), 4),
    }
    return df, plateau


# ---------------------------------------------------------------------------
# 2. Walk-forward across regimes, catalyst filter on/off
# ---------------------------------------------------------------------------

def walk_forward(base: dict, regimes: list[dict]) -> tuple[pd.DataFrame, dict]:
    rows, attribution = [], {}
    for reg in regimes:
        for filt in (False, True):
            cfg = _cell_cfg(base, portfolio__catalyst_filter=filt)
            cfg["experiment"]["stage"] = reg["stage"]
            cfg["experiment"]["name"] = f"p4_wf_{reg['name']}_{'filt' if filt else 'pure'}"
            cfg["data"]["sim_start"], cfg["data"]["sim_end"] = reg["start"], reg["end"]
            r = runner.run_resolved(cfg, label=f"{reg['name']} "
                                               f"{'catalyst' if filt else 'pure'}")
            rows.append({"regime": reg["name"], "catalyst": filt,
                         "stage": reg["stage"], **{
                             k: r["row"][k] for k in
                             ("ann_return", "ann_return_benchmark",
                              "excess_return_ann", "sharpe_vs_rf", "max_drawdown",
                              "ann_cost_drag", "t_stat", "p_raw")},
                         "median_cap_bn": r["row"].get("median_cap_bn"),
                         "exp_id": r["exp_id"][:8]})
            if not filt:
                attribution[reg["name"]] = {
                    "sector_contribution": r["metrics"].get("sector_contribution", {}),
                    "excess": r["row"]["excess_return_ann"],
                    "sharpe": r["row"]["sharpe_vs_rf"],
                    "capacity": r["capacity"] or {},
                }
    return pd.DataFrame(rows), attribution


# ---------------------------------------------------------------------------
# 3. Placebo: shuffled sector labels, N seeded iterations
# ---------------------------------------------------------------------------

def placebo_test(base: dict, n_iter: int) -> dict:
    d, s, p, v = base["data"], base["signal"], base["portfolio"], base["validation"]
    gen = rng.make_rng(base["rng"])
    con = db.init_db(PKG_ROOT / d.get("db_path", "data/ngx.sqlite"))
    lv = db.index_levels_asof(con, d["sim_end"], d["universe"] + [d["benchmark"]],
                              min_confidence=d["min_confidence"],
                              vintage=d["vintage"] or None, sources=d["sources"])
    wide = lv.pivot(index="trade_date", columns="index_code", values="close_value")
    wide.index = pd.to_datetime(wide.index)
    universe, bench = wide[d["universe"]], wide[d["benchmark"]]
    scores = runner.build_scores(base, universe, con)
    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                             base["costs"]["brokerage_override_pct"])
    ev = db.events_asof(con, d["sim_end"], min_confidence=d["min_confidence"])

    def one_run(sc):
        res = backtest_lite.run(
            universe, bench, sc, ev, top_n=p["top_n"],
            construction=p["construction"], rebalance=p["rebalance"],
            execution_lag_days=p["execution_lag_days"], catalyst_filter=False,
            impairment_window_months=p["impairment_window_months"],
            buy_rate=rates["buy_rate"], sell_rate=rates["sell_rate"],
            sim_start=d["sim_start"], sim_end=d["sim_end"])
        return metrics.compute(res, v["risk_free_annual_pct"])

    real = one_run(scores)
    real_stat = real["sharpe_vs_rf"]
    placebo_stats = []
    vals = scores.to_numpy()
    for _ in range(n_iter):
        shuffled = scores.copy()
        perm = vals.copy()
        for i in range(perm.shape[0]):          # permute labels per date
            perm[i] = perm[i][gen.permutation(perm.shape[1])]
        shuffled.iloc[:, :] = perm
        placebo_stats.append(one_run(shuffled)["sharpe_vs_rf"])

    p_val = stats.placebo_p_value(real_stat, placebo_stats)
    summary = {
        "real_sharpe": real_stat,
        "placebo_mean_sharpe": round(float(pd.Series(placebo_stats).mean()), 3),
        "placebo_p95_sharpe": round(float(pd.Series(placebo_stats).quantile(0.95)), 3),
        "placebo_max_sharpe": round(float(max(placebo_stats)), 3),
        "placebo_p_value": round(p_val, 4),
        "n_iterations": n_iter,
    }
    reg = registry.connect_registry()
    cfg = copy.deepcopy(base)
    cfg["experiment"]["stage"] = "placebo"
    cfg["experiment"]["name"] = "p4_placebo_shuffled_labels"
    cfg["rng"]["iterations"] = n_iter
    registry.record_experiment(
        reg, config=cfg, config_path=None, metrics=summary,
        validation_flags={"synthetic_data": True, "counts_as_evidence": False,
                          "placebo_suite": True},
        notes=f"shuffled-label placebo, {n_iter} seeded iterations")
    reg.close()
    con.close()
    return summary


# ---------------------------------------------------------------------------
# Cross-sectional variants (engine.type = "cross_sectional", 2026-07-22).
# Same validation semantics; grid is generic dotted-key cartesian; placebo
# shuffles labels within formation dates / event cohorts via backtest_xs.
# ---------------------------------------------------------------------------

def stability_map_xs(base: dict, grid: dict) -> tuple[pd.DataFrame, dict]:
    import itertools
    keys = list(grid)
    rows = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        overrides = {k.replace(".", "__"): v for k, v in zip(keys, combo)}
        cfg = _cell_cfg(base, **overrides)
        label = " ".join(f"{k.split('.')[1]}={v}" for k, v in zip(keys, combo))
        cfg["experiment"]["name"] = "p4_stability_" + label.replace(" ", "_")
        r = runner.run_resolved(cfg, label=label)
        rows.append({**{k.split(".")[1]: v for k, v in zip(keys, combo)},
                     "excess": r["row"]["excess_return_ann"],
                     "sharpe": r["row"]["sharpe_vs_rf"],
                     "p_raw": r["row"]["p_raw"], "exp_id": r["exp_id"][:8],
                     "cell": label})
    df = pd.DataFrame(rows)
    plateau = {
        "n_cells": len(df),
        "frac_positive_excess": round(float((df.excess > 0).mean()), 3),
        "best_cell_excess": float(df.excess.max()),
        "median_cell_excess": float(df.excess.median()),
        "best_minus_median": round(float(df.excess.max() - df.excess.median()), 4),
    }
    return df, plateau


def walk_forward_xs(base: dict, regimes: list[dict]) -> tuple[pd.DataFrame, dict]:
    rows, attribution = [], {}
    for reg in regimes:
        cfg = _cell_cfg(base)
        cfg["experiment"]["stage"] = reg["stage"]
        cfg["experiment"]["name"] = f"p4_wf_{reg['name']}"
        cfg["data"]["sim_start"], cfg["data"]["sim_end"] = reg["start"], reg["end"]
        r = runner.run_resolved(cfg, label=reg["name"])
        rows.append({"regime": reg["name"], "catalyst": False,
                     "stage": reg["stage"], **{
                         k: r["row"][k] for k in
                         ("ann_return", "ann_return_benchmark",
                          "excess_return_ann", "sharpe_vs_rf", "max_drawdown",
                          "ann_cost_drag", "t_stat", "p_raw")},
                     "median_cap_bn": r["row"].get("median_cap_bn"),
                     "exp_id": r["exp_id"][:8]})
        attribution[reg["name"]] = {
            "sector_contribution": dict(list(
                r["metrics"].get("sector_contribution", {}).items())[:10]),
            "excess": r["row"]["excess_return_ann"],
            "sharpe": r["row"]["sharpe_vs_rf"],
            "capacity": r["capacity"] or {},
        }
    return pd.DataFrame(rows), attribution


def placebo_test_xs(base: dict, n_iter: int) -> dict:
    from . import backtest_xs
    gen = rng.make_rng(base["rng"])
    d = base["data"]
    con = db.init_db(PKG_ROOT / d.get("db_path", "data/ngx.sqlite"))
    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                             base["costs"]["brokerage_override_pct"])
    real_stat, placebo_stats = backtest_xs.placebo_stats(
        con, base, rates, n_iter, gen)
    p_val = stats.placebo_p_value(real_stat, placebo_stats)
    summary = {
        "real_sharpe": real_stat,
        "placebo_mean_sharpe": round(float(pd.Series(placebo_stats).mean()), 3),
        "placebo_p95_sharpe": round(float(pd.Series(placebo_stats).quantile(0.95)), 3),
        "placebo_max_sharpe": round(float(max(placebo_stats)), 3),
        "placebo_p_value": round(p_val, 4),
        "n_iterations": n_iter,
    }
    reg = registry.connect_registry()
    cfg = copy.deepcopy(base)
    cfg["experiment"]["stage"] = "placebo"
    cfg["experiment"]["name"] = "p4_placebo_shuffled_labels_xs"
    cfg["rng"]["iterations"] = n_iter
    registry.record_experiment(
        reg, config=cfg, config_path=None, metrics=summary,
        validation_flags={"synthetic_data": True, "counts_as_evidence": False,
                          "placebo_suite": True},
        notes=f"xs placebo (within-date/cohort label shuffle), "
              f"{n_iter} seeded iterations")
    reg.close()
    con.close()
    return summary


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_phase4(config_path: str | Path) -> dict:
    raw = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    p4 = raw.pop("phase4")
    base = runner.apply_defaults(raw)
    if base["engine"]["type"] == "cross_sectional":
        return run_phase4_xs(base, p4)

    print("=== 1/4 parameter stability map (lite engine, development window) ===")
    stab_df, plateau = stability_map(base, p4["stability"])
    for rb in p4["stability"]["rebalance"]:
        pv = stab_df[stab_df.rebalance == rb].pivot(
            index="lookbacks", columns="top_n", values="excess")
        print(f"\n net excess return — rebalance={rb}")
        print(pv.to_string())
    print(f"\n plateau: {plateau}")

    print("\n=== 2/4 multiple-testing correction across parameter cells ===")
    pvals = {f"{r.lookbacks}|N{r.top_n}|{r.rebalance}": r.p_raw
             for r in stab_df.itertuples() if r.p_raw is not None}
    holm_df = stats.holm(pvals)
    bh_df = stats.benjamini_hochberg(pvals)
    n_sig_raw = int((stab_df.p_raw < 0.05).sum())
    n_sig_holm = int(holm_df.significant_after_holm.sum())
    n_sig_bh = int(bh_df.significant_after_bh.sum())
    print(f" cells significant: raw p<0.05: {n_sig_raw}/{len(pvals)} | "
          f"after Holm: {n_sig_holm} | after BH(FDR): {n_sig_bh}")

    print("\n=== 3/4 placebo (shuffled sector labels) ===")
    plc = placebo_test(base, p4["placebo"]["iterations"])
    print(" ", json.dumps(plc))

    print("\n=== 4/4 walk-forward across regimes (full engine) ===")
    wf_df, attribution = walk_forward(base, p4["regimes"])
    print(wf_df.to_string(index=False))

    # ---- final failure-condition evaluation with complete evidence --------
    dev = wf_df[(wf_df.stage != "final_oos") & (~wf_df.catalyst)]
    oos = wf_df[(wf_df.stage == "final_oos") & (~wf_df.catalyst)]
    evidence = {
        "placebo_p": plc["placebo_p_value"],
        "is_sharpe": float(dev.sharpe_vs_rf.mean()),
        "oos_sharpe": float(oos.sharpe_vs_rf.iloc[0]) if len(oos) else None,
        "regime_excess": {r: a["excess"] for r, a in attribution.items()},
    }
    final_cfg = _cell_cfg(base)
    final_cfg["experiment"]["stage"] = "walk_forward"
    final_cfg["experiment"]["name"] = "p4_final_evaluation"
    final = runner.run_resolved(final_cfg, label="final evaluation",
                                phase4_evidence=evidence)
    fc = final["flags"]["failure_conditions"]

    rating = confidence_rating.rate(
        data_confidence=final["flags"]["data_min_confidence_seen"],
        synthetic=final["flags"]["synthetic_data"],
        n_decisions=final["metrics"]["n_rebalances"],
        n_regimes=len(attribution),
        p_corrected=(float(holm_df.p_holm.min()) if len(holm_df) else None),
        plateau_frac=plateau["frac_positive_excess"],
        placebo_pass=plc["placebo_p_value"] <= base["failure_conditions"]["placebo_alpha"],
    )

    bundle = {
        "variant": base["experiment"]["name"],
        "hypothesis_id": base["experiment"]["hypothesis_id"],
        "stability": stab_df, "plateau": plateau,
        "corrections": {"raw": n_sig_raw, "holm": n_sig_holm, "bh": n_sig_bh,
                        "n_tests": len(pvals),
                        "min_p_holm": float(holm_df.p_holm.min()) if len(holm_df) else None},
        "placebo": plc, "walk_forward": wf_df, "attribution": attribution,
        "failure_conditions": fc, "final_flags": final["flags"],
        "final_metrics": final["metrics"], "rating": rating,
        "evidence": evidence,
        "data_limitations": [
            ("SYNTHETIC DATA (confidence 0.0): every figure in this memo is a "
             "machinery rehearsal, not evidence about NGX"
             if final["flags"]["synthetic_data"] else
             f"minimum data confidence used: "
             f"{final['flags']['data_min_confidence_seen']}"),
            "within-sector weights are a trailing-ADTV proxy, not float-adjusted "
            "index weights (flatters capacity)",
            "risk-free rate placeholder 0% — NGN T-bill yields would materially "
            "lower every Sharpe shown" if
            final["flags"]["risk_free_rate_is_placeholder"] else
            "risk-free rate: configured",
            f"diagnostics at run time: errors={final['flags']['diagnostics'].get('errors', [])}, "
            f"warnings={final['flags']['diagnostics'].get('warnings', [])}",
        ],
        "implementation_risks": [
            "single-session execution assumed: real multi-day execution raises "
            "capacity roughly linearly with horizon but adds timing risk",
            "slippage (30bps) and sqrt-impact coefficient (15bps) are assumed, "
            "not estimated from NGX fill data",
            "brokerage is the dominant cost line (~60% of drag) and is "
            "negotiable — economics swing materially with the negotiated rate",
            "thin sectors (insurance) are persistent capacity bottlenecks; "
            "index membership churn risk not yet stress-tested",
        ],
    }
    memo_path = ic_report.generate(bundle)
    print(f"\nIC memo written: {memo_path}")
    print(f"confidence rating: {rating['rating']} (score {rating['score']})")
    return bundle


def run_phase4_xs(base: dict, p4: dict) -> dict:
    """Phase 4 for cross-sectional hypotheses. Identical validation
    semantics: stability grid → Holm/BH → seeded placebo → walk-forward
    with untouched final OOS → failure conditions → IC memo."""
    print("=== 1/4 parameter stability map (cross-sectional, development) ===")
    stab_df, plateau = stability_map_xs(base, p4["stability"]["grid"])
    print(stab_df.drop(columns=["exp_id"]).to_string(index=False))
    print(f"\n plateau: {plateau}")

    print("\n=== 2/4 multiple-testing correction across parameter cells ===")
    pvals = {r.cell: r.p_raw for r in stab_df.itertuples()
             if r.p_raw is not None}
    holm_df = stats.holm(pvals)
    bh_df = stats.benjamini_hochberg(pvals)
    n_sig_raw = int((stab_df.p_raw < 0.05).sum())
    n_sig_holm = int(holm_df.significant_after_holm.sum())
    n_sig_bh = int(bh_df.significant_after_bh.sum())
    print(f" cells significant: raw p<0.05: {n_sig_raw}/{len(pvals)} | "
          f"after Holm: {n_sig_holm} | after BH(FDR): {n_sig_bh}")

    print("\n=== 3/4 placebo (within-date/cohort label shuffle) ===")
    plc = placebo_test_xs(base, p4["placebo"]["iterations"])
    print(" ", json.dumps(plc))

    print("\n=== 4/4 walk-forward across regimes ===")
    wf_df, attribution = walk_forward_xs(base, p4["regimes"])
    print(wf_df.to_string(index=False))

    dev = wf_df[wf_df.stage != "final_oos"]
    oos = wf_df[wf_df.stage == "final_oos"]
    evidence = {
        "placebo_p": plc["placebo_p_value"],
        "is_sharpe": float(dev.sharpe_vs_rf.mean()),
        "oos_sharpe": float(oos.sharpe_vs_rf.iloc[0]) if len(oos) else None,
        "regime_excess": {r: a["excess"] for r, a in attribution.items()},
    }
    final_cfg = _cell_cfg(base)
    final_cfg["experiment"]["stage"] = "walk_forward"
    final_cfg["experiment"]["name"] = "p4_final_evaluation"
    final = runner.run_resolved(final_cfg, label="final evaluation",
                                phase4_evidence=evidence)
    fc = final["flags"]["failure_conditions"]

    rating = confidence_rating.rate(
        data_confidence=final["flags"]["data_min_confidence_seen"],
        synthetic=final["flags"]["synthetic_data"],
        n_decisions=final["metrics"]["n_rebalances"],
        n_regimes=len(attribution),
        p_corrected=(float(holm_df.p_holm.min()) if len(holm_df) else None),
        plateau_frac=plateau["frac_positive_excess"],
        placebo_pass=plc["placebo_p_value"] <= base["failure_conditions"]["placebo_alpha"],
    )

    bundle = {
        "variant": base["experiment"]["name"],
        "hypothesis_id": base["experiment"]["hypothesis_id"],
        "stability": stab_df, "plateau": plateau,
        "corrections": {"raw": n_sig_raw, "holm": n_sig_holm, "bh": n_sig_bh,
                        "n_tests": len(pvals),
                        "min_p_holm": float(holm_df.p_holm.min()) if len(holm_df) else None},
        "placebo": plc, "walk_forward": wf_df, "attribution": attribution,
        "failure_conditions": fc, "final_flags": final["flags"],
        "final_metrics": final["metrics"], "rating": rating,
        "evidence": evidence,
        "data_limitations": [
            f"minimum data confidence used: "
            f"{final['flags']['data_min_confidence_seen']}",
            "price-only per-stock returns (no dividend reinvestment) — "
            "conservative for winner-tilted longs; total-return retest "
            "possible after the DOL dividend layer lands",
            "177 single-source recovered days (close-only) in the panel — "
            "documented in docs/DATA_FREEZE_2026-07-21.md",
            "risk-free rate placeholder 0% — NGN T-bill yields would "
            "materially lower every Sharpe shown" if
            final["flags"]["risk_free_rate_is_placeholder"] else
            "risk-free rate: configured",
            f"diagnostics at run time: errors={final['flags']['diagnostics'].get('errors', [])}, "
            f"warnings={final['flags']['diagnostics'].get('warnings', [])}",
        ],
        "implementation_risks": [
            "single-session execution assumed at each rebalance leg",
            "brokerage (retail schedule, 'assumed' confidence) dominates "
            "cost drag and is negotiable — economics swing with the rate",
            "capacity distribution is ADTV-based; participation cap is "
            "reported, not enforced inside the simulation",
            "benchmark is the EW-IRU investable null computed by the same "
            "engine under the same costs (not an index)",
        ],
    }
    memo_path = ic_report.generate(bundle)
    print(f"\nIC memo written: {memo_path}")
    print(f"confidence rating: {rating['rating']} (score {rating['score']})")
    return bundle
