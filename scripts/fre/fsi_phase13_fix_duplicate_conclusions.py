"""FSI Phase 13 bug fix: remove duplicate financial_reasoning_conclusions
rows accidentally created for the 5 ORIGINAL FSI tickers (UCAP, BUAFOODS,
AFRIPRUD, CAP, NASCON).

Root cause: fsi_phase3_compute_metrics.py / fsi_phase3_classify_trends.py /
fsi_phase3_compute_flags.py (all frozen, unmodified Phase 3 scripts) each
call list_tickers(con), which now returns all 10 tickers after Phase 13's
extraction -- these scripts were only ever run ONCE before, against the
then-only 5 tickers, and have no dedup/upsert logic (a straight INSERT
per result, by original design -- append-only, no existing-row check was
ever needed because no ticker had EVER been re-processed before). Running
them again during Phase 13 to compute the 5 NEW tickers' conclusions
correctly added 90 new rows for those tickers, but ALSO re-computed and
re-inserted a byte-for-byte duplicate of the pre-existing 177 conclusions
for the 5 original tickers (354 total for those 5 tickers = 177 original
+ 177 duplicate, confirmed by direct inspection: conclusion_id 1-177 is
the untouched original set, every duplicate row has conclusion_id > 177).

This is a real mistake made DURING this phase's own execution (not a
historical production defect, and not a frozen-module defect requiring
owner authorization to fix) -- the fix is to delete the 177 wrongly-
duplicated rows (and their financial_reasoning_conclusion_facts children)
for the 5 original tickers, leaving conclusion_id 1-177 exactly as they
were, the 5 new tickers' 90 rows exactly as computed, and Phase 3's own
scripts unmodified (the actual, disclosed general lesson: any future
re-run of these scripts against an EXPANDED ticker set must first delete
or otherwise scope out already-processed tickers -- left as a documented
operational note, not a code change, since these scripts are frozen).

  PYTHONPATH=src python scripts/fre/fsi_phase13_fix_duplicate_conclusions.py            # dry run
  PYTHONPATH=src python scripts/fre/fsi_phase13_fix_duplicate_conclusions.py --apply    # writes for real
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

ORIGINAL_TICKERS = ("UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON")
BASELINE_MAX_CONCLUSION_ID = 177  # confirmed: ids 1-177 are the pre-Phase-13 original set


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    real_db = db.DEFAULT_DB
    if args.apply:
        backup_path = real_db.parent / f"ngx.sqlite.pre_fsi_phase13_dupfix_backup_{date.today().isoformat()}"
        if not backup_path.exists():
            shutil.copy(real_db, backup_path)
            print(f"Backup created: {backup_path}")

    con = sqlite3.connect(real_db)
    before_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in ("financial_reasoning_conclusions", "financial_reasoning_conclusion_facts")}

    placeholders = ",".join("?" * len(ORIGINAL_TICKERS))
    dup_ids = [r[0] for r in con.execute(
        f"SELECT conclusion_id FROM financial_reasoning_conclusions "
        f"WHERE ticker IN ({placeholders}) AND conclusion_id > ?",
        (*ORIGINAL_TICKERS, BASELINE_MAX_CONCLUSION_ID),
    ).fetchall()]

    print(f"Found {len(dup_ids)} duplicate conclusion rows to delete "
          f"(expected 177, one full duplicate of the original 5-ticker baseline).")
    assert len(dup_ids) == 177, f"expected exactly 177 duplicate rows, found {len(dup_ids)} -- stopping, not deleting"

    linked_facts_count = con.execute(
        f"SELECT COUNT(*) FROM financial_reasoning_conclusion_facts "
        f"WHERE conclusion_id IN ({','.join('?' * len(dup_ids))})",
        dup_ids,
    ).fetchone()[0] if dup_ids else 0
    print(f"Linked financial_reasoning_conclusion_facts rows to delete: {linked_facts_count}")

    if args.apply:
        con.execute(
            f"DELETE FROM financial_reasoning_conclusion_facts "
            f"WHERE conclusion_id IN ({','.join('?' * len(dup_ids))})",
            dup_ids,
        )
        con.execute(
            f"DELETE FROM financial_reasoning_conclusions "
            f"WHERE conclusion_id IN ({','.join('?' * len(dup_ids))})",
            dup_ids,
        )
        con.commit()

    after_counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("financial_reasoning_conclusions", "financial_reasoning_conclusion_facts")}
    print(f"\nBefore: {before_counts}")
    print(f"After:  {after_counts}")
    if args.apply:
        remaining_old = con.execute(
            f"SELECT COUNT(*) FROM financial_reasoning_conclusions WHERE ticker IN ({placeholders})",
            ORIGINAL_TICKERS,
        ).fetchone()[0]
        print(f"Original 5 tickers' conclusion count after fix: {remaining_old} (expected 177)")
        assert remaining_old == 177
        fk_bad = con.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check: {'CLEAN' if not fk_bad else fk_bad}")
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check: {integrity}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
