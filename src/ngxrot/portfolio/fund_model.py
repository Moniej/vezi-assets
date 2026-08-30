"""Phase 11: Institutional / Fund Foundation -- DATA MODEL ONLY
(2026-08-12, BUILD ASSIGNMENT).

NOT LIVE. NOT REGULATED. NOT INVESTOR-READY. NOT CONNECTED TO EXTERNAL
CAPITAL. Every table this module writes to (funds, strategies, accounts,
investors, capital_allocations, fee_schedules) has a CHECK constraint in
schema/portfolio.sql restricting `status` to exactly one placeholder value
(e.g. funds.status can ONLY be 'CONCEPTUAL' -- the schema itself refuses
any other value, not just this module's own discipline). Going live is
therefore a DELIBERATE future schema migration, never a value reachable
from this build.

This module intentionally does NOT build: fundraising systems, LP
dashboards, compliance workflows, investor onboarding, fund
administration, or broker integration -- per the build assignment's
explicit instruction not to spend time there "until a capacity-viable
strategy exists." What exists here is the minimum data shape so that day,
if it comes, doesn't require another schema migration to represent a
fund/strategy/account/investor/capital-allocation/fee-schedule at all.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def create_fund(con: sqlite3.Connection, name: str, base_currency: str = "NGN") -> str:
    fund_id = f"FUND-{uuid.uuid4()}"
    con.execute("INSERT INTO funds (fund_id, name, status, base_currency, created_at) "
               "VALUES (?,?,?,?,?)",
               (fund_id, name, "CONCEPTUAL", base_currency,
                datetime.now(timezone.utc).isoformat(timespec="seconds")))
    con.commit()
    return fund_id


def create_strategy(con: sqlite3.Connection, name: str, hypothesis_ids: list[str],
                    fund_id: str | None = None) -> str:
    import json
    strategy_id = f"STRAT-{uuid.uuid4()}"
    con.execute("INSERT INTO strategies (strategy_id, fund_id, name, hypothesis_ids_json, "
               "status, created_at) VALUES (?,?,?,?,?,?)",
               (strategy_id, fund_id, name, json.dumps(hypothesis_ids), "RESEARCH",
                datetime.now(timezone.utc).isoformat(timespec="seconds")))
    con.commit()
    return strategy_id


def create_account(con: sqlite3.Connection, portfolio_id: str, fund_id: str | None = None) -> str:
    account_id = f"ACCT-{uuid.uuid4()}"
    con.execute("INSERT INTO accounts (account_id, fund_id, portfolio_id, account_type, created_at) "
               "VALUES (?,?,?,?,?)",
               (account_id, fund_id, portfolio_id, "SIMULATED",
                datetime.now(timezone.utc).isoformat(timespec="seconds")))
    con.commit()
    return account_id


def create_placeholder_investor(con: sqlite3.Connection, name: str) -> str:
    """A PLACEHOLDER investor record -- explicitly not a real onboarded
    person or entity. Exists only so capital_allocations has something
    legal to reference."""
    investor_id = f"INV-{uuid.uuid4()}"
    con.execute("INSERT INTO investors (investor_id, name, status, created_at) VALUES (?,?,?,?)",
               (investor_id, name, "PLACEHOLDER",
                datetime.now(timezone.utc).isoformat(timespec="seconds")))
    con.commit()
    return investor_id


def create_fee_schedule(con: sqlite3.Connection, fund_id: str, management_fee_pct: float = 0.0,
                        performance_fee_pct: float = 0.0) -> str:
    fee_schedule_id = f"FEE-{uuid.uuid4()}"
    con.execute(
        "INSERT INTO fee_schedules (fee_schedule_id, fund_id, management_fee_pct, "
        "performance_fee_pct, high_water_mark, status, notes) VALUES (?,?,?,?,?,?,?)",
        (fee_schedule_id, fund_id, management_fee_pct, performance_fee_pct, 1, "CONCEPTUAL",
         "NOT LIVE. NOT REGULATED. NOT INVESTOR-READY. NOT CONNECTED TO EXTERNAL CAPITAL."))
    con.commit()
    return fee_schedule_id
