"""Confidence rating for research conclusions: High / Moderate / Low /
Inconclusive.

Rule-based, so a rating can always be traced to its inputs (each criterion
contributes 0-2 points). Hard override: conclusions drawn from synthetic or
confidence-0 data are Inconclusive regardless of score — good numbers on
fake data are still fake.
"""

from __future__ import annotations

THRESHOLDS = [(8, "High"), (5, "Moderate"), (3, "Low")]


def rate(*, data_confidence: float, synthetic: bool, n_decisions: int,
         n_regimes: int, p_corrected: float | None, plateau_frac: float | None,
         placebo_pass: bool | None) -> dict:
    reasons, score = [], 0

    if data_confidence >= 0.7:
        score += 2; reasons.append("data: exchange-official grade (+2)")
    elif data_confidence >= 0.4:
        score += 1; reasons.append("data: aggregator/manual grade (+1)")
    else:
        reasons.append("data: low/no confidence (+0)")

    if n_decisions >= 100:
        score += 2; reasons.append(f"sample: {n_decisions} decisions (+2)")
    elif n_decisions >= 40:
        score += 1; reasons.append(f"sample: {n_decisions} decisions (+1)")
    else:
        reasons.append(f"sample: only {n_decisions} decisions (+0)")

    if n_regimes >= 3:
        score += 2; reasons.append(f"regimes: {n_regimes} covered (+2)")
    elif n_regimes == 2:
        score += 1; reasons.append("regimes: 2 covered (+1)")
    else:
        reasons.append("regimes: single regime (+0)")

    if p_corrected is not None and p_corrected < 0.05:
        score += 2; reasons.append(f"significance: corrected p={p_corrected:.3f} (+2)")
    elif p_corrected is not None and p_corrected < 0.10:
        score += 1; reasons.append(f"significance: corrected p={p_corrected:.3f} (+1)")
    else:
        reasons.append(f"significance: corrected p="
                       f"{'n/a' if p_corrected is None else f'{p_corrected:.3f}'} (+0)")

    if plateau_frac is not None and plateau_frac >= 0.6:
        score += 2; reasons.append(f"robustness: {plateau_frac:.0%} of parameter "
                                   f"space acceptable (+2)")
    elif plateau_frac is not None and plateau_frac >= 0.4:
        score += 1; reasons.append(f"robustness: {plateau_frac:.0%} plateau (+1)")
    else:
        reasons.append("robustness: narrow/unknown plateau (+0)")

    if placebo_pass is True:
        score += 2; reasons.append("placebo: real strategy distinguishable (+2)")
    elif placebo_pass is None:
        reasons.append("placebo: not run (+0)")
    else:
        reasons.append("placebo: FAILED — indistinguishable from noise (+0)")

    if synthetic:
        return {"rating": "Inconclusive", "score": score,
                "reasons": ["OVERRIDE: synthetic/confidence-0 data — any score "
                            "is a plumbing result, not evidence"] + reasons}
    rating = next((name for floor, name in THRESHOLDS if score >= floor),
                  "Inconclusive")
    return {"rating": rating, "score": score, "reasons": reasons}
