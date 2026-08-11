"""Decision Intelligence Phase 7: Confidence Engine.

Six separate, named confidence dimensions -- never blended into one
meaningless number. Every dimension is either a direct passthrough of an
existing, real platform signal, or a fixed, disclosed, non-tuned
threshold rule over `company_state.CompanyState`. No dimension is
computed from another dimension (no double-counting): `valuation_
confidence` is `TriangulatedValuation.valuation_confidence` verbatim;
`thesis_confidence` is `CompanyThesis.confidence` verbatim (bucketed);
the rest are computed once each, directly from state/thesis fields.
"""
from __future__ import annotations

from dataclasses import dataclass

from ngxrot.fre.company_state import KNOWN, CompanyState
from ngxrot.fre.company_thesis import CompanyThesis

LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"
_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}


@dataclass
class ConfidenceDimensions:
    ticker: str
    as_of_date: str
    data_confidence: str
    data_confidence_reason: str
    fundamental_confidence: str
    fundamental_confidence_reason: str
    thesis_confidence: str
    thesis_confidence_reason: str
    valuation_confidence: str  # passthrough of TriangulatedValuation.valuation_confidence's own vocabulary
    valuation_confidence_reason: str
    catalyst_confidence: str
    catalyst_confidence_reason: str
    risk_confidence: str
    risk_confidence_reason: str
    overall: str
    overall_reasons: list[str]


def _bucket(value: float | None, low_max: float, med_max: float) -> str:
    if value is None:
        return LOW
    if value < low_max:
        return LOW
    if value < med_max:
        return MEDIUM
    return HIGH


def compute_confidence(state: CompanyState, thesis: CompanyThesis | None) -> ConfidenceDimensions:
    # --- Data confidence: state.data_completeness (already computed, real
    # fraction of KNOWN DataPoints) ------------------------------------------
    dc = _bucket(state.data_completeness, 0.35, 0.65)
    dc_reason = f"data_completeness={state.data_completeness:.0%} (fraction of company_state " \
                f"fields with status=KNOWN); threshold: <35% LOW, <65% MEDIUM, else HIGH"

    # --- Fundamental confidence: how many of the core financial line items
    # are KNOWN, penalized for fired accounting-anomaly flags ---------------
    core_fields = ("revenue", "net_profit", "equity", "assets", "liabilities")
    n_known = sum(1 for f in core_fields if state.financial[f].status == KNOWN)
    fc = _bucket(n_known / len(core_fields), 0.4, 0.8)
    flags_dp = state.financial["accounting_anomaly_flags"]
    n_fired = len(flags_dp.value) if flags_dp.status == KNOWN and isinstance(flags_dp.value, dict) else 0
    if n_fired > 0 and fc == HIGH:
        fc = MEDIUM
    fc_reason = f"{n_known}/{len(core_fields)} core financial line items KNOWN" \
                + (f"; capped at MEDIUM: {n_fired} accounting-anomaly flag(s) fired" if n_fired else "")

    # --- Thesis confidence: bucketed passthrough of the existing, real
    # CompanyThesis.confidence float (never recomputed) --------------------
    if thesis is None or thesis.confidence is None:
        tc, tc_reason = LOW, "no CompanyThesis available, or its own confidence field is None"
    else:
        tc = _bucket(thesis.confidence, 0.4, 0.7)
        tc_reason = f"company_thesis.CompanyThesis.confidence={thesis.confidence:.2f} verbatim " \
                    f"(the most recent non-blocked implication's own recorded value), bucketed"

    # --- Valuation confidence: DIRECT passthrough of value_company()'s own
    # vocabulary, never recomputed or softened -------------------------------
    vc_dp = state.financial["valuation_confidence"]
    _VAL_MAP = {"no_data": LOW, "single_method": LOW, "low": LOW, "medium": MEDIUM, "high": HIGH}
    if vc_dp.status == KNOWN:
        vconf = _VAL_MAP.get(vc_dp.value, LOW)
        vc_reason = f"valuation_engine.TriangulatedValuation.valuation_confidence={vc_dp.value!r} " \
                    f"verbatim, bucketed (no_data/single_method/low -> LOW, medium -> MEDIUM, high -> HIGH)"
    else:
        vconf, vc_reason = LOW, "valuation_confidence unavailable in company_state"

    # --- Catalyst confidence: presence and count of real catalysts named
    # in the (unmodified) CompanyThesis -----------------------------------
    catalysts = (thesis.catalysts if thesis else None) or []
    if not catalysts:
        cc, cc_reason = LOW, "no catalysts named in the current thesis"
    elif len(catalysts) == 1:
        cc, cc_reason = MEDIUM, "exactly 1 catalyst named"
    else:
        cc, cc_reason = HIGH, f"{len(catalysts)} catalysts named"

    # --- Risk confidence: presence of named risks AND a contradiction_note
    # (evidence the thesis engine actively searched for counter-evidence,
    # per company_thesis.py's own design) ------------------------------------
    risks = (thesis.key_risks if thesis else None) or []
    has_contradiction_note = bool(thesis and thesis.contradiction_note)
    if not risks:
        rc, rc_reason = LOW, "no risks named in the current thesis"
    elif has_contradiction_note:
        rc, rc_reason = HIGH, f"{len(risks)} risk(s) named, plus an active contradiction_note " \
                              f"(counter-evidence was actively searched for, not just risks listed)"
    else:
        rc, rc_reason = MEDIUM, f"{len(risks)} risk(s) named, no contradiction_note recorded"

    # --- Overall: the FLOOR of all six dimensions (weakest link, never an
    # average) -- transparent, disclosed rule, matching this platform's own
    # confidence_propagation.py convention (a derived value's confidence is
    # the weakest of its inputs, never a blend). ------------------------------
    dims = {"data": dc, "fundamental": fc, "thesis": tc, "valuation": vconf,
            "catalyst": cc, "risk": rc}
    overall = min(dims.values(), key=lambda v: _ORDER[v])
    weakest = [k for k, v in dims.items() if v == overall]
    overall_reasons = [f"overall confidence = floor of all 6 dimensions (weakest link, never "
                        f"averaged) = {overall}", f"weakest dimension(s): {', '.join(weakest)}"]

    return ConfidenceDimensions(
        ticker=state.ticker, as_of_date=state.as_of_date,
        data_confidence=dc, data_confidence_reason=dc_reason,
        fundamental_confidence=fc, fundamental_confidence_reason=fc_reason,
        thesis_confidence=tc, thesis_confidence_reason=tc_reason,
        valuation_confidence=vconf, valuation_confidence_reason=vc_reason,
        catalyst_confidence=cc, catalyst_confidence_reason=cc_reason,
        risk_confidence=rc, risk_confidence_reason=rc_reason,
        overall=overall, overall_reasons=overall_reasons,
    )
