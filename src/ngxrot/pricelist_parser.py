"""Parser for NGX daily PRICES tables (PRICES1.pdf inside pricelist ZIPs).

PARSER_VERSION is part of provenance: ingested rows carry a source named
ngx_pricelist_<version> so any future parser fix re-ingests under a new
source and the PIT machinery keeps both vintages.

Method (proven on samples before bulk use):
  - pdfplumber extract_words; lines grouped by y; the header line (contains
    COMPANY + CLOSE + VOLUME) defines column x-boundaries as midpoints
    between consecutive header x0s — tolerant to format drift because the
    map is rebuilt per page from whatever headers exist;
  - rows start with an integer S/N; continuation lines (wrapped company
    names) merge into the previous row;
  - '-' = null; thousands separators stripped; per-row extraction
    confidence = fraction of expected fields parsed, minus OHLC-sanity
    penalty; failures are logged, never fatal;
  - glued-token repair (v2): when wide TRADES/VOLUME/VALUE numbers print
    with no gap pdfplumber emits ONE word ("3,459,46522,480,193,525.60");
    v1 assigned it whole to one column (volume ~1e17..1e25, value NULL).
    v2 splits such cells at the unique point where every part is a valid
    comma-grouped number, VWAP-disambiguating (value/volume within
    [0.25,4]x close) when several splits are comma-valid — same logic that
    restated the 54 historical v1 rows (scripts/restate_glued_volumes.py).
    An unsplittable glue is nulled, never kept: NULL volume beats a
    fabricated 1e17 print.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import pdfplumber

PARSER_VERSION = "v2"  # v1 -> v2: glued TRADES/VOLUME/VALUE token repair

HEADER_FIELDS = {"S/N", "COMPANY", "PCLOSE", "OOPEN", "OPEN", "HIGH", "LOW",
                 "%SPREAD", "OCLOSE", "CLOSE", "CHANGE", "%CHANGE", "TRADES",
                 "VOLUME", "VALUE"}
NUMERIC = {"PCLOSE", "OOPEN", "OPEN", "HIGH", "LOW", "%SPREAD", "OCLOSE",
           "CLOSE", "CHANGE", "%CHANGE", "TRADES", "VOLUME", "VALUE"}


def _num(s: str) -> float | None:
    s = s.strip().replace(",", "")
    if s in ("-", "", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# strict comma-grouped number; glued tokens always fail it because the two
# halves' groups concatenate into a 4+-digit group at the seam
NUM_RE = re.compile(r"\d{1,3}(,\d{3})*(\.\d+)?")
# columns wide enough to glue, in table order
GLUEABLE = ("TRADES", "VOLUME", "VALUE")


def split_glued(tok: str, parts: int) -> list[tuple[str, ...]]:
    """All ways to split ``tok`` into ``parts`` valid comma-grouped numbers.
    Only the last part may carry decimals (VALUE); earlier parts (TRADES,
    VOLUME) must be integers."""
    if parts == 1:
        return [(tok,)] if NUM_RE.fullmatch(tok) else []
    out = []
    for i in range(1, len(tok)):
        head = tok[:i]
        if "." not in head and NUM_RE.fullmatch(head):
            out.extend((head, *rest) for rest in split_glued(tok[i:], parts - 1))
    return out


def _repair_glued(row: dict, cols: list[str]) -> str | None:
    """Split a glued TRADES/VOLUME/VALUE cell in place; return a note if the
    row was touched (split applied, or glue nulled as unrecoverable)."""
    trio = [c for c in GLUEABLE if c in cols]
    txt = {c: row[c].strip() for c in trio if c in row}
    glued = [c for c, t in txt.items()
             if re.fullmatch(r"[\d,]+(\.\d+)?", t) and not NUM_RE.fullmatch(t)]
    if len(glued) != 1:
        return None
    g = glued[0]
    # the glue owns its own column plus every trio column that got no word
    # at all ('-' nulls still emit a word, so they are not swallowed)
    run = sorted(({g} | {c for c in trio if c not in row}), key=trio.index)
    idx = [trio.index(c) for c in run]
    if len(run) < 2 or idx != list(range(idx[0], idx[0] + len(run))):
        row[g] = ""
        return f"unsplittable numeric {txt[g]!r} in {g} — nulled"
    cands = split_glued(txt[g], len(run))
    if run[0] == "TRADES":
        cands = [c for c in cands if float(c[0].replace(",", "")) < 100_000]
    close = _num(row.get("CLOSE", ""))

    def vwap_ok(cand: tuple[str, ...]) -> bool:
        m = dict(zip(run, cand))
        vol = _num(m.get("VOLUME", row.get("VOLUME", "")))
        val = _num(m.get("VALUE", row.get("VALUE", "")))
        return bool(vol and val and close) and 0.25 <= (val / vol) / close <= 4

    if not cands:
        row[g] = ""
        return f"no valid split of glue {txt[g]!r} in {g} — nulled"
    if len(cands) == 1:
        cand, how = cands[0], "unique split"
    else:
        ok = [c for c in cands if vwap_ok(c)]
        if len(ok) != 1:
            row[g] = ""
            return (f"AMBIGUOUS glue {txt[g]!r} in {g} ({len(cands)} splits, "
                    f"{len(ok)} vwap-plausible) — nulled")
        cand, how = ok[0], f"vwap-disambiguated split ({len(cands)} candidates)"
    row.update(zip(run, cand))
    return f"{how} of {txt[g]!r} -> {dict(zip(run, cand))}"


def _lines(words: list[dict], tol: float = 3.0) -> list[list[dict]]:
    lines: dict[int, list] = {}
    for w in words:
        lines.setdefault(round(w["top"] / tol), []).append(w)
    return [sorted(v, key=lambda x: x["x0"]) for _, v in sorted(lines.items())]


def parse_prices_pdf(pdf_bytes: bytes, trade_date: str) -> tuple[pd.DataFrame, list[str]]:
    issues: list[str] = []
    rows: list[dict] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pno, page in enumerate(pdf.pages):
            words = page.extract_words()
            if not words:
                issues.append(f"p{pno}: no text")
                continue
            header, cols = None, None
            for ln in _lines(words):
                texts = {w["text"].upper() for w in ln}
                if "COMPANY" in texts and "CLOSE" in texts and "VOLUME" in texts:
                    header = [w for w in ln if w["text"].upper() in HEADER_FIELDS]
                    header.sort(key=lambda w: w["x0"])
                    xs = [w["x0"] for w in header]
                    bounds = [0.0] + [(xs[i] + header[i - 1]["x1"]) / 2
                                      for i in range(1, len(xs))] + [page.width + 60]
                    cols = [w["text"].upper() for w in header]
                    break
            if cols is None:
                issues.append(f"p{pno}: no header")
                continue

            def col_of(w) -> int:
                cx = (w["x0"] + w["x1"]) / 2
                for i in range(len(cols)):
                    if bounds[i] <= cx < bounds[i + 1]:
                        return i
                return len(cols) - 1

            def flush(row: dict) -> None:
                note = _repair_glued(row, cols)
                if note:
                    issues.append(f"p{pno} [{row.get('COMPANY', '?')}]: "
                                  f"glued-token {note}")
                rows.append(row)

            current: dict | None = None
            header_top = min(w["top"] for w in header)
            for ln in _lines(words):
                if min(x["top"] for x in ln) <= header_top:
                    continue
                cells: dict[int, list[str]] = {}
                for w in ln:
                    cells.setdefault(col_of(w), []).append(w["text"])
                joined = {cols[i]: " ".join(v) for i, v in cells.items()}
                sn = joined.get("S/N", "")
                if re.fullmatch(r"\d{1,4}", sn.strip()):
                    if current:
                        flush(current)
                    current = {"page": pno, **joined}
                elif current and set(joined) <= {"COMPANY", "S/N"}:
                    current["COMPANY"] = (current.get("COMPANY", "") + " "
                                          + joined.get("COMPANY", "")).strip()
                # other non-row lines (footers/sections) ignored
            if current:
                flush(current)
                current = None

    out = []
    for r in rows:
        rec = {"trade_date": trade_date,
               "symbol": (r.get("COMPANY", "").split() or [""])[0],
               "company": r.get("COMPANY", "")}
        n_expected = n_got = 0
        for f in NUMERIC:
            if f in r:
                n_expected += 1
                v = _num(r[f])
                rec[f.lower().replace("%", "pct_")] = v
                if v is not None or r[f].strip() == "-":
                    n_got += 1
        conf = n_got / n_expected if n_expected else 0.0
        h, l, c, o = (rec.get("high"), rec.get("low"), rec.get("close"),
                      rec.get("open"))
        if all(v is not None for v in (h, l, c)) and not (l <= c <= h):
            conf -= 0.25
            rec["ohlc_flag"] = 1
        rec["row_conf"] = round(max(conf, 0.0), 3)
        if rec["symbol"] and rec.get("close") is not None:
            out.append(rec)
    df = pd.DataFrame(out)
    return df, issues


def parse_pricelist_zip(zip_path: Path) -> tuple[pd.DataFrame, list[str]]:
    trade_date = zip_path.name[:10]
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return pd.DataFrame(), [f"{zip_path.name}: bad zip"]
    member = None
    for n in z.namelist():
        base = Path(n).name.upper()
        if re.fullmatch(r"PRICES[_ ]?1.*\.PDF", base):
            member = n
            break
    if member is None:  # fallback: any PRICES pdf that is not the sector LIST2
        for n in z.namelist():
            base = Path(n).name.upper()
            if "PRICES" in base and "LIST2" not in base and base.endswith(".PDF"):
                member = n
                break
    if member is None:  # last resort: sniff content — PRICES1 format has a
        # PCLOSE header regardless of filename ('Pricelist for X.pdf' etc.);
        # LIST2-format files (sector layout, no PCLOSE) stay failures.
        for n in z.namelist():
            base = Path(n).name.upper()
            if not base.endswith(".PDF") or "GAINERS" in base or "LIST2" in base:
                continue
            try:
                with pdfplumber.open(io.BytesIO(z.read(n))) as pdf:
                    txt = pdf.pages[0].extract_text() or ""
            except Exception:  # noqa: BLE001
                continue
            if "PCLOSE" in txt.upper():
                member = n
                break
    if member is None:
        return pd.DataFrame(), [f"{zip_path.name}: no PRICES pdf "
                                f"(members: {[Path(x).name for x in z.namelist()][:4]})"]
    df, issues = parse_prices_pdf(z.read(member), trade_date)
    return df, [f"{zip_path.name}: {i}" for i in issues]
