"""Sprint 1: ingest CBN MPC meeting events from the CBN documents API.

  python scripts/ingest_mpc.py

Source: https://www.cbn.gov.ng/api/GetAllDocuments?type=mpc (probed
2026-07-16; primary, exchange... central-bank-official). Raw catalogue is
archived before parsing. This pass ingests MEETING EVENTS ONLY:
announced_date = meeting end date parsed from the communique title;
outcome_numeric (MPR level) requires per-PDF extraction and is a separate,
later pass — unknown stays unknown, per mandate.

Titles that cannot be date-parsed are written to
data/staging/mpc_unparsed.csv for manual verification — never guessed.
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db, event_pipeline  # noqa: E402
from ngxrot.providers import CSVProvider  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def parse_meeting_end(title: str) -> str | None:
    """Extract the LAST (day, month, year) mentioned — the meeting end date.

    Handles: 'held on Tuesday, 24th February 2026', 'held on May 19th and
    20th May 2026', 'held on Monday 25th and Tuesday 26th March, 2019',
    'July 24 and 25, 2023' etc. Returns ISO date or None (never guesses).
    """
    t = title.lower().replace(",", " ")
    years = re.findall(r"\b(20\d\d)\b", t)
    if not years:
        return None
    year = int(years[-1])
    month_hits = [(m.start(), MONTHS[m.group(0)]) for m in
                  re.finditer("|".join(MONTHS), t)]
    if not month_hits:
        return None
    days = [(m.start(), int(m.group(1))) for m in
            re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", t)
            if 1 <= int(m.group(1)) <= 31]
    if not days:
        return None
    # candidate dates: each day paired with the nearest month mention
    candidates = []
    for dpos, dnum in days:
        mpos, mnum = min(month_hits, key=lambda mh: abs(mh[0] - dpos))
        try:
            candidates.append(date(year, mnum, dnum))
        except ValueError:
            continue
    return max(candidates).isoformat() if candidates else None


print("fetching CBN documents catalogue (type=mpc)...")
r = requests.get("https://www.cbn.gov.ng/api/GetAllDocuments",
                 params={"type": "mpc"}, headers=UA, timeout=90)
r.raise_for_status()
items = r.json()
(STAGING / "cbn_api").mkdir(parents=True, exist_ok=True)
(STAGING / "cbn_api" / f"mpc_catalogue_{date.today().isoformat()}.json"
 ).write_text(json.dumps(items), encoding="utf-8")
print(f"catalogue: {len(items)} documents archived")

def _is_mpc_communique(it: dict) -> bool:
    """Titles vary across 25 years ('Central Bank of Nigeria Communique
    No...', 'Communique No 45 of the Monetary Policy Committee...'). Accept
    any communique tied to MPC/monetary policy; exclude personal statements
    and other committees (FSRCC etc. lack the MPC linkage)."""
    title, ref = str(it.get("title", "")), str(it.get("refNo", ""))
    if not re.search(r"communiqu[eé]", title, re.I):
        return False
    if re.search(r"personal statement", title, re.I):
        return False
    return bool(re.search(r"monetary policy|mpc", title + ref, re.I))


comms = [it for it in items if _is_mpc_communique(it)]
print(f"MPC communiques (excl. personal statements): {len(comms)}")

rows, unparsed = [], []
for it in comms:
    end = parse_meeting_end(it["title"])
    ref = it.get("refNo", "")
    if end is None:
        unparsed.append(it)
        continue
    rows.append(dict(
        event_type="mpc_decision", category="monetary",
        announced_date=end, effective_date=end,
        publication_ts="", scope="market", index_code="", ticker="",
        headline=it["title"][:200], outcome_numeric="", outcome_text="",
        severity="high", direction="unknown", structurally_impairing=0,
        source_url="https://www.cbn.gov.ng" + str(it.get("link", "")).replace(" ", "%20"),
        notes=f"refNo={ref}; documentDate={it.get('documentDate')}; "
              f"meeting end date parsed from title; MPR level pending PDF "
              f"extraction (unknown, not guessed)"))

if unparsed:
    pd.DataFrame(unparsed).to_csv(STAGING / "mpc_unparsed.csv", index=False)
    print(f"UNPARSED titles -> staging/mpc_unparsed.csv: {len(unparsed)}")
    for u in unparsed[:5]:
        print("   ?", u["title"][:110])

df = pd.DataFrame(rows).sort_values("announced_date")
# dedupe repeated uploads of the same communique (same meeting date)
df = df.drop_duplicates(subset=["announced_date"], keep="first")
per_year = df.announced_date.str[:4].value_counts().sort_index()
print("\nmeetings per year parsed:")
print(per_year.to_string())

batch_dir = ROOT / "data" / "events_mpc" / "events"
batch_dir.mkdir(parents=True, exist_ok=True)
df.to_csv(batch_dir / f"mpc_meetings_{date.today().isoformat()}.csv", index=False)

provider = CSVProvider(ROOT / "data" / "events_mpc",
                       name="cbn_documents_api", base_confidence=0.9)
con = db.init_db()
report = event_pipeline.ingest_events(con, provider,
                                      start="2005-01-01", end="2026-07-16")
print(f"\nquality report: {report}")
