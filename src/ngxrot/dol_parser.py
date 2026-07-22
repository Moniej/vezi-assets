"""Parser for the DOL (Equities) dividend/ex-date layer.

DOL_PARSER_VERSION provenance as with the pricelist parser.

Extracts per (file, symbol): business-done date, LAST EX-DIV DATE, last
ex-scrip date, dividend date-paid — using a layout-free method:
  - rows located by symbol whitelist (first word of line ∈ known symbols);
  - all dd/mm/yy date-words on the row collected with x-positions;
  - date x-centers across the whole file cluster into <=4 bands (gaps>18pt);
    left→right bands = [business_done, ex_div, ex_sc, date_paid];
  - missing bands per row are fine: dates assign to nearest band center.
Ex-div CALENDAR construction: the set of distinct (symbol, ex_div) values
across sampled files = the ex-dividend date history.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import pdfplumber

DOL_PARSER_VERSION = "v1"
DATE_RX = re.compile(r"\d{2}/\d{2}/\d{2}")


def _dates_in_word(w: dict) -> list[tuple[str, float]]:
    """All dd/mm/yy substrings in a word (dates are often FUSED:
    '18/08/2507/07/96'), each with an interpolated x-center."""
    text = w["text"]
    out = []
    width = w["x1"] - w["x0"]
    for m in DATE_RX.finditer(text):
        frac = (m.start() + 4) / max(len(text), 1)   # center of the 8-char date
        out.append((m.group(0), w["x0"] + frac * width))
    return out


def _norm(d: str, file_year: int) -> str | None:
    dd, mm, yy = d.split("/")
    yr = int(yy)
    century = 2000 if yr <= (file_year % 100) + 1 else 1900
    try:
        return f"{century + yr:04d}-{int(mm):02d}-{int(dd):02d}"
    except ValueError:
        return None


def parse_dol_exdiv(pdf_path: Path, symbols: set[str]) -> pd.DataFrame:
    file_date = pdf_path.name[:10]
    file_year = int(file_date[:4])
    rows = []
    date_xs = []
    per_page_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            lines: dict[int, list] = {}
            for w in words:
                lines.setdefault(round(w["top"] / 3), []).append(w)
            for _, ws in sorted(lines.items()):
                ws = sorted(ws, key=lambda x: x["x0"])
                per_page_lines.append(ws)
                for w in ws:
                    for _, cx in _dates_in_word(w):
                        date_xs.append(cx)
    if not date_xs:
        return pd.DataFrame()

    xs = sorted(date_xs)
    bands = [[xs[0]]]
    for x in xs[1:]:
        if x - bands[-1][-1] > 18:
            bands.append([x])
        else:
            bands[-1].append(x)
    centers = [sum(b) / len(b) for b in bands][:4]
    names = ["bd_date", "ex_div", "ex_sc", "date_paid"][:len(centers)]

    for ws in per_page_lines:
        if not ws or ws[0]["text"] not in symbols:
            continue
        rec = {"symbol": ws[0]["text"], "file_date": file_date}
        for w in ws:
            for dtxt, cx in _dates_in_word(w):
                band = min(range(len(centers)), key=lambda i: abs(centers[i] - cx))
                rec.setdefault(names[band], _norm(dtxt, file_year))
        rows.append(rec)
    return pd.DataFrame(rows)


def parse_bytes(pdf_bytes: bytes, file_date: str, symbols: set[str]) -> pd.DataFrame:
    tmp = io.BytesIO(pdf_bytes)
    # pdfplumber needs a path-like or stream; reuse the path variant via stream
    file_year = int(file_date[:4])
    rows, date_xs, per_page_lines = [], [], []
    with pdfplumber.open(tmp) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            lines: dict[int, list] = {}
            for w in words:
                lines.setdefault(round(w["top"] / 3), []).append(w)
            for _, ws in sorted(lines.items()):
                ws = sorted(ws, key=lambda x: x["x0"])
                per_page_lines.append(ws)
                for w in ws:
                    if DATE_RX.match(w["text"]):
                        date_xs.append((w["x0"] + w["x1"]) / 2)
    if not date_xs:
        return pd.DataFrame()
    xs = sorted(date_xs)
    bands = [[xs[0]]]
    for x in xs[1:]:
        (bands[-1].append(x) if x - bands[-1][-1] <= 18 else bands.append([x]))
    centers = [sum(b) / len(b) for b in bands][:4]
    names = ["bd_date", "ex_div", "ex_sc", "date_paid"][:len(centers)]
    for ws in per_page_lines:
        if not ws or ws[0]["text"] not in symbols:
            continue
        rec = {"symbol": ws[0]["text"], "file_date": file_date}
        for w in ws:
            if DATE_RX.match(w["text"]):
                cx = (w["x0"] + w["x1"]) / 2
                band = min(range(len(centers)), key=lambda i: abs(centers[i] - cx))
                rec.setdefault(names[band], _norm(w["text"], file_year))
        rows.append(rec)
    return pd.DataFrame(rows)
