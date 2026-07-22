"""Validate the DOL close-price parser against equity_prices on overlap days
(days where BOTH the DOL archive and validated pricelist rows exist) BEFORE
any gap-day ingestion. Mirrors the pricelist V3 pattern.

  python -u scripts/validate_dol_prices.py [n_days]

Pass rule (pre-declared): traded-row close match rate >= 99% overall and in
every format era (2014-2018 vs 2019+), coverage (pricelist symbols recovered
per day) >= 90% median. Report: reports/dol_price_validation.md
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db  # noqa: E402

N_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def work(args):
    pdf_path, symbols = args
    from ngxrot.dol_price_parser import parse_dol_prices
    try:
        df, ptime = parse_dol_prices(pdf_path, symbols)
        return pdf_path, df, ptime, None
    except Exception as e:  # noqa: BLE001
        return pdf_path, None, None, f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    con = db.connect()
    symbols = frozenset(r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9"))
    have = {r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM equity_prices WHERE confidence >= 0.9")}
    by_date = {}
    for p in sorted((ROOT / "data/archive/dol_equities").glob("2*.pdf")):
        by_date[p.name[:10]] = p          # last file wins for dup dates
    overlap = sorted(d for d in by_date if d in have)
    step = max(len(overlap) // N_DAYS, 1)
    sample = overlap[::step][:N_DAYS]
    print(f"overlap days: {len(overlap)} | sampling {len(sample)} "
          f"({sample[0]}..{sample[-1]})", flush=True)

    frames, errs, ptimes = [], [], {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, (str(by_date[d]), symbols)) for d in sample]
        for f in as_completed(futs):
            path, df, ptime, err = f.result()
            ptimes[Path(path).name[:10]] = ptime
            if err:
                errs.append(f"{Path(path).name}: {err}")
            elif df is not None and len(df):
                frames.append(df)
    dol = pd.concat(frames, ignore_index=True)
    early = {d for d, t in ptimes.items() if t is not None and t < "14:30"}
    dol["early_print"] = dol.file_date.isin(early)

    px = pd.read_sql(
        "SELECT ticker AS symbol, trade_date AS file_date, close AS px_close "
        "FROM equity_prices WHERE confidence >= 0.9", con)
    m = dol[dol.traded & dol.close.notna()].merge(px, on=["symbol", "file_date"])
    m["era"] = (m.file_date < "2019-01-01").map(
        {True: "2014-2018", False: "2019+"})
    m["match"] = (m.close - m.px_close).abs() < 0.005

    lines = [f"# DOL Close-Price Validation — {date.today().isoformat()}", ""]
    lines.append(f"Sampled {len(sample)} overlap days; parse errors: "
                 f"{len(errs)}; traded rows joined: {len(m):,}")
    lines.append(f"Print times: {sum(1 for t in ptimes.values() if t)} of "
                 f"{len(ptimes)} files carry one; intraday prints (<14:30, "
                 f"EXCLUDED from ingestible stats): {sorted(early) or 'none'}")
    m_all = m
    m = m[~m.early_print]
    overall = m.match.mean()
    lines.append(f"\n## Close match (|diff| < 0.005) vs equity_prices")
    lines.append(f"- overall (ingestible, early prints excluded): "
                 f"{overall:.4%}  ({len(m):,} rows)")
    lines.append(f"- incl. early prints (context only): "
                 f"{m_all.match.mean():.4%}  ({len(m_all):,} rows)")
    for era, g in m.groupby("era"):
        lines.append(f"- {era}: {g.match.mean():.4%}  ({len(g):,} rows)")
    mm = m[~m.match]
    if len(mm):
        lines.append(f"\n### Mismatches ({len(mm)}):")
        lines.append(mm[["symbol", "file_date", "close", "px_close"]]
                     .head(40).to_string(index=False))

    # coverage: per sampled day, share of pricelist symbols recovered
    good_days = [d for d in sample if d not in early]
    px_day = px[px.file_date.isin(good_days)].groupby("file_date").symbol.nunique()
    dol_day = (dol[dol.traded & dol.close.notna() & ~dol.early_print]
               .groupby("file_date").symbol.nunique())
    cov = (dol_day / px_day).dropna()
    lines.append(f"\n## Coverage (DOL traded rows / pricelist symbols per day)")
    lines.append(f"- median {cov.median():.1%} | p10 {cov.quantile(.1):.1%} "
                 f"| min {cov.min():.1%} ({cov.idxmin() if len(cov) else '-'})")
    if errs:
        lines.append("\n## Parse errors\n" + "\n".join(errs[:20]))

    era_ok = all(g.match.mean() >= 0.99 for _, g in m.groupby("era"))
    verdict = (overall >= 0.99 and era_ok and cov.median() >= 0.90)
    lines.append(f"\n## VERDICT: {'PASS' if verdict else 'FAIL'} "
                 f"(rule: match >= 99% overall + per era, median coverage >= 90%)")
    report = "\n".join(lines)
    (ROOT / "reports" / "dol_price_validation.md").write_text(
        report, encoding="utf-8")
    print(report)
