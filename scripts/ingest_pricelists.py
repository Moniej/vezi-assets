"""Validate parsed pricelist data and ingest to equity_prices (conf 0.9).

  python -u scripts/ingest_pricelists.py

Validation battery (report: reports/pricelist_validation.md):
  V1 internal: row-confidence distribution, OHLC-sanity rate;
  V2 continuity: pclose(t) == close(prev trading day) match rate (catches
     column misalignment / date mis-mapping);
  V3 independent-implementation: parsed PDF rows vs the captured REST JSON
     for the same trade date (two NGX publication paths, field-by-field);
  V4 coverage: symbols/day over time.

Ingestion: append-only, provenance source 'ngx_pricelist_<PARSER_VERSION>'
(v1 = original word-position parse; v2 adds glued VOLUME/VALUE token repair
— see pricelist_parser docstring), as_of = today, confidence 0.9 x row
filter (rows with row_conf < 0.8 excluded and counted). Then: coverage
dashboard + gate regenerate; completion report written.

NOTE staging is version-blind: data/staging/parsed_pricelists CSVs written
before a parser bump are NOT re-parsed (parse_pricelists.py is resume-safe).
Harmless under --delta (old dates are already in the DB and skipped); for a
full re-ingest under a new parser version, clear the staging dir first.
"""

import glob
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, coverage  # noqa: E402
from ngxrot.ingest import register_provider  # noqa: E402
from ngxrot.providers.base import DataProvider, ProviderInfo  # noqa: E402
from ngxrot.pricelist_parser import PARSER_VERSION  # noqa: E402

PARSED = ROOT / "data" / "staging" / "parsed_pricelists"
REPORTS = ROOT / "reports"

files = sorted(PARSED.glob("*.csv"))
print(f"parsed files: {len(files)}", flush=True)
df = pd.concat((pd.read_csv(f, dtype=str) for f in files), ignore_index=True)
NUM_COLS = ["pclose", "oopen", "open", "high", "low", "pct_spread", "oclose",
            "close", "change", "pct_change", "trades", "volume", "value",
            "row_conf", "ohlc_flag"]
for c in NUM_COLS:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
df = df[df.trade_date.astype(str).str.match(r"\d{4}-\d{2}-\d{2}")]
df = df[df.symbol.notna() & df.close.notna()]
if "--delta" in sys.argv:
    # ingest only trade_dates absent from equity_prices: the full run would
    # re-append every row under a new as_of (a fake vintage). Validation
    # still runs over the delta subset.
    _con = db.connect()
    _have = {r[0] for r in _con.execute(
        "SELECT DISTINCT trade_date FROM equity_prices WHERE confidence >= 0.9")}
    new_dates = sorted(set(df.trade_date) - _have)
    print(f"--delta: {len(new_dates)} new trade dates: {new_dates}", flush=True)
    if not new_dates:
        sys.exit("nothing to ingest")
    df = df[df.trade_date.isin(new_dates)]
print(f"total rows: {len(df):,} | dates: {df.trade_date.nunique()} "
      f"({df.trade_date.min()}..{df.trade_date.max()}) | "
      f"symbols: {df.symbol.nunique()}", flush=True)

# ---- V1 internal ----------------------------------------------------------
v1 = {
    "rows": len(df),
    "row_conf_ge_0.9": float((df.row_conf >= 0.9).mean()),
    "row_conf_lt_0.8_excluded": int((df.row_conf < 0.8).sum()),
    "ohlc_flag_rate": float(df.get("ohlc_flag", pd.Series(dtype=float)).notna().mean()),
}

# ---- V2 continuity (markdown-aware) ---------------------------------------
# pclose(t) is the OFFICIAL prev close: it differs from raw prev close on
# ex-dividend/bonus markdown days (a feature, not an error) and where our
# archive has gaps. So: only compare when we hold the market's immediately
# preceding trading day, and split mismatches into DOWN-gaps (markdown-
# consistent, expected) vs UP-gaps (suspicious). Pass rule: suspicious <= 1%.
# Diagnosis (2026-07-17, pre-ingestion): mismatch rate is 1.5% on
# calendar-adjacent transitions but 28-64% on transitions spanning our
# missing archive days — i.e. raw V2 measured ARCHIVE COMPLETENESS (the
# dashboard's job), not parser alignment (V2's job). Rule: evaluate only
# adjacency-clean transitions, cal_gap ∈ {1,3} (next weekday / Fri→Mon);
# cal_gap=2 (midweek holiday or missing day, indistinguishable without an
# independent holiday calendar) and >3 are excluded from the parser test.
market_days = sorted(df.trade_date.unique())
prev_day = {d: market_days[i - 1] for i, d in enumerate(market_days) if i}
sample_syms = df.symbol.value_counts().head(40).index
checks = match = down_gap = up_gap = skipped_gapspan = 0
for s in sample_syms:
    g = (df[df.symbol == s].drop_duplicates("trade_date")
         .set_index("trade_date").sort_index())
    for d, row in g.iterrows():
        pd_ = prev_day.get(d)
        if pd_ is None or pd_ not in g.index or pd.isna(row.pclose):
            continue
        cal_gap = (pd.Timestamp(d) - pd.Timestamp(pd_)).days
        if cal_gap not in (1, 3):
            skipped_gapspan += 1
            continue
        diff = row.pclose - g.loc[pd_, "close"]
        checks += 1
        if abs(diff) < 0.005:
            match += 1
        elif diff < 0:
            down_gap += 1     # markdown-consistent (ex-div/bonus)
        else:
            up_gap += 1       # suspicious
v2 = {"checks": checks, "match_rate": match / checks if checks else None,
      "markdown_consistent_rate": down_gap / checks if checks else None,
      "suspicious_up_rate": up_gap / checks if checks else None,
      "excluded_gap_spanning": skipped_gapspan}

# ---- V3 PDF vs REST same-day ----------------------------------------------
v3 = {"status": "no capture overlap found"}
for cap_dir in sorted(glob.glob(str(ROOT / "data/capture/*")), reverse=True):
    js = sorted(Path(cap_dir).glob("ngx_equities_pricelist_*.json"))
    if not js:
        continue
    rest = pd.DataFrame(json.loads(js[0].read_text(encoding="utf-8")))
    rest["trade_date"] = pd.to_datetime(rest.TradeDate).dt.strftime("%Y-%m-%d")
    td = rest.trade_date.iloc[0]
    pdf_day = df[df.trade_date == td]
    if pdf_day.empty:
        continue
    m = pdf_day.merge(rest, left_on="symbol", right_on="Symbol",
                      suffixes=("_pdf", "_rest"))
    if m.empty:
        continue
    close_ok = float((abs(m.close - m.ClosePrice) < 0.005).mean())
    vol_ok = float((abs(m.volume - m.Volume) < 1).mean())
    val_ok = float((abs(m.value - m.Value) < 1).mean())
    trades_ok = float((abs(m.trades - m.Trades) < 1).mean())
    v3 = {"trade_date": td, "matched_symbols": len(m),
          "close_match": close_ok, "volume_match": vol_ok,
          "value_match": val_ok, "trades_match": trades_ok}
    break

print("V1:", v1, flush=True)
print("V2 continuity:", v2, flush=True)
print("V3 pdf-vs-rest:", v3, flush=True)

# ---- gate the ingest on validation ----------------------------------------
ok = ((v2["suspicious_up_rate"] if v2["suspicious_up_rate"] is not None else 1) <= 0.01
      and (v3.get("close_match", 0) > 0.99 if "close_match" in v3 else True))
if not ok:
    sys.exit("VALIDATION FAILED — not ingesting. Review reports and parser.")

# ---- ingest ----------------------------------------------------------------
con = db.init_db()
info = ProviderInfo(name=f"ngx_pricelist_{PARSER_VERSION}",
                    kind="exchange_official", reliability="primary",
                    base_confidence=0.9,
                    notes=f"Daily PRICES tables parsed from archived pricelist "
                          f"zips; parser {PARSER_VERSION}; word-position method")


class _Shim(DataProvider):
    def __init__(self):
        self.info = info


source_id = register_provider(con, _Shim())
good = df[df.row_conf >= 0.8].copy()
n_zero = int((good.close <= 0).sum())
good = good[good.close > 0]
print(f"excluded {n_zero} zero/negative-close rows (schema CHECK close>0)",
      flush=True)
for t in good.symbol.unique():
    con.execute("INSERT OR IGNORE INTO securities (ticker, name, notes) "
                "VALUES (?, ?, 'auto from ngx_pricelist ingest')", (t, t))
out = pd.DataFrame({
    "ticker": good.symbol, "trade_date": good.trade_date,
    "open": good.open, "high": good.high, "low": good.low,
    "close": good.close, "volume": good.volume,
    "value_traded": good.value, "deals": good.trades,
})
out["source_id"] = source_id
out["confidence"] = 0.9
out["as_of_date"] = date.today().isoformat()
# append-only; PK (ticker,trade_date,source,as_of) dedupes re-runs same day
out = out.drop_duplicates(subset=["ticker", "trade_date"])
out.to_sql("equity_prices", con, if_exists="append", index=False)
con.commit()
n = con.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM equity_prices "
                "WHERE confidence >= 0.9").fetchone()
print(f"ingested: equity_prices now {n[0]:,} rows / {n[1]} tickers @0.9",
      flush=True)

# ---- validation report -----------------------------------------------------
REPORTS.mkdir(exist_ok=True)
(REPORTS / "pricelist_validation.md").write_text(f"""# Pricelist Extraction Validation — {date.today().isoformat()}

Parser: {PARSER_VERSION} (word-position method). Source archive:
data/archive/pricelist_zips ({len(files)} parsed days).

## V1 internal
- rows parsed: {v1['rows']:,}; row_conf >= 0.9: {v1['row_conf_ge_0.9']:.1%}
- rows excluded (<0.8 conf): {v1['row_conf_lt_0.8_excluded']}
- OHLC-sanity flags: {v1['ohlc_flag_rate']:.2%}

## V2 cross-day continuity (40 most-active symbols; adjacency-clean, markdown-aware)
- adjacency-clean checks (cal_gap 1 or 3): {v2['checks']:,}; exact match: {v2['match_rate']:.2%}
- DOWN-gaps (markdown-consistent, ex-div/bonus — expected): {v2['markdown_consistent_rate']:.2%}
- UP-gaps (suspicious): {v2['suspicious_up_rate']:.2%} (pass rule: <= 1%)
- excluded gap-spanning transitions (archive holes/holidays): {v2['excluded_gap_spanning']:,}
- Methodology audit trail (both refinements made BEFORE any ingestion):
  (1) raw 97%-match rule mis-scored legitimate ex-dividend markdowns as
  failures — replaced by up/down decomposition; (2) diagnosis showed 28–64%
  mismatch on transitions spanning missing archive days vs 1.5% on adjacent
  days — archive completeness is measured by the coverage dashboard, so V2
  now evaluates parser alignment on adjacency-clean transitions only.

## V3 independent implementation (PDF vs REST JSON, same day)
{json.dumps(v3, indent=1)}

## Notes
- Price list contains only securities that TRADED each day (no stale rows).
- Symbols follow NGX conventions incl. renames (GUARANTY->GTCO etc.);
  symbol-mapping handled at research-universe level, not by rewriting rows.
- Pending: investing.com spot-check (vendor currently rate-limiting).
""", encoding="utf-8")

gate = coverage.generate(con)
print(f"coverage dashboard regenerated — gate: "
      f"{'PASS' if gate['gate_pass'] else 'FAIL'} "
      f"(ready years: {gate['ready_years']})", flush=True)
