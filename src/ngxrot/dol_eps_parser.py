"""EPS / P.E. extraction from Daily Official List PDFs (approved engineering
task 2026-07-22: unlocks the Value/E-P factor family).

Column semantics established empirically 2026-07-22 (draw-order probe
across 2019/2022/2023 formats, cross-validated against equity_prices):
  - The rightmost two numeric fields in a symbol's row are (EPS, P.E.),
    validated via EPS x P.E. ~= Close (close from the validated
    equity_prices panel, NOT re-derived here).
  - NAIVE "take the last two numeric tokens" fails ~20-40% of rows: many
    symbols (DANGCEM, NESTLE, MTNN, TOTAL, OKOMUOIL, ARADEL, ...) print a
    BLANK EPS/P.E. on many days, and the naive rule then grabs an earlier
    column (52wk High/Low, or the repeated Price field) instead — silently
    wrong, not just missing. Fix: per-page header calibration on the
    'P.E.' header token (isolated, stable across eras: x0 ~= 743-798
    depending on era) — a numeric token is accepted as P.E. only if its
    x0 sits within PE_TOL of the header, and as EPS only if it is the
    token IMMEDIATELY preceding P.E. with a tight gap (real EPS/P.E. are
    printed as adjacent columns; a wide gap means the intervening field is
    blank and whatever sits further left is a DIFFERENT column, not EPS —
    reject rather than fabricate).
  - A recurring third-from-last token (commonly, but not always, "0.30")
    sits before EPS in some rows. Its semantics could NOT be confirmed —
    it does NOT vary sensibly by company — and is NOT extracted or
    claimed as any field here.
  - DIVIDEND CASH AMOUNTS are NOT extracted by this module. The "Div/Sc"
    fields near the row's middle were probed and found to sometimes carry
    a non-numeric 'X' (ex-dividend marker) and to disagree with the
    already-verified GTCO FY2023 primary-source anchor (paid 2.70; a
    naive column read here found 0.50 — the par-value column bleeding
    through, not the real dividend). The corp-actions PDF pipeline
    (scripts/build_corp_actions_db.py) remains the correct, validated
    source for dividend cash amounts.
  - Two numbers sometimes print with no gap ("13.301.77"): split via ALL
    valid two-decimal-place partitions, disambiguated by which partition's
    product is closest to the known close (an exact arithmetic identity).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PARSER_VERSION = "v2"  # v1 (naive last-two) superseded 2026-07-22
NUM_RX = re.compile(r"-?\d+\.\d{2}")
GLUED_2DP_RX = re.compile(r"^\d+\.\d{2}$")
PE_X_TOL = 20.0     # header-to-token x0 tolerance
ADJACENT_GAP_MAX = 30.0  # max x0(PE) - x1(EPS) for "immediately preceding"


def _split_two(tok: str) -> list[tuple[float, float]]:
    """All ways to split a glued digit string into two X.XX numbers."""
    if "." not in tok:
        return []
    out = []
    dots = [i for i, c in enumerate(tok) if c == "."]
    for d1 in dots:
        end1 = d1 + 3
        if end1 > len(tok) or not GLUED_2DP_RX.match(tok[:end1].lstrip("-")):
            continue
        rest = tok[end1:]
        if GLUED_2DP_RX.match(rest.lstrip("-")):
            try:
                out.append((float(tok[:end1]), float(rest)))
            except ValueError:
                continue
    return out


def extract_eps_pe(pdf_path: str | Path, symbols: frozenset[str],
                   closes: dict[str, float]) -> pd.DataFrame:
    """closes: {symbol -> known validated close for this file's date}
    (from equity_prices, NOT re-derived here). Returns
    DataFrame(symbol, file_date, eps, pe, implied_close, close_used,
    rel_error)."""
    import pdfplumber
    from .page_layout import rows_from_chars, chain_streams, extract_dates

    p = Path(pdf_path)
    file_date = p.name[:10]
    out = []
    with pdfplumber.open(p) as pdf:
        for page in pdf.pages:
            pe_x0 = None
            for row in rows_from_chars(page.chars):
                streams = chain_streams(row)
                if pe_x0 is None:
                    pe_hdr = next((s for s in streams if s.text == "P.E."),
                                  None)
                    if pe_hdr is not None:
                        pe_x0 = pe_hdr.x0
                        continue
                if pe_x0 is None:
                    continue
                srt = sorted(row, key=lambda c: c["x0"])
                lead = "".join(c["text"] for c in srt[:20])
                cands = [t for t in symbols if lead.startswith(t)]
                if not cands:
                    continue
                sym = max(cands, key=len)
                close = closes.get(sym)
                if close is None or close <= 0:
                    continue
                _, leftover = extract_dates(row)
                nums = sorted(
                    (s for s in chain_streams(leftover)
                     if NUM_RX.fullmatch(s.text) or len(s.text) >= 6),
                    key=lambda s: s.x0)

                eps = pe = None
                pe_tok = next((s for s in nums
                              if abs(s.x0 - pe_x0) <= PE_X_TOL), None)
                if pe_tok is not None and NUM_RX.fullmatch(pe_tok.text):
                    idx = nums.index(pe_tok)
                    if idx > 0:
                        prev = nums[idx - 1]
                        if (NUM_RX.fullmatch(prev.text)
                                and pe_tok.x0 - prev.x1 <= ADJACENT_GAP_MAX):
                            eps, pe = float(prev.text), float(pe_tok.text)
                elif pe_tok is not None:  # glued: pe_tok IS the eps+pe blob
                    cands2 = _split_two(pe_tok.text)
                    if cands2:
                        eps, pe = min(
                            cands2, key=lambda ab: abs(ab[0] * ab[1] - close))
                if eps is None:
                    continue
                if not (0 < pe <= 100) or abs(eps - close) < 0.01:
                    continue
                implied = eps * pe
                rel_err = abs(implied - close) / close
                out.append(dict(symbol=sym, file_date=file_date, eps=eps,
                                pe=pe, implied_close=round(implied, 2),
                                close_used=close, rel_error=round(rel_err, 4)))
    return pd.DataFrame(out)
