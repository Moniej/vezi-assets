"""DAL demonstration: providers -> validated ingest -> confidence-aware PIT reads.

Proves five things:
  1. the same ingest() call works for any provider (synthetic here; CSV and
     future web/vendor providers plug into the identical path);
  2. contract validation rejects malformed rows and logs them, never repairs;
  3. the future-dating guard rejects observations dated after as_of;
  4. every stored row carries source + confidence lineage;
  5. min_confidence filtering isolates synthetic (0.0) data — a robustness
     floor of 0.5 sees NOTHING until real data arrives, by construction.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ngxrot import db, ingest  # noqa: E402
from ngxrot.providers import CSVProvider, SyntheticProvider  # noqa: E402
from ngxrot.providers.base import DataProvider, ProviderInfo  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ngx.sqlite"
DB_PATH.unlink(missing_ok=True)
con = db.init_db(DB_PATH)

AS_OF = "2026-07-15"
syn = SyntheticProvider()

print("=== 1. Uniform ingestion across datasets (SyntheticProvider) ===")
reports = [
    ingest.ingest(con, syn, "index_levels", as_of=AS_OF,
                  index_codes=None, start="2016-01-01", end="2026-06-30"),
    ingest.ingest(con, syn, "equity_prices", as_of=AS_OF,
                  tickers=None, start="2016-01-01", end="2026-06-30"),
    ingest.ingest(con, syn, "corporate_actions", as_of=AS_OF, tickers=None),
    ingest.ingest(con, syn, "index_membership", as_of=AS_OF, index_codes=None),
    ingest.ingest(con, syn, "events", as_of=AS_OF,
                  start="2016-01-01", end="2026-06-30"),
]
for r in reports:
    print("  ", r)

print("\n=== 2+3. Validation & future-dating guards (malicious CSV provider) ===")
bad_dir = ROOT / "data" / "csv_demo" / "index_levels"
bad_dir.mkdir(parents=True, exist_ok=True)
pd.DataFrame({
    "index_code": ["NGXBNK", "NGXBNK", "NGXBNK", "", "NGXBNK", "NGXBNK"],
    "trade_date": ["2026-07-10", "2026-07-10", "not-a-date", "2026-07-11",
                   "2026-07-20", "2026-07-13"],
    "close_value": ["141000.5", "141000.5", "141200", "140900", "150000", "-5"],
}).to_csv(bad_dir.parent / "index_levels" / "sample.csv", index=False)
# rows: ok / duplicate / bad date / blank code / FUTURE-DATED vs as_of / negative
csvp = CSVProvider(bad_dir.parent, name="user_csv_demo")
rep = ingest.ingest(con, csvp, "index_levels", as_of=AS_OF,
                    index_codes=["NGXBNK"], start="2026-01-01", end="2026-12-31")
print("  ", rep)
dq = pd.read_sql("SELECT check_name, entity_code, trade_date, severity FROM data_quality_log "
                 "WHERE check_name LIKE 'ingest_reject%'", con)
print(dq.to_string(index=False))

print("\n=== 4. Lineage on stored rows ===")
print(pd.read_sql("""
    SELECT s.name AS source, s.reliability, il.confidence, COUNT(*) AS rows_,
           MIN(il.trade_date) AS first_date, MAX(il.trade_date) AS last_date
    FROM index_levels il JOIN sources s USING (source_id)
    GROUP BY s.name ORDER BY s.name""", con).to_string(index=False))

print("\n=== 5. Confidence floor isolates synthetic data ===")
for floor in (0.0, 0.4, 0.5):
    n = len(db.index_levels_asof(con, "2026-07-15", ["NGXBNK"], min_confidence=floor))
    print(f"   min_confidence={floor:.1f}: {n:>5} NGXBNK rows visible "
          f"({'synthetic + csv' if floor == 0.0 else 'csv only' if floor == 0.4 else 'nothing — real data required'})")

print("\n=== Provider registry (capability matrix) ===")
from ngxrot.providers import (NGXWebProvider, InvestingComProvider,  # noqa: E402
                              TradingViewProvider, WebArchiveProvider)
rows = []
for p in (syn, csvp, NGXWebProvider(), InvestingComProvider(),
          TradingViewProvider(), WebArchiveProvider()):
    i = p.info
    implemented = type(p).fetch_index_levels is not DataProvider.fetch_index_levels \
        or "index_levels" not in i.capabilities
    rows.append(dict(provider=i.name, kind=i.kind, base_conf=i.base_confidence,
                     capabilities=",".join(sorted(i.capabilities)) or "-",
                     status="implemented" if isinstance(p, (SyntheticProvider, CSVProvider))
                            else "stub (pending feasibility probe)"))
print(pd.DataFrame(rows).to_string(index=False))

print("\n=== Synthetic sanity: regime shape (annualised index returns, conf=0.0 data) ===")
lv = db.index_levels_asof(con, "2026-06-30")
pv = lv.pivot(index="trade_date", columns="index_code", values="close_value")
for a, b, label in [("2016-01-04", "2022-12-30", "pre-2023"),
                    ("2023-01-02", "2024-12-31", "2023-24 shock"),
                    ("2025-01-02", "2026-06-30", "2025-26 bull")]:
    w = pv.loc[a:b]
    yrs = len(w) / 252
    ann = (w.iloc[-1] / w.iloc[0]) ** (1 / yrs) - 1
    top = ann.drop("NGXASI").sort_values(ascending=False)
    print(f"   {label:14s} ASI {ann['NGXASI']:+7.1%} | best {top.index[0]} "
          f"{top.iloc[0]:+7.1%} | worst {top.index[-1]} {top.iloc[-1]:+7.1%}")
print("\nNOTE: all figures above are synthetic (confidence 0.0) — plumbing test only.")
