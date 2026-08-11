"""FRE-7B.1: currency backfill for existing NULL-currency financial-
statement facts, using the platform's own authoritative
`securities.reporting_currency` reference field (populated for 64
tickers, unrelated to and pre-dating this stage).

## Why this is safe and not fabrication

`securities.reporting_currency` is a real, existing, authoritative column
on this platform (not created by this script) that already correctly
distinguishes AIRTELAFRI (USD) from every NGN-domestic reporter --
verified directly before running this backfill. This script does not
guess, infer, or default a currency: it only fills in `extracted_facts.
currency` for rows where it is currently NULL, using this single,
authoritative, pre-existing reference value, and ONLY when that
reference value exists (a ticker with no `reporting_currency` on record --
DEAPCAP, VERITASKAP -- is left NULL, disclosed as still unknown, not
guessed as NGN by default).

## Root cause (FRE-7B.1 finding, not previously diagnosed by FRE-7B)

`scripts/fre/stage4a_balance_sheet_cashflow_2026-08-08.py` and
`scripts/fre/stage5a_depth_campaign_2026-08-08.py` (both pre-existing,
NOT modified by this script) never set the `currency` column on INSERT --
every fact those two scripts wrote has `currency IS NULL`, which silently
excludes them from every currency-guarded computation in
`financial_ratios.py` and `valuation_engine.py`, even though the
underlying value is unambiguously NGN. This script does not touch those
two scripts; it only backfills the column they omitted, using data that
already existed on the platform independently of anything either script
produced.

## Scope

Only `extracted_facts.currency IS NULL` rows for the 14 financial-
statement fact types are touched (corporate-action fact types --
dividend/rights_issue/bonus_issue/share_reconstruction -- are
deliberately left alone; currency is not meaningful for a share-count
event). No other column is modified.

  PYTHONPATH=src python scripts/fre/fre7b1_currency_backfill.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

FACT_TYPES = (
    "net_profit", "equity", "revenue", "assets", "liabilities", "ebit", "ebitda",
    "cfo", "cfi", "cff", "capex", "fcf", "gross_profit", "cogs",
)


def main() -> int:
    con = db.init_db(ROOT / "data" / "ngx.sqlite")

    before = con.execute(
        f"SELECT COUNT(*) FROM extracted_facts WHERE currency IS NULL AND fact_type IN "
        f"({','.join('?' * len(FACT_TYPES))})", FACT_TYPES,
    ).fetchone()[0]

    rows = con.execute(
        f"SELECT f.fact_id, d.ticker, s.reporting_currency FROM extracted_facts f "
        f"JOIN documents d ON d.doc_id = f.doc_id "
        f"LEFT JOIN securities s ON s.ticker = d.ticker "
        f"WHERE f.currency IS NULL AND f.fact_type IN ({','.join('?' * len(FACT_TYPES))})",
        FACT_TYPES,
    ).fetchall()

    updated = 0
    left_null = 0
    by_ticker: dict[str, int] = {}
    for fact_id, ticker, reporting_currency in rows:
        if reporting_currency is None:
            left_null += 1
            continue
        con.execute("UPDATE extracted_facts SET currency = ? WHERE fact_id = ?",
                     (reporting_currency, fact_id))
        updated += 1
        by_ticker[ticker] = by_ticker.get(ticker, 0) + 1

    con.commit()

    after = con.execute(
        f"SELECT COUNT(*) FROM extracted_facts WHERE currency IS NULL AND fact_type IN "
        f"({','.join('?' * len(FACT_TYPES))})", FACT_TYPES,
    ).fetchone()[0]

    print(f"NULL-currency financial-statement facts before: {before}")
    print(f"Backfilled from securities.reporting_currency: {updated}")
    for t, n in sorted(by_ticker.items()):
        print(f"  {t}: {n}")
    print(f"Left NULL (no reporting_currency on record -- genuinely unknown, not guessed): {left_null}")
    print(f"NULL-currency financial-statement facts after: {after}")
    assert before - updated == after
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
