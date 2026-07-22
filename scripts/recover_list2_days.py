"""Validate the LIST2 parser on overlap days, then recover the gap days
that have ONLY a LIST2-format pricelist (no PRICES1, no DOL).

  python -u scripts/recover_list2_days.py

Validation (pre-declared): on >= 20 sampled days where BOTH PRICES1-derived
rows (equity_prices) and a LIST2 PDF exist, symbol-mapped LIST2 closes must
match equity_prices closes >= 99%, volume match >= 95% (trades>0 rows).
Only on PASS are the target days ingested (source ngx_list2_v1, conf 0.9,
value_traded NULL). Report: reports/list2_recovery.md
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, coverage  # noqa: E402
from ngxrot.ingest import register_provider  # noqa: E402
from ngxrot.providers.base import DataProvider, ProviderInfo  # noqa: E402
from ngxrot.list2_parser import (PARSER_VERSION, dol_name_map,  # noqa: E402
                                 parse_list2_pdf, list2_member)

con = db.init_db()
symbols = frozenset(r[0] for r in con.execute(
    "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9"))
have = {r[0] for r in con.execute(
    "SELECT DISTINCT trade_date FROM equity_prices WHERE confidence >= 0.9")}
zips = {}
for p in sorted((ROOT / "data/archive/pricelist_zips").glob("2*.zip")):
    zips[p.name[:10]] = p
dols = {}
for p in sorted((ROOT / "data/archive/dol_equities").glob("2*.pdf")):
    dols[p.name[:10]] = p

targets = sorted(d for d in zips if d not in have)
print(f"gap days with a zip (LIST2 candidates): {targets}", flush=True)

# name maps from era-matched DOLs (names drift: 'ZENITH INTERNATIONAL BANK'
# 2016 vs 'ZENITH BANK' 2023). For any date, use the nearest DOL.
dol_dates = sorted(dols)


def name_map_for(d: str) -> dict[str, str]:
    nearest = min(dol_dates, key=lambda x: abs(
        (pd.Timestamp(x) - pd.Timestamp(d)).days))
    return dol_name_map(dols[nearest], symbols)


# ---- validation on overlap days -------------------------------------------
# sample days spread over eras that have BOTH equity_prices rows and a zip
overlap = [d for d in sorted(zips) if d in have]
sample = overlap[:: max(len(overlap) // 20, 1)][:20]
vrows = []
for d in sample:
    b = list2_member(zips[d])
    if b is None:
        continue
    df, unm = parse_list2_pdf(b, d, name_map_for(d))
    if len(df):
        vrows.append(df.assign(n_unmatched=len(unm)))
val = pd.concat(vrows, ignore_index=True)
val = val[val.trades > 0]
px = pd.read_sql(
    "SELECT ticker symbol, trade_date, close px_close, volume px_vol "
    "FROM equity_prices WHERE confidence >= 0.9", con)
m = val.merge(px, on=["symbol", "trade_date"])
close_ok = ((m.close - m.px_close).abs() < 0.005).mean()
# volume comparable only where the px row itself carries volume (DOL-
# recovered days are close-only by design and say nothing about LIST2)
mv = m[m.px_vol.notna()]
vol_ok = ((mv.volume - mv.px_vol).abs() < 1).mean()
print(f"validation: {len(m):,} joined rows over {val.trade_date.nunique()} "
      f"days | close match {close_ok:.4%} | volume match {vol_ok:.4%}",
      flush=True)
verdict = close_ok >= 0.99 and vol_ok >= 0.95 and len(m) >= 1000
lines = [f"# LIST2 Recovery — {date.today().isoformat()}", "",
         f"Validation on {val.trade_date.nunique()} overlap days "
         f"({len(m):,} rows): close match {close_ok:.4%} "
         f"(rule >= 99%), volume match {vol_ok:.4%} (rule >= 95%).",
         f"VERDICT: {'PASS' if verdict else 'FAIL'}", ""]
mm = m[(m.close - m.px_close).abs() >= 0.005]
if len(mm):
    lines += ["Mismatches:", mm[["symbol", "trade_date", "close", "px_close"]]
              .head(30).to_string(index=False), ""]
if not verdict:
    (ROOT / "reports" / "list2_recovery.md").write_text(
        "\n".join(lines), encoding="utf-8")
    sys.exit("LIST2 validation FAILED — not ingesting. See report.")

# ---- ingest target days ----------------------------------------------------
info = ProviderInfo(
    name=f"ngx_list2_{PARSER_VERSION}", kind="exchange_official",
    reliability="primary", base_confidence=0.9,
    notes="Sector-format price list (PRICES_LIST2) recovery for days with "
          "no PRICES1 and no DOL; name-mapped to tickers via era-matched "
          "DOL security names; close/trades/volume; value NULL.")


class _Shim(DataProvider):
    def __init__(self):
        self.info = info


source_id = register_provider(con, _Shim())
tot = 0
for d in targets:
    b = list2_member(zips[d])
    if b is None:
        lines.append(f"- {d}: no LIST2-format member found — NOT recovered")
        continue
    df, unm = parse_list2_pdf(b, d, name_map_for(d))
    df = df[(df.trades > 0) & df.close.notna() & (df.close > 0)]
    if not len(df):
        lines.append(f"- {d}: parsed 0 traded rows — NOT recovered")
        continue
    out = pd.DataFrame({
        "ticker": df.symbol, "trade_date": df.trade_date, "close": df.close,
        "volume": df.volume, "deals": df.trades,
    })
    out["source_id"] = source_id
    out["confidence"] = 0.9
    out["as_of_date"] = date.today().isoformat()
    out.to_sql("equity_prices", con, if_exists="append", index=False)
    con.execute(
        "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
        "trade_date, severity, detail) VALUES (?,?,?,?,?,?)",
        ("single_source_day", "ticker", "ALL", d, "warn",
         f"ngx_list2_v1: {len(out)} rows (close/volume/deals); "
         f"{len(unm)} unmatched names; no second publication for this day"))
    tot += len(out)
    lines.append(f"- {d}: ingested {len(out)} rows "
                 f"({len(unm)} unmatched names)")
con.commit()
lines.append(f"\ntotal rows ingested: {tot}")
(ROOT / "reports" / "list2_recovery.md").write_text(
    "\n".join(lines), encoding="utf-8")
print("\n".join(lines[-12:]), flush=True)

gate = coverage.generate(con)
print(f"coverage dashboard regenerated — gate: "
      f"{'PASS' if gate['gate_pass'] else 'FAIL'} "
      f"(ready years: {gate['ready_years']})", flush=True)
