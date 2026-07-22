"""Quality diagnostics over the per-stock database (feeds Coverage Gate v2).

  python -u scripts/run_equity_diagnostics.py

D1 unexplained_jump: SESSION-adjacent |return| > 12% — beyond the NGX ±10%
   daily band, so impossible without an official re-basing or a data error —
   that is NOT accounted for by any of (2026-07-21 evidence hierarchy):
     a) a verified market day between the two rows that our panel lacks
        (index_levels days whose value CHANGED — value-change test kills
        vendor holiday padding): the move spans 2+ sessions, legal;
     b) NGX's own Gainers/Losers report for that transition certifying the
        official move was within band off an OFFICIALLY ADJUSTED base
        (parenthesized re-basings: dividends/bonus/restructuring);
     c) closure-of-register (DOL ex-div calendar) or earnings filing
        (X-Issuer) within ±3 business days.
   Threshold (12%) and the gate's 2% IRU rate are unchanged.
   Logged per ticker to data_quality_log (gate input).
D2 stale runs: >=20 identical consecutive closes (existing diagnostic class).
D3 volume contradictions: value>0 with volume=0 etc.
D4 volume plausibility (2026-07-21, after the SEPLAT glued-token find):
   implausible_volume: volume > 1e12 shares — the signature of PRICES1
   VOLUME+VALUE gluing (pdfplumber emits one word when the columns touch;
   see scripts/restate_glued_volumes.py) and beyond any real NGX print;
   vwap_inconsistent: value/volume outside [0.25, 4]x close — catches
   column misassignment and zero-value days.
   All checks run on the LATEST vintage per (ticker, trade_date) — matching
   equity_prices_asof — so restated rows are judged by their correction,
   not by superseded captures.
Report: reports/equity_diagnostics.md
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot import db  # noqa: E402

con = db.connect()
px = pd.read_sql(
    "SELECT ticker, trade_date, close, volume, value_traded, as_of_date "
    "FROM equity_prices WHERE confidence >= 0.9 ORDER BY ticker, trade_date",
    con)
# latest vintage per (ticker, trade_date) — same dedup as equity_prices_asof;
# superseded captures (e.g. glued-volume rows restated 2026-07-21) must not
# be re-flagged
px = (px.sort_values(["ticker", "trade_date", "as_of_date"])
        .drop_duplicates(["ticker", "trade_date"], keep="last")
        .drop(columns="as_of_date"))
closures = pd.read_csv(ROOT / "data/reference/exdiv_closure_calendar.csv")
closures["d"] = pd.to_datetime(closures.closure_date)
earn = pd.read_csv(ROOT / "data/staging/xissuer/earnings_calendar.csv")
earn["d"] = pd.to_datetime(earn.created_date)
events = {}
for src in (closures, earn):
    for sym, g in src.groupby("symbol"):
        events.setdefault(sym, []).extend(g.d.tolist())


def _explained(sym, d):
    """closure-of-register OR earnings filing within ±3 business days."""
    for f in events.get(sym, ()):
        lo, hi = (d, f) if d <= f else (f, d)
        if (hi - lo).days <= 7 and np.busday_count(lo.date(), hi.date()) <= 3:
            return True
    return False


# NGX Gainers/Losers transitions: official per-move record incl. adjusted
# bases. Keyed (end_date, symbol).
gt = pd.read_csv(ROOT / "data/reference/gainers_transitions.csv")
gainers = {(r.end_date, r.symbol): r for r in gt.itertuples()}

# PRICES1's PCLOSE column = the officially ADJUSTED base for the day, so
# close/pclose is the exchange's own within-band return for every
# pricelist-sourced day (independent of the gainers reports' gaps).
oc = pd.read_csv(ROOT / "data/reference/official_prev_close.csv")
official_base = {(r.trade_date, r.symbol): (r.pclose, r.close)
                 for r in oc.itertuples() if pd.notna(r.pclose)}


def _official_move(sym, d_iso, our_close):
    """True if the exchange's own records certify this transition as a
    within-band move off the official (possibly adjusted) base:
    via the Gainers/Losers report, or via PRICES1's PCLOSE column."""
    r = gainers.get((d_iso, sym))
    if (r is not None and abs(r.pct) <= 10.55
            and abs(r.new - our_close) < 0.005):
        return True
    b = official_base.get((d_iso, sym))
    return (b is not None and b[0] > 0
            and abs(b[1] - our_close) < 0.005
            and abs(b[1] / b[0] - 1) <= 0.1055)


# verified market calendar: index days whose value changed vs the previous
# index day (vendor pads holidays with carry-forward values)
_iv = pd.read_sql(
    "SELECT trade_date, close_value FROM index_levels "
    "WHERE index_code = (SELECT index_code FROM index_levels GROUP BY "
    "index_code ORDER BY COUNT(*) DESC LIMIT 1) "
    "ORDER BY trade_date", con).drop_duplicates("trade_date")
verified_mkt = set(_iv.trade_date[_iv.close_value.diff() != 0])

session_idx = {d: i for i, d in enumerate(sorted(px.trade_date.unique()))}
vmkt_sorted = sorted(verified_mkt)
import bisect  # noqa: E402


def _spans_missing_day(p_iso, d_iso):
    j = bisect.bisect_right(vmkt_sorted, p_iso)
    return j < len(vmkt_sorted) and vmkt_sorted[j] < d_iso


jump_rows, stale_rows, vol_rows, impvol_rows, vwap_rows = [], [], [], [], []
n_span = n_official = n_event = 0
for t, g in px.groupby("ticker"):
    g = g.drop_duplicates("trade_date").sort_values("trade_date")
    dts = pd.to_datetime(g.trade_date)
    ret = g.close.pct_change().values
    sgap = g.trade_date.map(session_idx).diff().values
    for i in range(1, len(g)):
        if sgap[i] == 1 and abs(ret[i]) > 0.12:
            d_iso, p_iso = g.trade_date.iloc[i], g.trade_date.iloc[i - 1]
            if _spans_missing_day(p_iso, d_iso):
                n_span += 1                # 2+ real sessions: legal compound
            elif _official_move(t, d_iso, float(g.close.iloc[i])):
                n_official += 1            # exchange-certified re-basing
            elif _explained(t, dts.iloc[i]):
                n_event += 1               # closure/earnings ±3bd
            else:
                jump_rows.append(dict(ticker=t, trade_date=d_iso,
                                      ret=round(float(ret[i]), 4)))
    runs = (g.close != g.close.shift()).cumsum()
    rc = g.groupby(runs).agg(n=("close", "size"), d0=("trade_date", "min"))
    for _, r in rc[rc.n >= 20].iterrows():
        stale_rows.append(dict(ticker=t, trade_date=r.d0, sessions=int(r.n)))
    bad = g[(g.volume.fillna(0) == 0) & (g.value_traded.fillna(0) > 0)]
    for _, r in bad.iterrows():
        vol_rows.append(dict(ticker=t, trade_date=r.trade_date))
    # D4a: no NGX print reaches 1e12 shares — glued-token signature
    for _, r in g[g.volume.fillna(0) > 1e12].iterrows():
        impvol_rows.append(dict(ticker=t, trade_date=r.trade_date,
                                volume=float(r.volume)))
    # D4b: naira value / share volume must sit near the close (value NULL —
    # e.g. ngx_dol_v1 fallback rows — is exempt; value 0 with volume is not)
    vw = g[(g.volume.fillna(0) > 0) & g.value_traded.notna()]
    vw = vw[(vw.value_traded / vw.volume < 0.25 * vw.close)
            | (vw.value_traded / vw.volume > 4 * vw.close)]
    for _, r in vw.iterrows():
        vwap_rows.append(dict(ticker=t, trade_date=r.trade_date,
                              vwap=round(float(r.value_traded / r.volume), 4),
                              close=float(r.close)))

for name, rows_, sev in (("unexplained_jump", jump_rows, "error"),
                         ("stale_price", stale_rows, "warn"),
                         ("liquidity_anomaly", vol_rows, "warn"),
                         ("implausible_volume", impvol_rows, "error"),
                         ("vwap_inconsistent", vwap_rows, "warn")):
    con.execute("DELETE FROM data_quality_log WHERE check_name = ? AND "
                "entity_type = 'ticker' AND detail LIKE 'equity_diag_v1%'",
                (name,))
    for r in rows_[:5000]:
        con.execute(
            "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
            "trade_date, severity, detail) VALUES (?,?,?,?,?,?)",
            (name, "ticker", r["ticker"], r["trade_date"], sev,
             f"equity_diag_v1: {r}"))
con.commit()

n_tickers = px.ticker.nunique()
report = f"""# Equity Data Diagnostics — {date.today().isoformat()}

Scope: {len(px):,} rows / {n_tickers} tickers (conf >= 0.9).

| check | findings | tickers affected |
|---|---|---|
| unexplained_jump (session-adjacent >12%, unaccounted) | {len(jump_rows)} | {len(set(r['ticker'] for r in jump_rows))} |
| stale_price (>=20 identical closes) | {len(stale_rows)} | {len(set(r['ticker'] for r in stale_rows))} |
| volume/value contradictions | {len(vol_rows)} | {len(set(r['ticker'] for r in vol_rows))} |
| implausible_volume (> 1e12 shares, glued-token signature) | {len(impvol_rows)} | {len(set(r['ticker'] for r in impvol_rows))} |
| vwap_inconsistent (value/volume outside [0.25, 4]x close) | {len(vwap_rows)} | {len(set(r['ticker'] for r in vwap_rows))} |

Jump scan uses the NGX ±10% daily band: moves beyond 12% between CONSECUTIVE
MARKET SESSIONS are impossible without an official re-basing or a data error.
Candidate >12% moves this run resolved as:
- spanning a verified market day our panel lacks (legal 2+ session
  compound; index-verified calendar): {n_span}
- certified by NGX's own Gainers/Losers report as within-band off an
  officially adjusted base ({len(gt):,} mover rows): {n_official}
- closure-of-register ({len(closures):,} events) or earnings filing
  ({len(earn):,}) within ±3bd: {n_event}
- UNEXPLAINED (logged, gate input): {len(jump_rows)}
"""
(ROOT / "reports" / "equity_diagnostics.md").write_text(report, encoding="utf-8")
print(report)
