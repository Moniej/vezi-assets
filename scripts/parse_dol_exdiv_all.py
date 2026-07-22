"""Parse the ex-dividend layer from ALL archived DOL PDFs (char-level method,
validated 2026-07-18: GTCO anchor perfect + 28/28 clean on 10 symbols x 3 yrs).

  python -u scripts/parse_dol_exdiv_all.py

Parallel, resume-safe. Output: data/staging/dol_exdiv/<date>.csv with
(symbol, file_date, bd_date, ex_div, ex_sc, date_paid_band).
The ex_div band (leftmost non-business date band) is the validated field —
it records CLOSURE-OF-REGISTER dates (= markdown-adjacent). date_paid_band
semantics unverified in newer formats; carried but flagged.
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ARCHIVE = ROOT / "data" / "archive" / "dol_equities"
OUT = ROOT / "data" / "staging" / "dol_exdiv"
OUT.mkdir(parents=True, exist_ok=True)


def work(args):
    pdf_path, symbols = args
    import pdfplumber
    from ngxrot.page_layout import rows_from_chars, extract_dates
    p = Path(pdf_path)
    file_date = p.name[:10]
    fy = int(file_date[:4])

    def norm(d):
        dd, mm, yy = d.split("/")
        c = 2000 if int(yy) <= (fy % 100) + 1 else 1900
        try:
            return f"{c + int(yy):04d}-{int(mm):02d}-{int(dd):02d}"
        except ValueError:
            return None

    recs, all_x = [], []
    try:
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                for row in rows_from_chars(page.chars):
                    s = sorted(row, key=lambda c: c["x0"])
                    lead = "".join(c["text"] for c in s[:16])
                    sym = next((t for t in symbols if lead.startswith(t)), None)
                    if sym is None:
                        continue
                    dates, _ = extract_dates(row)
                    nonbd = sorted([d for d in dates if d.x0 > 560],
                                   key=lambda d: d.x0)
                    bd = next((d.text for d in dates if d.x0 <= 560), None)
                    for d in nonbd:
                        all_x.append(d.x0)
                    recs.append((sym, bd, nonbd))
    except Exception as e:  # noqa: BLE001
        return p.name, 0, f"{type(e).__name__}"
    if not recs:
        return p.name, 0, "no rows"

    xs = sorted(all_x)
    bands = [[xs[0]]] if xs else []
    for x in xs[1:]:
        (bands[-1].append(x) if x - bands[-1][-1] <= 8 else bands.append([x]))
    centers = [sum(b) / len(b) for b in bands]

    out_rows = []
    for sym, bd, nonbd in recs:
        rec = dict(symbol=sym, file_date=file_date,
                   bd_date=norm(bd) if bd else None)
        for d in nonbd:
            if centers:
                b = min(range(len(centers)), key=lambda i: abs(centers[i] - d.x0))
                name = ["ex_div", "ex_sc", "date_paid_band"][min(b, 2)]
                rec.setdefault(name, norm(d.text))
        out_rows.append(rec)
    df = pd.DataFrame(out_rows).drop_duplicates(subset=["symbol"])
    df.to_csv(OUT / f"{file_date}.csv", index=False)
    return p.name, len(df), None


if __name__ == "__main__":
    import sqlite3
    con = sqlite3.connect(ROOT / "data/ngx.sqlite")
    symbols = frozenset(pd.read_sql(
        "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9",
        con).ticker)
    pdfs = sorted(ARCHIVE.glob("*.pdf"))
    todo = [p for p in pdfs if not (OUT / (p.name[:10] + ".csv")).exists()]
    print(f"DOLs: {len(pdfs)} | to parse: {len(todo)}", flush=True)
    fails, n_rows = [], 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(work, (str(p), symbols)): p for p in todo}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                name, n, err = f.result()
                n_rows += n
                if err:
                    fails.append(dict(file=name, err=err))
            except Exception as e:  # noqa: BLE001
                fails.append(dict(file=futs[f].name, err=type(e).__name__))
            if i % 200 == 0:
                print(f"[{i}/{len(todo)}] rows={n_rows:,} fails={len(fails)}",
                      flush=True)
    if fails:
        pd.DataFrame(fails).to_csv(OUT / "_parse_failures.csv", index=False)
    print(f"DONE: files={len(list(OUT.glob('2*.csv')))} rows={n_rows:,} "
          f"fails={len(fails)}", flush=True)
