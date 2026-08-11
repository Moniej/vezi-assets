"""FRE-7B.1: correction for a real, disclosed finding in FRE-7B's audit --
`financial_ratios.list_tickers()`'s own `CORP_ACTION_FACT_TYPES` exclusion
tuple (`('dividend', 'rights_issue', 'bonus_issue')`) does not include
`share_reconstruction`, a corporate-action/reconstruction event fact, not
a financial-statement metric. Two real tickers (NEM, TRANSCORP) have
exactly one `share_reconstruction` fact each and NO other non-corporate-
action fact -- `list_tickers()` counts them as "fact-bearing" anyway,
which silently misrepresented both tickers as having real
financial-statement data throughout FRE-6/FRE-7/FRE-7A.

## Why this is a NEW, additive module and not an edit to financial_ratios.py

`list_tickers()` lives in `financial_ratios.py`, part of the frozen
accounting core this stage is explicitly forbidden from modifying. The
smallest safe correction is therefore an ADDITIVE filter layered on top of
`list_tickers()`'s own (unmodified) output, in a separate module -- never
a change to the core's own exclusion tuple, its SQL, or its return value.
`list_tickers()` itself is regression-tested elsewhere
(`scripts/fre/test_financial_ratios.py`) to prove it is unchanged.

## Reproduction (verified directly, not assumed)

    SELECT COUNT(*) FROM extracted_facts f JOIN documents d ON d.doc_id=f.doc_id
    WHERE d.ticker='NEM' AND f.fact_type NOT IN ('dividend','rights_issue','bonus_issue')
    -- returns 1 (a single share_reconstruction fact)

Same for TRANSCORP. Both tickers have ZERO net_profit/equity/revenue/
assets/liabilities/ebit/ebitda/cfo/cfi/cff/capex/fcf/gross_profit/cogs
facts of any kind -- confirmed by direct query
(docs/fre_runs/fre7b_accounting_data_depth_audit.md Section 7).
"""
from __future__ import annotations

import sqlite3

from ngxrot.fre.financial_ratios import CORP_ACTION_FACT_TYPES, list_tickers

# share_reconstruction is a corporate-action/reconstruction EVENT
# (recorded alongside bonus_issue in every real bonus_split-doc_type
# filing observed on this platform -- see fre7b's own Part A query), not
# a financial-statement metric. Extending the exclusion set here, in this
# additive module only, never in financial_ratios.py's own tuple.
_NON_FINANCIAL_STATEMENT_FACT_TYPES = CORP_ACTION_FACT_TYPES + ("share_reconstruction",)


def list_genuine_financial_statement_tickers(con: sqlite3.Connection) -> list[str]:
    """Same contract as financial_ratios.list_tickers(), corrected to also
    exclude share_reconstruction-only tickers. Every ticker returned here
    has at least one REAL financial-statement-shaped fact (revenue,
    net_profit, equity, assets, liabilities, ebit, ebitda, or a cash-flow
    line item) -- never merely a corporate-action/reconstruction event."""
    rows = con.execute(
        "SELECT DISTINCT d.ticker FROM extracted_facts f JOIN documents d ON d.doc_id = f.doc_id "
        "WHERE f.fact_type NOT IN (?,?,?,?) AND d.ticker IS NOT NULL ORDER BY d.ticker",
        _NON_FINANCIAL_STATEMENT_FACT_TYPES,
    ).fetchall()
    return [r[0] for r in rows]


def share_reconstruction_only_tickers(con: sqlite3.Connection) -> list[str]:
    """The exact set list_tickers() over-counts: present in
    list_tickers()'s own output, absent from
    list_genuine_financial_statement_tickers()'s. Provided for audit/
    regression purposes, not for use as a filter itself."""
    broad = set(list_tickers(con))
    narrow = set(list_genuine_financial_statement_tickers(con))
    return sorted(broad - narrow)
