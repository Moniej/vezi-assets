"""Decision Intelligence Phase 2: Change Detection.

Purely a diff over two `company_state.CompanyState` snapshots (an earlier
`as_of_date` and a later one, both built by the unmodified Phase-1 engine).
No new data source, no new computation over raw facts -- every detected
change is traceable to a specific DataPoint difference between the two
snapshots the caller supplies.

A `DataPoint` whose status is not `KNOWN` in EITHER snapshot never
produces a change (comparing two `UNKNOWN`s, or a `KNOWN` against an
`UNKNOWN`, is not "no change" -- it's "cannot compare," and is skipped,
not defaulted to "unchanged").
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ngxrot.fre.company_state import KNOWN, CompanyState


@dataclass
class DetectedChange:
    ticker: str
    category: str  # financial | corporate_event | regulatory | insider | market | business
    field: str
    direction: str  # improved | worsened | new | resolved | changed | unknown
    magnitude: float | None  # relative change where both values are numeric, else None
    description: str
    timestamp: str  # the LATER snapshot's as_of_date
    source: str
    confidence: str  # KNOWN-vs-KNOWN -> 'high'; either side STALE -> 'low'
    prior_value: object
    current_value: object


def _numeric_change(prior, current, ticker, category, field_name, timestamp, source, confidence,
                     higher_is_better: bool = True) -> DetectedChange | None:
    if prior is None or current is None or prior == current:
        return None
    try:
        magnitude = (current - prior) / abs(prior) if prior != 0 else None
    except TypeError:
        magnitude = None
    if magnitude is not None:
        improved = (magnitude > 0) == higher_is_better
        direction = "improved" if improved else "worsened"
    else:
        direction = "changed"
    return DetectedChange(
        ticker=ticker, category=category, field=field_name, direction=direction,
        magnitude=magnitude, description=f"{field_name}: {prior!r} -> {current!r}",
        timestamp=timestamp, source=source, confidence=confidence,
        prior_value=prior, current_value=current,
    )


def detect_changes(prior: CompanyState, current: CompanyState) -> list[DetectedChange]:
    if prior.ticker != current.ticker:
        raise ValueError("detect_changes() compares two snapshots of the SAME ticker only")
    if prior.as_of_date > current.as_of_date:
        raise ValueError("prior snapshot's as_of_date must be <= current snapshot's -- "
                          "never compare backward in time")

    changes: list[DetectedChange] = []
    ticker = current.ticker

    # --- financial line items: direction from sign of change ---------------
    for field_name in ("revenue", "net_profit", "equity", "assets", "liabilities"):
        p, c = prior.financial[field_name], current.financial[field_name]
        if p.status == KNOWN and c.status == KNOWN:
            confidence = "low" if "STALE" in (p.status, c.status) else "high"
            chg = _numeric_change(p.value, c.value, ticker, "financial", field_name,
                                   current.as_of_date, c.source, confidence,
                                   higher_is_better=(field_name != "liabilities"))
            if chg:
                changes.append(chg)
        elif p.status != KNOWN and c.status == KNOWN:
            changes.append(DetectedChange(
                ticker=ticker, category="financial", field=field_name, direction="new",
                magnitude=None, description=f"{field_name} became knowable ({c.value!r})",
                timestamp=current.as_of_date, source=c.source, confidence="high",
                prior_value=None, current_value=c.value))

    # --- valuation confidence: ordinal improvement/degradation -------------
    _VAL_CONF_ORDER = {"no_data": 0, "single_method": 1, "low": 1, "medium": 2, "high": 3}
    p_vc, c_vc = prior.financial["valuation_confidence"], current.financial["valuation_confidence"]
    if p_vc.status == KNOWN and c_vc.status == KNOWN and p_vc.value != c_vc.value:
        p_ord, c_ord = _VAL_CONF_ORDER.get(p_vc.value, 0), _VAL_CONF_ORDER.get(c_vc.value, 0)
        changes.append(DetectedChange(
            ticker=ticker, category="valuation", field="valuation_confidence",
            direction="improved" if c_ord > p_ord else "worsened" if c_ord < p_ord else "changed",
            magnitude=None, description=f"valuation_confidence: {p_vc.value} -> {c_vc.value}",
            timestamp=current.as_of_date, source=c_vc.source, confidence="high",
            prior_value=p_vc.value, current_value=c_vc.value))

    # --- newly fired accounting-anomaly flags -------------------------------
    p_flags, c_flags = prior.financial["accounting_anomaly_flags"], current.financial["accounting_anomaly_flags"]
    if c_flags.status == KNOWN:
        prior_fired = set(p_flags.value.keys()) if p_flags.status == KNOWN else set()
        newly_fired = set(c_flags.value.keys()) - prior_fired
        for flag_name in sorted(newly_fired):
            changes.append(DetectedChange(
                ticker=ticker, category="financial", field=f"flag:{flag_name}", direction="worsened",
                magnitude=None, description=f"{flag_name} newly fired", timestamp=current.as_of_date,
                source=c_flags.source, confidence="low" if c_flags.status != KNOWN else "high",
                prior_value=False, current_value=True))

    # --- new corporate events (by event_id, not present in the prior
    # snapshot) --------------------------------------------------------------
    for category, dp_field in (("corporate_event", "corporate_events"), ("regulatory", "regulatory")):
        p_dp = getattr(prior, dp_field)
        c_dp = getattr(current, dp_field)
        if c_dp.status != KNOWN:
            continue
        prior_ids = {e["event_id"] for e in p_dp.value} if p_dp.status == KNOWN else set()
        for evt in c_dp.value:
            if evt["event_id"] not in prior_ids:
                changes.append(DetectedChange(
                    ticker=ticker, category=category, field=evt["event_type"], direction="new",
                    magnitude=None, description=evt["headline"] or evt["event_type"],
                    timestamp=evt["announced_date"], source=c_dp.source, confidence="high",
                    prior_value=None, current_value=evt))

    # --- new insider transactions (by doc_id) -------------------------------
    p_ins, c_ins = prior.insider_activity, current.insider_activity
    if c_ins.status == KNOWN:
        prior_doc_ids = {t.doc_id for t in p_ins.value} if p_ins.status == KNOWN else set()
        for txn in c_ins.value:
            if txn.doc_id not in prior_doc_ids:
                changes.append(DetectedChange(
                    ticker=ticker, category="insider", field=txn.nature, direction="new",
                    magnitude=None,
                    description=f"insider {txn.nature.lower()}{' (routine/scheme)' if txn.routine_flag else ''}",
                    timestamp=txn.filing_date, source=c_ins.source, confidence="high",
                    prior_value=None, current_value=txn))

    # --- market: price and watchlist status -----------------------------------
    p_close, c_close = prior.market["close"], current.market["close"]
    if p_close.status == KNOWN and c_close.status == KNOWN:
        chg = _numeric_change(p_close.value, c_close.value, ticker, "market", "close",
                               current.as_of_date, c_close.source, "high")
        if chg:
            changes.append(chg)
    p_watch, c_watch = prior.market["watchlist_status"], current.market["watchlist_status"]
    if p_watch.status != KNOWN and c_watch.status == KNOWN:
        changes.append(DetectedChange(
            ticker=ticker, category="market", field="watchlist_status", direction="new",
            magnitude=None, description="added to watchlist", timestamp=current.as_of_date,
            source=c_watch.source, confidence="high", prior_value=None, current_value=c_watch.value))
    elif p_watch.status == KNOWN and c_watch.status != KNOWN:
        changes.append(DetectedChange(
            ticker=ticker, category="market", field="watchlist_status", direction="resolved",
            magnitude=None, description="removed from watchlist", timestamp=current.as_of_date,
            source=p_watch.source, confidence="high", prior_value=p_watch.value, current_value=None))

    # --- business: sector/sub_industry reclassification (rare, real if it
    # ever happens -- e.g. a company's own securities.sector_ngx updated) ---
    for field_name in ("sector", "sub_industry"):
        p, c = prior.business[field_name], current.business[field_name]
        if p.status == KNOWN and c.status == KNOWN and p.value != c.value:
            changes.append(DetectedChange(
                ticker=ticker, category="business", field=field_name, direction="changed",
                magnitude=None, description=f"{field_name}: {p.value} -> {c.value}",
                timestamp=current.as_of_date, source=c.source, confidence="high",
                prior_value=p.value, current_value=c.value))

    return changes
