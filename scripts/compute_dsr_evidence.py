"""Recompute daily-frequency net-return series for every resolved
hypothesis's canonical final-evaluation config, to derive the inputs the
Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014) requires: per-trial
daily Sharpe ratio (for cross-sectional variance V[{SR_n}]), and for the
focal hypothesis, daily skewness/kurtosis/T.

Deliberately does NOT call runner.run_resolved() / registry.record_experiment
-- that would (a) write new rows into the immutable registry for a pure
statistics-recomputation task, doubling as noise, and (b) fail outright for
any hypothesis already frozen (H-001), since the registry's SQL triggers
forbid new experiments under a frozen hypothesis_id by design (ledger.py:
"Permanently close a RESOLVED hypothesis: no further status changes and no
new experiments under this ID"). Instead this replicates only the
data-to-returns path runner.run_resolved() already uses internally, read-only,
using each hypothesis's own already-frozen final-evaluation config_json
(frozen data, frozen seed, frozen code fingerprint at the time it was run).

Each hypothesis's recomputed annualized Sharpe is checked against the
value already stored in the registry as an integrity check on the rerun
faithfully reproducing history -- reported plainly, not hidden, if it
disagrees.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from scipy import stats as scipy_stats

from ngxrot import backtest_lite, backtest_xs, costs, db, metrics, runner

PKG_ROOT = Path(__file__).resolve().parents[1]
REG_DB = PKG_ROOT / "data" / "registry.sqlite"


def latest_final_eval_configs() -> dict:
    con = sqlite3.connect(REG_DB)
    rows = con.execute(
        "SELECT hypothesis_id, experiment_id, created_at, config_json, metrics "
        "FROM experiments WHERE stage='walk_forward' AND notes LIKE '%final evaluation%' "
        "ORDER BY hypothesis_id, created_at").fetchall()
    con.close()
    latest = {}
    for h, eid, created, cfgjson, metricsjson in rows:
        latest[h] = (eid, created, json.loads(cfgjson), json.loads(metricsjson))
    return latest


def rerun_readonly(cfg: dict):
    """Reproduce runner.run_resolved()'s data->result path with zero writes."""
    e, d, s, p, c, v = (cfg["experiment"], cfg["data"], cfg["signal"],
                        cfg["portfolio"], cfg["costs"], cfg["validation"])
    con = db.init_db(PKG_ROOT / d.get("db_path", "data/ngx.sqlite"))
    xs = cfg["engine"]["type"] == "cross_sectional"
    if not xs:
        runner._ensure_data(con, d["sources"], d["sim_end"])
    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                              c["brokerage_override_pct"])
    if xs:
        result, capacity, data_conf = backtest_xs.run_from_config(con, cfg, rates)
    else:
        lv = db.index_levels_asof(
            con, d["sim_end"], d["universe"] + [d["benchmark"]],
            min_confidence=d["min_confidence"], vintage=d["vintage"] or None,
            sources=d["sources"])
        wide = lv.pivot(index="trade_date", columns="index_code", values="close_value")
        wide.index = pd.to_datetime(wide.index)
        universe, bench = wide[d["universe"]], wide[d["benchmark"]]
        ev = db.events_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                             vintage=d["vintage"] or None)
        scores = runner.build_scores(cfg, universe, con)
        result = backtest_lite.run(
            universe, bench, scores, ev,
            top_n=p["top_n"], construction=p["construction"],
            rebalance=p["rebalance"], execution_lag_days=p["execution_lag_days"],
            catalyst_filter=p["catalyst_filter"],
            impairment_window_months=p["impairment_window_months"],
            buy_rate=rates["buy_rate"], sell_rate=rates["sell_rate"],
            sim_start=d["sim_start"], sim_end=d["sim_end"])
    con.close()
    return result


def main():
    latest = latest_final_eval_configs()
    out = {}
    for h, (eid, created, cfg, stored_metrics) in sorted(latest.items()):
        print(f"=== {h} (orig exp {eid[:8]}, {created}) ===")
        try:
            result = rerun_readonly(cfg)
        except Exception as e:
            print(f"  RERUN FAILED: {e!r}")
            out[h] = {"error": repr(e)}
            continue
        m = metrics.compute(result, cfg["validation"]["risk_free_annual_pct"])
        r, bench = result.net_returns, result.benchmark_returns
        excess = (r - bench).dropna()
        daily_sr = float(excess.mean() / excess.std()) if excess.std() > 0 else None
        skew = float(scipy_stats.skew(excess, bias=False))
        kurt = float(scipy_stats.kurtosis(excess, fisher=False, bias=False))
        recomputed_ann_sharpe = m["sharpe_vs_rf"]
        stored_ann_sharpe = stored_metrics.get("sharpe_vs_rf")
        match = (recomputed_ann_sharpe == stored_ann_sharpe)
        print(f"  daily excess SR = {daily_sr:.4f}  T={len(excess)}  "
              f"skew={skew:.3f}  kurt={kurt:.3f}")
        print(f"  annualized sharpe: stored={stored_ann_sharpe} "
              f"recomputed={recomputed_ann_sharpe} MATCH={match}")
        out[h] = {
            "orig_experiment_id": eid,
            "daily_excess_sharpe": daily_sr,
            "T_daily_obs": int(len(excess)),
            "skewness": skew,
            "kurtosis_regular": kurt,
            "stored_annualized_sharpe": stored_ann_sharpe,
            "recomputed_annualized_sharpe": recomputed_ann_sharpe,
            "integrity_check_pass": match,
        }
    dest = PKG_ROOT / "experiments" / "dsr_evidence_2026-08-02.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwritten: {dest}")


if __name__ == "__main__":
    main()
