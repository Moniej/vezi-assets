"""Ingest DOL-derived closes for trading days MISSING from equity_prices
(remediation step 5 — gap-day fallback; runs only after
scripts/validate_dol_prices.py has PASSED).

  python -u scripts/ingest_dol_prices.py

Target days: dates evidenced by an archived pricelist zip or DOL PDF but
absent from equity_prices @ conf>=0.9, restricted to days with a DOL.
Rows: traded securities only (business-done date == file date), close only —
volume/value/deals NULL (the DOL Qty column is the last trade's size, not
daily volume; never fabricate). Source ngx_dol_v1, confidence 0.9.
Each ingested day is logged to data_quality_log (check 'single_source_day',
warn): DOL days have no second NGX publication to cross-validate against,
and an intraday-print variant exists in the wild (observed 2022-03-16,
~1/60 sampled overlap days) that cannot be detected from the file alone.
Report: reports/dol_ingestion.md. Coverage dashboard regenerates at the end.
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, coverage  # noqa: E402
from ngxrot.ingest import register_provider  # noqa: E402
from ngxrot.providers.base import DataProvider, ProviderInfo  # noqa: E402
from ngxrot.dol_price_parser import PARSER_VERSION  # noqa: E402


def work(args):
    pdf_path, symbols = args
    from ngxrot.dol_price_parser import parse_dol_prices
    try:
        df, _ = parse_dol_prices(pdf_path, symbols)
        return pdf_path, df, None
    except Exception as e:  # noqa: BLE001
        return pdf_path, None, f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    val = ROOT / "reports" / "dol_price_validation.md"
    if "VERDICT: PASS" not in val.read_text(encoding="utf-8"):
        sys.exit("dol_price_validation.md is not a PASS — refusing to ingest.")

    con = db.init_db()
    symbols = frozenset(r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9"))
    have = {r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM equity_prices WHERE confidence >= 0.9")}
    by_date = {}
    for p in sorted((ROOT / "data/archive/dol_equities").glob("2*.pdf")):
        by_date[p.name[:10]] = p
    zips = {p.name[:10] for p in
            (ROOT / "data/archive/pricelist_zips").glob("2*.zip")}
    evidenced = set(by_date) | zips
    targets = sorted(d for d in evidenced & set(by_date)
                     if d not in have and d >= "2014-06-30")
    print(f"gap days with a DOL: {len(targets)}", flush=True)

    frames, errs = [], []
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, (str(by_date[d]), symbols)) for d in targets]
        for i, f in enumerate(as_completed(futs), 1):
            path, df, err = f.result()
            if err:
                errs.append(f"{Path(path).name}: {err}")
            elif df is not None and len(df):
                frames.append(df)
            if i % 50 == 0:
                print(f"[{i}/{len(targets)}]", flush=True)
    dol = pd.concat(frames, ignore_index=True)
    good = dol[dol.traded & dol.close.notna() & (dol.close > 0)].copy()
    day_rows = good.groupby("file_date").size()
    print(f"parsed {dol.file_date.nunique()} days | traded rows {len(good):,} "
          f"| rows/day median {day_rows.median():.0f} | errors {len(errs)}",
          flush=True)

    info = ProviderInfo(
        name=f"ngx_dol_{PARSER_VERSION}", kind="exchange_official",
        reliability="primary", base_confidence=0.9,
        notes="Close-only gap-day recovery from Daily Official List PDFs; "
              "draw-order char parser; validated vs pricelist closes "
              "(reports/dol_price_validation.md). volume/value/deals NULL "
              "by design — not recoverable from the DOL.")

    class _Shim(DataProvider):
        def __init__(self):
            self.info = info

    source_id = register_provider(con, _Shim())
    out = pd.DataFrame({
        "ticker": good.symbol, "trade_date": good.file_date,
        "close": good.close,
    })
    out["source_id"] = source_id
    out["confidence"] = 0.9
    out["as_of_date"] = date.today().isoformat()
    out = out.drop_duplicates(subset=["ticker", "trade_date"])
    out.to_sql("equity_prices", con, if_exists="append", index=False)
    for d_, n in day_rows.items():
        con.execute(
            "INSERT INTO data_quality_log (check_name, entity_type, "
            "entity_code, trade_date, severity, detail) VALUES (?,?,?,?,?,?)",
            ("single_source_day", "ticker", "ALL", d_, "warn",
             f"ngx_dol_v1: {int(n)} close-only rows; no second NGX "
             f"publication exists for cross-validation; intraday-print "
             f"risk documented in dol_price_validation.md"))
    con.commit()
    n = con.execute("SELECT COUNT(*), COUNT(DISTINCT trade_date) FROM "
                    "equity_prices WHERE confidence >= 0.9").fetchone()
    print(f"equity_prices now {n[0]:,} rows / {n[1]:,} distinct days @0.9",
          flush=True)

    per_year = good.groupby(good.file_date.str[:4]).agg(
        days=("file_date", "nunique"), rows=("symbol", "size"))
    report = f"""# DOL Gap-Day Ingestion — {date.today().isoformat()}

Source ngx_dol_{PARSER_VERSION} (conf 0.9). Close-only; volume/value/deals
NULL by design (DOL Qty = last trade size, not daily volume). Traded-row
filter: business-done date == file date. Validation gate:
reports/dol_price_validation.md (PASS required before this script runs).

| year | days recovered | rows |
|---|---|---|
{chr(10).join(f"| {y} | {r.days} | {r.rows} |" for y, r in per_year.iterrows())}

Parse errors: {len(errs)}
{chr(10).join(errs[:20])}

Every ingested day carries a data_quality_log 'single_source_day' warning:
no second NGX publication exists for these days, and an undetectable
intraday-print variant was observed on 1 of 60 sampled overlap days
(2022-03-16; ≤ ~3% close deviation on a subset of symbols).
"""
    (ROOT / "reports" / "dol_ingestion.md").write_text(report, encoding="utf-8")
    print(report)

    gate = coverage.generate(con)
    print(f"coverage dashboard regenerated — gate: "
          f"{'PASS' if gate['gate_pass'] else 'FAIL'} "
          f"(ready years: {gate['ready_years']})", flush=True)
