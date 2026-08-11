"""Writes real, specific data_quality_log entries for the NGX Pulse cross-
validation findings -- reuses the EXISTING data_quality_log table/schema
(check_name/entity_type/entity_code/trade_date/severity/detail/resolved),
matching the convention its own CREATE TABLE comment already documents
(`'unadjusted_jump'`, `'stale_series'`, ...). No new table. Append-only --
never updates or deletes an existing row.

  PYTHONPATH=src python scripts/ngxpulse_log_dq_findings.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402


def main() -> int:
    con = db.connect()
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    def log(check_name, entity_code, trade_date, severity, detail, resolved):
        nonlocal inserted
        con.execute(
            "INSERT INTO data_quality_log (check_name, entity_type, entity_code, trade_date, "
            "severity, detail, resolved, logged_at) VALUES (?,?,?,?,?,?,?,?)",
            (check_name, "ticker", entity_code, trade_date, severity, detail, resolved, now),
        )
        inserted += 1

    # --- RESOLVED: CILEASING's bonus-issue-driven price markdown, confirmed
    # both against extracted_facts (fact_id=350) and independently reproduced
    # live in NGX Pulse's own raw series (2026-08-10 cross-validation). -----
    log("unadjusted_jump", "CILEASING", "2024-01-05", "info",
        "RESOLVED: close moved 5.13->3.38 (-34.1%) on this date. Explained by a real "
        "2-for-3 bonus issue (extracted_facts.fact_id=350, price-adjustment factor 0.60, "
        "AGM/markdown 2023-11-13) -- both ngx_pricelist_v2 (this platform's primary "
        "reference) and NGX Pulse show this IDENTICAL raw, unadjusted jump, confirming "
        "NEITHER source retroactively adjusts historical closes for bonus/scrip issues. "
        "Any raw-return calculation spanning this date will show a spurious ~34% one-day "
        "loss that is not a real economic loss. See docs/fre_runs/"
        "ngxpulse_cross_validation_report.md Section 5, Cause context, and the platform's "
        "own prior docs/METHODOLOGY_HARDENING_2026-08-04.md (this is the exact "
        "'bonus/scrip-issue price-adjustment gap' that document flagged as real but "
        "'not numerically quantified' -- now quantified with a clean, confirmed example.",
        1)

    # --- OPEN: REDSTAREX genuine multi-day stale-price carryforward in NGX
    # Pulse specifically (ngx_pricelist_v2 shows real day-to-day movement
    # during the same window). -------------------------------------------------
    log("stale_series", "REDSTAREX", "2026-05-11", "warn",
        "NGX Pulse (source=ngx_pulse) shows a real stale-price-carryforward pattern "
        "2026-05-07 to 2026-05-15 -- several individual days repeat the prior day's "
        "close (e.g. 05-11 close 25.05 exactly equals 05-08's close) one real trading "
        "day behind where ngx_pricelist_v2 (this platform's own reference) already shows "
        "movement, before both sources reconverge by 05-18. Not explained by any "
        "corporate action (checked, none found for REDSTAREX in this window). OPEN: not "
        "yet bounded across the full universe -- only directly observed for this one "
        "lower-liquidity ticker. See docs/fre_runs/ngxpulse_cross_validation_report.md "
        "Section 5, Cause A.",
        0)

    # --- OPEN: single-day date-attribution drift pattern (NESTLE example). -
    log("date_attribution_drift", "NESTLE", "2025-05-19", "warn",
        "NGX Pulse attributes a real close-price move (1331.0 -> 1464.1) to 2025-05-19; "
        "ngx_pricelist_v2 attributes the identical move to 2025-05-20, one real trading "
        "day later. Both values are real (appear in both series on adjacent dates) -- "
        "this is a date-CONVENTION difference, not a wrong price. OPEN: only 2 of 124 "
        "real MATERIAL_DIFFERENCE observations were individually traced to a root cause "
        "this pass (this one, and the REDSTAREX staleness pattern); the remaining ~122 "
        "are logged in bulk below, not individually. See docs/fre_runs/"
        "ngxpulse_cross_validation_report.md Section 5, Cause B.",
        0)

    # --- OPEN, bulk: the remaining untraced material differences ------------
    log("unresolved_material_difference", "MULTIPLE", None, "info",
        "122 of 124 real MATERIAL_DIFFERENCE observations found in the 2026-08-10 "
        "ngx_pulse vs ngx_pricelist_v2 cross-validation (19,905 overlapping "
        "observations across 12 tickers) were NOT individually traced to a specific "
        "root cause beyond the two general patterns logged separately (stale_series, "
        "date_attribution_drift). Full detail: data/raw/cross_validation_full_overlap.csv "
        "(all rows) and docs/fre_runs/ngxpulse_cross_validation_report.md. Marked "
        "unresolved, not assumed benign.",
        0)

    con.commit()
    print(f"{inserted} data_quality_log rows inserted.")

    total = con.execute("SELECT COUNT(*) FROM data_quality_log").fetchone()[0]
    print(f"data_quality_log now has {total} total rows.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
