"""Apply METH-002 (real, PIT-correct CBN MPR-based risk-free rate) to every
resolved hypothesis's frozen final-evaluation config, read-only (same
rerun_readonly path as compute_dsr_evidence.py, same reasons: avoids the
frozen-hypothesis SQL trigger on H-001 and avoids ledger noise for a pure
metrics-recomputation task). Reports the real, honest before/after Sharpe
for every hypothesis, not just the confirmed one.
"""
from __future__ import annotations

import json

from scripts.compute_dsr_evidence import latest_final_eval_configs, rerun_readonly
from ngxrot import metrics, riskfree


def main():
    latest = latest_final_eval_configs()
    hist = riskfree.load_mpr_history()
    out = {}
    for h, (eid, created, cfg, stored) in sorted(latest.items()):
        cfg = dict(cfg)
        cfg["validation"] = dict(cfg["validation"])
        cfg["validation"]["use_real_risk_free_rate"] = True
        print(f"=== {h} ===")
        try:
            result = rerun_readonly(cfg)
        except Exception as e:
            print(f"  RERUN FAILED: {e!r}")
            out[h] = {"error": repr(e)}
            continue
        rf_series = riskfree.mpr_asof_series(result.net_returns.index, hist)
        m = metrics.compute(result, cfg["validation"]["risk_free_annual_pct"], rf_series)
        integrity_ok = m["sharpe_vs_rf"] == stored["sharpe_vs_rf"]
        print(f"  flat-0.0 sharpe: stored={stored['sharpe_vs_rf']} "
              f"recomputed={m['sharpe_vs_rf']} match={integrity_ok}")
        print(f"  real-CBN-MPR sharpe: {m['sharpe_vs_real_rf']}  "
              f"(mean real rate over window: {m.get('real_rf_ann_pct_mean')}%, "
              f"coverage_gap_days={m['real_rf_coverage_gap']})")
        out[h] = {
            "orig_experiment_id": eid,
            "flat_0pct_sharpe_stored": stored["sharpe_vs_rf"],
            "flat_0pct_sharpe_recomputed": m["sharpe_vs_rf"],
            "integrity_check_pass": integrity_ok,
            "real_mpr_sharpe": m["sharpe_vs_real_rf"],
            "real_rf_ann_pct_mean": m.get("real_rf_ann_pct_mean"),
            "real_rf_coverage_gap_days": m["real_rf_coverage_gap"],
        }
    dest_path = "experiments/real_rf_evidence_2026-08-02.json"
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"\nwritten: {dest_path}")


if __name__ == "__main__":
    main()
