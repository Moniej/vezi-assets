"""Anti-hallucination and anti-vagueness checks (docs/AI_INTELLIGENCE_LAYER_
ARCHITECTURE.md §4.4, docs/REASONING_ENGINE_SPECIFICATION.md §11). Two
independent checks, both mechanical — neither trusts the model's own
self-report:

  check_grounding    a quoted_text must actually appear in the source
                     document (whitespace-tolerant substring match) —
                     "every conclusion must be traceable back to quoted
                     evidence" made checkable, not just asked for.
  check_banned_phrase  an explanation that is just a restated verdict with
                     no causal content ("this is bullish.") fails
                     regardless of how confident the model sounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass(frozen=True)
class GroundingResult:
    passed: bool
    reason: str


def check_grounding(quoted_text: str, source_text: str) -> GroundingResult:
    """Whitespace-tolerant substring match. Does not do fuzzy/OCR-noise
    matching yet (Phase A found ~36% of the archive is OCR-pending and
    excluded from this pilot entirely — fuzzy matching for OCR noise is
    future work, flagged in the completion report, not built speculatively
    for text this pilot doesn't touch)."""
    if not quoted_text or not quoted_text.strip():
        return GroundingResult(False, "empty quoted_text")
    q = _normalize_whitespace(quoted_text)
    s = _normalize_whitespace(source_text)
    if q in s:
        return GroundingResult(True, "exact substring match (whitespace-normalized)")
    return GroundingResult(False, f"quoted_text not found verbatim in source "
                           f"(first 80 chars of quote: {q[:80]!r})")


_BANNED_PATTERNS = [
    re.compile(r"^(this is|it'?s|that'?s)\s+(good|bad|great|terrible|bullish|"
              r"bearish|positive|negative|favou?rable|unfavou?rable)\.?$", re.I),
    re.compile(r"^(bullish|bearish|positive|negative|neutral)\.?$", re.I),
]
_MIN_EXPLANATION_CHARS = 25   # a real causal explanation is rarely shorter than this


def check_banned_phrase(explanation: str) -> GroundingResult:
    """Flags an explanation that restates a verdict without saying why.
    Deliberately conservative (a short real explanation can still slip
    through) — this catches the worst, most obviously templated failures;
    it is a floor, not a substitute for human review."""
    text = (explanation or "").strip()
    if not text:
        return GroundingResult(False, "empty explanation")
    for pat in _BANNED_PATTERNS:
        if pat.match(text):
            return GroundingResult(False, f"matches banned template pattern: {text!r}")
    if len(text) < _MIN_EXPLANATION_CHARS:
        return GroundingResult(False, f"explanation below minimum length "
                               f"({len(text)} < {_MIN_EXPLANATION_CHARS} chars): {text!r}")
    return GroundingResult(True, "not a banned template, meets minimum length")
