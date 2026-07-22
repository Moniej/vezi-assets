"""Consolidate market capitalization from the PRICES_LIST2 sector-format
price list across the full pricelist archive (approved engineering task
2026-07-22: unlocks the Size factor family + a cap-weighted benchmark).

  python -u scripts/build_market_cap_panel.py

Name->ticker maps are expensive to build (parse a ~30-page DOL PDF), so
ONE map is built per calendar year from a mid-year DOL and reused for every
zip that year (unmatched names are logged, not fatal — this trades a
little completeness for tractable runtime; the validation step below
measures how much).

Validation (pre-declared, printed + written to
reports/market_cap_validation.md): market_cap / close = IMPLIED SHARE
COUNT, which should be near-constant per ticker between corporate actions.
Flag day-over-day implied-share-count jumps > 2% (excluding the first
observation of a ticker) — these should cluster on/near corp-action dates,
not be noise. This is a data-quality signal, not a gate: nothing here
touches the frozen equity_prices panel or the Coverage Gate.

Output: data/reference/market_cap_panel.csv
        (trade_date, symbol, market_cap_nm, close, implied_shares_m)
"""

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db, universe  # noqa: E402


def _build_year_maps(dol_dir: Path, symbols: frozenset[str]) -> dict[str, dict]:
    from ngxrot.list2_parser import dol_name_map
    dols = sorted(dol_dir.glob("2*.pdf"))
    by_year: dict[str, Path] = {}
    for p in dols:
        y = p.name[:4]
        month = int(p.name[5:7])
        cur = by_year.get(y)
        if cur is None or abs(month - 7) < abs(int(cur.name[5:7]) - 7):
            by_year[y] = p
    print(f"building {len(by_year)} per-year name maps "
          f"(one DOL parse each)...", flush=True)
    maps = {}
    for y, p in sorted(by_year.items()):
        maps[y] = dol_name_map(p, symbols)
        print(f"  {y}: {len(maps[y])} names from {p.name}", flush=True)
    return maps


def work(args):
    zp, name_map = args
    from ngxrot.list2_parser import list2_member, parse_list2_pdf
    trade_date = Path(zp).name[:10]
    b = list2_member(zp)
    if b is None:
        return trade_date, None, 0
    df, unmatched = parse_list2_pdf(b, trade_date, name_map)
    return trade_date, df, len(unmatched)


if __name__ == "__main__":
    con = db.connect()
    symbols = frozenset(r[0] for r in con.execute(
        "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.9"))
    dol_dir = ROOT / "data/archive/dol_equities"
    year_maps = _build_year_maps(dol_dir, symbols)

    zips = sorted((ROOT / "data/archive/pricelist_zips").glob("2*.zip"))
    print(f"pricelist zips to scan: {len(zips)}", flush=True)
    args = [(str(z), year_maps.get(z.name[:4], {})) for z in zips]

    frames, no_list2, total_unmatched = [], 0, 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(work, a): a for a in args}
        for i, f in enumerate(as_completed(futs), 1):
            td, df, n_unm = f.result()
            if df is None:
                no_list2 += 1
            elif len(df):
                frames.append(df[["symbol", "trade_date", "market_cap_nm",
                                  "close"]])
                total_unmatched += n_unm
            if i % 300 == 0:
                print(f"[{i}/{len(zips)}] days_with_data={len(frames)} "
                      f"no_list2={no_list2}", flush=True)

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.dropna(subset=["market_cap_nm"])
    panel = panel.drop_duplicates(subset=["symbol", "trade_date"])
    panel = panel.sort_values(["symbol", "trade_date"])
    panel["implied_shares_m"] = panel.market_cap_nm / panel.close

    # ---- validation ---------------------------------------------------
    panel["prev_shares"] = panel.groupby("symbol").implied_shares_m.shift()
    panel["share_jump_pct"] = (
        (panel.implied_shares_m - panel.prev_shares).abs()
        / panel.prev_shares.replace(0, pd.NA))
    jumps = panel[panel.share_jump_pct > 0.02].dropna(subset=["share_jump_pct"])
    corp = pd.read_csv(ROOT / "data/staging/xissuer/"
                       "corporate_actions_calendar_classified.csv")
    corp["d"] = pd.to_datetime(corp.created.str[:10])
    corp_by_sym = corp.groupby("symbol").d.apply(list).to_dict()

    def near_corp_action(sym, d_str):
        d = pd.Timestamp(d_str)
        return any(abs((d - f).days) <= 10 for f in corp_by_sym.get(sym, ()))

    jumps = jumps.copy()
    jumps["near_ca_filing"] = [near_corp_action(r.symbol, r.trade_date)
                               for r in jumps.itertuples()]
    explained_rate = jumps.near_ca_filing.mean() if len(jumps) else None

    out_cols = ["trade_date", "symbol", "market_cap_nm", "close",
               "implied_shares_m"]
    OUT = ROOT / "data/reference/market_cap_panel.csv"
    panel[out_cols].to_csv(OUT, index=False)

    report = f"""# Market-Cap Panel Validation — {pd.Timestamp.today().date()}

Source: PRICES_LIST2 sector-format price list, {len(zips):,} archived
pricelist zips scanned ({no_list2} had no LIST2-format member — mostly
early-era zips with a single combined PDF). Name->ticker resolution via
one per-calendar-year map built from a mid-year DOL (12 maps, not 2,800 —
runtime tradeoff; unmatched names logged, not fatal). Full-issue market
cap as printed (NOT float-adjusted — no shares-outstanding/free-float
dataset exists yet; that remains a separate backlog item).

- rows: {len(panel):,} | symbols: {panel.symbol.nunique()} | days: {panel.trade_date.nunique():,}
- unmatched name instances (not fatal, excluded): {total_unmatched:,}
- date range: {panel.trade_date.min()} .. {panel.trade_date.max()}

## Implied-share-count stability check

market_cap / close = implied share count, which should be near-constant
between corporate actions. Day-over-day jumps > 2%: {len(jumps):,}
({len(jumps) / len(panel):.3%} of rows).
Of those jumps, occurring within ±10 days of a corporate-actions filing
for that symbol: {f'{explained_rate:.1%}' if explained_rate is not None else 'n/a'}

This is informational (Size-factor input quality), not a gate — it does
not touch equity_prices or the Coverage Gate.
"""
    (ROOT / "reports/market_cap_validation.md").write_text(
        report, encoding="utf-8")
    print(report)
    print(f"wrote {OUT.relative_to(ROOT)}")
