"""Validate the EPS/P.E. extractor on a sample of DOL PDFs before any bulk
build (mirrors validate_dol_prices.py's discipline).

  python -u scripts/validate_eps_pe.py [n_days]

Pass rule (pre-declared): among rows where a value is extracted,
EPS x P.E. must be within 3% of the known close (rounding tolerance) for
>= 95% of them, on >= 500 sampled rows. Report: reports/eps_pe_validation.md
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db  # noqa: E402

N_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 80


def work(args):
    pdf_path, symbols, closes = args
    from ngxrot.dol_eps_parser import extract_eps_pe
    try:
        return pdf_path, extract_eps_pe(pdf_path, symbols, closes), None
    except Exception as e:  # noqa: BLE001
        return pdf_path, None, f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    con = db.connect()
    symbols = frozenset(r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9"))
    px = pd.read_sql(
        "SELECT ticker, trade_date, close FROM equity_prices "
        "WHERE confidence >= 0.9", con)
    by_date = {}
    for p in sorted((ROOT / "data/archive/dol_equities").glob("2*.pdf")):
        by_date[p.name[:10]] = p
    have = set(px.trade_date)
    overlap = sorted(d for d in by_date if d in have)
    step = max(len(overlap) // N_DAYS, 1)
    sample = overlap[::step][:N_DAYS]
    print(f"overlap days: {len(overlap)} | sampling {len(sample)} "
          f"({sample[0]}..{sample[-1]})", flush=True)

    close_by_day = {d: dict(zip(g.ticker, g.close))
                    for d, g in px[px.trade_date.isin(sample)]
                    .groupby("trade_date")}

    frames, errs = [], []
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, (str(by_date[d]), symbols,
                                 close_by_day.get(d, {}))) for d in sample]
        for f in as_completed(futs):
            path, df, err = f.result()
            if err:
                errs.append(f"{Path(path).name}: {err}")
            elif df is not None and len(df):
                frames.append(df)
    all_rows = pd.concat(frames, ignore_index=True)

    ok = all_rows.rel_error <= 0.03
    pass_rate = ok.mean()
    lines = [f"# EPS / P.E. Extraction Validation — {date.today().isoformat()}",
            "",
            f"Sampled {len(sample)} days ({sample[0]}..{sample[-1]}), "
            f"{len(all_rows):,} symbol-day rows extracted, {len(errs)} "
            f"file errors.",
            "",
            f"## Cross-check: EPS x P.E. within 3% of known close",
            f"- pass rate: {pass_rate:.2%}  ({int(ok.sum()):,} / {len(all_rows):,})",
            f"- median |rel error| (passing rows): "
            f"{all_rows[ok].rel_error.median():.4f}",
            f"- coverage: {all_rows.symbol.nunique()} symbols represented",
            ]
    bad = all_rows[~ok].sort_values("rel_error", ascending=False)
    if len(bad):
        lines += ["", f"### Worst {min(20, len(bad))} mismatches:",
                  bad.head(20)[["symbol", "file_date", "eps", "pe",
                               "implied_close", "close_used", "rel_error"]]
                  .to_string(index=False)]
    verdict = pass_rate >= 0.95 and len(all_rows) >= 500
    lines += ["", f"## VERDICT: {'PASS' if verdict else 'FAIL'} "
             f"(rule: pass rate >= 95% on >= 500 rows)"]
    report = "\n".join(lines)
    (ROOT / "reports/eps_pe_validation.md").write_text(report, encoding="utf-8")
    print(report)
