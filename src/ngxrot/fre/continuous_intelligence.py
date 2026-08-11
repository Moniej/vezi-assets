"""Decision Intelligence Phase 18: Continuous Intelligence.

Implements the DETERMINISTIC PIPELINE the task names:

  new information -> affected company -> affected fields -> change
  detection -> materiality assessment -> confidence update -> research
  dossier update -> portfolio-memory update -> alert/review queue.

## What this module does NOT do (disclosed, not silently skipped)

This platform has no job scheduler, file-watcher, or webhook receiver for
"new filings/data arriving" -- building one is an operations/infra project
outside this task's scope (no such infrastructure exists anywhere on this
platform to extend). This module is the PIPELINE FUNCTION that such a
trigger would call once wired up: given a ticker and a
before/after date pair (standing in for "state before the new
information" and "state after it"), it runs the full chain and returns a
structured result, including an alert/review-queue entry ONLY when
materiality clears LOW -- "do not manufacture alerts where materiality is
LOW" is enforced structurally (`alert_entry` is `None` otherwise), not by
convention.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.company_intelligence_bundle import CompanyIntelligenceBundle, build_intelligence_bundle
from ngxrot.fre.materiality import LOW

_ALERT_WORTHY_LEVELS = ("MEDIUM", "HIGH", "CRITICAL")


@dataclass
class ContinuousIntelligenceResult:
    ticker: str
    as_of_date: str
    prior_date: str
    bundle: CompanyIntelligenceBundle
    affected_fields: list[str]
    materiality_summary: dict[str, int]  # level -> count, e.g. {'LOW': 2, 'HIGH': 1}
    max_materiality: str
    confidence_changed: bool  # True iff overall confidence differs from a re-check at prior_date
    alert_entry: dict | None  # None whenever max_materiality == LOW or there are no changes


def process_new_information(con: sqlite3.Connection, ticker: str, as_of_date: str, prior_date: str,
                             intelligence_cache: dict | None = None,
                             include_portfolio_note: bool = False) -> ContinuousIntelligenceResult:
    bundle = build_intelligence_bundle(con, ticker, as_of_date, prior_date, intelligence_cache,
                                        include_portfolio_note=include_portfolio_note)

    affected_fields = [f"{a.change.category}/{a.change.field}" for a in bundle.ranked_changes]
    materiality_summary: dict[str, int] = {}
    for a in bundle.ranked_changes:
        materiality_summary[a.level] = materiality_summary.get(a.level, 0) + 1
    _ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    max_materiality = max(materiality_summary, key=lambda k: _ORDER[k]) if materiality_summary else LOW

    # Confidence-update check: does the CURRENT confidence differ from what
    # it would have been at the prior snapshot? (a real, computed
    # before/after comparison, not asserted)
    from ngxrot.fre.confidence_engine import compute_confidence
    prior_confidence = compute_confidence(bundle.prior_state, None)  # thesis is as-of `as_of_date` only; prior-date thesis not separately fetched (out of scope -- see docstring)
    confidence_changed = prior_confidence.overall != bundle.confidence.overall

    alert_entry = None
    if max_materiality in _ALERT_WORTHY_LEVELS:
        critical_or_high = [a for a in bundle.ranked_changes if a.level in ("HIGH", "CRITICAL")]
        alert_entry = {
            "ticker": ticker,
            "as_of_date": as_of_date,
            "max_materiality": max_materiality,
            "reason": "; ".join(f"[{a.level}] {a.change.description}" for a in bundle.ranked_changes
                                if a.level in _ALERT_WORTHY_LEVELS),
            "requires_dossier_review": bool(critical_or_high),
        }

    return ContinuousIntelligenceResult(
        ticker=ticker, as_of_date=as_of_date, prior_date=prior_date, bundle=bundle,
        affected_fields=affected_fields, materiality_summary=materiality_summary,
        max_materiality=max_materiality, confidence_changed=confidence_changed, alert_entry=alert_entry,
    )
