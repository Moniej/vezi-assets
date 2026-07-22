"""Momentum signal construction (Phase 2).

KNOWN BIAS, carried in every experiment's validation_flags until Phase 3:
sector index levels are PRICE indices — trailing returns here exclude
dividends, which systematically understates momentum for high-yield sectors
(Banking). Phase 3 builds constituent-level total-return series; until then
'momentum' means price momentum and results are flagged accordingly.
"""

from __future__ import annotations

import pandas as pd


def month_end_trading_dates(daily_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last actual trading date of each month present in the data."""
    s = pd.Series(daily_index, index=daily_index)
    return pd.DatetimeIndex(s.groupby(daily_index.to_period("M")).max().values)


def monthly_closes(levels: pd.DataFrame) -> pd.DataFrame:
    """Levels sampled at the last trading date of each month."""
    return levels.loc[month_end_trading_dates(levels.index)]


def momentum_scores(
    levels: pd.DataFrame,
    lookbacks_months: list[int],
    lookback_weights: list[float],
) -> pd.DataFrame:
    """Cross-sectional momentum score per month-end date.

    For each lookback k: trailing k-month return, converted to a cross-
    sectional percentile rank (rank-based, robust to one sector's outlier
    return dominating a z-score). Score = weighted average of rank
    percentiles. Rows without full history for the longest lookback are
    dropped — no partial-lookback scores.
    """
    if len(lookbacks_months) != len(lookback_weights):
        raise ValueError("lookbacks and weights must have equal length")
    wsum = sum(lookback_weights)
    weights = [w / wsum for w in lookback_weights]

    mclose = monthly_closes(levels)
    score = None
    for k, w in zip(lookbacks_months, weights):
        ret_k = mclose / mclose.shift(k) - 1.0
        rank_k = ret_k.rank(axis=1, pct=True)
        score = rank_k * w if score is None else score + rank_k * w
    return score.dropna(how="any")


def select_top_n(
    scores_row: pd.Series,
    top_n: int,
    excluded: set[str],
    construction: str,
) -> pd.Series:
    """Target weights from one date's scores.

    Excluded (structurally impaired) sectors are removed BEFORE selection, so
    the next-ranked sector fills the slot (portfolio stays fully invested —
    long-only, no cash sleeve in Phase 2).
    """
    candidates = scores_row.drop(labels=[c for c in excluded if c in scores_row.index])
    picks = candidates.nlargest(top_n)
    if construction == "equal_weight":
        w = pd.Series(1.0 / len(picks), index=picks.index)
    elif construction == "score_weight":
        w = picks / picks.sum()
    else:
        raise ValueError(f"unknown construction {construction!r}")
    return w.reindex(scores_row.index, fill_value=0.0)


def macro_gate_scores(
    levels: pd.DataFrame,
    macro: pd.Series,
    target: str,
    neutral: str,
    lookback_months: int,
) -> pd.DataFrame:
    """Two-asset gate driven by an external macro series (H-004 spec; reusable
    for any series-gated allocation).

    At each month-end t: trailing return R = macro(t)/macro(t-L months) - 1
    using only values dated <= t (macro must be a PIT series). Scores:
    target = 1.0 if R > 0 else 0.0; neutral = 0.5 constant — with top_n=1 the
    portfolio holds target when the gate is on, neutral otherwise.
    Dates without full lookback history are dropped, never padded.
    """
    if not isinstance(macro.index, pd.DatetimeIndex) or not macro.index.is_monotonic_increasing:
        raise ValueError("macro series must be sorted with a DatetimeIndex")
    rows = {}
    for d in month_end_trading_dates(levels.index):
        now = macro.asof(d)
        prev = macro.asof(d - pd.DateOffset(months=lookback_months))
        if pd.isna(now) or pd.isna(prev) or prev <= 0:
            continue
        gate_on = (now / prev - 1.0) > 0
        rows[d] = {target: 1.0 if gate_on else 0.0, neutral: 0.5}
    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return df.reindex(columns=levels.columns).fillna(0.0)


def event_window_scores(
    levels: pd.DataFrame,
    event_dates: list,
    target: str,
    neutral: str,
    hold_days: int,
) -> pd.DataFrame:
    """Event-window allocation scores (H-005 spec; generic for event studies).

    On each event date: score row putting target=1.0 (enter, subject to the
    engine's execution lag); hold_days trading days later, a score row with
    target=0.0 (revert to neutral). Overlapping windows extend: entries are
    written first and exits never overwrite an entry date.
    """
    dates = levels.index
    entries, exits = {}, {}
    for ed in sorted(pd.Timestamp(e) for e in event_dates):
        i0 = dates.searchsorted(ed)
        if i0 >= len(dates):
            continue
        entries[dates[i0]] = {target: 1.0, neutral: 0.5}
        ix = i0 + hold_days
        if ix < len(dates):
            exits[dates[ix]] = {target: 0.0, neutral: 0.5}
    rows = {**{d: v for d, v in exits.items() if d not in entries}, **entries}
    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return df.reindex(columns=levels.columns).fillna(0.0)


def catalyst_activity_scores(
    levels: pd.DataFrame,
    events: pd.DataFrame,
    sectors: list[str],
    neutral: str,
    window_months: int,
    categories: list[str],
) -> pd.DataFrame:
    """Direction-free catalyst-activity scores (H-003 prereg spec).

    An event is ACTIVE at t if announced_date <= t <= max(effective_date,
    announced_date + window_months). A sector scores 1.0 if it has any
    active sector-scoped event in the allowed categories AND no active
    event with structurally_impairing=1; otherwise 0.0. The neutral asset
    scores 1.0 only when no sector qualifies. Weights come from
    score_weight construction (equal weight among qualifying sectors).
    """
    ev = events[(events.index_code.isin(sectors))
                & (events.category.isin(categories))].copy()
    ev["start"] = pd.to_datetime(ev.announced_date)
    eff = pd.to_datetime(ev.effective_date, errors="coerce")
    ev["end"] = pd.concat(
        [eff, ev.start + pd.DateOffset(months=window_months)], axis=1).max(axis=1)

    rows = {}
    for t in month_end_trading_dates(levels.index):
        active = ev[(ev.start <= t) & (t <= ev.end)]
        score = {}
        for s in sectors:
            sec = active[active.index_code == s]
            impaired = bool((sec.structurally_impairing == 1).any())
            score[s] = 1.0 if (len(sec) and not impaired) else 0.0
        score[neutral] = 1.0 if sum(score.values()) == 0 else 0.0
        rows[t] = score
    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return df.reindex(columns=levels.columns).fillna(0.0)


def excluded_sectors(events: pd.DataFrame, sim_date: pd.Timestamp,
                     impairment_window_months: int) -> set[str]:
    """Sectors under an active structural-impairment flag on sim_date.

    An event excludes its sector from announced_date until effective_date
    (or announced + window if no effective date). The flag direction is a
    JUDGMENT stored in the events DATA (structurally_impairing=1), not in
    code — e.g. a recapitalisation directive could be read as dilution risk
    or as a bullish catalyst; the researcher decides when recording the event.
    """
    if events.empty:
        return set()
    ev = events[(events.structurally_impairing == 1) & events.index_code.notna()]
    out = set()
    for _, e in ev.iterrows():
        start = pd.Timestamp(e.announced_date)
        end = (pd.Timestamp(e.effective_date) if pd.notna(e.effective_date)
               else start + pd.DateOffset(months=impairment_window_months))
        if start <= sim_date <= end:
            out.add(e.index_code)
    return out
