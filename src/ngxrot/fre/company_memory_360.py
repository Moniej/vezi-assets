"""FSI Phase 6: Unified Point-in-Time Company Memory
(docs/fre_runs/fsi_phase6_preregistration.md).

A pure, read-only COMPOSITION layer over two already-frozen, already-
tested PIT-safe modules -- FRE-3's `company_memory.build_company_memory()`
(dividend/corporate-action/filing/management/event history) and FSI
Phase 4's `pit_financial_memory.as_of()` (ratio/trend/flag conclusions).
Neither underlying module is modified, forked, or reimplemented here --
this module calls both, unmodified, and returns their results together.

No new fact, no new computation, no new inference, no synthesized field
of any kind -- in particular, NO combined "health score," "rating," or
"summary" is ever produced. Both source objects are returned exactly as
their own modules build them, so every existing guarantee (provenance,
confidence, PIT cutoff) each already provides is inherited unchanged,
not re-derived.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.company_memory import CompanyMemory, build_company_memory
from ngxrot.fre.pit_financial_memory import CompanyFinancialReasoningSnapshot, as_of as financial_as_of


@dataclass
class CompanyMemory360:
    ticker: str
    as_of_date: str
    corporate: CompanyMemory
    financial: CompanyFinancialReasoningSnapshot


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyMemory360:
    """Single-ticker only (mirrors the guardrail already enforced in both
    underlying modules): calls `build_company_memory()` and
    `pit_financial_memory.as_of()` for the SAME (ticker, as_of_date) and
    returns both results, unmodified, side by side. No default for
    as_of_date, matching both underlying modules' own convention."""
    corporate = build_company_memory(con, ticker, as_of_date)
    financial = financial_as_of(con, ticker, as_of_date)
    return CompanyMemory360(
        ticker=ticker, as_of_date=as_of_date, corporate=corporate, financial=financial,
    )
