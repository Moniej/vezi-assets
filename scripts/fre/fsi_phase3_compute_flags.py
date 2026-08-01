"""FSI Phase 3, Step 3: financial health flags
(docs/fre_runs/fsi_phase3_preregistration.md Area 3,
docs/fre_runs/fsi_phase3_implementation_log.md).

Evaluates the fixed, named rule set in
src/ngxrot/fre/financial_health_flags.py (leverage_increasing,
cash_flow_earnings_divergence, margin_compression) for every ticker,
reading Step 1/2's already-written conclusions. Depends on Steps 1-2
having already run.

  PYTHONPATH=src python scripts/fre/fsi_phase3_compute_flags.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_phase3_compute_flags.py --apply    # writes for real
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.financial_health_flags import compute_flags_for_ticker, write_flag_results  # noqa: E402
from ngxrot.fre.financial_ratios import list_tickers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase3_flags_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("financial_reasoning_conclusions", "financial_reasoning_conclusion_facts",
                               "extracted_facts", "documents")}

    total_written = 0
    for ticker in list_tickers(con):
        results = compute_flags_for_ticker(con, ticker)
        for r in results:
            fired_str = "n/a" if r.fired is None else ("FIRED" if r.fired else "not fired")
            print(f"{'[DRY RUN] ' if not args.apply else ''}ticker={r.ticker} flag={r.flag_name} "
                  f"status={r.status} {fired_str} value={r.triggering_value} tier={r.confidence_tier}")
        if args.apply:
            total_written += write_flag_results(con, results)

    if args.apply:
        con.commit()

    after_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("financial_reasoning_conclusions", "financial_reasoning_conclusion_facts",
                              "extracted_facts", "documents")}
    print(f"\nBefore: {before_counts}")
    print(f"After:  {after_counts}")
    print(f"extracted_facts/documents unchanged: "
          f"{before_counts['extracted_facts'] == after_counts['extracted_facts'] and before_counts['documents'] == after_counts['documents']}")
    if args.apply:
        print(f"Wrote {total_written} new financial_reasoning_conclusions rows.")
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
