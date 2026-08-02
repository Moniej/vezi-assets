"""Recompute the Deflated Sharpe Ratio (METH-001) using real-risk-free-rate
daily excess returns (METH-002) instead of the original benchmark-excess
daily returns -- the named-but-not-yet-performed follow-up from both
METH-001's and METH-002's own reports: "every statistical inference [should
be] based on a consistent definition of risk-adjusted return."

Read-only, same rerun_readonly path and same reasons as
compute_dsr_evidence.py / compute_real_rf_evidence.py (avoids the frozen-
hypothesis SQL trigger on H-001, avoids ledger noise for a pure
recomputation task).

H-006 is EXCLUDED from the trial pool, not filled with any value: its
final-evaluation window starts 14 days before verified CBN MPR coverage
begins (2015-07-23), so no real-risk-free daily excess series can be
computed for it at all -- this is the same "leave it out, don't invent it"
discipline as everywhere else in this platform, applied to a trial-pool
member rather than a single date.
"""
from __future__ import annotations

import json

from scipy import stats as scipy_stats

from scripts.compute_dsr_evidence import latest_final_eval_configs, rerun_readonly
from ngxrot import riskfree, stats

TRADING_DAYS = 252


def real_rf_daily_excess(result, hist):
    rf_series = riskfree.mpr_asof_series(result.net_returns.index, hist)
    if rf_series.isna().any():
        return None  # no fabricated partial series
    daily_rf = (1.0 + rf_series / 100.0) ** (1.0 / TRADING_DAYS) - 1.0
    return (result.net_returns - daily_rf).dropna()


def main():
    latest = latest_final_eval_configs()
    hist = riskfree.load_mpr_history()
    per_hyp = {}
    for h, (eid, created, cfg, stored) in sorted(latest.items()):
        cfg = dict(cfg)
        cfg["validation"] = dict(cfg["validation"])
        cfg["validation"]["use_real_risk_free_rate"] = True
        print(f"=== {h} ===")
        try:
            result = rerun_readonly(cfg)
        except Exception as e:
            print(f"  RERUN FAILED: {e!r}")
            continue
        excess = real_rf_daily_excess(result, hist)
        if excess is None:
            print("  EXCLUDED: no real-rf coverage for this window")
            per_hyp[h] = {"excluded_no_coverage": True}
            continue
        daily_sr = float(excess.mean() / excess.std()) if excess.std() > 0 else None
        skew = float(scipy_stats.skew(excess, bias=False))
        kurt = float(scipy_stats.kurtosis(excess, fisher=False, bias=False))
        T = int(len(excess))
        print(f"  daily real-rf-excess SR={daily_sr:.4f}  T={T}  skew={skew:.3f}  kurt={kurt:.3f}")
        per_hyp[h] = {"daily_real_rf_sharpe": daily_sr, "T": T, "skew": skew, "kurtosis": kurt}

    covered = {h: v for h, v in per_hyp.items() if not v.get("excluded_no_coverage")}
    print(f"\n{len(covered)}/{len(per_hyp)} hypotheses have real-rf coverage "
          f"(excluded: {[h for h, v in per_hyp.items() if v.get('excluded_no_coverage')]})")

    trial_sharpes_full = [v["daily_real_rf_sharpe"] for v in covered.values()]
    h011 = covered["H-011"]
    dsr_full = stats.deflated_sharpe_ratio(
        trial_sharpes_full, h011["daily_real_rf_sharpe"], h011["skew"], h011["kurtosis"], h011["T"])
    print(f"\nDSR (real-rf basis), N={len(trial_sharpes_full)} (full covered pool): {dsr_full}")

    xs_only = ["H-007", "H-008", "H-009", "H-010", "H-011", "H-012"]
    trial_sharpes_xs = [covered[h]["daily_real_rf_sharpe"] for h in xs_only if h in covered]
    dsr_xs = stats.deflated_sharpe_ratio(
        trial_sharpes_xs, h011["daily_real_rf_sharpe"], h011["skew"], h011["kurtosis"], h011["T"])
    print(f"DSR (real-rf basis), N={len(trial_sharpes_xs)} (cross-sectional-engine peers only): {dsr_xs}")

    out = {
        "per_hypothesis": per_hyp,
        "dsr_full_pool": dsr_full,
        "dsr_xs_only_pool": dsr_xs,
        "excluded_from_pool": [h for h, v in per_hyp.items() if v.get("excluded_no_coverage")],
    }
    dest = "experiments/dsr_realrf_evidence_2026-08-02.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"\nwritten: {dest}")


if __name__ == "__main__":
    main()
