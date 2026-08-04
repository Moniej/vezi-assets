"""H-017 (Dividend Payer-Status) Phase 4 gauntlet -- full H-011-grade
bar: stability grid -> Holm/BH -> placebo -> walk-forward with
untouched final OOS -> failure conditions -> confidence rating -> IC
memo, via phase4.run_phase4_xs (the same function H-011/H-016 were
evaluated through). Single leg (unlike H-016) -- payer-status has one
pre-registered direction (long payers), per
docs/PREREG_H-017_dividend_payer_status.md.

  python -u scripts/run_h017_phase4.py

After the gauntlet, computes HAC (Newey-West) t-stat and real-rf DSR
context for the base-cell config (a supplementary run, separate
registry row, mirroring scripts/run_h016_phase4.py's own pattern).
"""
import json

from ngxrot import ledger, metrics, phase4, registry, riskfree, runner, stats

HYP_ID = "H-017"
CONFIG_PATH = "configs/h017_payer_status.toml"

with open("experiments/dsr_realrf_evidence_2026-08-02.json") as f:
    _dsr_evidence = json.load(f)
EXISTING_TRIAL_SHARPES = [
    v["daily_real_rf_sharpe"] for v in _dsr_evidence["per_hypothesis"].values()
    if not v.get("excluded_no_coverage")]


def main():
    base = runner.load_config(CONFIG_PATH)

    reg = registry.connect_registry()
    row = reg.execute("SELECT status FROM hypotheses WHERE hypothesis_id=?",
                      (HYP_ID,)).fetchone()
    if row and row[0] == "untested":
        ledger.set_status(reg, HYP_ID, "testing", "beginning Phase 4 gauntlet")

    print(f"\n{'='*70}\nH-017: {CONFIG_PATH}\n{'='*70}")
    bundle = phase4.run_phase4_xs(base, base["phase4"])

    print("\n--- supplementary: HAC t-stat + real-rf DSR context ---")
    hac_cfg = dict(base)
    hac_cfg["experiment"] = {**base["experiment"], "name": "h017_hacdsr_basis"}
    final = runner.run_resolved(hac_cfg, label="H-017 hac/dsr basis")
    result = final["result"]
    excess = (result.net_returns - result.benchmark_returns).dropna()
    hac = stats.newey_west_tstat(excess)

    rf_series = riskfree.mpr_asof_series(result.net_returns.index)
    m_realrf = metrics.compute(result, 0.0, rf_series)
    daily_realrf_excess = None
    dsr_context = None
    if m_realrf["real_rf_coverage_gap"] == 0:
        daily_rf = (1.0 + rf_series.reindex(result.net_returns.index) / 100.0) ** (1.0 / 252) - 1.0
        daily_realrf_excess = float((result.net_returns - daily_rf).mean() /
                                    (result.net_returns - daily_rf).std())
        dsr_context = stats.deflated_sharpe_ratio(
            EXISTING_TRIAL_SHARPES + [daily_realrf_excess], daily_realrf_excess,
            float((result.net_returns - daily_rf).skew()),
            float((result.net_returns - daily_rf).kurtosis() + 3), len(excess))

    out = {
        "hyp_id": HYP_ID,
        "stability": bundle["stability"].drop(columns=["exp_id"]).to_dict("records"),
        "plateau": bundle["plateau"],
        "corrections": bundle["corrections"],
        "placebo": bundle["placebo"],
        "walk_forward": bundle["walk_forward"].to_dict("records"),
        "failure_conditions": bundle["failure_conditions"],
        "final_metrics": bundle["final_metrics"],
        "rating": bundle["rating"],
        "hac_ttest": hac,
        "daily_realrf_excess_sharpe": daily_realrf_excess,
        "dsr_context_vs_existing_pool": dsr_context,
    }
    dest = "experiments/h017_phase4_2026-08-04.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)
    print(f"\nwritten: {dest}")
    print(f"\nSUMMARY H-017: plateau={bundle['plateau']} "
          f"placebo_p={bundle['placebo']['placebo_p_value']} "
          f"holm_sig={bundle['corrections']['holm']}/{bundle['corrections']['n_tests']} "
          f"bh_sig={bundle['corrections']['bh']}/{bundle['corrections']['n_tests']} "
          f"hac_p={hac['p_value']} rating={bundle['rating']['rating']}")


if __name__ == "__main__":
    main()
