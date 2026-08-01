"""Phase 1 smoke test: build the schema and prove the PIT guards work.

Uses synthetic rows (clearly marked, source=manual_seed) — no real market
data is loaded in Phase 1. Three lookahead traps are set; the test passes
only if all three are blocked.

Runs against a fresh SCRATCH database (db.new_scratch_db_path()), never the
real data/ngx.sqlite -- this script originally hardcoded the production path
and unconditionally unlinked it, which was harmless when first written (no
real data existed yet) but silently wiped the real, since-populated
production database when re-run on 2026-08-01
(docs/fre_runs/incident_2026-08-01_prod_db_wipe.md). Fixed, not just
patched: use the one sanctioned scratch-DB helper instead of hand-rolling
the path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ngxrot import db  # noqa: E402

DB_PATH = db.new_scratch_db_path()

con = db.init_db(DB_PATH)

tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
views = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
print("TABLES:", ", ".join(tables))
print("VIEWS: ", ", ".join(views))
print("indices seeded:", con.execute("SELECT COUNT(*) FROM indices").fetchone()[0])

# --- synthetic PIT traps -----------------------------------------------------
con.execute("INSERT INTO securities (ticker, name, board) VALUES ('ZENITHBANK','Zenith Bank Plc','premium')")
con.execute("INSERT INTO securities (ticker, name, board, delisting_date, delisting_reason) "
            "VALUES ('OANDO','Oando Plc','main', NULL, NULL)")

# Trap 1: index level restated later. On 2025-06-11 we knew 105000; on
# 2025-06-13 NGX restated it to 105500. A query as-of 2025-06-12 must return
# the ORIGINAL value.
con.executemany(
    "INSERT INTO index_levels (index_code, trade_date, close_value, source_id, as_of_date) "
    "VALUES (?,?,?,?,?)",
    [("NGXBNK", "2025-06-10", 105000.0, 1, "2025-06-11"),
     ("NGXBNK", "2025-06-10", 105500.0, 1, "2025-06-13")])

# Trap 2: membership change effective 2025-07-01 but only announced 2025-06-20.
# A query as-of 2025-06-15 must NOT show OANDO in the Oil & Gas index... and a
# membership record effective in the past but announced later must stay hidden
# until announcement.
con.execute(
    "INSERT INTO index_membership (index_code, ticker, effective_from, effective_to, "
    "announced_date, reason_in, source_id, as_of_date) "
    "VALUES ('NGXOILGAS','OANDO','2025-06-01',NULL,'2025-06-20','review_add',1,'2025-06-20')")

# Trap 3: recapitalisation deadline effective 2026-03-31, announced 2024-03-28.
# Visible from 2024-03-28 onward; a second event announced 2025-08-01 must be
# invisible on 2025-06-15.
con.executemany(
    "INSERT INTO events (event_type, announced_date, effective_date, scope, index_code, "
    "headline, structurally_impairing, source_id, as_of_date) VALUES (?,?,?,?,?,?,?,?,?)",
    [("recapitalisation_directive", "2024-03-28", "2026-03-31", "sector", "NGXBNK",
      "CBN raises minimum capital for international banks to N500bn", 1, 1, "2024-03-28"),
     ("sec_directive", "2025-08-01", "2025-08-01", "sector", "NGXINS",
      "Hypothetical future directive (trap row)", 0, 1, "2025-08-01")])
con.commit()

print("\n--- PIT trap results (knowledge_date = 2025-06-15 unless noted) ---")

lv = db.index_levels_asof(con, "2025-06-12", ["NGXBNK"], vintage="2025-06-12")
v1 = lv.loc[lv.trade_date == "2025-06-10", "close_value"].iloc[0]
lv2 = db.index_levels_asof(con, "2025-06-14", ["NGXBNK"], vintage="2025-06-14")
v2 = lv2.loc[lv2.trade_date == "2025-06-10", "close_value"].iloc[0]
ok1 = (v1 == 105000.0) and (v2 == 105500.0)
print(f"Trap 1 (restatement): vintage 06-12 -> {v1:.0f}, vintage 06-14 -> {v2:.0f}  "
      f"{'BLOCKED OK' if ok1 else 'LOOKAHEAD LEAK'}")

m_before = db.membership_asof(con, "NGXOILGAS", "2025-06-15")
m_after = db.membership_asof(con, "NGXOILGAS", "2025-06-21")
ok2 = m_before.empty and (len(m_after) == 1)
print(f"Trap 2 (late-announced membership): visible before announce={len(m_before)}, "
      f"after={len(m_after)}  {'BLOCKED OK' if ok2 else 'LOOKAHEAD LEAK'}")

ev = db.events_asof(con, "2025-06-15")
ok3 = (len(ev) == 1) and (ev.iloc[0].event_type == "recapitalisation_directive")
print(f"Trap 3 (future event hidden): {len(ev)} event(s) visible, "
      f"first={ev.iloc[0].headline[:45]}...  {'BLOCKED OK' if ok3 else 'LOOKAHEAD LEAK'}")

print("\n--- Cost schedule as of 2025-06-15 (all rates ASSUMED, must be confirmed) ---")
print(db.cost_schedule_asof(con, "2025-06-15").to_string(index=False))

fees = db.cost_schedule_asof(con, "2025-06-15")
tv = fees[fees.applies_to == "trade_value"]
buy = tv[tv.side.isin(["buy", "both"])].rate_pct.sum()
sell = tv[tv.side.isin(["sell", "both"])].rate_pct.sum()
vat = fees[fees.fee_name == "vat"].rate_pct.iloc[0] / 100
vatable_buy = tv[(tv.side.isin(["buy", "both"])) & (tv.fee_name.isin(["brokerage", "cscs_fee"]))].rate_pct.sum()
vatable_sell = tv[(tv.side.isin(["sell", "both"])) & (tv.fee_name.isin(["brokerage", "cscs_fee"]))].rate_pct.sum()
rt = buy + sell + vat * (vatable_buy + vatable_sell)
print(f"\nImplied ROUND-TRIP cost at max brokerage: ~{rt:.2f}% of trade value")
print("(This is the hurdle each rotation must clear. Monthly full rotation at "
      "these rates costs ~%.0f%%+ per year before any alpha.)" % (rt * 12 / 2))

sys.exit(0 if (ok1 and ok2 and ok3) else 1)
