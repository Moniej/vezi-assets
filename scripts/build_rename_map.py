"""Build the symbol-rename map: detection + verification seed.

  python scripts/build_rename_map.py

Detection rule (deterministic): symbol A's last trading day D_A and symbol
B's first trading day D_B within 15 market days, close prices within 25%,
and A never trades again — emitted as a CANDIDATE. Candidates matching the
independently verified known-renames list are marked verified; the rest
stay 'candidate' (used for reporting only, NOT applied) until verified.
Output: data/reference/symbol_renames.csv
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db  # noqa: E402

# independently documented renames (verify dates against detection below)
KNOWN = [
    ("GUARANTY", "GTCO", "2021 holdco restructuring"),
    ("ACCESS", "ACCESSCORP", "2022 holdco restructuring"),
    ("FBNH", "FIRSTHOLDCO", "2025 rename"),
    ("MOBIL", "11PLC", "2017 rename after Nipco acquisition"),
    ("FO", "ARDOVA", "2019 rename Forte Oil -> Ardova"),
]

con = db.connect()
px = pd.read_sql(
    "SELECT ticker, trade_date, close FROM equity_prices WHERE confidence>=0.9",
    con)
span = px.groupby("ticker").agg(d_first=("trade_date", "min"),
                                d_last=("trade_date", "max"))
market_days = sorted(px.trade_date.unique())
idx = {d: i for i, d in enumerate(market_days)}
last_day = market_days[-1]

rows = []
for old, g in span.iterrows():
    if g.d_last == last_day:
        continue  # still trading; not a disappearance
    for new, h in span.iterrows():
        if new == old or h.d_first <= g.d_last:
            continue
        gap = idx[h.d_first] - idx[g.d_last]
        if 0 < gap <= 15:
            c_old = px[(px.ticker == old) & (px.trade_date == g.d_last)].close.iloc[0]
            c_new = px[(px.ticker == new) & (px.trade_date == h.d_first)].close.iloc[0]
            if abs(c_new / c_old - 1) <= 0.25:
                known = next((k for k in KNOWN if k[0] == old and k[1] == new), None)
                rows.append(dict(
                    old_symbol=old, new_symbol=new,
                    old_last=g.d_last, new_first=h.d_first, gap_days=gap,
                    close_old=c_old, close_new=c_new,
                    status="verified" if known else "candidate",
                    evidence=known[2] if known else
                    "price/timing continuity detection — verify before use"))

df = pd.DataFrame(rows).sort_values(["status", "old_last"],
                                    ascending=[False, True])
# knowns not caught by detection (e.g., trading-gap > 15d) still included
detected = {(r.old_symbol, r.new_symbol) for r in df.itertuples()} if len(df) else set()
extra = []
for old, new, ev in KNOWN:
    if (old, new) not in detected and old in span.index and new in span.index:
        extra.append(dict(old_symbol=old, new_symbol=new,
                          old_last=span.loc[old, "d_last"],
                          new_first=span.loc[new, "d_first"],
                          gap_days=None, close_old=None, close_new=None,
                          status="verified", evidence=ev + " (manual; detection missed)"))
if extra:
    df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

out = ROOT / "data" / "reference" / "symbol_renames.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"rename map: {len(df)} rows "
      f"({(df.status == 'verified').sum()} verified, "
      f"{(df.status == 'candidate').sum()} candidates)")
print(df.to_string(index=False, max_colwidth=40))
