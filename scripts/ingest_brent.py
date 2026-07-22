"""Acquire Brent daily series into macro_series (feeds F12/F1 and H-004).

  python scripts/ingest_brent.py

Sources in preference order:
  1. FRED DCOILBRENTEU (Brent Europe spot, EIA-sourced) — confidence 0.9
  2. stooq.com CB.F continuous Brent futures — confidence 0.6 (aggregator;
     futures splice differs slightly from spot — recorded as caveat)
Raw payload archived under data/staging/macro/. Coverage check before insert:
refuse if <90% weekday coverage over 2012-2026 or any |daily move| > 40%
(a diversified commodity benchmark should never print that outside 2020-04;
that month is whitelisted — negative WTI era saw Brent -47% intraday swings).
"""

import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db  # noqa: E402
from ngxrot.ingest import register_provider  # noqa: E402
from ngxrot.providers.base import DataProvider, ProviderInfo  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging" / "macro"
STAGING.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_fred() -> pd.DataFrame | None:
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                         params={"id": "DCOILBRENTEU"}, headers=UA, timeout=60)
        r.raise_for_status()
        (STAGING / f"fred_brent_{date.today().isoformat()}.csv").write_text(r.text)
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["trade_date", "value"]
        df = df[pd.to_numeric(df.value, errors="coerce").notna()]
        df["value"] = df.value.astype(float)
        return df
    except Exception as e:  # noqa: BLE001
        print(f"FRED failed: {type(e).__name__} {str(e)[:120]}")
        return None


def fetch_stooq() -> pd.DataFrame | None:
    try:
        r = requests.get("https://stooq.com/q/d/l/",
                         params={"s": "cb.f", "i": "d"}, headers=UA, timeout=60)
        r.raise_for_status()
        (STAGING / f"stooq_brent_{date.today().isoformat()}.csv").write_text(r.text)
        df = pd.read_csv(io.StringIO(r.text))
        df = df.rename(columns={"Date": "trade_date", "Close": "value"})[
            ["trade_date", "value"]]
        return df
    except Exception as e:  # noqa: BLE001
        print(f"stooq failed: {type(e).__name__} {str(e)[:120]}")
        return None


df, src_name, conf, notes = None, None, None, None
df = fetch_fred()
if df is not None and len(df) > 1000:
    src_name, conf = "fred_brent_spot", 0.9
    notes = "FRED DCOILBRENTEU (EIA Brent Europe spot)"
else:
    df = fetch_stooq()
    if df is not None and len(df) > 1000:
        src_name, conf = "stooq_brent_futures", 0.6
        notes = ("stooq CB.F continuous Brent futures — futures splice, not "
                 "spot; caveat recorded")
if df is None or src_name is None:
    sys.exit("no Brent source reachable — retry later; DO NOT hand-enter values")

df = df[(df.trade_date >= "2010-01-01")].dropna()
s = df.set_index(pd.DatetimeIndex(pd.to_datetime(df.trade_date))).value
wd = pd.bdate_range(s.index.min(), s.index.max())
coverage = len(s) / len(wd)
ret = s.pct_change().abs()
bad_moves = ret[(ret > 0.40) & ~ret.index.to_period("M").isin(
    [pd.Period("2020-04")])]
print(f"source={src_name} rows={len(df)} coverage={coverage:.1%} "
      f"moves>40%={len(bad_moves)}")
if coverage < 0.90 or len(bad_moves):
    print(bad_moves.head())
    sys.exit("staging checks failed — refusing to ingest")

con = db.init_db()
info = ProviderInfo(name=src_name, kind="vendor",
                    reliability="secondary" if conf < 0.9 else "primary",
                    base_confidence=conf, notes=notes,
                    capabilities=frozenset())


class _Shim(DataProvider):
    def __init__(self):
        self.info = info


source_id = register_provider(con, _Shim())
out = pd.DataFrame({"series_code": "BRENT", "trade_date": df.trade_date,
                    "value": df.value.astype(float)})
out["source_id"] = source_id
out["confidence"] = conf
out["as_of_date"] = date.today().isoformat()
out.to_sql("macro_series", con, if_exists="append", index=False)
con.commit()
print(f"ingested {len(out)} BRENT rows at confidence {conf} "
      f"({out.trade_date.min()}..{out.trade_date.max()})")
