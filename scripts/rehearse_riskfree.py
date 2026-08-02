"""Synthetic + structural rehearsal for METH-002 (riskfree.py, metrics.py's
rf_series parameter). Mirrors the platform's R-series convention.
"""
from __future__ import annotations

import pandas as pd

from ngxrot import riskfree

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


hist = riskfree.load_mpr_history()
print(f"loaded {len(hist)} verified MPR decisions, "
      f"{hist.decision_date.min().date()} to {hist.decision_date.max().date()}")

print("\n=== T1: no look-ahead across a known rate-change boundary ===")
# 2016-07-26: MPR raised 12.00 -> 14.00
before = riskfree.mpr_asof_series(pd.DatetimeIndex(["2016-07-25"]), hist)
on = riskfree.mpr_asof_series(pd.DatetimeIndex(["2016-07-26"]), hist)
after = riskfree.mpr_asof_series(pd.DatetimeIndex(["2016-07-27"]), hist)
check("T1a day before the decision still sees the OLD rate",
      before.iloc[0] == 12.00, f"got {before.iloc[0]}")
check("T1b decision day itself sees the NEW rate (decision_date is PIT-safe)",
      on.iloc[0] == 14.00, f"got {on.iloc[0]}")
check("T1c day after still sees the new rate",
      after.iloc[0] == 14.00, f"got {after.iloc[0]}")

print("\n=== T2: pre-coverage date is NaN, never invented ===")
early = riskfree.mpr_asof_series(pd.DatetimeIndex(["2010-01-01"]), hist)
check("T2 date before 2015-07-23 is NaN (not silently filled)",
      pd.isna(early.iloc[0]), f"got {early.iloc[0]}")

print("\n=== T3: coverage_status reports gaps honestly ===")
cov_ok = riskfree.coverage_status(pd.DatetimeIndex(["2020-01-01", "2024-01-01"]), hist)
cov_bad = riskfree.coverage_status(pd.DatetimeIndex(["2010-01-01", "2020-01-01"]), hist)
check("T3a fully-covered range reports full_coverage=True", cov_ok["full_coverage"])
check("T3b range including a pre-2015 date reports full_coverage=False",
      not cov_bad["full_coverage"], f"{cov_bad}")

print("\n=== T4: metrics.compute backward compatibility (rf_series=None) ===")
from ngxrot import metrics


class _FakeResult:
    def __init__(self, r, b):
        self.net_returns = r
        self.benchmark_returns = b
        self.weights = pd.DataFrame(index=[r.index[0], r.index[len(r)//2]])
        self.turnover = pd.Series([0.1, 0.1])
        self.costs = pd.Series([0.001] * len(r), index=r.index)
        self.gross_returns = r


import numpy as np
rng = np.random.default_rng(1)
idx = pd.bdate_range("2018-01-01", periods=500)
r = pd.Series(rng.normal(0.0006, 0.01, len(idx)), index=idx)
b = pd.Series(rng.normal(0.0003, 0.008, len(idx)), index=idx)
fake = _FakeResult(r, b)
m_old = metrics.compute(fake, rf_annual_pct=5.0)
m_new_no_series = metrics.compute(fake, rf_annual_pct=5.0, rf_series=None)
check("T4 identical output with rf_series omitted vs explicit None",
      m_old == m_new_no_series)
check("T4b no real-rf keys leak in when rf_series is None",
      "sharpe_vs_real_rf" not in m_old)

print("\n=== T5: real-rf Sharpe differs from flat-rf Sharpe when the real rate is nonzero ===")
rf_series = riskfree.mpr_asof_series(idx, hist)
m_real = metrics.compute(fake, rf_annual_pct=0.0, rf_series=rf_series)
check("T5a sharpe_vs_real_rf computed (full coverage for this 2018+ window)",
      m_real["real_rf_coverage_gap"] == 0 and m_real["sharpe_vs_real_rf"] is not None,
      f"{m_real.get('sharpe_vs_real_rf')}")
check("T5b real-rf Sharpe is materially lower than the old flat-0.0 Sharpe "
      "(real rates were ~11-14% over this window)",
      m_real["sharpe_vs_real_rf"] < m_old["sharpe_vs_rf"],
      f"real={m_real['sharpe_vs_real_rf']} flat0={metrics.compute(fake, 0.0)['sharpe_vs_rf']}")

print("\n=== T6: coverage-gap window correctly refuses (None), not silently substitutes ===")
idx_gap = pd.bdate_range("2010-01-01", periods=100)
r_gap = pd.Series(rng.normal(0.0005, 0.01, len(idx_gap)), index=idx_gap)
b_gap = pd.Series(rng.normal(0.0002, 0.008, len(idx_gap)), index=idx_gap)
fake_gap = _FakeResult(r_gap, b_gap)
rf_gap_series = riskfree.mpr_asof_series(idx_gap, hist)
m_gap = metrics.compute(fake_gap, 0.0, rf_gap_series)
check("T6 pre-coverage window returns sharpe_vs_real_rf=None, not a fabricated number",
      m_gap["sharpe_vs_real_rf"] is None and m_gap["real_rf_coverage_gap"] > 0,
      f"{m_gap}")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    raise SystemExit(f"REHEARSAL FAILED: {FAIL}")
