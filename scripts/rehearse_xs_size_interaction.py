"""Synthetic rehearsal for Phase R2 (H-013/H-014/H-015): liquidity_scores,
interaction_bucket_members, targets_from_bucketed_size,
benchmark_targets_bucket, and the xs_size_interaction branches in
run_from_config / placebo_stats. Mirrors the R1-R12 convention: checks
against KNOWN properties on synthetic data, run BEFORE any real
hypothesis backtest. Per docs/PREREG_H013-015_size_interactions.md
Section 6.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ngxrot import backtest_xs as xs

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


print("=== I1: interaction_bucket_members produces a clean median split ===")
rng = np.random.default_rng(20260803)
tickers = [f"T{i:03d}" for i in range(40)]
f = pd.Timestamp("2020-03-31")
size = {f: pd.Series(rng.normal(0, 1, 40), index=tickers)}
xdim = {f: pd.Series(rng.normal(0, 1, 40), index=tickers)}
buckets = xs.interaction_bucket_members(size, xdim)
b = buckets[f]
check("I1a high+low buckets partition all 40 tickers",
      sorted(b["high"] + b["low"]) == sorted(tickers))
check("I1b buckets are roughly balanced (median split)",
      abs(len(b["high"]) - len(b["low"])) <= 2,
      f"high={len(b['high'])} low={len(b['low'])}")

print("\n=== I2: only tickers scored by BOTH dimensions enter a bucket ===")
size2 = {f: pd.Series(rng.normal(0, 1, 40), index=tickers)}
xdim2 = {f: pd.Series(rng.normal(0, 1, 30), index=tickers[:30])}  # 10 missing
buckets2 = xs.interaction_bucket_members(size2, xdim2)
b2 = buckets2[f]
check("I2 restricted to the 30 tickers present in both",
      sorted(b2["high"] + b2["low"]) == sorted(tickers[:30]),
      f"got {len(b2['high']) + len(b2['low'])} names")

print("\n=== I3: targets_from_bucketed_size selects top_n by SIZE within the bucket only ===")
close_index = pd.date_range("2020-01-01", periods=5, freq="D")
high_names = ["A", "B", "C", "D", "E", "F"]      # 6 names, top_n=2 within
low_names = ["G", "H", "I", "J", "K", "L"]        # 6 names, top_n=2 within
size3 = {f: pd.Series(
    [6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
    index=high_names + low_names)}
buckets3 = {f: {"high": high_names, "low": low_names}}
idx = pd.DatetimeIndex(sorted(set(close_index) | {f, f + pd.Timedelta(days=1)}))
tgt_high = xs.targets_from_bucketed_size(size3, buckets3, "high", idx, top_n=2, lag=1)
tgt_low = xs.targets_from_bucketed_size(size3, buckets3, "low", idx, top_n=2, lag=1)
sel_high = set(next(iter(tgt_high.values())).index) if tgt_high else set()
sel_low = set(next(iter(tgt_low.values())).index) if tgt_low else set()
check("I3a high bucket top_n=2 by size picks A,B (highest z, per size_scores convention)",
      sel_high == {"A", "B"}, f"got {sel_high}")
check("I3b low bucket top_n=2 by size picks G,H (highest z WITHIN that bucket)",
      sel_low == {"G", "H"}, f"got {sel_low}")
check("I3c no cross-bucket leakage (low-bucket names never in the high selection)",
      not (set(low_names) & sel_high) and not (set(high_names) & sel_low))

print("\n=== I4: benchmark_targets_bucket is EW over the WHOLE bucket, not size-filtered ===")
bench_high = xs.benchmark_targets_bucket(buckets3, "high", idx, lag=1)
w = next(iter(bench_high.values()))
check("I4 bucket benchmark includes ALL 6 high-bucket names equally weighted",
      set(w.index) == set(high_names) and abs(w.iloc[0] - 1/6) < 1e-9,
      f"got {dict(w)}")

print("\n=== I5: liquidity_scores sign convention (least liquid -> highest score) ===")
class _FakePanel(dict):
    pass


dates = pd.date_range("2019-01-01", periods=400, freq="D")
tick_names = [f"N{i:02d}" for i in range(12)]
adtv_vals = {t: (1e9 if t == "N00" else 1e6 if t == "N01" else 1e7)
             for t in tick_names}
adtv = pd.DataFrame({t: np.full(400, v) for t, v in adtv_vals.items()}, index=dates)
close = pd.DataFrame(100.0, index=dates, columns=tick_names)
obs = pd.DataFrame(True, index=dates, columns=tick_names)
panel = {"close_ff": close, "obs": obs, "adtv60": adtv}


class _FakeCon:
    def execute(self, *a, **k):
        raise NotImplementedError


from ngxrot import universe as _universe

orig_iru = _universe.iru_members
orig_rules = _universe.load_rules


def _fake_iru(con, date, rules):
    return pd.DataFrame({"ticker": tick_names})


_universe.iru_members = _fake_iru
_universe.load_rules = lambda: {}
try:
    cfg = {"signal": {"min_obs_formation": 10}, "data": {"sim_start": "2019-01-01",
                                                         "sim_end": "2019-12-31"},
           "portfolio": {"rebalance": "quarterly"}}
    liq = xs.liquidity_scores(_FakeCon(), panel, cfg)
    any_date = next(iter(liq))
    z = liq[any_date]
    check("I5 lowest-ADTV ticker (N01) gets the HIGHEST liquidity score",
          z.idxmax() == "N01", f"scores={dict(z)}")
    check("I5b highest-ADTV ticker (N00) gets the LOWEST liquidity score",
          z.idxmin() == "N00", f"scores={dict(z)}")
finally:
    _universe.iru_members = orig_iru
    _universe.load_rules = orig_rules

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    raise SystemExit(f"REHEARSAL FAILED: {FAIL}")
