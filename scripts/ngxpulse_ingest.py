"""CLI for NGX Pulse ingestion (Section 35 of the ingestion spec) --
thin wrapper over the existing NGXPulseProvider + ingest.py pipeline, no
new infrastructure. Follows this repo's own established convention of
operational scripts living under scripts/ (e.g. scripts/fre/manage_
watchlist.py), not a new package-level CLI framework.

Writes to the REAL production database (data/ngx.sqlite) by default --
pass --db to target a different path (e.g. a scratch DB for a rehearsal).

Usage:
  PYTHONPATH=src python scripts/ngxpulse_ingest.py status
  PYTHONPATH=src python scripts/ngxpulse_ingest.py stocks
  PYTHONPATH=src python scripts/ngxpulse_ingest.py indices --codes NGXASI,NGX30
  PYTHONPATH=src python scripts/ngxpulse_ingest.py dividends --tickers GTCO,MTNN
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db, ingest  # noqa: E402
from ngxrot.providers.ngxpulse import NGXPulseProvider  # noqa: E402


def _print_report(rep) -> None:
    print(f"[{rep.provider}/{rep.dataset}] fetched={rep.fetched} accepted={rep.accepted} "
          f"rejected={rep.rejected}")
    if rep.reject_reasons:
        print(f"  reject_reasons: {rep.reject_reasons}")


def cmd_status(provider: NGXPulseProvider, args) -> None:
    status = provider.market_status()
    print(status)
    if not status.get("data", {}).get("is_open", False):
        print("Market is CLOSED -- a live scheduler should skip intraday polling "
              "and only run the once-daily post-close jobs, per spec Section 9.")


def cmd_stocks(provider: NGXPulseProvider, con, args) -> None:
    """Today's full-universe snapshot in ONE call (/stocks) -- deliberately
    NOT routed through fetch_equity_prices (which now costs one real call
    PER ticker via the real historical /prices/:symbol endpoint). This
    command applies the exact same `contracts.EQUITY_PRICES` validation
    ingest.py itself uses, just against a differently-shaped (multi-ticker,
    single-day) source frame that the DataProvider dispatch pattern doesn't
    cleanly cover. Use `history` for real multi-year daily prices."""
    import pandas as pd
    from ngxrot import contracts as _contracts

    source_id = ingest.register_provider(con, provider)
    payload = provider._get("/ngxdata/stocks", "stocks", date.today().isoformat())
    rows = payload.get("stocks", [])
    df = pd.DataFrame(rows)
    df["ticker"] = df["symbol"]
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    df["close"] = df["current_price"]
    df["volume"] = df["volume"]

    contract = _contracts.CONTRACTS["equity_prices"]
    bad = pd.Series(False, index=df.index)
    for col, detector in contract.required.items():
        mask = detector(df[col]).fillna(True)
        bad |= mask
    good = df[~bad].copy()
    cols = [c for c in contract.all_columns() if c in good.columns]
    good = good[cols]
    good["source_id"] = source_id
    good["confidence"] = provider.info.base_confidence
    good["as_of_date"] = date.today().isoformat()
    good.to_sql("equity_prices", con, if_exists="append", index=False)
    con.commit()
    print(f"[ngx_pulse/equity_prices (snapshot)] fetched={len(df)} accepted={len(good)} "
          f"rejected={int(bad.sum())}")


def cmd_history(provider: NGXPulseProvider, con, args) -> None:
    if not args.tickers:
        print("ERROR: --tickers is required (one real API call per ticker; never loops "
              "the full universe silently).")
        sys.exit(1)
    tickers = args.tickers.split(",")
    start = args.start or "2015-01-01"
    end = args.end or date.today().isoformat()
    source_id = ingest.register_provider(con, provider)

    # --- idempotency guard: never re-insert a (ticker, trade_date) pair this
    # SAME source already has in the database. This is NOT a delete/upsert --
    # existing rows are never touched, read, or modified; the incoming batch
    # is simply pre-filtered down to genuinely new observations before it
    # ever reaches ingest.ingest()'s own insert path. Re-running this exact
    # command twice in a row is therefore always safe (the second run
    # inserts 0 rows, never raises, never duplicates). -----------------------
    existing = set(con.execute(
        "SELECT ticker, trade_date FROM equity_prices WHERE source_id = ? AND ticker IN ({})".format(
            ",".join("?" * len(tickers))), (source_id, *tickers)).fetchall())
    if existing:
        print(f"idempotency guard: {len(existing)} (ticker, trade_date) row(s) already present "
              f"for this source -- will be skipped, not re-inserted or overwritten")

    class _IdempotentProvider:
        """Thin, local, single-call wrapper -- delegates everything to the
        real provider except fetch_equity_prices, whose output it filters.
        Does not modify ngxpulse.py or ingest.py."""
        def __init__(self, inner):
            self._inner = inner
            self.info = inner.info

        def fetch(self, dataset, **kwargs):
            df = self._inner.fetch(dataset, **kwargs)
            if dataset == "equity_prices" and not df.empty:
                keep = [not ((row.ticker, row.trade_date) in existing) for row in df.itertuples()]
                skipped = len(df) - sum(keep)
                if skipped:
                    print(f"  filtered out {skipped} already-present row(s) before insert")
                df = df[keep]
            return df

    rep = ingest.ingest(con, _IdempotentProvider(provider), "equity_prices",
                         tickers=tickers, start=start, end=end)
    _print_report(rep)


def cmd_indices(provider: NGXPulseProvider, con, args) -> None:
    codes = args.codes.split(",") if args.codes else \
        [r[0] for r in con.execute("SELECT index_code FROM indices").fetchall()]
    start = args.start or (date.today() - timedelta(days=7)).isoformat()
    end = args.end or date.today().isoformat()
    ingest.register_provider(con, provider)
    rep = ingest.ingest(con, provider, "index_levels", index_codes=codes, start=start, end=end)
    _print_report(rep)


def cmd_dividends(provider: NGXPulseProvider, con, args) -> None:
    if not args.tickers:
        print("ERROR: --tickers is required (no aggregate dividends endpoint exists; "
              "looping the full universe would burn the entire 100/day quota).")
        sys.exit(1)
    tickers = args.tickers.split(",")
    ingest.register_provider(con, provider)
    rep = ingest.ingest(con, provider, "corporate_actions", tickers=tickers)
    _print_report(rep)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="DB path (default: production data/ngx.sqlite)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("stocks")
    p_idx = sub.add_parser("indices")
    p_idx.add_argument("--codes", default=None, help="comma-separated index_codes; default: all known")
    p_idx.add_argument("--start", default=None)
    p_idx.add_argument("--end", default=None)
    p_div = sub.add_parser("dividends")
    p_div.add_argument("--tickers", default=None, help="comma-separated tickers (required)")
    p_hist = sub.add_parser("history")
    p_hist.add_argument("--tickers", default=None,
                         help="comma-separated tickers (required; 1 real API call per ticker)")
    p_hist.add_argument("--start", default=None, help="default: 2015-01-01")
    p_hist.add_argument("--end", default=None, help="default: today")
    args = parser.parse_args()

    provider = NGXPulseProvider()

    if args.command == "status":
        cmd_status(provider, args)
        return 0

    con = db.init_db(args.db) if args.db else db.connect()
    try:
        if args.command == "stocks":
            cmd_stocks(provider, con, args)
        elif args.command == "indices":
            cmd_indices(provider, con, args)
        elif args.command == "dividends":
            cmd_dividends(provider, con, args)
        elif args.command == "history":
            cmd_history(provider, con, args)
        con.commit()
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
