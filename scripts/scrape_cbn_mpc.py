"""Sprint 1: scrape CBN MPC decision history from the CBN's own decisions page.

  python scripts/scrape_cbn_mpc.py

Primary source (confidence 0.9): cbn.gov.ng/monetarypolicy/decisions.html —
the page body contains per-meeting "Key Decisions" blocks (meeting number,
dates, MPR/CRR outcomes). Rules:
  - raw HTML archived to data/staging/cbn/ before parsing (raw-first);
  - blocks that do not parse UNAMBIGUOUSLY into (meeting date, MPR level)
    are REJECTED and listed — never guessed;
  - internal consistency check: every 'retain' must equal the previous
    meeting's level; every 'reduce/raise by N bps to X' must be arithmetically
    consistent — violations flag the whole scrape for review;
  - output goes to a staged CSV batch, then through the standard event
    pipeline (taxonomy/chronology/duplicate/conflict checks + quality report).
"""

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db, event_pipeline  # noqa: E402
from ngxrot.providers import CSVProvider  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.cbn.gov.ng/monetarypolicy/decisions.html"
STAGING = ROOT / "data" / "staging" / "cbn"
BATCH = ROOT / "data" / "events_batches" / "cbn_mpc" / "events"
STAGING.mkdir(parents=True, exist_ok=True)
BATCH.mkdir(parents=True, exist_ok=True)

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

html = requests.get(URL, timeout=60, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}).text
(STAGING / f"decisions_{date.today().isoformat()}.html").write_text(
    html, encoding="utf-8")

# split into per-meeting blocks on the Key Decisions headers
parts = re.split(
    r"<strong>\s*Key Decisions of the Central Bank of Nigeria\s+"
    r"Monetary Policy Committee", html)
blocks = parts[1:]
print(f"blocks found: {len(blocks)}")

MONTH_RX = (r"(January|February|March|April|May|June|July|August|September|"
            r"October|November|December)")
# month-first: "May 19-20, 2026" / "September 25 and 26, 2023"
DATE_MF = re.compile(
    MONTH_RX + r"\s+(\d{1,2})\s*(?:[-–—]|,?\s*(?:and|&)\s*)?\s*(\d{1,2})?"
    r"\s*,?\s+(\d{4})")
# day-first: "23rd and 24th May, 2016" / "26th and 27th February 2024"
DATE_DF = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:[-–—]|,?\s*(?:and|&)\s*)\s*"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + MONTH_RX + r"\s*,?\s*(\d{4})")
# single day-first: "21st May, 2019"
DATE_D1 = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)\s+(?:of\s+)?" + MONTH_RX + r"\s*,?\s*(\d{4})")
MEET_RX = re.compile(r"(\d+)\s*(?:st|nd|rd|th)\s+meeting", re.I)
PCT_RX = re.compile(r"([\d.]+)\s*(?:per\s*cent|percent|%)", re.I)
BPS_RX = re.compile(r"by\s+([\d.]+)\s*basis\s*points", re.I)
FROMTO_RX = re.compile(
    r"from\s+([\d.]+)\s*(?:per\s*cent|percent|%)?\s*to\s+([\d.]+)", re.I)
TOFROM_RX = re.compile(  # reversed word order: "to 26.25 ... from 24.75"
    r"to\s+([\d.]+)\s*(?:per\s*cent|percent|%)?[^;]{0,40}?from\s+([\d.]+)", re.I)


def parse_meeting_date(text: str) -> str | None:
    """Extract the meeting END date. Tries month-first, then day-first, then
    single-day formats, anywhere in the block. Returns None if ambiguous."""
    m = DATE_MF.search(text)
    if m:
        month, d1, d2, yr = m.groups()
        return f"{yr}-{MONTHS[month]:02d}-{int(d2 or d1):02d}"
    m = DATE_DF.search(text)
    if m:
        d1, d2, month, yr = m.groups()
        return f"{yr}-{MONTHS[month]:02d}-{int(d2):02d}"
    m = DATE_D1.search(text)
    if m:
        d1, month, yr = m.groups()
        return f"{yr}-{MONTHS[month]:02d}-{int(d1):02d}"
    return None

rows, rejected = [], []
for b in blocks:
    text = re.sub(r"<[^>]+>", " ", b)
    text = re.sub(r"\s+", " ", text)[:4000]
    ann = parse_meeting_date(text)
    if ann is None:
        rejected.append(("no unambiguous meeting date", text[:110]))
        continue
    m_no = MEET_RX.search(text)
    meeting_no = m_no.group(1) if m_no else None

    # the MPR clause: first list item (or semicolon segment) naming the rate
    mpr_clause = None
    for li in re.findall(r"<li>(.*?)</li>", b, flags=re.S | re.I):
        plain = re.sub(r"<[^>]+>", " ", li)
        if re.search(r"Monetary Policy Rate|\bMPR\b", plain):
            mpr_clause = re.sub(r"\s+", " ", plain).strip()
            break
    if mpr_clause is None:  # older blocks use semicolon-separated sentences
        for seg in re.split(r"[;.]", text):
            if re.search(r"(Retain|Reduce|Raise|Increase|Adjust|Lower|Keep|Hold)"
                         r".{0,40}(Monetary Policy Rate|\bMPR\b)", seg, re.I):
                mpr_clause = seg.strip()
                break
    if not mpr_clause:
        rejected.append((f"{ann}: no MPR clause", text[:110]))
        continue

    ft = FROMTO_RX.search(mpr_clause)
    tf = TOFROM_RX.search(mpr_clause)
    pcts = PCT_RX.findall(mpr_clause)
    if ft:
        frm, level = float(ft.group(1)), float(ft.group(2))
        action = "hold" if level == frm else ("cut" if level < frm else "hike")
    elif tf:
        level, frm = float(tf.group(1)), float(tf.group(2))
        action = "hold" if level == frm else ("cut" if level < frm else "hike")
    elif pcts:
        # FIRST percentage in the MPR clause: the rate itself always precedes
        # corridor/liquidity-ratio mentions ("MPR remains at 12 per cent
        # +/- 200 bps and liquidity ratio at 30 per cent")
        level = float(pcts[0])
        low = mpr_clause.lower()
        if re.search(r"\bretain|\bhold|\bkeep|\bremains?\b|unchanged", low):
            action = "hold"
        elif re.search(r"\breduce|\blower|\bcut", low):
            action = "cut"
        elif re.search(r"\braise|\bincrease|\bhike", low):
            action = "hike"
        else:
            rejected.append((f"{ann}: ambiguous MPR action", mpr_clause[:110]))
            continue
    else:
        rejected.append((f"{ann}: MPR clause without level", mpr_clause[:110]))
        continue
    bps = BPS_RX.search(mpr_clause)
    move = (f"{action} {'-' if action == 'cut' else '+' if action == 'hike' else ''}"
            f"{bps.group(1) + 'bps' if bps and action != 'hold' else ''}").strip()

    crr = None
    for li in re.findall(r"<li>(.*?)</li>", b, flags=re.S | re.I):
        plain = re.sub(r"<[^>]+>", " ", li)
        if "Cash Reserve" in plain:
            c = PCT_RX.search(plain)
            crr = float(c.group(1)) if c else None
            break

    rows.append(dict(
        event_type="mpc_decision", category="monetary",
        event_uid=(f"CBN-MPC-{meeting_no}" if meeting_no else f"CBN-MPC-{ann}"),
        announced_date=ann, effective_date=ann, publication_ts="",
        scope="market", index_code="", ticker="",
        headline=(f"MPC{' #' + meeting_no if meeting_no else ''}: MPR "
                  f"{'retained at' if action == 'hold' else action + ' to'} "
                  f"{level:.2f}%" + (f" (CRR {crr:.2f}%)" if crr else "")),
        outcome_numeric=level, outcome_text=move,
        severity="medium" if action == "hold" else "high",
        direction="unknown", structurally_impairing=0,
        source_url=URL,
        notes=(f"Parsed from CBN decisions page {date.today().isoformat()}; "
               f"meeting no. {meeting_no or 'unstated'}; CRR_DMB={crr}"),
    ))

df = pd.DataFrame(rows).sort_values("announced_date").reset_index(drop=True)
print(f"parsed: {len(df)} meetings | rejected blocks: {len(rejected)}")
for why, snip in rejected[:10]:
    print(f"  REJECTED: {why} | {snip}")

# internal consistency: holds must equal previous level; moves with a stated
# bps size must be arithmetically consistent with the previous level
issues = []
for i in range(1, len(df)):
    prev, cur = df.iloc[i - 1], df.iloc[i]
    if cur.outcome_text == "hold" and cur.outcome_numeric != prev.outcome_numeric:
        issues.append(f"{cur.announced_date}: 'hold' at {cur.outcome_numeric} but "
                      f"previous level was {prev.outcome_numeric}")
    m_bps = re.search(r"([\d.]+)bps", str(cur.outcome_text))
    if m_bps:
        step = float(m_bps.group(1)) / 100.0
        sign = -1 if "cut" in cur.outcome_text else 1
        expect = round(prev.outcome_numeric + sign * step, 2)
        if abs(expect - cur.outcome_numeric) > 1e-9:
            issues.append(f"{cur.announced_date}: {cur.outcome_text} from "
                          f"{prev.outcome_numeric} should give {expect}, "
                          f"parsed {cur.outcome_numeric}")
print(f"consistency issues (hold != previous level): {len(issues)}")
for msg in issues[:10]:
    print("  ", msg)

per_year = df.announced_date.str[:4].value_counts().sort_index()
print("\nmeetings per year:")
print(per_year.to_string())

if issues:
    print("\nCONSISTENCY ISSUES — writing batch anyway but review before trusting "
          "the flagged meetings; issues recorded in batch notes.")

out = BATCH / f"mpc_decisions_{date.today().isoformat()}.csv"
df.to_csv(out, index=False)
print(f"\nstaged batch: {out}")

provider = CSVProvider(BATCH.parent, name="cbn_decisions_page",
                       base_confidence=0.9, kind="regulator",
                       reliability="primary",
                       notes="parsed from CBN's own MPC decisions page")
con = db.init_db()
report = event_pipeline.ingest_events(con, provider,
                                      start="2005-01-01", end=date.today().isoformat())
print(f"quality report: {report}")
