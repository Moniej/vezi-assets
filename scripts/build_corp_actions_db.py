"""Stage 2: Corporate Actions Database — archive originals, extract structure.

  python scripts/build_corp_actions_db.py [--classes dividend,rights_capital,bonus_split]

Pipeline (idempotent; re-runnable as extraction improves):
  A. ARCHIVE: download every selected filing PDF once, permanently, to
     data/archive/xissuer_docs/<sp_id>_<filename>. Originals are never
     re-fetched or modified — extraction can always be redone.
  B. PARSE: pypdf text extraction; NGX-convention regexes for dividend per
     share (naira or kobo), qualification date, closure of register,
     payment date, bonus ratio, rights terms.
  C. EMIT: data/staging/xissuer/corporate_actions_extracted.csv with one row
     per filing: identifiers, announcement ts (list Created), every field
     found, and extraction_fields (count) as a per-row quality marker.

Rows are NOT ingested to the research DB here — promotion to evidence grade
happens only after sample validation against independently verified anchors.
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive" / "xissuer_docs"
STAGING = ROOT / "data" / "staging" / "xissuer"
ARCHIVE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

CLASSES = (sys.argv[sys.argv.index("--classes") + 1].split(",")
           if "--classes" in sys.argv
           else ["dividend", "rights_capital", "bonus_split"])

cal = pd.read_csv(STAGING / "corporate_actions_calendar_classified.csv")
todo = cal[cal.doc_class.isin(CLASSES)].copy()
print(f"selected {len(todo)} filings in classes {CLASSES}")

# ---------------------------------------------------------------- A. archive
n_dl, n_cached, n_fail = 0, 0, 0
paths = {}
for _, r in todo.iterrows():
    url = str(r.url)
    fname = f"{int(r.sp_id)}_{url.rsplit('/', 1)[-1][:120]}"
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", fname)
    p = ARCHIVE / fname
    if p.exists() and p.stat().st_size > 500:
        paths[r.sp_id] = p
        n_cached += 1
        continue
    try:
        resp = requests.get(url, headers=UA, timeout=60)
        resp.raise_for_status()
        p.write_bytes(resp.content)
        paths[r.sp_id] = p
        n_dl += 1
        time.sleep(0.35)
    except Exception:  # noqa: BLE001
        n_fail += 1
print(f"archive: {n_dl} downloaded, {n_cached} cached, {n_fail} failed")

# ---------------------------------------------------------------- B. parse
MONTH = (r"(?:January|February|March|April|May|June|July|August|September|"
         r"October|November|December)")
DATE = (rf"((?:\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTH}|{MONTH}\s+"
        rf"\d{{1,2}}(?:st|nd|rd|th)?)\s*,?\s*\d{{4}})")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def norm_date(s: str) -> str | None:
    m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH})\s*,?\s*(\d{{4}})", s)
    if not m:
        m2 = re.search(rf"({MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(\d{{4}})", s)
        if not m2:
            return None
        mo, d, y = m2.groups()
        return f"{y}-{MONTHS[mo]:02d}-{int(d):02d}"
    d, mo, y = m.groups()
    return f"{y}-{MONTHS[mo]:02d}-{int(d):02d}"


def extract(text: str) -> dict:
    t = re.sub(r"\s+", " ", text)
    out = {}
    m = re.search(r"(?:dividend of|dividend per share of|DPS of)\s*"
                  r"(?:N|NGN|=N=|₦)\s*([\d.]+)", t, re.I)
    if not m:
        m = re.search(r"(?:N|NGN|=N=|₦)\s*([\d.]+)\s*(?:per share|per ordinary share)"
                      r"[^.]{0,60}dividend|dividend[^.]{0,80}?(?:N|NGN|=N=|₦)"
                      r"\s*([\d.]+)\s*(?:per share|per ordinary share)", t, re.I)
    if m:
        out["dividend_per_share"] = float(next(g for g in m.groups() if g))
    else:
        k = re.search(r"([\d.]+)\s*[Kk]obo\s*(?:per share|per ordinary share)?"
                      r"[^.]{0,50}dividend|dividend[^.]{0,80}?([\d.]+)\s*[Kk]obo", t)
        if k:
            out["dividend_per_share"] = float(next(g for g in k.groups() if g)) / 100.0
    for field, pat in [
        ("qualification_date", rf"[Qq]ualification\s*[Dd]ate\s*[:\-]?\s*{DATE}"),
        ("closure_date", rf"[Cc]losure\s*(?:of\s*[Rr]egister)?\s*(?:[Dd]ate)?\s*[:\-]?\s*{DATE}"),
        ("payment_date", rf"[Pp]ayment\s*[Dd]ate\s*[:\-]?\s*{DATE}"),
        ("agm_date", rf"(?:AGM|[Aa]nnual [Gg]eneral [Mm]eeting)[^.]{{0,80}}?{DATE}"),
    ]:
        mm = re.search(pat, t)
        if mm:
            d = norm_date(mm.group(1))
            if d:
                out[field] = d
    b = re.search(r"[Bb]onus\s*(?:issue\s*)?of\s*(?:one|1)\s*(?:new\s*)?share.{0,40}?"
                  r"for\s*(?:every\s*)?(\w+|\d+)", t)
    if b:
        out["bonus_terms"] = b.group(0)[:80]
    ri = re.search(r"[Rr]ights\s*[Ii]ssue\s*of[^.]{0,120}", t)
    if ri:
        out["rights_terms"] = ri.group(0)[:120]
    return out


rows, n_noext = [], 0
for _, r in todo.iterrows():
    p = paths.get(r.sp_id)
    if p is None:
        continue
    try:
        text = " ".join((pg.extract_text() or "") for pg in PdfReader(p).pages[:6])
    except Exception:  # noqa: BLE001
        text = ""
    if len(text.strip()) < 40:
        n_noext += 1
        fields = {}
    else:
        fields = extract(text)
    rows.append(dict(sp_id=r.sp_id, symbol=r.symbol, company=r.company,
                     doc_class=r.doc_class, announced_ts=r.created,
                     url=r.url, archive_file=p.name,
                     extraction_fields=len(fields), **fields))

df = pd.DataFrame(rows)
out_path = STAGING / "corporate_actions_extracted.csv"
df.to_csv(out_path, index=False)

print(f"\nparsed {len(df)} docs | no-text (likely scanned): {n_noext}")
if len(df):
    have = df[df.extraction_fields > 0]
    print(f"docs with >=1 field: {len(have)} ({len(have)/len(df):.0%})")
    for c in ("dividend_per_share", "qualification_date", "closure_date",
              "payment_date", "bonus_terms", "rights_terms"):
        if c in df.columns:
            print(f"  {c:20s} {df[c].notna().sum():4d}")
    div = df[df.get("dividend_per_share").notna()] if "dividend_per_share" in df.columns else df.iloc[0:0]
    print(f"\ndividend rows with DPS + >=1 date: "
          f"{len(div[div[['qualification_date','closure_date','payment_date']].notna().any(axis=1)]) if len(div) else 0}")
print(f"extracted table: {out_path}")
