"""H-016 (Liquidity) Phase 4 gauntlet -- full bar, matching H-011's own
(NOT Phase R2's reduced scope, per docs/PREREG_H-016_liquidity.md Section
6): stability grid -> Holm/BH -> placebo -> walk-forward with untouched
final OOS -> failure conditions -> confidence rating -> IC memo, via
phase4.run_phase4_xs (the same function H-011 itself was evaluated
through). Run ONE leg per invocation (works around this environment's
long-running-foreground-process constraints):

  python -u scripts/run_h016_phase4.py A   # Leg A: illiquid
  python -u scripts/run_h016_phase4.py B   # Leg B: liquid

After the gauntlet, computes HAC (Newey-West) t-stat and real-rf DSR
context for the SAME base-cell config (a supplementary run, separate
registry row, mirroring scripts/run_size_interaction_phase.py's own
pattern) -- neither is produced by run_phase4_xs itself.
"""
import json
import sys
from pathlib import Path

from ngxrot import ledger, metrics, phase4, registry, riskfree, runner, stats

LEGS = {
    "A": ("H-016", "configs/h016a_liquidity_illiquid.toml"),
    "B": ("H-016", "configs/h016b_liquidity_liquid.toml"),
}

with open("experiments/dsr_realrf_evidence_2026-08-02.json") as f:
    _dsr_evidence = json.load(f)
EXISTING_TRIAL_SHARPES = [
    v["daily_real_rf_sharpe"] for v in _dsr_evidence["per_hypothesis"].values()
    if not v.get("excluded_no_coverage")]


def main():
    leg = sys.argv[1] if len(sys.argv) > 1 else "A"
    hyp_id, config_path = LEGS[leg]
    base = runner.load_config(config_path)

    reg = registry.connect_registry()
    row = reg.execute("SELECT status FROM hypotheses WHERE hypothesis_id=?",
                      (hyp_id,)).fetchone()
    if row and row[0] == "untested":
        ledger.set_status(reg, hyp_id, "testing",
                          f"beginning Phase 4 gauntlet, leg {leg}")

    print(f"\n{'='*70}\nH-016 leg {leg}: {config_path}\n{'='*70}")
    bundle = phase4.run_phase4_xs(base, base["phase4"])

    print("\n--- supplementary: HAC t-stat + real-rf DSR context ---")
    hac_cfg = dict(base)
    hac_cfg["experiment"] = {**base["experiment"], "name": f"h016_{leg}_hacdsr_basis"}
    final = runner.run_resolved(hac_cfg, label=f"H-016 leg {leg} hac/dsr basis")
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
        "hyp_id": hyp_id, "leg": leg,
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
    dest = f"experiments/h016_leg{leg}_phase4_2026-08-03.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)
    print(f"\nwritten: {dest}")
    print(f"\nSUMMARY leg {leg}: plateau={bundle['plateau']} "
          f"placebo_p={bundle['placebo']['placebo_p_value']} "
          f"holm_sig={bundle['corrections']['holm']}/{bundle['corrections']['n_tests']} "
          f"bh_sig={bundle['corrections']['bh']}/{bundle['corrections']['n_tests']} "
          f"hac_p={hac['p_value']} rating={bundle['rating']['rating']}")


if __name__ == "__main__":
    main()
