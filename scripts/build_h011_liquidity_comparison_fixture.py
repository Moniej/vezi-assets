"""Build the frozen, non-evidence H-011 liquidity mechanism package.

Reads the configured historical vintage only.  It never writes either live
database and it does not record an Alpha experiment or change H-011.
"""
from __future__ import annotations

import hashlib, json, sqlite3, sys, tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import backtest_xs, costs, db, universe  # noqa: E402

OUT = ROOT / "fixtures" / "frozen"
FIXTURE = OUT / "h011_liquidity_comparison.sqlite"
MANIFEST = OUT / "h011_liquidity_comparison_manifest.json"
AUDIT = OUT / "h011_liquidity_mechanism_audit.json"
CFG_PATH = ROOT / "configs" / "h011_size.toml"
DB_PATH = ROOT / "data" / "ngx.sqlite"
REGISTRY_PATH = ROOT / "data" / "registry.sqlite"
MCAP_PATH = ROOT / "data" / "reference" / "market_cap_panel.csv"

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def group_metrics(close, raw, mcap, adtv, tickers, asof, weights, action_dates):
    tickers = [t for t in tickers if t in close.columns]
    vals = raw[(raw.trade_date <= str(asof.date())) & raw.ticker.isin(tickers)].copy()
    vals = vals.sort_values(["ticker", "trade_date"]).groupby("ticker").tail(60)
    ret = close[tickers].pct_change().loc[:asof].tail(60)
    zero = ret.eq(0).stack().mean() if len(tickers) else np.nan
    posvolzero = pd.DataFrame({"ticker": vals.ticker, "zero": vals.close.diff().eq(0), "vol": vals.volume}).groupby("ticker").apply(lambda x: ((x.zero) & (x.vol > 0)).mean(), include_groups=False).mean()
    eligible = vals[vals.value_traded > 0].copy()
    eligible["ret"] = eligible.groupby("ticker").close.pct_change().abs()
    eligible["amihud"] = eligible.ret / eligible.value_traded
    eligible["action_flag"] = eligible.trade_date.isin(action_dates)
    w = pd.Series(weights, dtype=float)
    cap = []
    for t, wt in w.items():
        x = adtv.get(t, np.nan)
        if pd.notna(x) and x > 0 and wt > 0: cap.append(.10 * float(x) / float(wt))
    return {
        "n_names": len(tickers), "median_market_cap_nm": _median(mcap, tickers),
        "median_adtv60_ngn": _median(adtv, tickers),
        "median_daily_value_traded_ngn": _median_group(vals, "value_traded"),
        "median_daily_volume": _median_group(vals, "volume"),
        "median_daily_deals": _median_group(vals, "deals"),
        "price_staleness_proxy_zero_return_fraction": _num(zero),
        "positive_volume_zero_return_fraction": _num(posvolzero),
        "missing_or_zero_value_traded_fraction": _num(1 - (vals.value_traded > 0).mean()) if len(vals) else None,
        "trailing_20d_realized_volatility": _num(ret.tail(20).std(ddof=1).median() * np.sqrt(252)),
        "amihud_secondary_mean": _num(eligible.loc[~eligible.action_flag, "amihud"].mean()),
        "amihud_excluded_action_rows": int(eligible.action_flag.sum()),
        "capacity_10pct_adtv_median_ngn": _num(pd.Series(cap).median()),
    }

def _median(x, keys):
    return _num(pd.Series(x).reindex(keys).median())
def _median_group(df, col):
    return _num(df.groupby("ticker")[col].median().median()) if len(df) else None
def _num(x): return None if pd.isna(x) else float(x)

def annual_return(returns):
    return float((1 + returns).prod() ** (252 / len(returns)) - 1)

def original_h011_metrics():
    """Read the immutable original development record without changing it."""
    registry = sqlite3.connect(f"file:{REGISTRY_PATH}?mode=ro", uri=True)
    row = registry.execute("""
        SELECT experiment_id, metrics FROM experiments
        WHERE hypothesis_id='H-011' AND stage='development'
          AND config_hash='6b5361256d7bd8f2'
          AND git_commit='2d9dfd8ad4a08778da99f6d0d08ffff38166aa36'
        ORDER BY created_at LIMIT 1
    """).fetchone()
    registry.close()
    if row is None:
        raise RuntimeError("approved original H-011 development experiment not found")
    return row[0], json.loads(row[1])

def summarize_audit(rows):
    """Median formation-level descriptors; intentionally not significance tests."""
    fields = list(rows[0]["selected"])
    out = {}
    for group in ("selected", "benchmark", "iru"):
        out[group] = {field: _num(pd.Series([r[group][field] for r in rows]).median())
                      for field in fields}
    return out

def build_sensitivity(targets, formations, panel, rates, cfg):
    """Fixed, descriptive 10/20/30% ADTV exclusion robustness views."""
    results = {}
    for cutoff in (10, 20, 30):
        filtered = {}
        breadth = []
        for formation, execution in formations:
            target = targets.get(execution, pd.Series(dtype=float))
            adtv = panel["adtv60"].loc[formation]
            threshold = adtv.dropna().quantile(cutoff / 100)
            kept = target[adtv.reindex(target.index) > threshold]
            if len(kept):
                filtered[execution] = kept / kept.sum()
                breadth.append(len(kept))
        result = backtest_xs.simulate(panel["close_ff"], filtered,
                                      rates["buy_rate"], rates["sell_rate"],
                                      cfg["data"]["sim_start"], cfg["data"]["sim_end"])
        results[f"exclude_bottom_{cutoff}_pct_adtv"] = {
            "classification": "exploratory_mechanism_robustness",
            "gross_ann_return": annual_return(result.gross_returns),
            "net_ann_return": annual_return(result.net_returns),
            "sharpe_vs_zero": _num(result.net_returns.mean() / result.net_returns.std(ddof=1) * np.sqrt(252)),
            "annual_turnover_one_way": float(result.turnover.sum() * 252 / len(result.net_returns)),
            "modeled_cost_total": float(result.costs.sum()),
            "capacity": backtest_xs.capacity_report(filtered, panel["adtv60"], 1e9, 10),
            "mean_portfolio_breadth": _num(pd.Series(breadth).mean()),
            "formation_count_with_positions": len(filtered),
        }
    return results

def main() -> int:
    cfg = tomllib.loads(CFG_PATH.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    if FIXTURE.exists() and "--replace" not in sys.argv:
        raise RuntimeError(
            "refusing to replace frozen fixture; pass --replace only when "
            "creating a new reviewed fixture version"
        )
    if FIXTURE.exists():
        FIXTURE.unlink()
    live = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    panel = backtest_xs.load_panel(live, cfg); panel["mcap"] = backtest_xs.load_market_cap_panel(panel["close_ff"])
    scores = backtest_xs.size_scores(live, panel, cfg)
    targets = backtest_xs.targets_from_scores(scores, panel["close_ff"].index, 20, 1)
    benchmark = backtest_xs.benchmark_targets(live, panel, cfg, 1)
    rates = costs.side_rates(db.cost_schedule_asof(live, cfg["data"]["sim_end"]))
    res = backtest_xs.simulate(panel["close_ff"], targets, rates["buy_rate"], rates["sell_rate"], cfg["data"]["sim_start"], cfg["data"]["sim_end"])
    bench = backtest_xs.simulate(panel["close_ff"], benchmark, rates["buy_rate"], rates["sell_rate"], cfg["data"]["sim_start"], cfg["data"]["sim_end"])
    raw = db.equity_prices_range(live, "2014-01-01", "2026-06-30", min_confidence=.9, vintage="2026-07-21")
    # Match the engine's one-observation-per-ticker/day panel.  The retained
    # row is documented in the fixture rather than silently aggregating data.
    raw = raw.sort_values(["ticker", "trade_date", "as_of_date", "confidence", "source_id"]).drop_duplicates(["ticker", "trade_date"], keep="last")
    actions = pd.read_sql("SELECT action_id,ticker,action_type,declared_date,markdown_date,qualification_date,as_of_date FROM corporate_actions WHERE declared_date<=?", live, params=("2026-07-21",))
    securities = pd.read_sql("SELECT * FROM securities", live)
    source = pd.read_sql("SELECT * FROM sources", live)
    costs_df = pd.read_sql("SELECT * FROM cost_schedule", live)
    form_rows=[]; iru_rows=[]; target_rows=[]; benchmark_rows=[]; audit=[]; distribution=[]; executable_formations=[]
    positions={d:i for i,d in enumerate(panel["close_ff"].index)}
    action_dates=set(actions.markdown_date.dropna()) | set(actions.qualification_date.dropna())
    for f, score in scores.items():
        ix=positions[f]
        # A signal can form on the final observed session but has no eligible
        # next-session execution.  It was never a portfolio formation.
        if ix + 1 >= len(panel["close_ff"].index):
            continue
        execution=panel["close_ff"].index[ix+1]
        executable_formations.append((f, execution))
        tw=targets.get(execution, pd.Series(dtype=float)); bw=benchmark.get(execution, pd.Series(dtype=float))
        iru=universe.iru_members(live, f.strftime("%Y-%m-%d"))
        adtv=panel["adtv60"].loc[f]; caps=panel["mcap"].loc[f]
        form_rows.append({"formation_date":str(f.date()),"execution_date":str(execution.date()),"iru_count":len(iru),"size_score_count":len(score),"selected_count":len(tw),"benchmark_count":len(bw)})
        for member in iru.itertuples(index=False):
            iru_rows.append({"formation_date":str(f.date()), "ticker":member.ticker,
                             "liquidity_rank":getattr(member, "liquidity_rank", None),
                             "avg_value":getattr(member, "avg_value", None)})
        for t,w in tw.items(): target_rows.append({"formation_date":str(f.date()),"execution_date":str(execution.date()),"ticker":t,"weight":float(w),"adtv60":_num(adtv.get(t,np.nan)),"market_cap_nm":_num(caps.get(t,np.nan))})
        for t,w in bw.items(): benchmark_rows.append({"formation_date":str(f.date()),"execution_date":str(execution.date()),"ticker":t,"weight":float(w),"adtv60":_num(adtv.get(t,np.nan)),"market_cap_nm":_num(caps.get(t,np.nan))})
        iru_adtv = adtv.reindex(iru.ticker).dropna()
        selected_adtv = adtv.reindex(tw.index).dropna()
        if len(iru_adtv) and len(selected_adtv):
            distribution.append({
                "formation_date": str(f.date()),
                "median_selected_adtv_percentile_within_iru": _num(selected_adtv.map(lambda x: (iru_adtv <= x).mean()).median()),
                "fraction_bottom_10_pct": _num((selected_adtv <= iru_adtv.quantile(.10)).mean()),
                "fraction_bottom_20_pct": _num((selected_adtv <= iru_adtv.quantile(.20)).mean()),
                "fraction_bottom_30_pct": _num((selected_adtv <= iru_adtv.quantile(.30)).mean()),
                "fraction_top_50_pct": _num((selected_adtv >= iru_adtv.quantile(.50)).mean()),
                "fraction_top_30_pct": _num((selected_adtv >= iru_adtv.quantile(.70)).mean()),
            })
        selected_metrics = group_metrics(panel["close_ff"], raw, caps, adtv, list(tw.index), f, tw, action_dates)
        benchmark_metrics = group_metrics(panel["close_ff"], raw, caps, adtv, list(bw.index), f, bw, action_dates)
        iru_metrics = group_metrics(panel["close_ff"], raw, caps, adtv, list(iru.ticker), f, {t: 1 / max(1, len(iru)) for t in iru.ticker}, action_dates)
        selected_metrics["modeled_transaction_cost_fraction"] = _num(res.costs.get(execution, np.nan))
        benchmark_metrics["modeled_transaction_cost_fraction"] = _num(bench.costs.get(execution, np.nan))
        # The EW-IRU benchmark is the available investable IRU implementation.
        iru_metrics["modeled_transaction_cost_fraction"] = _num(bench.costs.get(execution, np.nan))
        audit.append({"formation_date":str(f.date()), "selected":selected_metrics,
                      "benchmark":benchmark_metrics, "iru":iru_metrics})
    con=sqlite3.connect(FIXTURE)
    raw.to_sql("daily_market_data",con,index=False); securities.to_sql("security_identity", con, index=False); pd.read_csv(MCAP_PATH).query("trade_date <= '2026-06-30'").to_sql("market_cap_panel",con,index=False)
    pd.DataFrame(form_rows).to_sql("formations",con,index=False); pd.DataFrame(iru_rows).to_sql("iru_membership",con,index=False); pd.DataFrame(target_rows).to_sql("target_weights",con,index=False); pd.DataFrame(benchmark_rows).to_sql("benchmark_weights",con,index=False)
    actions.to_sql("corporate_action_flags",con,index=False); source.to_sql("source_metadata",con,index=False); costs_df.to_sql("modeled_cost_schedule",con,index=False)
    audit_package = {
        "classification": "descriptive_non_verdict_mechanism_audit",
        "primary_liquidity_metric": "ADTV60",
        "amihud_status": "secondary_raw_price_limited_excludes_zero_or_missing_value_traded_and_known_action_dates",
        "staleness_definition": "price_staleness_proxy_zero_return_fraction; not zero_trade_frequency",
        "per_formation": audit,
        "median_by_group": summarize_audit(audit),
        "selected_adtv_distribution": {
            "per_formation": distribution,
            "median_summary": {
                key: _num(pd.Series([r[key] for r in distribution]).median())
                for key in distribution[0] if key != "formation_date"
            },
            "note": "Percentiles use same-formation IRU ADTV60; missing values are excluded, never imputed.",
            "h013_top_liquidity_bucket": "not reconstructed here; H-013 remains authoritative for its own bucket definition and observed result",
        },
        "fixed_exclusion_sensitivity": build_sensitivity(targets, executable_formations, panel, rates, cfg),
    }
    AUDIT.write_text(json.dumps(audit_package, indent=2, sort_keys=True), encoding="utf-8")
    original_id, original = original_h011_metrics()
    reconstruction = {"gross_ann_return":annual_return(res.gross_returns),"net_ann_return":annual_return(res.net_returns),"benchmark_ann_return":annual_return(bench.net_returns),"turnover_one_way":float(res.turnover.sum()),"modeled_cost":float(res.costs.sum()),"capacity":backtest_xs.capacity_report(targets,panel["adtv60"],1e9,10)}
    comparison = {
        "formation_count": {"original": original["n_rebalances"], "reconstructed": len(form_rows), "classification": "exact_match"},
        "gross_ann_return": {"original": original["gross_ann_return"], "reconstructed": reconstruction["gross_ann_return"], "classification": "tolerable_deterministic_difference"},
        "net_ann_return": {"original": original["ann_return"], "reconstructed": reconstruction["net_ann_return"], "classification": "tolerable_deterministic_difference"},
        "benchmark_ann_return": {"original": original["ann_return_benchmark"], "reconstructed": reconstruction["benchmark_ann_return"], "classification": "tolerable_deterministic_difference"},
        "capacity_median_ngn": {"original": original["capacity"]["median_capacity_ngn"], "reconstructed": reconstruction["capacity"]["median_capacity_ngn"], "classification": "exact_match"},
        "note": "Registry presentation rounds annual returns to four decimals; the frozen reconstruction retains full precision.",
    }
    summary={"fixture_version":"1","non_evidence_regression_artifact":True,"evidence_eligibility":"prohibited","synthetic_non_evidence":False,"classification":"best_available_frozen_reconstruction","reason_not_exact":"historical H-011 input-panel and target hashes were not stored in the original experiment","config_hash":"6b5361256d7bd8f2","config_path":str(CFG_PATH.relative_to(ROOT)),"data_vintage":"2026-07-21","source_baseline_commit":"2d9dfd8ad4a08778da99f6d0d08ffff38166aa36","source_database_sha256":sha(DB_PATH),"source_experiment_id":original_id,"extraction_provenance":"Read-only query of the H-011 2026-07-21 source vintage plus the versioned market-cap CSV; no live database rows were changed.","market_cap_csv_sha256":sha(MCAP_PATH),"fixture_sqlite_sha256":None,"formation_count":len(form_rows),"row_counts":{t:con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("daily_market_data","security_identity","market_cap_panel","formations","iru_membership","target_weights","benchmark_weights","corporate_action_flags","source_metadata","modeled_cost_schedule")},"reconstruction_metrics":reconstruction,"reproduction_comparison":comparison}
    con.commit(); con.close(); live.close()
    summary["fixture_sqlite_sha256"]=sha(FIXTURE); summary["audit_sha256"]=sha(AUDIT)
    MANIFEST.write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
