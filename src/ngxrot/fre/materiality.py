"""Decision Intelligence Phase 3: Materiality Engine.

Deterministic LOW/MEDIUM/HIGH/CRITICAL classification of a
`change_detection.DetectedChange`. Every rule below is a named,
explainable threshold or a direct passthrough of an existing, real
platform field -- never a sentiment score.

For corporate/regulatory events specifically, this reuses the `events`
table's OWN existing `severity`/`structurally_impairing` columns
(already real, already populated by the event-ingestion pipeline,
`event_pipeline.py`) rather than inventing a new severity heuristic from
scratch -- the platform already has a materiality-adjacent signal for
events; this module consumes it, it does not duplicate it.
"""
from __future__ import annotations

from dataclasses import dataclass

from ngxrot.fre.change_detection import DetectedChange

LOW, MEDIUM, HIGH, CRITICAL = "LOW", "MEDIUM", "HIGH", "CRITICAL"
_LEVEL_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3}

_EVENT_SEVERITY_MAP = {"low": LOW, "medium": MEDIUM, "high": HIGH, "critical": CRITICAL}

# Financial-magnitude thresholds (fraction change), applied only to
# 'high'-confidence changes -- a fixed, disclosed, non-tuned scale.
_FIN_THRESHOLDS = [(0.50, CRITICAL), (0.20, HIGH), (0.05, MEDIUM)]

_MARKET_THRESHOLDS = [(0.30, HIGH), (0.10, MEDIUM)]

_REGULATORY_CRITICAL_TYPES = {"suspension", "delisting"}


@dataclass
class MaterialityAssessment:
    change: DetectedChange
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    reasons: list[str]


def _cap(level: str, ceiling: str) -> str:
    return level if _LEVEL_ORDER[level] <= _LEVEL_ORDER[ceiling] else ceiling


def assess_materiality(change: DetectedChange) -> MaterialityAssessment:
    reasons: list[str] = []

    if change.category == "financial":
        if change.field.startswith("flag:"):
            level = HIGH
            reasons.append(f"newly-fired accounting-anomaly flag ({change.field}) -- a "
                            f"persistent structural signal, not a one-off fluctuation")
        elif change.magnitude is not None:
            level = LOW
            for threshold, mapped in _FIN_THRESHOLDS:
                if abs(change.magnitude) >= threshold:
                    level = mapped
                    break
            reasons.append(f"{change.field} changed {change.magnitude:+.1%} "
                            f"(threshold rule: >=50% CRITICAL, >=20% HIGH, >=5% MEDIUM, else LOW)")
        elif change.direction == "new":
            level = MEDIUM
            reasons.append(f"{change.field} became newly knowable (no prior value to compare "
                            f"magnitude against)")
        else:
            level = LOW
            reasons.append("financial change with no computable magnitude")
        if change.confidence == "low":
            level = _cap(level, MEDIUM)
            reasons.append("capped at MEDIUM: underlying data is STALE (not PIT-parameterized)")

    elif change.category == "valuation":
        level = LOW
        reasons.append("valuation_confidence change is methodological (data-coverage-driven), "
                        "not a fundamental change in the business")

    elif change.category in ("corporate_event", "regulatory"):
        evt = change.current_value
        severity = (evt or {}).get("severity") if isinstance(evt, dict) else None
        structurally_impairing = bool((evt or {}).get("structurally_impairing")) if isinstance(evt, dict) else False
        if severity in _EVENT_SEVERITY_MAP:
            level = _EVENT_SEVERITY_MAP[severity]
            reasons.append(f"events.severity={severity!r} (platform's own event-ingestion "
                            f"severity classification, reused directly, not recomputed)")
        else:
            level = MEDIUM
            reasons.append("events.severity not recorded for this event -- defaulted to MEDIUM, "
                            "not silently treated as LOW")
        if structurally_impairing:
            level = CRITICAL
            reasons.append("events.structurally_impairing=True -- overrides to CRITICAL")
        if change.category == "regulatory" and change.field in _REGULATORY_CRITICAL_TYPES:
            level = CRITICAL
            reasons.append(f"regulatory event_type={change.field!r} is inherently CRITICAL "
                            f"(suspension/delisting)")

    elif change.category == "insider":
        txn = change.current_value
        routine = getattr(txn, "routine_flag", False)
        if routine:
            level = LOW
            reasons.append("scheme/plan-flagged insider transaction -- routine, not discretionary")
        else:
            level = MEDIUM
            reasons.append(f"discretionary insider {change.field.lower()} -- single transaction; "
                            f"recurrence (multiple such transactions) would raise this, not assessed "
                            f"here (single-change scope)")

    elif change.category == "market":
        if change.field == "close" and change.magnitude is not None:
            level = LOW
            for threshold, mapped in _MARKET_THRESHOLDS:
                if abs(change.magnitude) >= threshold:
                    level = mapped
                    break
            reasons.append(f"price changed {change.magnitude:+.1%} between snapshots "
                            f"(threshold rule: >=30% HIGH, >=10% MEDIUM, else LOW)")
        elif change.field == "watchlist_status":
            level = MEDIUM
            reasons.append(f"watchlist status {change.direction} -- an analyst-level "
                            f"attention signal, not itself fundamental")
        else:
            level = LOW
            reasons.append("market change with no computable magnitude")

    elif change.category == "business":
        level = MEDIUM
        reasons.append(f"{change.field} reclassification -- rare, structurally meaningful "
                        f"when it happens")

    else:
        level = LOW
        reasons.append(f"unrecognized change category {change.category!r} -- defaulted to LOW, "
                        f"never guessed higher")

    return MaterialityAssessment(change=change, level=level, reasons=reasons)


def rank_by_materiality(assessments: list[MaterialityAssessment]) -> list[MaterialityAssessment]:
    """Stable sort, CRITICAL first, ties broken by original order (never by
    an invented secondary score)."""
    return sorted(assessments, key=lambda a: -_LEVEL_ORDER[a.level])
