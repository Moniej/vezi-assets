"""Parser for NGX PRICES_LIST2 (sector-grouped price list) — used ONLY to
recover days where neither PRICES1 nor a DOL exists (e.g. 2023-07-21, when
NGX published an empty PRICES1).

LIST2 rows carry company NAME (not ticker), market cap, PRICE (close),
%CHANGE, TRADES, VOLUME. Tickers are resolved through a name map built from
DOL security names of the same era (symbol + name columns), normalized.
Rows with TRADES == 0 are dropped to preserve pricelist semantics
(equity_prices holds traded rows only). Naira value is NOT in LIST2 →
value_traded NULL.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

PARSER_VERSION = "v1"

ROW_RX = re.compile(
    r"^\s*\d{1,3}\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+"
    r"(-?[\d.]+|-)\s+([\d,]+)\s+([\d,]+)\s*$")
DROP_TOKENS = {"PLC", "PLC.", "LIMITED", "LTD", "LTD.", "THE", "CO", "CO.",
               "COMPANY", "NIG", "NIG.", "NIGERIA", "NIGERIAN", "OF"}


def norm_name(s: str) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    toks = [t for t in s.split() if t not in DROP_TOKENS]
    return " ".join(toks)


def dol_name_map(dol_pdf: str | Path,
                 symbols: frozenset[str]) -> dict[str, str]:
    """normalized security name -> symbol, from one DOL PDF's name column."""
    import pdfplumber
    from .page_layout import rows_from_chars
    out: dict[str, str] = {}
    with pdfplumber.open(dol_pdf) as pdf:
        for page in pdf.pages:
            for row in rows_from_chars(page.chars):
                srt = sorted(row, key=lambda c: c["x0"])
                lead = "".join(c["text"] for c in srt[:20])
                cands = [t for t in symbols if lead.startswith(t)]
                if not cands:
                    continue
                sym = max(cands, key=len)
                name = "".join(c["text"] for c in srt
                               if 90 <= c["x0"] < 195)
                key = norm_name(name)
                if key:
                    out.setdefault(key, sym)
    return out


def parse_list2_pdf(pdf_bytes: bytes, trade_date: str,
                    name_map: dict[str, str]) -> tuple[pd.DataFrame, list[str]]:
    """Returns (df(symbol, trade_date, close, pct_change, trades, volume,
    market_cap, company), unmatched_names). market_cap is NGN millions as
    printed (column header 'MARKET CAP(Nm)') — full-issue capitalization
    (NOT float-adjusted; no shares-outstanding/free-float data exists on
    this platform yet). Only equities pages (skips Bonds/ETP pages lacking
    the equities header)."""
    import pdfplumber

    def _n(s):
        return float(s.replace(",", "")) if s not in ("-", "") else None

    rows, unmatched = [], []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Price List (Equities)" not in text:
                continue
            for line in text.splitlines():
                m = ROW_RX.match(line)
                if not m:
                    continue
                name, mcap, price, pct, trades, vol = m.groups()
                key = norm_name(name)
                sym = name_map.get(key)
                if sym is None:  # prefix fallback (era name drift)
                    hits = {v for k, v in name_map.items()
                            if k.startswith(key) or key.startswith(k)}
                    sym = hits.pop() if len(hits) == 1 else None
                if sym is None:
                    unmatched.append(name)
                    continue
                rows.append(dict(symbol=sym, trade_date=trade_date,
                                 close=_n(price), pct_change=_n(pct),
                                 trades=int(trades.replace(",", "")),
                                 volume=int(vol.replace(",", "")),
                                 market_cap_nm=_n(mcap), company=name))
    df = pd.DataFrame(rows)
    if len(df):
        df = df.drop_duplicates(subset=["symbol"])
    return df, unmatched


def list2_member(zip_path: str | Path) -> bytes | None:
    """The PRICES_LIST2-format PDF inside a pricelist zip (alternate names
    included: 'Price list for X.pdf' etc. — anything whose first page says
    'Price List (Equities)')."""
    import pdfplumber
    z = zipfile.ZipFile(zip_path)
    for n in z.namelist():
        base = Path(n).name.upper()
        if not base.endswith(".PDF") or "GAINERS" in base:
            continue
        try:
            b = z.read(n)
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                if "Price List (Equities)" in (pdf.pages[0].extract_text() or ""):
                    return b
        except Exception:  # noqa: BLE001
            continue
    return None
