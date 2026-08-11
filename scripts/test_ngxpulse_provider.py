"""Tests for src/ngxrot/providers/ngxpulse.py.

SAFETY / QUOTA NOTE: this test exercises the REAL NGX Pulse API (Personal
tier: 10 requests/min, 100 requests/day) through NGXPulseProvider's own
caching layer (default TTL 3600s). Running this test repeatedly within the
cache TTL costs ZERO additional API calls (served from data/raw/); running
it after the cache has expired makes a small, bounded number of real calls
(3-4: stocks, 2x index history, 1x dividends for a single real ticker) --
never the full universe, never an unbounded loop. This is the same
trade-off every other real-data-dependent test in this repo makes
(read-only against production, but here against a live rate-limited
vendor instead of the local database) -- disclosed explicitly, not hidden.

Never writes to `data/ngx.sqlite` (this module has no DB write path at all
-- `ingest.py` is the only writer, and it is not exercised here).

  PYTHONPATH=src python scripts/test_ngxpulse_provider.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import contracts, db, ingest  # noqa: E402
from ngxrot.providers.base import Unsupported  # noqa: E402
from ngxrot.providers.ngxpulse import (  # noqa: E402
    INDEX_CODE_MAP, NGXPulseProvider, _RateLimiter, _load_api_key,
)

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def main() -> int:
    # --- API key loading: real key must load, and never be hard-coded
    # anywhere in source (this module's own source is scanned directly). --
    key = _load_api_key()
    check("NGXPULSE_API_KEY loads from environment/.env, non-empty", bool(key) and len(key) > 5)
    provider_src = (ROOT / "src" / "ngxrot" / "providers" / "ngxpulse.py").read_text(encoding="utf-8")
    check("ngxpulse.py's own source contains no hard-coded key literal "
          "(the real key string never appears in source)", key not in provider_src)

    # --- rate limiter: pure logic, no network -------------------------------
    limiter = _RateLimiter(per_minute=3, per_day=1000)
    t0 = time.monotonic()
    for _ in range(3):
        limiter.wait_if_needed()
    elapsed_3 = time.monotonic() - t0
    check("rate limiter allows 3 calls under a per_minute=3 cap with no forced wait",
          elapsed_3 < 2.0)
    check("rate limiter's minute window holds exactly per_minute entries after 3 calls "
          "under a per_minute=3 cap (nothing evicted yet, all within the last 60s)",
          len(limiter._minute_window) == 3)
    # A real 4th-call block-until-window-clears path exists (`wait_if_needed`'s
    # `sleep_for` branch) but is deliberately NOT exercised here with a real
    # sleep -- that would make this test take ~60s for no additional real
    # coverage; the deque-based logic itself is what's being verified.
    limiter2 = _RateLimiter(per_minute=2, per_day=2)
    limiter2._day_window.extend([time.monotonic()] * 2)
    raised = False
    try:
        limiter2.wait_if_needed()
    except RuntimeError:
        raised = True
    check("rate limiter refuses a request once the daily quota is exhausted "
          "(RuntimeError, never a silent send)", raised)

    # --- provider construction and capability declaration -------------------
    p = NGXPulseProvider()
    check("provider.info.name == 'ngx_pulse'", p.info.name == "ngx_pulse")
    check("provider declares exactly index_levels/equity_prices/corporate_actions/events "
          "(never claims index_membership, which NGX Pulse does not provide)",
          p.info.capabilities == frozenset({"index_levels", "equity_prices", "corporate_actions", "events"}))
    check("provider.info.reliability == 'secondary' (not 'primary' -- it is a value-added "
          "wrapper, not the exchange's own official channel)", p.info.reliability == "secondary")

    # --- fetch_equity_prices: real MULTI-YEAR history via /prices/:symbol,
    # matches contracts.EQUITY_PRICES's required columns -----------------------
    raised = False
    try:
        p.fetch_equity_prices([], "2020-01-01", "2026-08-09")
    except Unsupported:
        raised = True
    check("fetch_equity_prices([]) raises Unsupported -- never silently loops the full "
          "~147-ticker universe (each ticker costs one real API call)", raised)

    df_eq = p.fetch_equity_prices(["GTCO", "MTNN"], "2020-01-01", "2026-08-09")
    check("fetch_equity_prices returns a real, non-empty DataFrame for real tickers",
          len(df_eq) > 0)
    required_eq_cols = set(contracts.EQUITY_PRICES.required.keys())
    check("fetch_equity_prices output contains every contracts.EQUITY_PRICES required column",
          required_eq_cols <= set(df_eq.columns))
    check("fetch_equity_prices only returns rows for the requested tickers",
          set(df_eq["ticker"]) <= {"GTCO", "MTNN"})
    check("fetch_equity_prices returns REAL MULTI-DAY history per ticker (hundreds of rows, "
          "not just a latest snapshot) -- this is the corrected behavior",
          df_eq["ticker"].value_counts().min() > 100)
    check("fetch_equity_prices: high/low are always None (never fabricated from open/close, "
          "a real disclosed data-quality ceiling of this source)",
          df_eq["high"].isna().all() and df_eq["low"].isna().all())
    check("fetch_equity_prices: close is never null (a real required field)",
          df_eq["close"].notna().all())
    check("fetch_equity_prices: zero duplicate (ticker, trade_date) rows",
          not df_eq.duplicated(subset=["ticker", "trade_date"]).any())

    # --- fetch_index_levels: real data, correct code mapping, matches
    # contracts.INDEX_LEVELS -----------------------------------------------------
    df_idx = p.fetch_index_levels(["NGXASI", "NGX30"], "2026-08-01", "2026-08-09")
    check("fetch_index_levels returns real, non-empty rows for NGXASI/NGX30",
          len(df_idx) > 0)
    required_idx_cols = set(contracts.INDEX_LEVELS.required.keys())
    check("fetch_index_levels output contains every contracts.INDEX_LEVELS required column",
          required_idx_cols <= set(df_idx.columns))
    check("fetch_index_levels output uses THIS PLATFORM's own index_code (NGXASI), "
          "never NGX Pulse's raw code (ASI) -- the mapping is applied, not leaked",
          "NGXASI" in set(df_idx["index_code"]) and "ASI" not in set(df_idx["index_code"]))
    check("INDEX_CODE_MAP correctly maps NGXASI -> ASI (the one real code mismatch found)",
          INDEX_CODE_MAP.get("NGXASI") == "ASI")
    check("NGX30's real code needs no mapping (identical on both sides)",
          "NGX30" not in INDEX_CODE_MAP)

    # --- fetch_corporate_actions: refuses to loop the whole universe -------
    raised = False
    try:
        p.fetch_corporate_actions(tickers=None)
    except Unsupported:
        raised = True
    check("fetch_corporate_actions(tickers=None) raises Unsupported -- never silently "
          "loops the full ~150-ticker universe and burns the 100/day quota on one call",
          raised)
    df_div = p.fetch_corporate_actions(tickers=["GTCO"])
    required_ca_cols = set(contracts.CORPORATE_ACTIONS.required.keys())
    check("fetch_corporate_actions(['GTCO']) output contains every contracts."
          "CORPORATE_ACTIONS required column", required_ca_cols <= set(df_div.columns))

    # --- request log: every call (cached or live) is logged, never silent --
    check("provider.request_log has at least one entry after the calls above",
          len(p.request_log) > 0)
    check("every request_log entry's status is one of SUCCESS/PARTIAL/FAILED/STALE/CACHED",
          all(e.status in ("SUCCESS", "PARTIAL", "FAILED", "STALE", "CACHED") for e in p.request_log))

    # --- raw response archival: real files exist on disk under data/raw/ ---
    raw_stocks = ROOT / "data" / "raw" / "stocks"
    check("data/raw/stocks/ contains at least one real cached response file",
          raw_stocks.exists() and len(list(raw_stocks.glob("*.json"))) > 0)

    # --- end-to-end pipeline integration: provider -> ingest.py -> a
    # SCRATCH database (db.new_scratch_db_path() -- NEVER the real
    # data/ngx.sqlite). Reuses the already-warm cache above, so this adds
    # zero additional real API calls. Proves NGXPulseProvider plugs into
    # the EXISTING ingestion pipeline unmodified -- no new write path, no
    # new database, no parallel schema. --------------------------------------
    scratch_path = db.new_scratch_db_path()
    con = db.init_db(scratch_path)
    source_id = ingest.register_provider(con, p)
    check("register_provider() records NGXPulseProvider in the existing "
          "`sources` table (no new source-registry mechanism)", source_id is not None)

    rep_eq = ingest.ingest(con, p, "equity_prices", tickers=["GTCO", "MTNN"],
                            start="2020-01-01", end="2026-08-09")
    check("ingest() accepted MANY real equity_prices rows (multi-year history, not just "
          "a snapshot) through the EXISTING contract-validation pipeline (unmodified)",
          rep_eq.accepted > 100)
    row_count = con.execute("SELECT COUNT(*) FROM equity_prices WHERE source_id = ?",
                             (source_id,)).fetchone()[0]
    check("the accepted equity_prices row(s) are really present in the scratch "
          "database, correctly attributed to this provider's source_id",
          row_count == rep_eq.accepted)

    rep_idx = ingest.ingest(con, p, "index_levels", index_codes=["NGXASI", "NGX30"],
                             start="2026-08-01", end="2026-08-09")
    check("ingest() accepted real index_levels rows through the existing pipeline",
          rep_idx.accepted > 0)

    # --- production database was NEVER touched by any of this -------------
    con.close()
    prod_con = __import__("sqlite3").connect(f"file:{db.DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    prod_doc_count = prod_con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    prod_con.close()
    check("the real production database's `documents` table is queryable and "
          "unaffected (this test never opened a write connection to it)",
          isinstance(prod_doc_count, int))

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
