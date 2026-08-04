"""H-017 mandatory orthogonality assessment against Size and Liquidity,
per docs/PREREG_H-017_dividend_payer_status.md Section 8. Read-only
analysis, no database writes.

Section 8.1 (unconditional): Spearman rank correlation between the
binary payer-status flag and (a) the Size z-score, (b) the Liquidity
(ADTV) z-score, at every formation date -- reported regardless of the
base test's outcome.

Section 8.2 (conditional -- only meaningful if the base test confirms):
double-sort bucket decomposition, mirroring Phase R2 (H-013/014/015)
applied prospectively. Always computed here for completeness and
disclosed either way, per the pre-registration's own instruction that
the correlation/decomposition evidence be reported "regardless of its
value."

  python -u scripts/run_h017_orthogonality.py
"""
import json

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from ngxrot import backtest_xs as bx
from ngxrot import costs, db, runner, stats, universe

CFG_C_BROKERAGE_KEY = "brokerage_override_pct"

CONFIG_PATH = "configs/h017_payer_status.toml"


def spearman_corr(payer_flags: pd.Series, other: pd.Series) -> float | None:
    common = payer_flags.index.intersection(other.index)
    if len(common) < 10:
        return None
    x = payer_flags.loc[common].astype(float)
    y = other.loc[common].astype(float)
    if x.std() == 0 or y.std() == 0:
        return None
    rho, _ = scipy_stats.spearmanr(x, y)
    return float(rho)


def main():
    base = runner.load_config(CONFIG_PATH)
    con = db.init_db(base["data"].get("db_path", "data/ngx.sqlite"))
    panel = bx.load_panel(con, base)
    close = panel["close_ff"]
    mcap = bx.load_market_cap_panel(close)
    panel["mcap"] = mcap

    payer_scores = bx.payer_status_scores(con, panel, base)
    size_cfg = dict(base)
    size_scores = bx.size_scores(con, panel, size_cfg)
    liq_cfg = {**base, "signal": {**base["signal"], "method": "xs_liquidity",
                                  "direction": "illiquid"}}
    liq_scores_raw = bx.xs_liquidity_scores(con, panel, liq_cfg)
    # xs_liquidity_scores signs by direction (illiquid = negative ADTV);
    # un-sign back to a plain standardized-ADTV score for correlation
    # purposes only (direction doesn't matter for a correlation check).
    liq_scores = {f: -sc for f, sc in liq_scores_raw.items()}

    # --- 8.1: unconditional Spearman correlation, every formation date ---
    rows = []
    for f, payers in payer_scores.items():
        iru_rules = universe.load_rules()
        elig = bx._eligible(con, panel, f, iru_rules,
                            int(base["signal"].get("min_obs_formation", 120)),
                            int(base["signal"].get("lookback_months", 12) * 31))
        if len(elig) < 10:
            continue
        flag = pd.Series(0.0, index=elig)
        flag.loc[flag.index.isin(payers.index)] = 1.0

        rho_size = spearman_corr(flag, size_scores.get(f, pd.Series(dtype=float)))
        rho_liq = spearman_corr(flag, liq_scores.get(f, pd.Series(dtype=float)))
        rows.append({"formation": str(f.date()), "n_elig": len(elig),
                     "n_payers": len(payers), "rho_size": rho_size,
                     "rho_liquidity": rho_liq})

    corr_df = pd.DataFrame(rows)
    summary = {
        "n_dates": len(corr_df),
        "rho_size": {
            "mean": float(corr_df.rho_size.mean()),
            "median": float(corr_df.rho_size.median()),
            "p25": float(corr_df.rho_size.quantile(0.25)),
            "p75": float(corr_df.rho_size.quantile(0.75)),
            "frac_abs_ge_0_6": float((corr_df.rho_size.abs() >= 0.6).mean()),
        },
        "rho_liquidity": {
            "mean": float(corr_df.rho_liquidity.mean()),
            "median": float(corr_df.rho_liquidity.median()),
            "p25": float(corr_df.rho_liquidity.quantile(0.25)),
            "p75": float(corr_df.rho_liquidity.quantile(0.75)),
            "frac_abs_ge_0_6": float((corr_df.rho_liquidity.abs() >= 0.6).mean()),
        },
    }
    print("=== Section 8.1: unconditional Spearman correlation ===")
    print(json.dumps(summary, indent=2))

    # --- 8.2: bucket decomposition (median-split Size, median-split
    # Liquidity), long-payers-within-bucket vs EW-of-bucket, evaluated
    # via the SAME simulate()/targets_from_scores() primitives, pooled
    # across formation dates into one return series per bucket. ---
    d, p, c = base["data"], base["portfolio"], base["costs"]
    rates = costs.side_rates(db.cost_schedule_asof(con, d["sim_end"]),
                             c["brokerage_override_pct"])
    lag = int(p["execution_lag_days"])
    close_index = close.loc[:d["sim_end"]].index
    pos = {dt: i for i, dt in enumerate(close_index)}

    def bucket_targets(size_half: str | None, liq_half: str | None) -> dict:
        out = {}
        for f, payers in payer_scores.items():
            iru_rules = universe.load_rules()
            elig = bx._eligible(con, panel, f, iru_rules,
                                int(base["signal"].get("min_obs_formation", 120)),
                                int(base["signal"].get("lookback_months", 12) * 31))
            pool = set(elig)
            if size_half is not None and f in size_scores:
                sc = size_scores[f].reindex(list(pool)).dropna()
                med = sc.median()
                keep = set(sc[sc >= med].index) if size_half == "small" \
                    else set(sc[sc < med].index)
                # size_scores is NEGATIVE cap (higher = smaller); "small"
                # half = higher score = above-median score
                pool = pool & keep
            if liq_half is not None and f in liq_scores:
                lc = liq_scores[f].reindex(list(pool)).dropna()
                med = lc.median()
                keep = set(lc[lc >= med].index) if liq_half == "liquid" \
                    else set(lc[lc < med].index)
                pool = pool & keep
            names = sorted(set(payers.index) & pool)
            i = pos.get(f)
            if not names or i is None or i + lag >= len(close_index):
                continue
            out[close_index[i + lag]] = pd.Series(1.0 / len(names), index=names)
        return out

    def bucket_benchmark(size_half: str | None, liq_half: str | None) -> dict:
        out = {}
        for f in payer_scores:
            iru_rules = universe.load_rules()
            elig = bx._eligible(con, panel, f, iru_rules,
                                int(base["signal"].get("min_obs_formation", 120)),
                                int(base["signal"].get("lookback_months", 12) * 31))
            pool = set(elig)
            if size_half is not None and f in size_scores:
                sc = size_scores[f].reindex(list(pool)).dropna()
                med = sc.median()
                keep = set(sc[sc >= med].index) if size_half == "small" \
                    else set(sc[sc < med].index)
                pool = pool & keep
            if liq_half is not None and f in liq_scores:
                lc = liq_scores[f].reindex(list(pool)).dropna()
                med = lc.median()
                keep = set(lc[lc >= med].index) if liq_half == "liquid" \
                    else set(lc[lc < med].index)
                pool = pool & keep
            i = pos.get(f)
            if not pool or i is None or i + lag >= len(close_index):
                continue
            out[close_index[i + lag]] = pd.Series(1.0 / len(pool), index=sorted(pool))
        return out

    def run_bucket(label: str, size_half, liq_half):
        tgt = bucket_targets(size_half, liq_half)
        bt = bucket_benchmark(size_half, liq_half)
        if not tgt or not bt:
            return {"label": label, "n_formations": len(tgt), "status": "insufficient_data"}
        strat = bx.simulate(close, tgt, rates["buy_rate"], rates["sell_rate"],
                            d["sim_start"], d["sim_end"])
        bench = bx.simulate(close, bt, rates["buy_rate"], rates["sell_rate"],
                            d["sim_start"], d["sim_end"])
        excess = (strat.net_returns - bench.net_returns).dropna()
        if excess.std() == 0 or len(excess) < 30:
            return {"label": label, "n_formations": len(tgt), "status": "degenerate"}
        sharpe = float(excess.mean() / excess.std() * np.sqrt(252))
        ttest = stats.newey_west_tstat(excess)
        ann_excess = float(((1 + excess).prod()) ** (252 / len(excess)) - 1)
        return {"label": label, "n_formations": len(tgt),
                "ann_excess": ann_excess, "sharpe": sharpe,
                "hac_t": ttest["t_stat"], "hac_p": ttest["p_value"],
                "status": "ok"}

    buckets = [
        run_bucket("size_small_half", "small", None),
        run_bucket("size_large_half", "large", None),
        run_bucket("liquidity_illiquid_half", None, "illiquid"),
        run_bucket("liquidity_liquid_half", None, "liquid"),
    ]
    print("\n=== Section 8.2: bucket decomposition (pooled return series, HAC t-test) ===")
    for b in buckets:
        print(json.dumps(b, indent=2))

    out = {"correlation_by_date": rows, "correlation_summary": summary,
          "bucket_decomposition": buckets}
    dest = "experiments/h017_orthogonality_2026-08-04.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)
    print(f"\nwritten: {dest}")


if __name__ == "__main__":
    main()
