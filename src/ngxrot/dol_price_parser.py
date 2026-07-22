"""Close-price extraction from Daily Official List PDFs (gap-day fallback).

PARSER_VERSION feeds provenance: rows ingest under source ngx_dol_<version>.

Column semantics established empirically (2026-07-21, anchored against
validated equity_prices rows on overlap days across 2015/2023/2026 formats):
  - The 'Market Price' column IS the official close of the file's day —
    exact match on liquid names in every era probed. (The 'Official Close'
    column is sparsely populated and NOT reliable.)
  - Numbers are RIGHT-aligned: a close stream's x1 sits at the 'Market
    Price' header's x1 (± tol). Header x differs by era (2015 ~298;
    2019+ ~422) so the band is calibrated per page from its own header.
  - The business-done 'Date' (any dd/mm/yy at x0 <= 560; ex-div bands sit
    right of 560 — discriminator validated by the exdiv parser on all
    2,830 DOLs) equals the file date iff the security traded that day.
    Some bd dates are DRAWN IN AN OFFSET BAND (different glyph row than
    the symbol), so they are collected page-wide from DRAW-ORDER runs
    (PDF content-stream order preserves text runs; geometric chaining
    does not survive column interleaving) and matched to rows by top-y.
  - The 'Qty' column is the LAST TRADE's quantity, NOT daily volume
    (ZENITHBANK 2026-07-01: Qty 600 vs true volume 19,627,148). Daily
    volume/value are NOT recoverable from the DOL: ingest close only,
    volume/value/deals NULL. Never fabricate.
  - Some DOLs are printed intraday (e.g. 2022-03-16, ~34% of closes
    disagree with the final pricelist): the header 'Printed' timestamp is
    returned so callers can refuse files printed before the close.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PARSER_VERSION = "v1"
NUM_RX = re.compile(r"^-?[\d,]+(\.\d+)?$")
DATE_RUN_RX = re.compile(r"\d{2}/\d{2}/\d{2}")
PRINT_RX = re.compile(r"Printed\s+\d{2}/\d{2}/\d{4}\s+(\d{2}:\d{2})")
X_TOL = 8.0
Y_TOL = 4.0


def _num(s: str) -> float | None:
    s = s.strip().replace(",", "")
    if s in ("-", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _draw_order_dates(chars: list[dict]) -> list[dict]:
    """dd/mm/yy runs found in content-stream order: glyphs of one text run
    are consecutive in page.chars, so interleaving columns cannot pollute
    the match the way x-sorted chaining can. Contiguity is still verified
    geometrically to reject accidental cross-run matches."""
    s = "".join(c["text"] for c in chars)
    out = []
    for m in DATE_RUN_RX.finditer(s):
        cs = chars[m.start():m.end()]
        tops = [c["top"] for c in cs]
        if max(tops) - min(tops) > 3.0:
            continue
        if not all(-1.0 <= cs[k + 1]["x0"] - cs[k]["x1"] <= 2.5
                   for k in range(len(cs) - 1)):
            continue
        dd, mm = int(m.group()[:2]), int(m.group()[3:5])
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            out.append(dict(text=m.group(), x0=cs[0]["x0"],
                            top=min(tops)))
    return out


def parse_dol_prices(pdf_path: str | Path,
                     symbols: frozenset[str]) -> tuple[pd.DataFrame, str | None]:
    """Parse one DOL PDF. Returns (df, print_time):
    df(symbol, file_date, close, bd_date, traded); print_time 'HH:MM' from
    the header (None if absent). file_date comes from the archive filename;
    callers should reject files whose internal date disagrees."""
    import pdfplumber
    from .page_layout import rows_from_chars, chain_streams

    p = Path(pdf_path)
    file_date = p.name[:10]
    d = file_date.split("-")
    bd_of_day = f"{d[2]}/{d[1]}/{d[0][2:]}"          # dd/mm/yy

    out: list[dict] = []
    mp_x1 = None
    print_time = None
    with pdfplumber.open(p) as pdf:
        for page in pdf.pages:
            if print_time is None:
                m = PRINT_RX.search(page.extract_text() or "")
                if m:
                    print_time = m.group(1)
            page_dates = [dt for dt in _draw_order_dates(page.chars)
                          if dt["x0"] <= 560]
            for row in rows_from_chars(page.chars):
                streams = chain_streams(row)
                texts = {s.text for s in streams}
                if "Market Price" in texts and "Symbol" in texts:
                    mp_x1 = next(s.x1 for s in streams
                                 if s.text == "Market Price")
                    continue
                if mp_x1 is None:
                    continue
                srt = sorted(row, key=lambda c: c["x0"])
                lead = "".join(c["text"] for c in srt[:20])
                cands = [t for t in symbols if lead.startswith(t)]
                if not cands:
                    continue
                sym = max(cands, key=len)     # CAP vs CAPOIL: longest wins
                row_top = min(c["top"] for c in row)
                near = [dt for dt in page_dates
                        if abs(dt["top"] - row_top) <= Y_TOL]
                bd = min(near, key=lambda dt: abs(dt["top"] - row_top)
                         )["text"] if near else None
                close = None
                for s in chain_streams(row):
                    if abs(s.x1 - mp_x1) <= X_TOL and NUM_RX.match(s.text):
                        close = _num(s.text)
                        break
                out.append(dict(symbol=sym, file_date=file_date, close=close,
                                bd_date=bd, traded=bd == bd_of_day))
    df = pd.DataFrame(out)
    if len(df):
        df = df.drop_duplicates(subset=["symbol"])
    return df, print_time
