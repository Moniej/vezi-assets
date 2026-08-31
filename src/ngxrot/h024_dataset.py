"""Pure, pre-outcome H-024 dataset primitives.

No function in this module reads a forward return, materializes an outcome, or
estimates a predictor/outcome association.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def eligibility_reason(*, adtv_valid_count: int, baseline_valid_count: int,
                       identity_status: str, zero_return_fraction: float | None = None) -> str | None:
    """Return the first frozen exclusion reason, retaining unknown identity."""
    if identity_status != "resolved":
        return f"identity_{identity_status}"
    if adtv_valid_count < 45:
        return "insufficient_adtv60"
    if baseline_valid_count < 120:
        return "insufficient_adtv_baseline"
    if zero_return_fraction is not None and zero_return_fraction > .80:
        return "extreme_staleness"
    return None


def _positive_adtv(window: pd.DataFrame) -> tuple[float | None, int]:
    values = pd.to_numeric(window["value_traded"], errors="coerce")
    valid = values[values > 0]
    return (float(valid.mean()) if len(valid) else None), int(len(valid))


def predictor_row(frame: pd.DataFrame, decision_time: pd.Timestamp) -> dict:
    """Construct only information available through ``decision_time``.

    ``frame`` is a single ticker's ordered raw-close, value-traded history.
    The historical ADTV baseline excludes the current decision session.
    """
    history = frame.copy()
    history["trade_date"] = pd.to_datetime(history["trade_date"])
    history = history[history.trade_date <= pd.Timestamp(decision_time)].sort_values("trade_date")
    trailing = history.tail(60)
    adtv60, valid_count = _positive_adtv(trailing)

    # Every rolling value uses its own trailing 60 sessions. Selecting the
    # 252 values immediately before the decision session therefore cannot use
    # current/future information while avoiding a costly nested reconstruction.
    values = pd.to_numeric(history["value_traded"], errors="coerce").where(lambda value: value > 0)
    rolling_adtv = values.rolling(60, min_periods=45).mean()
    baseline_values = rolling_adtv.iloc[max(0, len(history) - 253):len(history) - 1].dropna()
    baseline = float(np.median(np.log(baseline_values))) if len(baseline_values) else None
    shock = math.log(adtv60) - baseline if adtv60 and baseline is not None else None

    closes = pd.to_numeric(history["close"], errors="coerce")
    returns = closes.pct_change()
    trailing_returns = returns.tail(60)
    zero_fraction = float((trailing_returns == 0).mean()) if len(trailing_returns) else None
    volume = pd.to_numeric(history["volume"], errors="coerce")
    positive_volume_zero = ((trailing_returns == 0) & (volume > 0)).tail(60)
    positive_volume_zero_fraction = float(positive_volume_zero.mean()) if len(positive_volume_zero) else None

    def lagged_rv(horizon: int) -> float | None:
        sample = returns.tail(horizon).dropna()
        if len(sample) < horizon:
            return None
        return float(math.sqrt(252 / horizon) * sample.std(ddof=1))

    deals = pd.to_numeric(history.get("deals"), errors="coerce")
    return {
        "adtv60": adtv60,
        "adtv60_valid_count": valid_count,
        "historical_adtv_median_log": baseline,
        "historical_adtv_valid_count": int(len(baseline_values)),
        "liquidity_shock": shock,
        "lagged_rv5": lagged_rv(5),
        "lagged_rv20": lagged_rv(20),
        "lagged_rv60": lagged_rv(60),
        "trailing_zero_return_fraction": zero_fraction,
        "trailing_positive_volume_zero_return_fraction": positive_volume_zero_fraction,
        "trailing_median_deals": float(deals.tail(60).median()) if deals is not None and deals.notna().any() else None,
    }


def action_flags(decision_time: pd.Timestamp, action_dates: list[pd.Timestamp],
                 sessions: pd.DatetimeIndex) -> dict[str, bool]:
    """Flag known action dates in deterministic lagged and forward windows."""
    dates = pd.DatetimeIndex(pd.to_datetime(action_dates))
    position = sessions.get_indexer([pd.Timestamp(decision_time)])[0]
    if position < 0:
        raise ValueError("decision time is not an eligible session")

    def crossing(start: int, stop: int) -> bool:
        if start >= len(sessions):
            return False
        return bool(dates.isin(sessions[start:min(stop, len(sessions))]).any())

    return {
        "action_in_lagged_vol_window": crossing(max(0, position - 59), position + 1),
        "action_in_forward_5d_window": crossing(position + 1, position + 6),
        "action_in_forward_20d_window": crossing(position + 1, position + 21),
        "action_in_forward_60d_window": crossing(position + 1, position + 61),
    }
