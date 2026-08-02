"""Synthetic rehearsal for METH-001 (newey_west_tstat, probabilistic_sharpe_ratio,
deflated_sharpe_ratio). Mirrors the R1-R12 convention (rehearse_xs_engine*.py):
checks against KNOWN analytical properties on synthetic data, run BEFORE the
methodology is applied to any real platform evidence. Per
docs/PREREG_METH-001_statistical_hardening.md Section 7.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ngxrot import stats

rng = np.random.default_rng(20260802)
PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


print("=== S1: HAC == i.i.d. OLS variance for a true-white-noise series ===")
x = pd.Series(rng.normal(0, 1, 5000))
hac = stats.newey_west_tstat(x, lag=0)
iid = stats.excess_ttest(x, pd.Series(np.zeros(len(x))))
check("S1 HAC(lag=0) matches i.i.d. t-stat within rounding",
      abs(hac["t_stat"] - iid["t_stat"]) < 0.01,
      f"hac={hac['t_stat']} iid={iid['t_stat']}")

print("\n=== S2: HAC t-stat shrinks (SE grows) under positive AR(1) autocorrelation ===")
n, rho = 5000, 0.6
eps = rng.normal(0, 1, n)
ar1 = np.zeros(n)
for t in range(1, n):
    ar1[t] = rho * ar1[t - 1] + eps[t]
ar1_series = pd.Series(ar1 + 0.02)  # small positive mean to get a nonzero t-stat
hac_ar1 = stats.newey_west_tstat(ar1_series)
iid_ar1 = stats.excess_ttest(ar1_series, pd.Series(np.zeros(n)))
check("S2 HAC |t| < i.i.d. |t| under real positive autocorrelation",
      abs(hac_ar1["t_stat"]) < abs(iid_ar1["t_stat"]),
      f"hac={hac_ar1['t_stat']} (lag={hac_ar1['lag']}) iid={iid_ar1['t_stat']}")

print("\n=== S3: DSR(N=1) reduces exactly to PSR(SR*=0) ===")
sr_hat, skew, kurt, T = 0.05, 0.3, 5.0, 2200
psr_direct = stats.probabilistic_sharpe_ratio(sr_hat, 0.0, skew, kurt, T)
dsr_n1 = stats.deflated_sharpe_ratio([sr_hat], sr_hat, skew, kurt, T)
check("S3 DSR with N=1 equals direct PSR(SR*=0)",
      abs(dsr_n1["dsr"] - round(psr_direct, 5)) < 1e-9,
      f"dsr={dsr_n1['dsr']} psr_direct={round(psr_direct,5)}")

print("\n=== S4: DSR is non-increasing in N for fixed focal inputs ===")
trial_pool = list(rng.normal(0.02, 0.03, 50))
vals = []
for n_trials in [2, 5, 10, 20, 40]:
    d = stats.deflated_sharpe_ratio(trial_pool[:n_trials], sr_hat, skew, kurt, T)
    vals.append(d["dsr"])
    print(f"    N={n_trials:3d}  sr_star={d['sr_star_chance_benchmark']:.4f}  dsr={d['dsr']:.5f}")
check("S4 DSR non-increasing as N grows (monotone chance-benchmark)",
      all(vals[i] >= vals[i + 1] - 1e-9 for i in range(len(vals) - 1)),
      f"{vals}")

print("\n=== S5: DSR of a genuinely zero-mean strategy stays low across N ===")
null_trials = list(rng.normal(0.0, 0.03, 30))
low_vals = []
for n_trials in [5, 15, 30]:
    d = stats.deflated_sharpe_ratio(null_trials[:n_trials], 0.0, 0.1, 4.0, T)
    low_vals.append(d["dsr"])
check("S5 null strategy's DSR stays low (< 0.55) across trial counts",
      all(v < 0.55 for v in low_vals), f"{low_vals}")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    raise SystemExit(f"REHEARSAL FAILED: {FAIL}")
