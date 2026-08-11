"""Load real dividend corporate-actions from extracted_facts into
corporate_actions (2026-08-11, HANDOFF.md).

`corporate_actions` has held ONLY synthetic dev fixtures since the table
was created (31 rows, tickers SYNBNKA/B/C, source_id=4 'synthetic_dev',
confidence=0.0 -- confirmed by direct query before writing this script,
and independently by docs/FACTOR_REGISTRY.md's H-017 entry). Real
dividend data already exists, evidence-linked, in `extracted_facts`
(fact_type='dividend', 161 rows across 60 real tickers as of 2026-08-11)
-- this script derives corporate_actions rows from those facts. It does
NOT re-extract or re-parse anything; every value copied here already
passed the platform's existing extraction/grounding discipline.

## Scope (deliberately narrow this pass)

Dividend facts ONLY. bonus_issue/rights_issue/share_reconstruction facts
also exist in extracted_facts but their `numeric_value` is a PRICE-
ADJUSTMENT FACTOR (e.g. 0.6 for a 2-for-3 bonus), not the ratio_new/
ratio_old pair corporate_actions expects -- mapping those needs dedicated
parsing + validation, out of scope here and left for a follow-on pass
(some are also PROPOSED-ONLY or CANCELLED, per their own description
text, which a bulk loader must not silently treat as executed).

## markdown_date is deliberately left NULL -- do not populate it here

`corporate_actions` is a LIVE INPUT to `engine_full.py`'s total-return
overlay (`db.corporate_actions_asof` -> per-ticker dividend adjustment on
`markdown_date`, when `markdown_date` is a real index date). Per an
explicit owner decision (2026-08-11, alpha-untouched constraint): load
real dividend data so it is queryable/visible to the OS, but do NOT
populate `markdown_date`, so the overlay's activation condition
(`pd.Timestamp(a.markdown_date) in px.index`) can never be satisfied by
these rows -- `NaT` is never a member of a DatetimeIndex. Rows ARE
returned by `corporate_actions_asof` (it filters on
`COALESCE(declared_date, markdown_date)`, and `declared_date` IS set
here), but produce zero effect on any backtest total-return computation.
Do not "complete" this by backfilling markdown_date without a fresh,
explicit decision -- that is a real behavior change to a component this
phase was told not to touch.

Idempotent: a fact already linked via `corporate_actions.source_fact_id`
is skipped on rerun, never duplicated.

  PYTHONPATH=src python scripts/load_real_corporate_actions_dividends.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timezone, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="report what would be inserted, write nothing")
    args = p.parse_args()

    con = db.init_db()  # applies the additive source_fact_id migration if not already present

    candidates = con.execute("""
        SELECT ef.fact_id, ef.numeric_value, ef.qualification_date, ef.payment_date,
               ef.extraction_confidence, ef.description, ef.model_id,
               d.ticker, d.filing_date, d.source_id
        FROM extracted_facts ef
        JOIN documents d ON d.doc_id = ef.doc_id
        WHERE ef.fact_type = 'dividend' AND d.ticker IS NOT NULL
        ORDER BY ef.fact_id
    """).fetchall()

    already_loaded = {row[0] for row in con.execute(
        "SELECT source_fact_id FROM corporate_actions WHERE source_fact_id IS NOT NULL").fetchall()}

    to_insert = [c for c in candidates if c[0] not in already_loaded]
    skipped_unresolved_ticker = con.execute("""
        SELECT COUNT(*) FROM extracted_facts ef JOIN documents d ON d.doc_id = ef.doc_id
        WHERE ef.fact_type = 'dividend' AND d.ticker IS NULL
    """).fetchone()[0]

    print(f"candidate real dividend facts (resolved ticker): {len(candidates)}")
    print(f"already loaded (idempotent skip): {len(candidates) - len(to_insert)}")
    print(f"unresolved-ticker dividend facts, correctly excluded: {skipped_unresolved_ticker}")
    print(f"to insert this run: {len(to_insert)}")

    if args.dry_run:
        print("--dry-run: no writes performed")
        return 0

    as_of = datetime.now(timezone.utc).date().isoformat()
    n_with_amount = 0
    for fact_id, numeric_value, qualification_date, payment_date, confidence, description, model_id, \
            ticker, filing_date, source_id in to_insert:
        con.execute("""
            INSERT INTO corporate_actions
                (ticker, action_type, declared_date, qualification_date, markdown_date,
                 payment_date, dividend_per_share, currency, withholding_tax_pct, details,
                 source_id, confidence, as_of_date, source_fact_id)
            VALUES (?, 'dividend_cash', ?, ?, NULL, ?, ?, 'NGN', 10.0, ?, ?, ?, ?, ?)
        """, (ticker, filing_date, qualification_date, payment_date, numeric_value,
              description, source_id, confidence, as_of, fact_id))
        n_with_amount += numeric_value is not None

    con.commit()
    print(f"inserted: {len(to_insert)} rows ({n_with_amount} with a real dividend_per_share amount, "
          f"{len(to_insert) - n_with_amount} with dates only -- numeric_value not extracted, "
          f"never fabricated)")
    print("markdown_date left NULL on every inserted row (deliberate -- see module docstring)")

    total = con.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0]
    real = con.execute("SELECT COUNT(*) FROM corporate_actions WHERE source_fact_id IS NOT NULL").fetchone()[0]
    synthetic = con.execute(
        "SELECT COUNT(*) FROM corporate_actions WHERE source_id = "
        "(SELECT source_id FROM sources WHERE name = 'synthetic_dev')").fetchone()[0]
    print(f"\ncorporate_actions now holds {total} rows total: {real} real (fact-linked), "
          f"{synthetic} pre-existing synthetic dev fixtures (untouched)")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
