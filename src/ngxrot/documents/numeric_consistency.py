"""Deterministic numeric-magnitude consistency check (2026-08-12,
docs/alpha/FINANCIAL_EXTRACTION_QUALITY_FIX_REPORT.md, Fix 2). Mechanical,
does not trust another LLM judgment — mirrors grounding.py's own
discipline (a mechanical check the model's self-report cannot talk its way
past).

Root cause this exists to catch (found in the 2026-08-12 extraction
pilot, TRANSCORP net_profit): the model's quoted evidence and its own
reasoning correctly stated "N94.1 billion", but the structured
`numeric_value` field it wrote was 941,000,000,000 (94.1bn x 10) — a
transcription error isolated to the structured field. check_grounding
cannot catch this class of bug, because the quote itself is verbatim
correct; only comparing the PARSED MAGNITUDE of the quote against the
structured value can.

This module NEVER corrects a value — see check_numeric_consistency's own
docstring. It flags for review. Silently "fixing" a number the model
already got wrong once is a second unverified guess, not a fix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Naira/generic currency scale words, longest-match-first so "million" is
# not partially matched by an earlier shorter alternative. "b"/"m"/"k" as
# bare single letters are deliberately EXCLUDED (too ambiguous — "N1.00 per
# share" would falsely parse "N1" + nothing, but a bare trailing "m" in
# running prose is far too likely to be a false positive to include).
_SCALE_WORDS = [
    ("trillion", 1e12), ("tn", 1e12),
    ("billion", 1e9), ("bn", 1e9),
    ("million", 1e6), ("mn", 1e6),
    ("thousand", 1e3),
]
_NUMBER_RE = re.compile(
    r"(?:[₦N#]\s*)?"                       # optional currency marker
    r"(\d[\d,]*(?:\.\d+)?)"                # the number itself, e.g. 94.1 or 1,234,567
    r"\s*(" + "|".join(re.escape(w) for w, _ in _SCALE_WORDS) + r")\b",
    re.IGNORECASE,
)

# A mismatch is only reported when the ratio between the structured value
# and a parsed candidate lands suspiciously close to a ROUND factor
# (10x, 100x, 1000x, or their reciprocals) — exactly the shape of a
# decimal-point/scale-word transcription slip (94.1bn -> 941bn is a clean
# 10x; 1.25bn -> 12.5bn is a clean 10x; 940m -> 940bn is a clean 1000x).
# A generic "these two numbers differ" check would flag legitimate
# multi-figure documents (a quote mentioning both this year's and last
# year's number) constantly — round-factor-only keeps the false-positive
# rate low while still catching the exact failure mode this was built for.
_SUSPICIOUS_RATIOS = (10.0, 100.0, 1000.0)
_ROUND_FACTOR_TOLERANCE = 0.03   # 3% -- tight enough that a coincidental
                                 # near-round ratio between two genuinely
                                 # different real figures is unlikely
_CLOSE_ENOUGH_TOLERANCE = 0.02   # 2% -- rounding/formatting slack for a
                                 # value that DOES match a quoted figure


@dataclass(frozen=True)
class NumericConsistencyResult:
    status: str          # 'pass' | 'flag' | 'not_checked'
    reason: str
    candidates: tuple[float, ...] = ()   # every magnitude parsed from the quote


def _parsed_magnitudes(text: str) -> list[float]:
    out = []
    for match in _NUMBER_RE.finditer(text):
        raw_number, scale_word = match.groups()
        try:
            number = float(raw_number.replace(",", ""))
        except ValueError:
            continue
        scale = next(s for w, s in _SCALE_WORDS if w.lower() == scale_word.lower())
        out.append(number * scale)
    return out


def check_numeric_consistency(numeric_value: float | None,
                              quoted_text: str | None) -> NumericConsistencyResult:
    """Compares `numeric_value` (the structured field) against every
    number+scale-word magnitude parsed from `quoted_text` (the grounding
    evidence). Returns:

      'not_checked' — numeric_value is null, or the quote contains no
                      parseable number+scale-word magnitude (e.g. a
                      qualitative fact, or a number with no scale word
                      like a per-share figure) — nothing to compare, not
                      a pass or a failure.
      'pass'        — at least one parsed candidate is within 2% of
                      numeric_value.
      'flag'        — no candidate is close, AND at least one candidate's
                      ratio to numeric_value lands within 3% of a round
                      factor (10x/100x/1000x or its reciprocal) — the
                      specific, narrow signature of a scale/decimal
                      transcription error, not a generic "numbers differ"
                      complaint.

    Never corrects `numeric_value`. The caller decides what to do with a
    'flag' result (this fix: lower confidence and warn, matching the
    existing grounding-failure pattern in extract.py) — this function's
    only job is deterministic detection."""
    if numeric_value is None or numeric_value == 0:
        return NumericConsistencyResult("not_checked", "numeric_value is null or zero — nothing to compare")
    if not quoted_text:
        return NumericConsistencyResult("not_checked", "no quoted evidence to compare against")

    candidates = _parsed_magnitudes(quoted_text)
    if not candidates:
        return NumericConsistencyResult("not_checked",
            "no number+scale-word magnitude parseable from the quote "
            "(e.g. a qualitative statement, or a bare number with no scale word)")

    abs_value = abs(numeric_value)
    for c in candidates:
        if c == 0:
            continue
        if abs(abs_value - c) / max(abs_value, c) <= _CLOSE_ENOUGH_TOLERANCE:
            return NumericConsistencyResult("pass",
                f"numeric_value {numeric_value:,.0f} matches a quoted magnitude "
                f"{c:,.0f} within tolerance", tuple(candidates))

    for c in candidates:
        if c == 0:
            continue
        for ratio in (abs_value / c, c / abs_value):
            for suspicious in _SUSPICIOUS_RATIOS:
                if abs(ratio - suspicious) / suspicious <= _ROUND_FACTOR_TOLERANCE:
                    return NumericConsistencyResult("flag",
                        f"numeric_value {numeric_value:,.0f} is ~{ratio:.0f}x a quoted "
                        f"magnitude {c:,.0f} — matches the signature of a scale/decimal "
                        f"transcription error, not confirmed as wrong but not confirmed "
                        f"right either", tuple(candidates))

    return NumericConsistencyResult("not_checked",
        f"numeric_value {numeric_value:,.0f} does not closely match any quoted magnitude "
        f"{tuple(round(c) for c in candidates)}, and none of the differences look like a "
        f"round-factor transcription error either — genuinely inconclusive from this "
        f"quote alone, not flagged (avoids over-flagging on quotes with multiple figures)",
        tuple(candidates))


# ---------------------------------------------------------------------------
# Tabular-unit consistency check (2026-08-13, real ~1000x defect found on
# ELLAHLAKES doc 11122 during the FRE scale-validation program). Distinct
# failure mode from check_numeric_consistency above: that check catches a
# scale WORD stated immediately next to a number in the quoted evidence
# itself ("N94.1 billion"). It CANNOT catch a table's scale being declared
# once, in a column header several lines away from the actual data row
# ("₦'000" above a row reading "Revenue 146,658") -- the quote for that fact
# is just "146,658" with no adjacent scale word at all, so
# check_numeric_consistency correctly (by its own design) returns
# not_checked, silently missing the error. This check looks at the FULL
# document text (not just the fact's own quote) for a stated table-scale
# convention, deterministically -- no LLM arithmetic involved, per the same
# discipline as check_numeric_consistency itself.
# ---------------------------------------------------------------------------

# (pattern, multiplier) -- longest/most-specific alternatives first within
# each scale tier so e.g. "million" isn't partially shadowed by a shorter
# alternative. Deliberately excludes bare single-letter suffixes like a
# trailing "m"/"bn" directly on a number (too ambiguous in running prose,
# same reasoning _SCALE_WORDS above already documents) -- this checks for
# an explicit, self-contained UNIT DECLARATION (a header or note), not an
# inline-with-the-number scale word.
_TABLE_SCALE_DECLARATIONS = [
    # thousands
    (re.compile(r"[₦N#]\s*'?0{3}s?\b", re.IGNORECASE), 1e3, "thousands"),
    (re.compile(r"\bin\s+thousands(\s+of\s+(naira|N|₦))?\b", re.IGNORECASE), 1e3, "thousands"),
    (re.compile(r"\bthousands?\s+of\s+naira\b", re.IGNORECASE), 1e3, "thousands"),
    # millions
    (re.compile(r"[₦N#]\s*['\s]?m(?:illion)?\b(?!\w)", re.IGNORECASE), 1e6, "millions"),
    (re.compile(r"\bin\s+millions(\s+of\s+(naira|N|₦))?\b", re.IGNORECASE), 1e6, "millions"),
    # billions
    (re.compile(r"[₦N#]\s*['\s]?bn\b", re.IGNORECASE), 1e9, "billions"),
    (re.compile(r"[₦N#]\s*billion\b", re.IGNORECASE), 1e9, "billions"),
    (re.compile(r"\bin\s+billions(\s+of\s+(naira|N|₦))?\b", re.IGNORECASE), 1e9, "billions"),
]

_BARE_NUMBER_RE = re.compile(r"\(?\s*(\d[\d,]*(?:\.\d+)?)\s*\)?")


@dataclass(frozen=True)
class TabularUnitResult:
    status: str          # 'pass' | 'flag' | 'ambiguous' | 'not_checked'
    reason: str
    declared_scales: tuple[tuple[str, float], ...] = ()   # (label, multiplier) pairs found


def _declared_scales(document_text: str) -> list[tuple[str, float]]:
    """Every DISTINCT scale convention declared anywhere in the document,
    deduplicated by multiplier (a document repeating "₦'000" in every
    table header is one convention, not many)."""
    found: dict[float, str] = {}
    for pattern, multiplier, label in _TABLE_SCALE_DECLARATIONS:
        if pattern.search(document_text):
            found.setdefault(multiplier, label)
    return [(label, mult) for mult, label in sorted(found.items())]


def _raw_quoted_number(quoted_text: str) -> float | None:
    """The bare numeric literal in the quote, sign-stripped (parens =
    negative in NGX/IFRS statements, handled by the caller if needed) --
    the RAW figure as printed, before any scale is applied. Returns None
    if no clean single number is found (avoids guessing on a quote with
    multiple numbers or none)."""
    matches = _BARE_NUMBER_RE.findall(quoted_text)
    if len(matches) != 1:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def check_tabular_unit_consistency(numeric_value: float | None, quoted_text: str | None,
                                   document_text: str | None) -> TabularUnitResult:
    """Deterministic, document-level check for a table-header unit-scale
    convention (₦'000, thousands, million, billion) that numeric_value may
    have failed to apply. NEVER corrects numeric_value -- detection only,
    same discipline as check_numeric_consistency. Fails CLOSED (returns
    'ambiguous', not a guess) when the document declares more than one
    scale convention and which applies to THIS fact cannot be determined
    from the quote alone -- mixed-unit documents are a real, disclosed
    case this deliberately does not try to resolve automatically."""
    if numeric_value is None or numeric_value == 0:
        return TabularUnitResult("not_checked", "numeric_value is null or zero — nothing to compare")
    if not document_text:
        return TabularUnitResult("not_checked", "no document text available to scan for a unit declaration")

    scales = _declared_scales(document_text)
    if not scales:
        return TabularUnitResult("not_checked",
            "no table-scale convention (₦'000/thousands/million/billion) found anywhere "
            "in the document — nothing to validate against, not assumed to be correct")

    if len(scales) > 1:
        return TabularUnitResult("ambiguous",
            f"document declares more than one scale convention {tuple(l for l, _ in scales)} "
            f"— which applies to this specific fact cannot be determined deterministically; "
            f"failing closed rather than guessing", tuple(scales))

    label, multiplier = scales[0]

    if not quoted_text:
        # A scale convention exists somewhere in the document, but this
        # fact has no quote to check its raw figure against -- can't
        # confirm either way.
        return TabularUnitResult("not_checked",
            f"document declares a {label} convention, but this fact has no quoted "
            f"evidence to check the raw figure against", tuple(scales))

    raw = _raw_quoted_number(quoted_text)
    if raw is None:
        return TabularUnitResult("not_checked",
            f"document declares a {label} convention, but the quoted evidence does not "
            f"contain a single clean number to check numeric_value against", tuple(scales))

    abs_value = abs(numeric_value)

    # Does numeric_value look like the RAW, un-multiplied table figure?
    # (within 0.5% -- tighter than the round-factor check elsewhere,
    # since this is checking for an exact miss, not a fuzzy magnitude)
    if raw != 0 and abs(abs_value - raw) / raw <= 0.005:
        return TabularUnitResult("flag",
            f"numeric_value {numeric_value:,.0f} equals the RAW quoted figure {raw:,.0f} "
            f"verbatim, but the document declares a '{label}' (×{multiplier:,.0f}) "
            f"convention — this figure was very likely never scaled; expected value is "
            f"probably {raw * multiplier:,.0f}. NOT auto-corrected — flagged for review.",
            tuple(scales))

    # Does numeric_value look correctly scaled (raw * multiplier, within
    # rounding slack)?
    expected = raw * multiplier
    if expected != 0 and abs(abs_value - expected) / expected <= 0.02:
        return TabularUnitResult("pass",
            f"numeric_value {numeric_value:,.0f} matches the raw quoted figure "
            f"{raw:,.0f} scaled by the document's declared '{label}' convention "
            f"(×{multiplier:,.0f})", tuple(scales))

    return TabularUnitResult("not_checked",
        f"document declares a '{label}' convention, but numeric_value {numeric_value:,.0f} "
        f"matches neither the raw quoted figure {raw:,.0f} nor that figure scaled "
        f"(×{multiplier:,.0f} = {expected:,.0f}) — genuinely inconclusive, not flagged",
        tuple(scales))
