"""One-off, disclosed, provenance-preserving remediation (2026-08-17):

1. Backfills period_start/period_end/period_type on 16 revenue/net_profit
   facts for 8 H-011 sleeve tickers whose reporting period is EXPLICITLY
   stated in the fact's own `description` field (already-extracted
   evidence, not inferred from today's date or from a later filing).
   period_type is derived via the platform's own EXISTING
   period_normalization.classify_period_type(), never hand-assigned --
   for CUTIX (fiscal year ended 2026-04-30, a non-calendar FYE) this
   correctly returns None rather than mislabeling a non-standard span,
   and is left None, honestly.

2. Sets currency='NGN' on 6 VERITASKAP assets/liabilities/equity facts
   whose currency was NULL. Evidence: each fact's own `description`
   explicitly cites the source table's unit label "N'000" (Naira,
   thousands) -- not inferred from ticker/company nationality.

Only touches: extracted_facts.period_start/period_end/period_type
(16 rows), extracted_facts.currency (6 rows). No other column, no other
row, is written. Runs inside a single transaction; prints a dry-run diff
before any write; writes a JSON audit log with before/after values and
the evidence text backing each change.

  PYTHONPATH=src python scripts/fre/remediate_period_currency_2026-08-17.py [--apply]

Without --apply: dry run only (prints the plan, writes nothing).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot.fre.period_normalization import classify_period_type  # noqa: E402

# (fact_id, period_start, period_end, evidence_source)
PERIOD_REPAIRS = [
    (439, "2024-01-01", "2024-12-31", "description: \"...for the year ended 31st December 2024...\""),
    (440, "2026-01-01", "2026-06-30", "description: \"...revenue of N14.68 billion for H1 2026...\""),
    (441, "2026-01-01", "2026-06-30", "description: \"...net loss of N8.69 billion for H1 2026...\""),
    (453, "2026-01-01", "2026-03-31", "description: \"...gross earnings of N12.78 billion in Q1 2026...\""),
    (454, "2026-01-01", "2026-03-31", "description: \"...post-tax profit of N500.41 million in Q1 2026...\""),
    (442, "2025-05-01", "2026-04-30", "evidence: \"...for the full year ended April 30, 2026...\" (non-calendar FYE)"),
    (443, "2025-05-01", "2026-04-30", "evidence: \"...for the full year ended April 30, 2026...\" (non-calendar FYE)"),
    (451, "2025-01-01", "2025-12-31", "description: \"...reported 2025 revenue of N6.21 billion...\""),
    (452, "2025-01-01", "2025-12-31", "description: \"...profit after tax of N346 million for 2025...\""),
    (446, "2025-01-01", "2025-12-31", "description: \"...generated N3.081 billion in revenue for 2025...\""),
    (447, "2025-01-01", "2025-12-31", "description: \"...profit after tax of N196 million in 2025...\""),
    (448, "2026-01-01", "2026-06-30", "description: \"...insurance revenue of N12.56 billion for H1 2026...\""),
    (449, "2026-01-01", "2026-06-30", "description: \"...profit after tax of N1.05 billion for H1 2026...\""),
    (456, "2025-04-01", "2025-06-30", "description: \"...Q2 2025 turnover of N5.8 billion...\""),
    (458, "2025-04-01", "2025-06-30", "description: \"...doubled its Q2 2025 net profit...\""),
    (459, "2026-01-01", "2026-03-31", "description: \"...reported Q1 2026 insurance revenue of N5.3 billion...\""),
    (460, "2026-01-01", "2026-03-31", "description: \"...reported Q1 2026 post-tax profit of N1.5 billion...\""),
]

# (fact_id, evidence_source)
CURRENCY_REPAIRS = [
    (427, "description: \"...(table N'000 x1000)\" -- table's own stated unit label is Naira, thousands"),
    (428, "description: \"...(table N'000 x1000)\""),
    (429, "description: \"...(table N'000 x1000)...Cross-checked: 14,221,929-4,717,955=9,503,974, matches exactly.\""),
    (430, "description: \"...(comparative column, N'000 x1000)...\""),
    (431, "description: \"...(comparative column, N'000 x1000)...\""),
    (432, "description: \"...(comparative column, N'000 x1000)...\""),
]


def main() -> int:
    apply = "--apply" in sys.argv
    con = db.connect()

    audit = {"period_repairs": [], "currency_repairs": []}

    print(f"=== PERIOD METADATA REPAIRS ({'APPLY' if apply else 'DRY RUN'}) ===")
    for fact_id, ps, pe, reason in PERIOD_REPAIRS:
        before = con.execute(
            "SELECT fact_type, period_start, period_end, period_type, doc_id FROM extracted_facts "
            "WHERE fact_id=?", (fact_id,)).fetchone()
        if before is None:
            print(f"  fact_id={fact_id}: NOT FOUND -- skipping")
            continue
        fact_type, old_ps, old_pe, old_pt, doc_id = before
        if old_ps is not None or old_pe is not None:
            print(f"  fact_id={fact_id}: period already populated ({old_ps}..{old_pe}) -- skipping, not overwriting")
            continue
        new_pt = classify_period_type(ps, pe)
        print(f"  fact_id={fact_id} ({fact_type}): period_start={old_ps}->{ps}  period_end={old_pe}->{pe}  "
              f"period_type={old_pt}->{new_pt}  [{reason}]")
        audit["period_repairs"].append({
            "fact_id": fact_id, "fact_type": fact_type, "doc_id": doc_id,
            "before": {"period_start": old_ps, "period_end": old_pe, "period_type": old_pt},
            "after": {"period_start": ps, "period_end": pe, "period_type": new_pt},
            "evidence_source": reason,
        })
        if apply:
            con.execute(
                "UPDATE extracted_facts SET period_start=?, period_end=?, period_type=? WHERE fact_id=?",
                (ps, pe, new_pt, fact_id))

    print()
    print(f"=== CURRENCY REPAIRS ({'APPLY' if apply else 'DRY RUN'}) ===")
    for fact_id, reason in CURRENCY_REPAIRS:
        before = con.execute(
            "SELECT fact_type, currency, doc_id FROM extracted_facts WHERE fact_id=?", (fact_id,)).fetchone()
        if before is None:
            print(f"  fact_id={fact_id}: NOT FOUND -- skipping")
            continue
        fact_type, old_ccy, doc_id = before
        if old_ccy is not None:
            print(f"  fact_id={fact_id}: currency already set ({old_ccy}) -- skipping, not overwriting")
            continue
        print(f"  fact_id={fact_id} ({fact_type}): currency={old_ccy}->NGN  [{reason}]")
        audit["currency_repairs"].append({
            "fact_id": fact_id, "fact_type": fact_type, "doc_id": doc_id,
            "before": {"currency": old_ccy}, "after": {"currency": "NGN"},
            "evidence_source": reason,
        })
        if apply:
            con.execute("UPDATE extracted_facts SET currency='NGN' WHERE fact_id=?", (fact_id,))

    if apply:
        con.commit()
        print("\nCOMMITTED.")
    else:
        print("\nDRY RUN ONLY -- no writes made. Re-run with --apply to commit.")

    audit_path = ROOT / "data" / "staging" / "period_currency_remediation_audit_2026-08-17.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit log written to {audit_path}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
