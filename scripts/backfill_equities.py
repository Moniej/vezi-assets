"""Per-stock OHLCV backfill (pivot step 1). Resume-safe; paced for rate limits.

  python scripts/backfill_equities.py

Phase A — resolve: for every symbol in the 259-name X-Issuer filing universe,
search investing.com for a Lagos-exchange instrument id. Incremental: already-
resolved and known-unresolved symbols are skipped on re-run. Unresolved names
feed the survivorship/coverage audit — they are counted, never dropped
silently.

Phase B — ingest: per resolved symbol not yet in equity_prices, fetch daily
bars 2012->today via the DAL provider and ingest through the standard
validating pipeline (confidence 0.5). Per-ticker commits => partial progress
survives interruption/rate-limit death; re-run to resume.
"""

import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import db, ingest  # noqa: E402
from ngxrot.providers import InvestingComProvider  # noqa: E402
from ngxrot.providers.investing_com import EQUITY_IDS_PATH, _HEADERS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
START, END = "2012-01-01", date.today().isoformat()
UNRESOLVED_PATH = ROOT / "data" / "reference" / "investing_equity_unresolved.csv"
EQUITY_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)

cal = pd.read_csv(ROOT / "data/staging/xissuer/corporate_actions_calendar_classified.csv")
universe = (cal.dropna(subset=["symbol"])
            .groupby("symbol").company.first().reset_index())
print(f"filing universe: {len(universe)} symbols")

resolved = (pd.read_csv(EQUITY_IDS_PATH) if EQUITY_IDS_PATH.exists()
            else pd.DataFrame(columns=["symbol", "inst_id", "description"]))
unresolved = (set(pd.read_csv(UNRESOLVED_PATH).symbol)
              if UNRESOLVED_PATH.exists() else set())

# ---------------------------------------------------------------- A. resolve
todo = universe[~universe.symbol.isin(resolved.symbol)
                & ~universe.symbol.isin(unresolved)]
print(f"to resolve: {len(todo)} (resolved: {len(resolved)}, "
      f"known-unresolved: {len(unresolved)})")
def _persist():
    resolved.to_csv(EQUITY_IDS_PATH, index=False)
    pd.DataFrame({"symbol": sorted(unresolved)}).to_csv(UNRESOLVED_PATH, index=False)


backoff = 2.0
for i, (_, r) in enumerate(todo.iterrows(), 1):
    name = str(r.company).replace(" PLC", "").replace(" Plc", "").strip()[:40]
    try:
        resp = requests.get("https://api.investing.com/api/search/v2/search",
                            params={"q": name}, headers=_HEADERS, timeout=25)
        if resp.status_code in (403, 429):
            backoff = min(backoff * 2, 300)
            print(f"  [{i}/{len(todo)}] rate-limited; backoff {backoff:.0f}s",
                  flush=True)
            time.sleep(backoff)
            continue  # symbol retried on next run (not marked unresolved)
        resp.raise_for_status()
        backoff = 2.0
        lagos = [q for q in resp.json().get("quotes", [])
                 if q.get("exchange") == "Lagos"]
        if lagos:
            resolved = pd.concat([resolved, pd.DataFrame([dict(
                symbol=r.symbol, inst_id=lagos[0]["id"],
                description=lagos[0]["description"])])], ignore_index=True)
        else:
            unresolved.add(r.symbol)
    except Exception as e:  # noqa: BLE001
        print(f"  [{i}/{len(todo)}] {r.symbol}: {type(e).__name__}", flush=True)
        time.sleep(20)
    if i % 10 == 0:
        _persist()
        print(f"  [{i}/{len(todo)}] resolved={len(resolved)} "
              f"unresolved={len(unresolved)}", flush=True)
    time.sleep(2.0)
_persist()
print(f"resolved total: {len(resolved)} | unresolved total: {len(unresolved)}")

# ---------------------------------------------------------------- B. ingest
con = db.init_db()
have = {r[0] for r in con.execute(
    "SELECT DISTINCT ticker FROM equity_prices WHERE confidence >= 0.5")}
provider = InvestingComProvider(request_pause_s=1.1)
todo_syms = [s for s in resolved.symbol if s not in have]
print(f"to ingest: {len(todo_syms)} symbols (already have: {len(have)})")

ok = fail = 0
for i, sym in enumerate(todo_syms, 1):
    try:
        rep = ingest.ingest(con, provider, "equity_prices",
                            tickers=[sym], start=START, end=END)
        ok += 1
        if i % 10 == 0 or rep.accepted == 0:
            print(f"[{i}/{len(todo_syms)}] {sym}: {rep.accepted} rows "
                  f"({rep.rejected} rejected)")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"[{i}/{len(todo_syms)}] {sym}: FAILED {type(e).__name__} "
              f"{str(e)[:80]}")
        time.sleep(20)

n = con.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM equity_prices "
                "WHERE confidence >= 0.5").fetchone()
print(f"\nDONE: equity_prices now {n[0]:,} rows / {n[1]} tickers "
      f"(this run: {ok} ok, {fail} failed)")

from ngxrot import coverage  # noqa: E402
gate = coverage.generate(con)
print(f"coverage dashboard regenerated — gate: "
      f"{'PASS' if gate['gate_pass'] else 'FAIL'} "
      f"({gate['n_ready_years']} ready years)")
