"""Parser for NGX 'Gainers and Losers' PDFs (inside pricelist zips).

These reports are the exchange's own record of every security whose price
moved between two sessions, INCLUDING the officially adjusted base price
when a corporate action re-based the stock (shown in parentheses, e.g.
'NB 53.13 (42.50) 43.90 1.40 3.29' — % change computed off 42.50, and the
±10% band applies to the adjusted base). They are therefore the authority
for classifying raw close-over-close moves > band as official adjustments
vs data errors.

Zip naming is unreliable (a zip dated D may hold the D-1→D or the D→D+1
report), so callers must index by the INTERNAL start/end dates returned.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

DATES_RX = re.compile(
    r"Start Date\s+(\d{2}/\d{2}/\d{4})\s+through\s+End Date\s+"
    r"(\d{2}/\d{2}/\d{4})")
ROW_RX = re.compile(
    r"^\s*\d{1,3}\s+([A-Z0-9\-]+)\s+([\d,]+\.\d{2})"
    r"(?:\s+\(([\d,]+\.\d{2})\))?\s+([\d,]+\.\d{2})\s+"
    r"(-?[\d,]+\.\d{2})\s+(-?[\d.]+)\s*$")


def _iso(d: str) -> str:
    dd, mm, yy = d.split("/")
    return f"{yy}-{mm}-{dd}"


def _n(s: str) -> float:
    return float(s.replace(",", ""))


def parse_gainers_zip(zip_path: str | Path) -> dict | None:
    """Returns dict(start, end, rows={symbol: dict(prev, base, new, pct)})
    or None if the zip has no parseable gainers PDF. base == prev unless an
    official adjustment (parenthesized) was printed."""
    import pdfplumber
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return None
    member = next((n for n in z.namelist()
                   if "GAINERS" in Path(n).name.upper()
                   and n.upper().endswith(".PDF")), None)
    if member is None:
        return None
    try:
        with pdfplumber.open(io.BytesIO(z.read(member))) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:  # noqa: BLE001
        return None
    m = DATES_RX.search(text)
    if not m:
        return None
    start, end = _iso(m.group(1)), _iso(m.group(2))
    rows: dict[str, dict] = {}
    for line in text.splitlines():
        r = ROW_RX.match(line)
        if not r:
            continue
        sym, prev, adj, new, chg, pct = r.groups()
        rows.setdefault(sym, dict(
            prev=_n(prev), base=_n(adj) if adj else _n(prev),
            new=_n(new), pct=float(pct), adjusted=adj is not None))
    return dict(start=start, end=end, rows=rows)
