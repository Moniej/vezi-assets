"""Phase R2 orchestration: H-013/H-014/H-015 (Size interaction forensics).

For each of 6 bucket-configs (3 interactions x 2 buckets): stability grid
(stability_map_xs, real registry writes) -> Holm/BH correction -> placebo
test (placebo_test_xs, real registry write) -> one final single run at the
base cell (real registry write, stage=development, NO walk-forward/OOS --
disclosed scoping decision, docs/PREREG_H013-015_size_interactions.md
Section 6) -> HAC-corrected t-test on that final run's daily excess-vs-
bucket-benchmark returns -> DSR context against the EXISTING real-rf trial
pool (not a new trial slot, per the prereg).
"""
from __future__ import annotations

import json

from ngxrot import metrics, phase4, riskfree, runner, stats

CONFIGS = {
    "H-013": {
        "high": "configs/h013_size_x_liquidity_high.toml",
        "low": "configs/h013_size_x_liquidity_low.toml",
    },
    "H-014": {
        "high": "configs/h014_size_x_momentum_high.toml",
        "low": "configs/h014_size_x_momentum_low.toml",
    },
    "H-015": {
        "high": "configs/h015_size_x_volatility_high.toml",
        "low": "configs/h015_size_x_volatility_low.toml",
    },
}

GRID = {"portfolio.rebalance": ["quarterly", "semiannual"],
        "portfolio.top_n": [8, 12]}

with open("experiments/dsr_realrf_evidence_2026-08-02.json") as f:
    _dsr_evidence = json.load(f)
EXISTING_TRIAL_SHARPES = [
    v["daily_real_rf_sharpe"] for v in _dsr_evidence["per_hypothesis"].values()
    if not v.get("excluded_no_coverage")]


def run_one(hyp_id: str, bucket: str, config_path: str) -> dict:
    print(f"\n{'='*70}\n{hyp_id} / {bucket} bucket : {config_path}\n{'='*70}")
    base = runner.load_config(config_path)

    print(f"--- stability grid ({len(GRID['portfolio.rebalance']) * len(GRID['portfolio.top_n'])} cells) ---")
    stab_df, plateau = phase4.stability_map_xs(base, GRID)
    print(stab_df.drop(columns=["exp_id"]).to_string(index=False))
    pvals = {r.cell: r.p_raw for r in stab_df.itertuples() if r.p_raw is not None}
    holm_df = stats.holm(pvals)
    bh_df = stats.benjamini_hochberg(pvals)
    n_sig_holm = int(holm_df.significant_after_holm.sum()) if len(holm_df) else 0
    n_sig_bh = int(bh_df.significant_after_bh.sum()) if len(bh_df) else 0
    print(f"plateau: {plateau} | significant after Holm: {n_sig_holm}/{len(pvals)} "
          f"| after BH: {n_sig_bh}/{len(pvals)}")

    print("--- placebo (100 iterations) ---")
    placebo = phase4.placebo_test_xs(base, n_iter=100)
    print(placebo)

    print("--- final single run (base cell, development stage, no walk-forward) ---")
    final_cfg = dict(base)
    final_cfg["experiment"] = {**base["experiment"], "name": f"p2_final_{hyp_id}_{bucket}"}
    final = runner.run_resolved(final_cfg, label=f"final {hyp_id} {bucket}")
    result = final["result"]
    excess = (result.net_returns - result.benchmark_returns).dropna()
    hac = stats.newey_west_tstat(excess)
    iid = final["metrics"]["excess_ttest"]

    rf_series = riskfree.mpr_asof_series(result.net_returns.index)
    m_realrf = metrics.compute(result, 0.0, rf_series)
    daily_realrf_excess = None
    if m_realrf["real_rf_coverage_gap"] == 0:
        daily_rf = (1.0 + rf_series.reindex(result.net_returns.index) / 100.0) ** (1.0 / 252) - 1.0
        daily_realrf_excess = float((result.net_returns - daily_rf).mean() /
                                    (result.net_returns - daily_rf).std())
        dsr_context = stats.deflated_sharpe_ratio(
            EXISTING_TRIAL_SHARPES + [daily_realrf_excess], daily_realrf_excess,
            float((result.net_returns - daily_rf).skew()),
            float((result.net_returns - daily_rf).kurtosis() + 3), len(excess))
    else:
        dsr_context = None

    out = {
        "hyp_id": hyp_id, "bucket": bucket,
        "stability": stab_df.drop(columns=["exp_id"]).to_dict("records"),
        "plateau": plateau,
        "n_sig_holm": n_sig_holm, "n_sig_bh": n_sig_bh, "n_cells": len(pvals),
        "placebo": placebo,
        "final_excess_return_ann": final["metrics"]["excess_return_ann"],
        "final_sharpe_vs_bucket_bench_rf0": final["metrics"]["sharpe_vs_rf"],
        "iid_ttest": iid,
        "hac_ttest": hac,
        "daily_realrf_excess_sharpe": daily_realrf_excess,
        "dsr_context_vs_existing_pool": dsr_context,
        "attribution": result.attribution,
    }
    print(f"RESULT summary: excess_ann={out['final_excess_return_ann']} "
          f"iid_p={iid['p_value']} hac_p={hac['p_value']} "
          f"placebo_p={placebo['placebo_p_value']}")
    return out


def main():
    import sys
    if len(sys.argv) == 3:
        hyp_id, bucket = sys.argv[1], sys.argv[2]
        out = run_one(hyp_id, bucket, CONFIGS[hyp_id][bucket])
        dest = f"experiments/size_interaction_{hyp_id}_{bucket}_2026-08-03.json"
        with open(dest, "w") as f:
            json.dump(out, f, indent=2, sort_keys=True, default=str)
        print(f"\nwritten: {dest}")
        return
    for hyp_id, buckets in CONFIGS.items():
        for bucket, path in buckets.items():
            out = run_one(hyp_id, bucket, path)
            dest = f"experiments/size_interaction_{hyp_id}_{bucket}_2026-08-03.json"
            with open(dest, "w") as f:
                json.dump(out, f, indent=2, sort_keys=True, default=str)
            print(f"written: {dest}")


if __name__ == "__main__":
    main()
