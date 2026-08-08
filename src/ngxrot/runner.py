"""Config-driven experiment runner.

Running an experiment = pointing this at a TOML file (run_config), or — for
orchestrated validation (Phase 4) — calling run_resolved with a resolved
config dict. Both paths share identical guards and registration; there is no
way to run a backtest that skips the registry.

Guards enforced here (not by convention):
  - stage='development' runs may not touch dates >= validation.holdout_start —
    the run is refused, not silently clamped;
  - synthetic/low-confidence data forces counts_as_evidence=False whatever
    the metrics say;
  - an optional [sweep] table expands into the cartesian product of listed
    values; every cell is its own immutable experiment.
"""

from __future__ import annotations

import itertools
import tomllib
from pathlib import Path

import pandas as pd

from . import (backtest_lite, costs, db, diagnostics, engine_full,
               failure_conditions, metrics, registry, riskfree, rng)
from . import signal as sig
from .ingest import ingest
from .providers import SyntheticProvider

PKG_ROOT = Path(__file__).resolve().parents[2]

_DEFAULTS = {
    "experiment": {"stage": "development", "hypothesis_id": None, "seed": None},
    "data": {"min_confidence": 0.0, "vintage": ""},
    "signal": {"method": "rank_average"},
    "portfolio": {"construction": "equal_weight", "execution_lag_days": 1,
                  "catalyst_filter": False, "impairment_window_months": 12},
    "costs": {"source": "db", "brokerage_override_pct": -1.0},
    "liquidity": {"adtv_participation_cap_pct": 10.0, "adtv_window_days": 60,
                  "enforced": False},
    "validation": {"risk_free_annual_pct": 0.0, "use_real_risk_free_rate": False},
    "engine": {"type": "lite", "aum_ngn": 2e9, "slippage_bps": 30.0,
               "impact_coeff_bps": 15.0},
    "rng": {"algorithm": "PCG64", "seed": None, "iterations": 0},
    "failure_conditions": {"min_median_capacity_ngn": 0.0,
                           "max_single_sector_share": 1.0,
                           "placebo_alpha": 0.05,
                           "min_oos_sharpe_retention": 0.25,
                           "max_single_regime_share": 1.0},
    "diagnostics": {"run": True, "params": {}},
}


def load_config(path: str | Path) -> dict:
    cfg = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return apply_defaults(cfg)


def apply_defaults(cfg: dict) -> dict:
    for section, defaults in _DEFAULTS.items():
        cfg.setdefault(section, {})
        for k, v in defaults.items():
            cfg[section].setdefault(k, v)
    for section in ("experiment", "data", "signal", "portfolio", "validation"):
        if section not in cfg:
            raise ValueError(f"config missing [{section}]")
    return cfg


def _expand_sweep(cfg: dict) -> list[tuple[str, dict]]:
    sweep = cfg.pop("sweep", None)
    if not sweep:
        return [("", cfg)]
    keys, values = list(sweep), [sweep[k] for k in sweep]
    out = []
    for combo in itertools.product(*values):
        c = {s: dict(v) if isinstance(v, dict) else v for s, v in cfg.items()}
        label_parts = []
        for dotted, val in zip(keys, combo):
            section, key = dotted.split(".")
            c[section][key] = val
            label_parts.append(f"{key}={val}")
        out.append((", ".join(label_parts), c))
    return out


def _ensure_data(con, sources: list[str], sim_end: str) -> None:
    have = {r[0] for r in con.execute(
        "SELECT DISTINCT s.name FROM index_levels il JOIN sources s USING (source_id)")}
    missing = set(sources) - have
    if missing == {"synthetic_dev"}:
        syn = SyntheticProvider()
        for ds, kw in [("index_levels", dict(index_codes=None, start="2016-01-01", end=sim_end)),
                       ("equity_prices", dict(tickers=None, start="2016-01-01", end=sim_end)),
                       ("corporate_actions", dict(tickers=None)),
                       ("index_membership", dict(index_codes=None)),
                       ("events", dict(start="2016-01-01", end=sim_end))]:
            ingest(con, syn, ds, **kw)
    elif missing:
        raise RuntimeError(f"no ingested data for sources {sorted(missing)} — "
                           f"run the relevant provider ingestion first")


def _rf_series_if_enabled(v: dict, index: pd.DatetimeIndex):
    """None unless validation.use_real_risk_free_rate is set — opt-in,
    additive; every existing config's behavior is unchanged without it.
    See docs/PREREG_METH-002_risk_free_rate.md."""
    if not v.get("use_real_risk_free_rate"):
        return None
    return riskfree.mpr_asof_series(index)


def build_scores(cfg: dict, universe: pd.DataFrame, con) -> pd.DataFrame:
    """Single score-construction path shared by run_resolved and the Phase 4
    placebo test — signal methods are config-selected, never duplicated."""
    s, d = cfg["signal"], cfg["data"]
    method = s.get("method", "rank_average")
    if method == "macro_gate":
        macro = db.macro_series_asof(
            con, s["macro_series"], d["sim_end"],
            min_confidence=d["min_confidence"], vintage=d["vintage"] or None)
        if macro.empty:
            raise RuntimeError(f"macro series {s['macro_series']!r} has no rows "
                               f"under this config's confidence/vintage")
        return sig.macro_gate_scores(universe, macro, s["target_index"],
                                     s["neutral_index"], s["lookbacks_months"][0])
    if method == "event_window":
        ev = db.events_asof(con, d["sim_end"],
                            event_types=s["event_types"],
                            min_confidence=d["min_confidence"],
                            vintage=d["vintage"] or None)
        if ev.empty:
            raise RuntimeError(f"no events of types {s['event_types']} under "
                               f"this config's confidence/vintage")
        return sig.event_window_scores(
            universe, ev.announced_date.tolist(), s["target_index"],
            s["neutral_index"], hold_days=s["lookbacks_months"][0])
    if method == "catalyst_activity":
        ev = db.events_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                            vintage=d["vintage"] or None)
        if ev.empty:
            raise RuntimeError("no events under this config's confidence/vintage")
        sectors = [u for u in d["universe"] if u != s["neutral_index"]]
        return sig.catalyst_activity_scores(
            universe, ev, sectors, s["neutral_index"],
            window_months=s["lookbacks_months"][0],
            categories=s["event_categories"])
    if method == "rank_average":
        return sig.momentum_scores(universe, s["lookbacks_months"],
                                   s["lookback_weights"])
    raise ValueError(f"unknown signal method {method!r}")


def run_resolved(cfg: dict, label: str = "", config_path: str | None = None,
                 quiet: bool = True, phase4_evidence: dict | None = None) -> dict:
    """Run one fully resolved config; register it; return everything.

    Returns dict with: exp_id, row (summary), metrics, flags, result,
    capacity. ``phase4_evidence`` feeds the placebo/OOS/regime failure
    conditions once Phase 4 has produced them.
    """
    e, d, s, p, c, v = (cfg["experiment"], cfg["data"], cfg["signal"],
                        cfg["portfolio"], cfg["costs"], cfg["validation"])

    if d.get("requires_coverage_gate"):
        from . import coverage
        g = coverage.gate_status()
        if not g.get("gate_pass"):
            raise RuntimeError(
                f"coverage gate FAILING ({g.get('reason', 'thresholds unmet')}) — "
                f"per-stock hypotheses may not run until the Data Coverage "
                f"Dashboard passes configs/coverage_thresholds.toml. Refusing.")

    holdout = v.get("holdout_start")
    if e["stage"] == "development" and holdout and d["sim_end"] >= holdout:
        raise RuntimeError(
            f"stage=development but sim_end {d['sim_end']} >= holdout_start "
            f"{holdout}. Out-of-sample data is reserved for walk_forward/"
            f"final_oos stages. Refusing.")

    con = db.init_db(PKG_ROOT / d.get("db_path", "data/ngx.sqlite"))
    xs = cfg["engine"]["type"] == "cross_sectional"
    if not xs:
        _ensure_data(con, d["sources"], d["sim_end"])

    diag_summary = {}
    if cfg["diagnostics"]["run"]:
        ctx = diagnostics.DiagContext(con, d["sim_start"], d["sim_end"],
                                      cfg["diagnostics"]["params"])
        dres = diagnostics.run_all(ctx)
        diag_summary = {
            "errors": sorted(r.name for r in dres
                             if not r.passed and r.severity == "ERROR"),
            "warnings": sorted(r.name for r in dres
                               if not r.passed and r.severity == "WARNING"),
        }

    if cfg["rng"]["seed"] is not None:
        rng.make_rng(cfg["rng"])   # validates; Phase 4 stochastic code uses it

    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                             c["brokerage_override_pct"])
    if not xs:
        lv = db.index_levels_asof(
            con, d["sim_end"], d["universe"] + [d["benchmark"]],
            min_confidence=d["min_confidence"], vintage=d["vintage"] or None,
            sources=d["sources"])
        if lv.empty:
            raise RuntimeError("no index data visible under this config's "
                               "confidence/vintage/source constraints")
        data_conf = float(lv.confidence.min())

    capacity, fc_eval = {}, {}
    if xs:
        from . import backtest_xs
        result, capacity, data_conf = backtest_xs.run_from_config(
            con, cfg, rates)
        m = metrics.compute(result, v["risk_free_annual_pct"],
                            _rf_series_if_enabled(v, result.net_returns.index))
        m["capacity"] = capacity
        m["sector_contribution"] = result.sector_contribution
        if result.attribution:
            # E16 fix (2026-07-22): pooled_rank_run's diagnostics (cohort
            # return correlation, per-cohort turnover) were computed and
            # attached to result.attribution but never persisted past
            # this point — H-010's real correlation had to be recovered
            # by hand after the fact. Persist verbatim (already the
            # right shape/rounding from pooled_rank_run; unlike the
            # `full` engine's cost_attribution_cum below, this is a
            # nested diagnostics dict, not flat numeric costs — do not
            # apply the same {k: round(v,5)} transform to it).
            m["attribution"] = result.attribution
        # Stage 1 / A-2 (2026-08-08): the cross-sectional engine's own
        # sector_contribution is already keyed by TICKER, not sector (see
        # XSResult's field comment) — reused here, honestly relabeled, as
        # the new single_name_dependency check's input. The `full` engine
        # branch below does NOT get this (its sector_contribution is
        # genuinely per-sector), so it correctly stays "not evaluable"
        # rather than being fed the wrong granularity.
        fc_eval = failure_conditions.evaluate(
            cfg["failure_conditions"], m, capacity,
            result.sector_contribution, phase4_evidence,
            name_contribution=result.sector_contribution)
    elif cfg["engine"]["type"] == "full":
        result = engine_full.run_full(con, cfg)
        m = metrics.compute(result, v["risk_free_annual_pct"],
                            _rf_series_if_enabled(v, result.net_returns.index))
        capacity = engine_full.capacity_report(result, cfg["engine"]["aum_ngn"])
        m["capacity"] = capacity
        m["cost_attribution_cum"] = {k: round(val, 5) for k, val
                                     in result.attribution.items()}
        m["sector_contribution"] = result.sector_contribution
        m["tr_dividend_adjustments"] = result.tr_adjustments
        fc_eval = failure_conditions.evaluate(
            cfg["failure_conditions"], m, capacity, result.sector_contribution,
            phase4_evidence)
    else:
        wide = lv.pivot(index="trade_date", columns="index_code",
                        values="close_value")
        wide.index = pd.to_datetime(wide.index)
        universe, bench = wide[d["universe"]], wide[d["benchmark"]]
        ev = db.events_asof(con, d["sim_end"], min_confidence=d["min_confidence"],
                            vintage=d["vintage"] or None)
        scores = build_scores(cfg, universe, con)
        result = backtest_lite.run(
            universe, bench, scores, ev,
            top_n=p["top_n"], construction=p["construction"],
            rebalance=p["rebalance"], execution_lag_days=p["execution_lag_days"],
            catalyst_filter=p["catalyst_filter"],
            impairment_window_months=p["impairment_window_months"],
            buy_rate=rates["buy_rate"], sell_rate=rates["sell_rate"],
            sim_start=d["sim_start"], sim_end=d["sim_end"])
        m = metrics.compute(result, v["risk_free_annual_pct"],
                            _rf_series_if_enabled(v, result.net_returns.index))
        m["sector_contribution"] = result.sector_contribution
        fc_eval = failure_conditions.evaluate(
            cfg["failure_conditions"], m, {}, result.sector_contribution,
            phase4_evidence)

    full = cfg["engine"]["type"] == "full"
    flags = {
        "engine": cfg["engine"]["type"],
        "counts_as_evidence": data_conf > 0.0,
        "data_min_confidence_seen": data_conf,
        "synthetic_data": data_conf == 0.0,
        "price_index_only_no_dividends": not full,
        "within_sector_weights_are_adtv_proxy": full,
        "liquidity_constraint_enforced": full,
        "is_holdout_clean": not holdout or d["sim_end"] < holdout,
        "risk_free_rate_is_placeholder": (
            v["risk_free_annual_pct"] == 0.0 and not (
                v.get("use_real_risk_free_rate") and m.get("real_rf_coverage_gap") == 0)),
        "diagnostics": diag_summary,
        "failure_conditions": fc_eval,
        "hypothesis_reject_recommended": bool(
            fc_eval.get("_signal_reject_recommended", False)),
        "scalability_limited": bool(fc_eval.get("_scalability_limited", False)),
    }
    cfg_costs = {**c, "resolved_buy_rate": rates["buy_rate"],
                 "resolved_sell_rate": rates["sell_rate"],
                 "line_items": rates["line_items"]}
    reg = registry.connect_registry()
    exp_id = registry.record_experiment(
        reg, config={**cfg, "costs": cfg_costs}, config_path=config_path,
        metrics=m, validation_flags=flags,
        notes=(f"sweep cell: {label}" if label else ""))
    reg.close()
    con.close()

    row = {"experiment": exp_id[:8], "label": label or e["name"],
           "stage": e["stage"], "rebalance": p["rebalance"],
           "catalyst": p["catalyst_filter"],
           "brokerage%": (c["brokerage_override_pct"]
                          if c["brokerage_override_pct"] >= 0 else 1.35),
           **{k: m[k] for k in
              ("ann_return", "gross_ann_return", "ann_return_benchmark",
               "excess_return_ann", "sharpe_vs_rf", "max_drawdown",
               "hit_rate_vs_benchmark", "ann_turnover_oneway", "ann_cost_drag")},
           "t_stat": m["excess_ttest"]["t_stat"],
           "p_raw": m["excess_ttest"]["p_value"]}
    if capacity:
        row |= {"aum_bn": cfg["engine"]["aum_ngn"] / 1e9,
                "median_cap_bn": round(capacity["median_capacity_ngn"] / 1e9, 2),
                "legs_rejected%": capacity["pct_legs_rejected"],
                "signal_reject": flags["hypothesis_reject_recommended"],
                "scalability_limited": flags["scalability_limited"]}
    if not quiet and result.exclusions:
        print(f"   [{label or e['name']}] catalyst exclusions on "
              f"{len(result.exclusions)} rebalances")
    return {"exp_id": exp_id, "row": row, "metrics": m, "flags": flags,
            "result": result, "capacity": capacity, "config": cfg}


def run_config(config_path: str | Path, quiet: bool = False) -> pd.DataFrame:
    base = load_config(config_path)
    grid = _expand_sweep(base)
    rows = [run_resolved(cfg, label, str(config_path), quiet)["row"]
            for label, cfg in grid]
    return pd.DataFrame(rows)
