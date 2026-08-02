"""Point-in-time risk-free rate: CBN Monetary Policy Rate (MPR) history.

Fixes the disclosed placeholder in metrics.py (rf_annual_pct default 0.0,
"WRONG for Nigeria... the metric name says what was used"). Every
Sharpe ratio this platform has reported through H-012 used that flat 0.0.

Data: data/reference/cbn_mpr_history.csv, 51 rows, decision-date-indexed,
hand-verified against the CBN's own published MPC decisions page
(https://www.cbn.gov.ng/MonetaryPolicy/decisions.html) on 2026-08-02 via
THREE separate fetches cross-checked against each other and against MPC
meeting sequence numbers stated on the page. One extraction error was
caught this way: an initial pull mislabeled the 302nd meeting (a real
2025-09-22/23 decision) as "September 22-23, 2023" -- corrected using the
meeting-number cross-check, not silently included. No meeting is recorded
for H2 2023 -- this is a REAL historical fact (the MPC did not convene
between the 292nd meeting, Jul 2023, and the next captured decision, Feb
2024, during the CBN leadership transition), not a gap in this extraction.

DISCLOSED LIMITATION, not glossed over: MPR is the CBN's policy corridor
anchor, not the actual NGN Treasury-Bill stop rate an investor could earn
-- real T-bill yields track MPR with a variable spread. This is a
disclosed PROXY, chosen because it is the only rate series that could be
completely and cross-verifiably reconstructed with the tools available
this session (see docs/PREREG_METH-002_risk_free_rate.md Section 2 for the
rejected alternative of pursuing an actual T-bill stop-rate series).
Coverage begins 2015-07-23; any date before that has no real rate and
must not be silently filled.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[2]
MPR_CSV = PKG_ROOT / "data" / "reference" / "cbn_mpr_history.csv"


def load_mpr_history(path: Path = MPR_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["decision_date"])
    return df.sort_values("decision_date").reset_index(drop=True)


def mpr_asof_series(dates: pd.DatetimeIndex, history: pd.DataFrame | None = None) -> pd.Series:
    """Point-in-time MPR (annual %) for each date in `dates`.

    For date d, returns the mpr_pct of the latest decision_date <= d.
    NaN for any d before the earliest verified decision_date (2015-07-23) --
    never forward- or back-filled from outside the verified record.
    """
    hist = history if history is not None else load_mpr_history()
    dates = pd.DatetimeIndex(dates)
    idx = hist.set_index("decision_date")["mpr_pct"].sort_index()
    # asof requires the lookup index to be sorted; searchsorted gives the
    # position of the latest decision_date <= each date (side='right' - 1)
    pos = idx.index.searchsorted(dates, side="right") - 1
    out = pd.Series(index=dates, dtype=float)
    valid = pos >= 0
    out[valid] = idx.values[pos[valid]]
    out[~valid] = float("nan")
    return out


def coverage_status(dates: pd.DatetimeIndex, history: pd.DataFrame | None = None) -> dict:
    """Whether every date in `dates` has real, verified MPR coverage."""
    hist = history if history is not None else load_mpr_history()
    dates = pd.DatetimeIndex(dates)
    earliest = hist["decision_date"].min()
    n_uncovered = int((dates < earliest).sum())
    return {
        "earliest_verified_decision_date": earliest.date().isoformat(),
        "n_dates_requested": len(dates),
        "n_dates_uncovered": n_uncovered,
        "full_coverage": n_uncovered == 0,
    }
